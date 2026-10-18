"""Simple DeepSeek Pro launcher. Credentials stay outside the downloaded bundle."""
import argparse
import asyncio
import getpass
import os
from pathlib import Path
import re
from types import SimpleNamespace


def main():
    parser=argparse.ArgumentParser(description='Songs of Syx — DeepSeek Pro chat')
    parser.add_argument('--env-file',type=Path)
    parser.add_argument('--state-dir',default=str(Path.home()/'.local/share/syx-assistant'))
    parser.add_argument('--history-dir',default=str(Path.home()/'.local/share/syx-assistant-chat'))
    parser.add_argument('--check',action='store_true',help='Check the installed chat dependencies without connecting')
    args=parser.parse_args()
    if args.env_file:args.env_file=args.env_file.expanduser().resolve()
    os.chdir(Path(__file__).resolve().parent)
    from syx_chat_service import serve
    if args.check:
        print('DeepSeek Pro chat dependencies are ready.');return
    key_file=args.env_file or Path.home()/'.config/syx-ai-assistant/deepseek.env'
    if not os.environ.get('DEEPSEEK_API_KEY') and not key_file.exists():
        key=getpass.getpass('DeepSeek API key (saved privately on this computer): ').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,300}',key):raise SystemExit('The API key has an unexpected format.')
        key_file.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd=os.open(key_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as file:file.write('DEEPSEEK_API_KEY='+key+'\n')
    print('DeepSeek Pro chat is running. Keep this terminal open; press Ctrl+C to stop.')
    config=SimpleNamespace(state_dir=args.state_dir,history_dir=args.history_dir,
        env_file=str(key_file) if key_file.exists() else None,claude_env_file=None,advanced=False)
    try:asyncio.run(serve(config))
    except KeyboardInterrupt:pass


if __name__=='__main__':main()
