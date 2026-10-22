"""Publish a credential-free player ZIP only from a matching, validated mod build.

A failed candidate leaves latest-user-test.zip untouched. The previous working
ZIP remains downloadable as previous-user-test.zip when a new one is promoted.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parent
MODULES=['syx_blueprints','syx_blueprint_data','syx_blueprint_tools','syx_blueprint_chat','syx_housing','syx_mcp','syx_knowledge','syx_query','syx_api_support','syx_api_manifest','syx_live',
    'syx_capture','syx_tiles','syx_regions','syx_stockpiles','syx_chat_store','syx_deepseek','syx_chat','syx_chat_service','syx_claude','syx_claude_worker']


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def package(jar,validation,output):
    report=json.loads(validation.read_text())
    if not report.get('passed') or not report.get('real_provider_round_trip') or report.get('requested_model')!='deepseek-v4-pro':
        raise ValueError('A passing DeepSeek Pro user-test report is required')
    if report.get('mod_jar_sha256')!=digest(jar):raise ValueError('Mod JAR differs from the validated build')
    sources={str(p.relative_to(ROOT/'mod/src/main/java')) for p in (ROOT/'mod/src/main/java').rglob('*.java')}
    if set(report['production_source_sha256'])!=sources:raise ValueError('Incomplete production source evidence')
    for name,expected in report['production_source_sha256'].items():
        if digest(ROOT/'mod/src/main/java'/name)!=expected:raise ValueError('Game source changed since validation')
    for module in MODULES:
        if report['python_source_sha256'].get(module+'.py')!=digest(ROOT/(module+'.py')):
            raise ValueError('Chat source changed since validation: '+module)
    with zipfile.ZipFile(jar) as compiled:
        if any(not n.startswith('syx/assistant/') or not n.endswith('.class') for n in compiled.namelist()):
            raise ValueError('Mod archive contains unexpected files')
    output.mkdir(parents=True,exist_ok=True)
    candidate=output/'candidate-user-test.zip'
    files={module+'.py':ROOT/(module+'.py') for module in MODULES}
    files.update({n:ROOT/'user_test'/n for n in ['start-chat.sh','player.py','install-mod.py','requirements.txt','README.txt']})
    files['mod/syx-ai-assistant/V71/script/syx-ai-assistant.jar']=jar
    files['mod/syx-ai-assistant/_Info.txt']=jar.parents[2]/'_Info.txt'
    manifest={'builder_source_sha256':digest(ROOT/'build_mod.py'),'packager_source_sha256':digest(ROOT/'make_user_test.py'),'built_at':datetime.now(timezone.utc).isoformat(),'model':'deepseek-v4-pro','platform':'Linux',
        'game_version':'0.71.44','mod_jar_sha256':digest(jar),'files':{n:digest(p) for n,p in files.items()},
        'validation':report,'run_instructions':'README.txt'}
    with zipfile.ZipFile(candidate,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100755 if name.endswith('.sh') else 0o100644)<<16
            archive.writestr(info,path.read_bytes())
        archive.writestr('BUILD.json',json.dumps(manifest,indent=2)+'\n')
    latest=output/'latest-user-test.zip'
    if latest.exists():shutil.copy2(latest,output/'previous-user-test.zip')
    candidate.replace(latest)
    (output/'latest-user-test.json').write_text(json.dumps({**manifest,'download_sha256':digest(latest)},indent=2)+'\n')
    return latest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mod-jar',type=Path,required=True);p.add_argument('--validation',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'releases');args=p.parse_args()
    print(package(args.mod_jar,args.validation,args.output))
