"""Detached status text bounds; native scroll/layout remains a separate fixture."""
import os
from pathlib import Path
import subprocess


def test_status_wrapping_bounds_and_unicode(tmp_path):
    root = Path(__file__).resolve().parent
    compiler = ['java']
    if os.environ.get('SYX_JAVA_HOME'):
        compiler += ['-Djava.home=' + os.environ['SYX_JAVA_HOME']]
    sources = [root / 'dev/java/syx/assistant/candidate' / n for n in ['StatusLines.java', 'StatusLinesProbe.java']]
    subprocess.run([*compiler, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '16',
                    '-d', str(tmp_path), *map(str, sources)], capture_output=True, check=True, timeout=30)
    result = subprocess.run(['java', '-cp', str(tmp_path), 'syx.assistant.candidate.StatusLinesProbe'],
                            capture_output=True, text=True, check=True, timeout=30)
    assert result.stdout.startswith('PASS bounded status rows')
