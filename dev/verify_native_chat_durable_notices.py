"""Fixed native durable uncertainty integration; authored state and fake inference."""
import argparse
import asyncio
from pathlib import Path
from verify_native_chat_background import verify

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, required=True)
    asyncio.run(verify(parser.parse_args().state_dir, recovery=True, notices=True, durable=True))
