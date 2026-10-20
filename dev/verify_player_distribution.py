"""Check an extracted candidate in a fresh environment, with no inference or normal profile edits."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'dev')]
from check_user_test_release import check
from syx_chat_service import read_key_file


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(args):
    manifest=check(ROOT,args.candidate_dir,args.validation)
    base=Path(tempfile.mkdtemp(prefix='player-distribution-',dir=ROOT/'runtime'));os.chmod(base,0o700)
    client=base/'client';client.mkdir()
    archive=args.candidate_dir/'latest-user-test.zip'
    with zipfile.ZipFile(archive) as bundle:
        if args.env_file:
            key=read_key_file(args.env_file).encode()
            if not key or any(key in bundle.read(n) for n in bundle.namelist()):
                raise ValueError('Provided-key exclusion check failed')
        bundle.extractall(client)
    env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['KEY','TOKEN'])}
    env.pop('PYTHONPATH',None)
    def run(command):
        with (base/'setup.log').open('a') as log:
            subprocess.run(list(map(str,command)),cwd=client,env=env,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    run([sys.executable,'-m','venv',client/'.venv'])
    py=client/'.venv/bin/python'
    run([py,'-m','pip','install','-r',client/'requirements.txt'])
    run([py,client/'player.py','--check'])
    profile=base/'profile';run([py,client/'install-mod.py','--user-dir',profile])
    assert sha(profile/'mods/syx-ai-assistant/V71/script/syx-ai-assistant.jar')==manifest['mod_jar_sha256']
    fake=base/'fake.env'
    with os.fdopen(os.open(fake,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        f.write('DEEPSEEK_API_KEY=fixture-not-a-real-provider-key\n')
    state=base/'state';history=base/'history'
    with (base/'startup.log').open('w') as log:
        process=subprocess.Popen([str(py),str(client/'player.py'),'--env-file',str(fake),'--state-dir',str(state),'--history-dir',str(history)],cwd=client,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+30
            while not (state/'chat-ui.txt').exists():
                if process.poll() is not None:raise RuntimeError('Extracted launcher exited; inspect private startup log')
                if time.monotonic()>deadline:raise RuntimeError('Extracted launcher startup timeout')
                time.sleep(.2)
            text=(state/'chat-ui.txt').read_text()
            assert text.startswith('protocol=2\n') and '\nchat=' not in text
        finally:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    report=dict(passed=True,validated_at=datetime.now(timezone.utc).isoformat(),
        fresh_dependency_environment=True,extracted_check=True,extracted_helper_startup_no_inference=True,
        isolated_installer_jar_hash=True,provided_key_literal_absent_from_archive=bool(args.env_file),
        provider_calls=0,tested_pre_promotion_zip_sha256=sha(archive),tested_payload_files_sha256=manifest['files'],
        mod_jar_sha256=manifest['mod_jar_sha256'],
        production_source_sha256=manifest['validation']['production_source_sha256'],
        python_source_sha256=manifest['validation']['python_source_sha256'],
        verifier_source_sha256=sha(Path(__file__)),
        limits=['Fresh Linux Python environment and isolated temporary profile only; no physical input/all-platform acceptance.',
            'Fake startup credential never sent to provider; actual paid/native acceptance is reported separately.',
            'Container hash records this test archive. Final evidence metadata may change BUILD.json; payload file hashes must remain identical at promotion.'])
    output=base/'distribution-validation.json';output.write_text(json.dumps(report,indent=2)+'\n')
    print('Fresh extracted candidate checks passed:',output,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate-dir',type=Path,required=True);p.add_argument('--validation',type=Path,required=True)
    p.add_argument('--env-file',type=Path,help='Optional private key-exclusion check only; never sent to a provider')
    verify(p.parse_args())
