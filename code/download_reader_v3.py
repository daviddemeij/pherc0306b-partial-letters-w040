#!/usr/bin/env python3
"""Download selected PHerc0306B Reader v3 TIFFs with ZIP and file SHA-256 checks.

Code: MIT, Copyright (c) 2026 David de Meij. Data: CC BY-NC 4.0.
Python standard library only. No inference or image conversion is performed.
"""
import argparse,csv,hashlib,io,json,os,shutil,urllib.request,zipfile
from pathlib import Path,PurePosixPath
BASE='https://github.com/daviddemeij/pherc0306b-partial-letters-w040/releases/download/reader-v3-screen-v1.0.0'
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk:=f.read(1<<20):h.update(chunk)
    return h.hexdigest()
def safe_path(name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or not p.parts:raise ValueError('Unsafe archive path')
    return p
def metadata(name,args):
    if args.metadata_dir:
        return (args.metadata_dir/name).read_bytes()
    local=Path(__file__).resolve().parents[1]/'reader-v3-screen'/name
    if local.exists():return local.read_bytes()
    with urllib.request.urlopen(args.base_url+'/'+name,timeout=60) as response:return response.read()
def ensure_archive(name,expected_size,expected_hash,args):
    if Path(name).name!=name:raise ValueError('Unsafe asset name')
    args.cache.mkdir(parents=True,exist_ok=True)
    target=args.cache/name
    if target.exists():
        if target.stat().st_size==expected_size and sha256(target)==expected_hash:return target
        target.unlink()
        raise ValueError(f'Cached ZIP checksum mismatch: {name}; removed. Run again to download.')
    part=target.with_name(target.name+'.part')
    try:
        with urllib.request.urlopen(args.base_url+'/'+name,timeout=180) as source,part.open('wb') as out:
            shutil.copyfileobj(source,out,1<<20)
        if part.stat().st_size!=expected_size or sha256(part)!=expected_hash:raise ValueError('Downloaded ZIP checksum/size mismatch: '+name)
        os.replace(part,target)
    finally:
        part.unlink(missing_ok=True)
    return target
def extract_selected(archive,rows,output):
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate ZIP member')
        for row in rows:
            member=row['member'];safe_path(member)
            target=output/member;expected=row['sha256'];size=int(row['bytes'])
            # Refuse symlink traversal through pre-existing output directories.
            if target.is_symlink() or any(p.is_symlink() for p in target.parents):raise ValueError('Symlink in output path')
            if target.exists() and target.stat().st_size==size and sha256(target)==expected:continue
            info=z.getinfo(member)
            if info.file_size!=size:raise ValueError('ZIP member size mismatch')
            target.parent.mkdir(parents=True,exist_ok=True);part=target.with_name(target.name+'.part')
            try:
                with z.open(info) as source,part.open('wb') as out:shutil.copyfileobj(source,out,1<<20)
                if part.stat().st_size!=size or sha256(part)!=expected:raise ValueError('TIFF checksum mismatch: '+member)
                os.replace(part,target)
            finally:part.unlink(missing_ok=True)
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--band',help='Production interval, e.g. 6912-9216; repeat selections by running again')
    p.add_argument('--winding',help='e.g. w040')
    p.add_argument('--direction',choices=['reading','opposite'])
    p.add_argument('--depth',type=int,action='append',help='Depth offset; repeat for several depths')
    p.add_argument('--source',help='Exact supplemental source group, e.g. w073b_rv3')
    p.add_argument('--kind',choices=['production','supplemental','all'],default='production')
    p.add_argument('--list',action='store_true',help='List selected TIFFs and required assets without downloading ZIPs')
    p.add_argument('--cache',type=Path,default=Path('reader-v3-cache'))
    p.add_argument('--output',type=Path,default=Path('reader-v3-data'))
    p.add_argument('--metadata-dir',type=Path,help='Local release metadata directory')
    p.add_argument('--base-url',default=BASE)
    args=p.parse_args(argv);rows=[]
    if args.kind in ['production','all']:
        rows+=list(csv.DictReader(io.StringIO(metadata('files.csv',args).decode())))
    if args.kind in ['supplemental','all']:
        rows+=json.loads(metadata('supplemental-files.json',args))['files']
    depths={str(d) for d in args.depth} if args.depth else None
    rows=[r for r in rows if (not args.band or r.get('band')==args.band) and (not args.winding or r.get('winding')==args.winding) and (not args.direction or r.get('direction')==args.direction) and (depths is None or str(r.get('depth')) in depths) and (not args.source or r.get('source')==args.source)]
    if not rows:p.error('No TIFFs match the selection')
    groups={}
    for row in rows:groups.setdefault(row['asset'],[]).append(row)
    print(f'{len(rows)} TIFFs in {len(groups)} ZIP assets')
    if args.list:
        for row in rows:print(row['asset'],row['member'],row['bytes'],row['sha256'])
        return
    checks={}
    for line in metadata('SHA256SUMS',args).decode().splitlines():
        digest,name=line.split(maxsplit=1);checks[name.lstrip('*')]=digest
    args.output.mkdir(parents=True,exist_ok=True)
    for name,selected in groups.items():
        sizes={int(r['asset_bytes']) for r in selected}
        if len(sizes)!=1:raise ValueError('Conflicting asset size metadata')
        print('Downloading/verifying',name,flush=True)
        archive=ensure_archive(name,sizes.pop(),checks[name],args)
        extract_selected(archive,selected,args.output)
    print('Verified TIFFs saved to',args.output)
if __name__=='__main__':main()
