"""Fetch collaboration refs and report divergence/overlap; never merge or edit working files."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent.parent


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE)


def changed_paths(raw):
    entries=iter(raw.split(b'\0'));paths=[];conflicts=[]
    for entry in entries:
        if not entry:continue
        status=entry[:2].decode();path=os.fsdecode(entry[3:]);paths.append(path)
        if status in {'DD','AU','UD','UA','DU','AA','UU'}:conflicts.append(path)
        if 'R' in status or 'C' in status:
            original=next(entries,None)
            if original:paths.append(os.fsdecode(original))
    return sorted(set(paths)),sorted(set(conflicts))


def manifest(raw):
    if len(raw)>2*1024*1024:raise ValueError('Release manifest exceeds 2 MiB')
    value=json.loads(raw)
    return {k:value.get(k) for k in ['built_at','game_version','model','mod_jar_sha256','download_sha256']}


def inspect(root=ROOT,remote='origin',branch='main',fetch=True):
    root=Path(git(root,'rev-parse','--show-toplevel').decode().strip())
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',remote):raise ValueError('Use a configured remote name')
    git(root,'check-ref-format','refs/heads/'+branch)
    ref='refs/remotes/'+remote+'/'+branch
    fetched=False;fetch_error=False
    if fetch:
        try:
            subprocess.run(['git','-C',str(root),'fetch','--prune','--tags',remote],check=True,
                           stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=60)
            fetched=True
        except (subprocess.CalledProcessError,subprocess.TimeoutExpired):fetch_error=True
    paths,conflicts=changed_paths(git(root,'status','--porcelain=v1','-z','--untracked-files=all'))
    result={'head':git(root,'rev-parse','HEAD').decode().strip(),'comparison_ref':ref,
        'remote_fetched_this_check':fetched,'fetch_failed':fetch_error,'working_paths':paths,'conflict_paths':conflicts,
        'scope':'Tracked player ZIP/manifest on the fetched main ref and Git tags. No GitHub release-asset API attestation.',
        'mutations':'Fetch updates Git refs only. No pull, merge, stash, reset, checkout, file edit or conflict resolution.'}
    try:
        result['remote_head']=git(root,'rev-parse','--verify',ref).decode().strip()
        ahead,behind=map(int,git(root,'rev-list','--left-right','--count','HEAD...'+ref).split())
        base=git(root,'merge-base','HEAD',ref).decode().strip()
        upstream={os.fsdecode(p) for p in git(root,'diff','--name-only','-z',base,ref).split(b'\0') if p}
        committed={os.fsdecode(p) for p in git(root,'diff','--name-only','-z',base,'HEAD').split(b'\0') if p}
        result.update(ahead=ahead,behind=behind,remote_changed_paths=sorted(upstream),
            local_committed_paths=sorted(committed),overlap_paths=sorted(upstream & (set(paths)|committed)),
            state='diverged' if ahead and behind else 'behind' if behind else 'ahead' if ahead else 'aligned')
        try:result['remote_player_release']=manifest(git(root,'show',ref+':releases/latest-user-test.json'))
        except (subprocess.CalledProcessError,ValueError,KeyError):result['remote_player_release']=None
    except subprocess.CalledProcessError:
        result.update(state='unknown',remote_head=None,remote_player_release=None)
    try:result['local_player_release']=manifest((root/'releases/latest-user-test.json').read_bytes())
    except (OSError,ValueError,KeyError):result['local_player_release']=None
    local=result['local_player_release'];published=result['remote_player_release']
    result['published_bundle_differs']=None if not local or not published else local['download_sha256']!=published['download_sha256']
    result['reconciliation_required']=bool(conflicts or result['state'] in {'behind','diverged','unknown'} or fetch_error)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--remote',default='origin');p.add_argument('--branch',default='main')
    p.add_argument('--no-fetch',action='store_true',help='Inspect cached refs only; never claims they are fresh')
    a=p.parse_args();r=inspect(a.repo,a.remote,a.branch,not a.no_fetch)
    print(json.dumps(r,indent=2))
    if r['fetch_failed'] or r['state']=='unknown':raise SystemExit(2)


if __name__=='__main__':main()
