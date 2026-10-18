"""Install only this mod, keeping the previous copy outside the game's mod directory."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import shutil


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-dir',type=Path,default=Path.home()/'.local/share/songsofsyx')
    args=parser.parse_args()
    source=Path(__file__).resolve().parent/'mod/syx-ai-assistant'
    if not (source/'V71/script/syx-ai-assistant.jar').is_file():raise SystemExit('Extract the complete user-test ZIP first.')
    target=args.user_dir.expanduser().resolve()/'mods/syx-ai-assistant'
    if target.is_symlink():raise SystemExit('The mod destination is a symlink; select a regular user directory.')
    target.parent.mkdir(parents=True,exist_ok=True)
    backup=None
    if target.exists():
        backups=args.user_dir.expanduser().resolve()/'syx-assistant-backups'
        backups.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        backup=backups/stamp
        shutil.move(str(target),str(backup))
    try:shutil.copytree(source,target)
    except Exception:
        if target.exists():shutil.rmtree(target)
        if backup is not None:shutil.move(str(backup),str(target))
        raise
    print('Installed Syx AI Assistant. Enable it in the game launcher, load a game, then click AI chat.')


if __name__=='__main__':main()
