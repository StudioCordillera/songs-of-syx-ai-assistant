"""Fixed native candidate notices from explicitly authored disposable recovery states."""
import argparse
import asyncio
from pathlib import Path
from verify_native_chat_background import verify

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, required=True)
    asyncio.run(verify(parser.parse_args().state_dir, recovery=True, notices=True))
