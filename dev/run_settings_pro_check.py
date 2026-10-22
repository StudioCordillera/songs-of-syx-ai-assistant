"""Explicit two-turn paid Pro/native check, including configured settings and quantization caveat."""
import argparse
from pathlib import Path
from run_player_chat_check import run
from game_fixture_lock import exclusive_fixture

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game-dir','save','java','jdk-home','env-file'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mod-jar',type=Path);p.add_argument('--prior-validation',type=Path)
    args=p.parse_args();args.settings_pro=True
    with exclusive_fixture():run(args)
