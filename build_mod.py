"""Build against a user's licensed game jar; never copy it into the mod."""
import argparse
import os
import shutil
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).parent

def build(game_dir: Path, output: Path):
    game_jar = game_dir / 'SongsOfSyx.jar'
    if not game_jar.is_file():
        raise SystemExit('Expected SongsOfSyx.jar inside --game-dir')
    classes = ROOT / 'build' / 'java-classes'
    if classes.exists(): shutil.rmtree(classes)
    classes.mkdir(parents=True, exist_ok=True)
    sources = sorted((ROOT / 'mod' / 'src' / 'main' / 'java').rglob('*.java'))
    # Java 16 bytecode matches the installed game classes. Code uses no newer APIs.
    java = ['java']
    if os.environ.get('SYX_JAVA_HOME'):
        java += ['-Djava.home=' + os.environ['SYX_JAVA_HOME']]
    subprocess.run([*java, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '-encoding', 'UTF-8',
        '--release', '16', '-classpath', str(game_jar), '-d', str(classes),
        *map(str, sources)], check=True)
    mod = output / 'syx-ai-assistant'
    if mod.exists(): shutil.rmtree(mod)
    scripts = mod / 'V71' / 'script'
    scripts.mkdir(parents=True, exist_ok=True)
    jar = scripts / 'syx-ai-assistant.jar'
    with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(classes.rglob('*.class')):
            z.write(f, f.relative_to(classes))
    (mod / '_Info.txt').write_text('VERSION: "0.9.0",\nNAME: "Syx AI Assistant",\n'
        'DESC: "Local game-state bridge. Experimental. Targets 0.71.44.",\n'
        'AUTHOR: "StudioCordillera",\nINFO: "https://github.com/StudioCordillera/songs-of-syx-ai-assistant",\n')
    print(jar)
    return jar

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--game-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.game_dir, args.output)
