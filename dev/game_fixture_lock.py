"""Advisory machine-wide lock for cooperating local native-game fixture runners."""
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess


@contextmanager
def exclusive_fixture(directory=None):
    directory=Path(directory or os.environ.get('SYX_DEV_LOCK_DIR',Path.home()/'.cache/syx-ai-assistant'))
    if directory.is_symlink():raise ValueError('Fixture lock directory must not be a symlink')
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=directory/'game-fixture.lock'
    fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another cooperating native-game fixture owns the device lock; wait for it to finish. Do not kill it or remove its lock file.') from None
        os.fchmod(fd,0o600);os.ftruncate(fd,0)
        os.write(fd,json.dumps({'pid':os.getpid(),'checkout':str(Path.cwd()),'started_at':datetime.now(timezone.utc).isoformat()}).encode())
        try:yield path
        finally:os.ftruncate(fd,0);fcntl.flock(fd,fcntl.LOCK_UN)
    finally:os.close(fd)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command:p.error('Provide a native fixture command after --')
    try:
        with exclusive_fixture():raise SystemExit(subprocess.run(command).returncode)
    except (RuntimeError,ValueError) as error:raise SystemExit(str(error))
