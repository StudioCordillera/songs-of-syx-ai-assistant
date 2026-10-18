"""Independent Sign in with ChatGPT public-client registration for this local app.

Never reads Codex/ChatGPT credentials. Tokens live outside game exports and chat logs.
Official flow: https://developers.openai.com/siwc/token-sharing-open-source/sign-in
"""
import argparse
import asyncio
import base64
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import parse_qs,urlencode,urlsplit
from uuid import uuid4

import httpx
import jwt

ISSUER='https://auth.openai.com'
AUTHORIZE=ISSUER+'/api/accounts/authorize'
TOKEN=ISSUER+'/api/accounts/oauth/token'
JWKS=ISSUER+'/.well-known/jwks.json'
RESOURCE='https://api.openai.com/v1'
SCOPES='openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'


class SignInError(ValueError):pass
class SignInDenied(SignInError):pass


def atomic_private(path,value):
    temporary=path.with_name(path.name+'.'+str(uuid4())+'.tmp')
    fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as file:
            json.dump(value,file,ensure_ascii=False,allow_nan=False);file.flush();os.fsync(file.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def private_json(path,limit=65536):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as file:raw=file.read(limit+1)
    if len(raw)>limit:raise SignInError('Local credential record exceeds bounds')
    return json.loads(raw)


class ChatGPTSignIn:
    def __init__(self,directory):
        self.directory=Path(directory).expanduser()
        if self.directory.is_symlink():raise SignInError('Auth directory cannot be a symlink')
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700);self.directory.chmod(0o700)
        host=self.directory/'host.json'
        if not host.exists():atomic_private(host,{'host_id':'urn:uuid:'+str(uuid4())})
        self.host_id=private_json(host)['host_id']
        if not re.fullmatch(r'urn:uuid:[0-9a-f-]{36}',self.host_id):raise SignInError('Invalid saved host identity')

    def prepare(self,redirect_uri,client_id=None,id_token_hint=None,subject=None):
        parsed=urlsplit(redirect_uri)
        if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.path!='/auth/callback' or not parsed.port or parsed.query or parsed.fragment or parsed.username:
            raise SignInError('An exact IPv4 loopback callback is required')
        if client_id=='dynamic_agent_client':raise SignInError('The dynamic registration entrypoint is not a saved client ID')
        verifier=secrets.token_urlsafe(48)
        pending=dict(state=secrets.token_urlsafe(32),nonce=secrets.token_urlsafe(32),verifier=verifier,redirect_uri=redirect_uri,
            client_id=client_id,subject=subject,started=time.monotonic())
        params=dict(client_id=client_id or 'dynamic_agent_client',ext_agent_host_id=self.host_id,response_type='code',redirect_uri=redirect_uri,
            scope=SCOPES,resource=RESOURCE,state=pending['state'],nonce=pending['nonce'],code_challenge_method='S256',
            code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode())
        if not client_id:params['agent_name_hint']='Songs of Syx AI Assistant'
        elif id_token_hint:params['id_token_hint']=id_token_hint
        return pending,AUTHORIZE+'?'+urlencode(params)

    @staticmethod
    def callback(pending,query):
        if time.monotonic()-pending['started']>300:raise SignInError('Sign-in attempt expired')
        values=parse_qs(query,keep_blank_values=True,max_num_fields=12)
        if any(len(v)!=1 for v in values.values()):raise SignInError('Duplicate callback fields')
        state=values.get('state',[''])[0]
        if not hmac.compare_digest(state,pending['state']):raise SignInError('Sign-in state did not match')
        if 'error' in values:raise SignInDenied('Sign-in was declined or failed; no token exchange attempted')
        client=values.get('client_id',[pending['client_id']])[0]
        if not isinstance(client,str) or client=='dynamic_agent_client' or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',client):raise SignInError('Registration did not return an issued client ID')
        if pending['client_id'] and client!=pending['client_id']:raise SignInError('Returning registration changed client identity')
        code=values.get('code',[''])[0]
        if not code or len(code)>8192:raise SignInError('Authorization code missing or too large')
        return client,code

    @staticmethod
    def validate(tokens,keys,pending,client_id):
        try:
            raw=tokens['id_token'];header=jwt.get_unverified_header(raw)
            if header.get('alg')!='RS256':raise SignInError('Unsupported identity token signature')
            candidates=[key for key in keys['keys'] if key.get('kid')==header.get('kid')]
            if len(candidates)!=1:raise SignInError('Identity signing key unavailable')
            key=jwt.PyJWK.from_dict(candidates[0]).key
            claims=jwt.decode(raw,key,algorithms=['RS256'],audience=client_id,issuer=ISSUER,
                options={'require':['exp','iat','sub','iss','aud','nonce']})
            if not isinstance(claims['nonce'],str) or not hmac.compare_digest(claims['nonce'],pending['nonce']):raise SignInError('Identity nonce did not match')
            if not isinstance(claims['sub'],str) or not claims['sub']:raise SignInError('Missing verified account identity')
            if pending['subject'] and claims['sub']!=pending['subject']:raise SignInError('Sign-in returned a different account')
            scopes=tokens.get('scope','').split()
            if 'chatgpt.tokens.use.direct' not in scopes or 'resource.invoke' not in scopes:raise SignInError('ChatGPT plan permission was not granted')
            if tokens.get('token_type','').lower()!='bearer' or not isinstance(tokens.get('access_token'),str) or not tokens['access_token']:raise SignInError('Invalid bearer credential response')
            if type(tokens.get('expires_in')) is not int or not 0<tokens['expires_in']<=2592000:raise SignInError('Invalid credential expiry')
            return claims,scopes
        except SignInError:raise
        except Exception:raise SignInError('Identity token or granted permissions could not be verified') from None

    async def exchange(self,pending,client_id,code,client=None):
        owned=client is None;client=client or httpx.AsyncClient(timeout=20,follow_redirects=False)
        try:
            response=await client.post(TOKEN,data=dict(grant_type='authorization_code',client_id=client_id,code=code,
                code_verifier=pending['verifier'],redirect_uri=pending['redirect_uri'],resource=RESOURCE))
            if response.status_code!=200:raise SignInError('Code exchange failed; begin a new sign-in attempt')
            if len(response.content)>65536:raise SignInError('Token response exceeds bounds')
            tokens=response.json()
            response=await client.get(JWKS)
            if response.status_code!=200 or len(response.content)>262144:raise SignInError('Official identity signing keys unavailable')
            claims,scopes=self.validate(tokens,response.json(),pending,client_id)
            record=dict(issuer=ISSUER,subject=claims['sub'],email=claims.get('email'),client_id=client_id,ext_agent_host_id=self.host_id,
                id_token=tokens['id_token'],access_token=tokens['access_token'],refresh_token=tokens.get('refresh_token'),
                token_type='Bearer',scopes=scopes,saved_at=time.time(),expires_in=tokens['expires_in'])
            name=hashlib.sha256((client_id+'\0'+claims['sub']).encode()).hexdigest()+'.json'
            atomic_private(self.directory/name,record)
            return self.directory/name
        except SignInError:raise
        except (ValueError,TypeError,KeyError):raise SignInError('Official credential response could not be validated') from None
        except httpx.HTTPError:raise SignInError('Official sign-in connection failed; no alternate endpoint attempted') from None
        finally:
            if owned:await client.aclose()

    async def login(self,on_url,client_id=None,id_token_hint=None,subject=None):
        loop=asyncio.get_running_loop();completed=loop.create_future();holder={}
        class Callback(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):
                valid=False;result=None;denied=None
                try:
                    if len(self.path)>16384:raise SignInError('Callback exceeds bounds')
                    target=urlsplit(self.path)
                    if self.headers.get('Host')!='127.0.0.1:'+str(self.server.server_port) or target.path!='/auth/callback':raise SignInError('Unexpected callback target')
                    result=ChatGPTSignIn.callback(holder['pending'],target.query);valid=True
                except SignInDenied as error:denied=error
                except Exception:pass
                body=b'Sign-in received. You may return to the assistant.' if valid else b'Sign-in callback rejected. Return to the assistant and retry.'
                self.send_response(200 if valid else 400);self.send_header('Content-Type','text/plain; charset=utf-8')
                self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                if valid or denied:
                    def resolve():
                        if not completed.done():
                            if denied:completed.set_exception(denied)
                            else:completed.set_result(result)
                    loop.call_soon_threadsafe(resolve)
        class LoopbackServer(HTTPServer):
            def get_request(self):
                sock,address=super().get_request();sock.settimeout(2);return sock,address
        server=LoopbackServer(('127.0.0.1',0),Callback)
        pending,url=self.prepare('http://127.0.0.1:'+str(server.server_port)+'/auth/callback',client_id,id_token_hint,subject)
        holder['pending']=pending
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.05),daemon=True);thread.start()
        try:
            on_url(url)
            try:issued,code=await asyncio.wait_for(completed,300)
            except TimeoutError:raise SignInError('Sign-in timed out; no credentials saved') from None
            return await self.exchange(pending,issued,code)
        finally:server.shutdown();server.server_close();thread.join(timeout=1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--auth-dir',default=str(Path.home()/'.local/share/syx-assistant-auth'))
    args=parser.parse_args()
    async def run():
        auth=ChatGPTSignIn(args.auth_dir)
        def show(url):print(json.dumps({'event':'authorize','url':url}),flush=True)
        try:
            path=await auth.login(show)
            print(json.dumps({'event':'connected','credential_record':path.name,'plan_permission_verified':True}),flush=True)
        except SignInError as error:print(json.dumps({'event':'not_connected','message':str(error)}),flush=True)
    asyncio.run(run())


if __name__=='__main__':main()
