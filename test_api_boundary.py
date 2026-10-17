from pathlib import Path
import ast
import zipfile

ROOT=Path(__file__).parent

def test_game_source_stays_in_mod_namespace_without_bypass():
    sources=list((ROOT/'mod/src/main/java').rglob('*.java'))
    assert {p.name for p in sources}=={'AssistantScript.java','StateCollector.java','JsonWriter.java'}
    forbidden=['java.lang.reflect','setAccessible(','trySetAccessible(', 'org.lwjgl',
               'java.awt.Robot','ProcessBuilder','Runtime.getRuntime().exec','copyFB(', 'CORE_RESOURCE']
    for source in sources:
        text=source.read_text()
        assert text.startswith('package syx.assistant;')
        assert not any(pattern in text for pattern in forbidden)

def test_packaged_modules_have_no_control_adapter():
    import tomllib
    config=tomllib.loads((ROOT/'pyproject.toml').read_text())
    assert 'syx_control' not in config['tool']['setuptools']['py-modules']
    tree=ast.parse((ROOT/'syx_mcp.py').read_text())
    assert not any(isinstance(n,ast.ImportFrom) and n.module=='syx_control' for n in ast.walk(tree))
