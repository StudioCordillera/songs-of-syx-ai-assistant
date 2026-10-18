import asyncio
import base64
import hashlib
import json
import stat
import time
from urllib.parse import parse_qs,urlencode,urlsplit

from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
import jwt
import pytest

from syx_openai_auth import ChatGPTSignIn,SignInError,SignInDenied,ISSUER,TOKEN,JWKS


def fixture(tmp_path):
    auth=ChatGPTSignIn(tmp_path/'auth')
    pending,url=auth.prepare('http://127.0.0.1:1455/auth/callback')
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()));jwk['kid']='test-key'
    claims=dict(iss=ISSUER,aud='issued-client',sub='test-subject',nonce=pending['nonce'],iat=int(time.time()),exp=int(time.time())+300)
    def tokens(**change):
        body={**claims,**change}
        return dict(id_token=jwt.encode(body,key,algorithm='RS256',headers={'kid':'test-key'}),access_token='test-access',refresh_token='test-refresh',token_type='Bearer',expires_in=3600,scope='resource.invoke chatgpt.tokens.use.direct')
    return auth,pending,url,tokens,{'keys':[jwk]}


def test_host_pkce_and_callback_identity(tmp_path):
    auth,pending,url,tokens,keys=fixture(tmp_path)
    assert ChatGPTSignIn(tmp_path/'auth').host_id==auth.host_id
    params=parse_qs(urlsplit(url).query)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(pending['verifier'].encode()).digest()).rstrip(b'=').decode()
    assert params['code_challenge']==[challenge] and params['client_id']==['dynamic_agent_client']
    assert 'verifier' not in params
    query=urlencode(dict(code='code',state=pending['state'],client_id='issued-client'))
    assert auth.callback(pending,query)==('issued-client','code')
    for value in [query+'&state=duplicate',query.replace(pending['state'],'bad'),urlencode(dict(code='code',state=pending['state']))]:
        with pytest.raises(SignInError):auth.callback(pending,value)
    with pytest.raises(SignInDenied):auth.callback(pending,urlencode(dict(error='access_denied',state=pending['state'])))
    returning,_=auth.prepare(pending['redirect_uri'],client_id='issued-client',subject='test-subject')
    with pytest.raises(SignInError):auth.callback(returning,urlencode(dict(code='code',state=returning['state'],client_id='different-client')))
    assert stat.S_IMODE((tmp_path/'auth').stat().st_mode)==0o700


@pytest.mark.parametrize('change',[{'aud':'wrong'},{'iss':'wrong'},{'nonce':'wrong'},{'exp':1},{'sub':''},{'iat':int(time.time())+3600}])
def test_identity_validation_rejects_wrong_claims(tmp_path,change):
    auth,pending,url,tokens,keys=fixture(tmp_path)
    with pytest.raises(SignInError):auth.validate(tokens(**change),keys,pending,'issued-client')


def test_scope_signature_and_subject_are_required(tmp_path):
    auth,pending,url,tokens,keys=fixture(tmp_path)
    good=tokens();claims,scopes=auth.validate(good,keys,pending,'issued-client');assert claims['sub']=='test-subject'
    for changes in [dict(scope='openid email'),dict(token_type='Basic'),dict(expires_in=-1),dict(access_token=''),dict(id_token='malformed')]:
        with pytest.raises(SignInError):auth.validate({**good,**changes},keys,pending,'issued-client')
    with pytest.raises(SignInError):auth.validate(good,{'keys':[]},pending,'issued-client')
    with pytest.raises(SignInError):auth.validate(good,keys,{**pending,'subject':'other-account'},'issued-client')


def test_exchange_validates_before_private_storage(tmp_path):
    async def run():
        auth,pending,url,tokens,keys=fixture(tmp_path);seen=[]
        def handle(request):
            seen.append(request)
            return httpx.Response(200,json=tokens() if str(request.url)==TOKEN else keys)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            path=await auth.exchange(pending,'issued-client','test-code',client)
        record=json.loads(path.read_text());assert record['subject']=='test-subject'
        assert record['ext_agent_host_id']==auth.host_id
        assert stat.S_IMODE(path.stat().st_mode)==0o600
        assert parse_qs(seen[0].content.decode())['code_verifier']==[pending['verifier']]
        assert [str(r.url) for r in seen]==[TOKEN,JWKS]
        assert not (auth.directory/'active.json').exists() # No implicit account switch.
    asyncio.run(run())


def test_loopback_denial_stops_attempt(tmp_path):
    async def run():
        auth=ChatGPTSignIn(tmp_path/'auth');ready=asyncio.Queue()
        task=asyncio.create_task(auth.login(ready.put_nowait))
        url=await ready.get();params=parse_qs(urlsplit(url).query)
        callback=params['redirect_uri'][0]+'?'+urlencode(dict(error='access_denied',state=params['state'][0]))
        async with httpx.AsyncClient(trust_env=False) as client:
            response=await client.get(callback)
        assert response.status_code==400
        with pytest.raises(SignInDenied):await asyncio.wait_for(task,2)
        assert list(auth.directory.glob('*.json'))==[auth.directory/'host.json']
    asyncio.run(run())


def test_invalid_exchange_never_saves_or_echoes_tokens(tmp_path):
    async def run():
        auth,pending,url,tokens,keys=fixture(tmp_path)
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(401,text='sensitive-server-body'))) as client:
            with pytest.raises(SignInError) as caught:await auth.exchange(pending,'issued-client','test-code',client)
            assert 'sensitive-server-body' not in str(caught.value)
        bad=tokens(nonce='wrong')
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,json=bad if str(request.url)==TOKEN else keys))) as client:
            with pytest.raises(SignInError):await auth.exchange(pending,'issued-client','test-code',client)
        assert list(auth.directory.glob('*.json'))==[auth.directory/'host.json']
    asyncio.run(run())
