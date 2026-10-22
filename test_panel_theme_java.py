"""Detached palette math/strict input; no native pixels, game, provider or WCAG certification."""
import os
from pathlib import Path
import subprocess


def test_candidate_palette_validation_and_abstract_contrast(tmp_path):
    root = Path(__file__).resolve().parent
    compiler = ['java']
    if os.environ.get('SYX_JAVA_HOME'):
        compiler += ['-Djava.home=' + os.environ['SYX_JAVA_HOME']]
    sources = [root / 'dev/java/syx/assistant/candidate' / n for n in ['PanelTheme.java', 'PanelThemeProbe.java']]
    subprocess.run([*compiler, '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '16',
                    '-d', str(tmp_path), *map(str, sources)], capture_output=True, check=True, timeout=30)
    result = subprocess.run(['java', '-cp', str(tmp_path), 'syx.assistant.candidate.PanelThemeProbe'],
                            capture_output=True, text=True, check=True, timeout=30)
    assert result.stdout.strip() == 'PASS presets, strict accents, 4096 abstract contrast samples and engine-channel bounds'
