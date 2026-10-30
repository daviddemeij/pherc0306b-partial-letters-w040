"""depthpair: combine an ink model's predictions at several depths so that letters which are clearest at different
depths in different places all keep full strength, without adding single-depth noise, and check the result on the
blind face.

On a traced surface the best depth varies below segment scale (the surface sits a few voxels off the papyrus, by
different amounts in different places). A single depth loses letters that peak elsewhere; a mean over depths dilutes
them; a max over depths adds every depth's noise. Real ink spans a couple of voxels along the normal, so a real stroke
shows at two neighbouring depths. depthpair keeps, per pixel, the best mean of two ADJACENT depths:

    score(x) = max_d  ( m_d(x) + m_{d+1}(x) ) / 2

where m_d is the prediction at depth d, optionally averaged over its test-time flips first. A stroke keeps (nearly) its
peak value at its own depth; a blob at a single depth is halved.

The same rule is applied to the blind-face maps (the model run on the reversed layer order, which most ink-model
pipelines write next to the reading face). That is the control: a combination rule that grows letter-like strokes on
the blind face is inventing them.

    python depthpair.py OUT_DIR --map -2=d-2.tif --map -1=d-1.tif --map 0=d0.tif,d0_fx.tif,d0_fy.tif ... \
        [--blind -2=d-2_blind.tif ...] [--png] [--window lo hi]

Maps: single-channel TIFF/PNG, same shape, any dtype (uint8 255 = probability 1 is typical). Several files for one
depth (comma-separated) are averaged first (flips, seeds). Writes depthpair.tif (+ depthpair_blind.tif), the per-pixel
winning depth pair (bestpair.tif), and with --png grey views (raw 0..1 and windowed) of both faces. MIT licence."""
import argparse,json
from pathlib import Path
import numpy as np,tifffile
def load(spec):
    out={}
    for s in spec or []:
        d,files=s.split('=',1);arr=[]
        for f in files.split(','):
            a=tifffile.imread(f) if f.lower().endswith(('.tif','.tiff')) else np.asarray(__import__('PIL.Image',fromlist=['Image']).open(f))
            arr.append(a.astype(np.float32))
        out[int(d)]=np.mean(arr,0)
    return dict(sorted(out.items()))
def pair(maps):
    ds=list(maps);
    if len(ds)<2:raise SystemExit('need at least two depths')
    gaps=[b-a for a,b in zip(ds,ds[1:])]
    if any(g!=1 for g in gaps):print('warning: depths are not consecutive; pairing neighbours in the list',ds)
    st=np.stack([(maps[a]+maps[b])/2 for a,b in zip(ds,ds[1:])]);k=st.argmax(0);return st.max(0),k,list(zip(ds,ds[1:]))
def grey(a,lo,hi,scale):
    from PIL import Image
    return Image.fromarray((np.clip((a/scale-lo)/(hi-lo),0,1)*255).astype(np.uint8))
def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('out')
    ap.add_argument('--map',action='append',required=True,help='DEPTH=file[,file...] for the reading face');ap.add_argument('--blind',action='append',help='DEPTH=file[,file...] for the blind face')
    ap.add_argument('--png',action='store_true');ap.add_argument('--window',type=float,nargs=2,default=[0.30,0.75]);ap.add_argument('--scale',type=float,default=None,help='value meaning probability 1 (default: 255 for uint8-range maps, else 1)')
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);rep={}
    for face,spec in (('reading',a.map),('blind',a.blind)):
        if not spec:continue
        maps=load(spec);s,k,prs=pair(maps);scale=a.scale or (255.0 if max(m.max() for m in maps.values())>1.5 else 1.0);suf='' if face=='reading' else '_blind'
        tifffile.imwrite(out/f'depthpair{suf}.tif',s.astype(np.float32),compression='zlib')
        if face=='reading':tifffile.imwrite(out/'bestpair.tif',k.astype(np.uint8),compression='zlib')
        rep[face]={'depths':list(maps),'pairs':prs,'pair_share':{f'{p[0]}..{p[1]}':float((k==i).mean()) for i,p in enumerate(prs)},'scale':scale}
        if a.png:
            grey(s,0,1,scale).save(out/f'depthpair{suf}_raw.png');grey(s,*a.window,scale).save(out/f'depthpair{suf}_window.png')
    (out/'depthpair.json').write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps(rep,indent=1))
if __name__=='__main__':main()
