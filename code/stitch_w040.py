"""Stitch the w040 letter row with its continuations into one strip in w040's flat frame (px = level-0 voxels):
  left    data/lab/inkwindow/w040-v3-left   (w040 mesh, rows 90-183, cols 110-200)
  letters data/lab/inkwindow/w040-v3-letters (w040 mesh, rows 90-183, cols 190-332)
  right   data/lab/inkwindow/w041-v3-right  (w041 mesh, rows 85-150, cols 50-185), placed by the right-stitch
          translation [5466,187] flat px (experiments/0306b-w040-right-stitch-v1: median edge residual ~2 vox).
Per source: CT = mean of render layers 31-35; ink = Reader v3 depth pair (data/w040-v3/depthpair*, made by
release/depthpair/depthpair.py from d-4..+2 with flips at d-2, d0, d+1), both faces. Each source's ink is put on the
letters' display scale (median and p99 over its valid pixels). Later sources fill only pixels earlier ones leave
empty (order: letters, left, right). One integer translation per source; no warping, no blending.
Writes data/w040-v3/stitch/{ct,ink,ink_blind,source}.npy + stitch.json. Display in reading orientation (no rotation:
w040's flat frame has z increasing down and the winding angle increasing right, as w073's verified reading page)."""
from pathlib import Path
import json,numpy as np,tifffile,zarr
R=Path(__file__).resolve().parents[2];I=R/'data/lab/inkwindow';O=R/'data/w040-v3/stitch';O.mkdir(parents=True,exist_ok=True)
SRC=[('letters','w040-v3-letters','depthpair',(0,0)),('left','w040-v3-left','depthpair-left',(0,0)),('right','w041-v3-right','depthpair-right',(5466,187))]
def main():
    parts=[]
    for name,run,dp,(sx,sy) in SRC:
        d=I/run
        if not (R/'data/w040-v3'/dp/'depthpair.tif').exists():print('missing',name);continue
        fr=json.loads((d/'summary.json').read_text())['frame'];ox,oy=fr['origin_flat_px'];g=zarr.open_group(str(d/'render.zarr'),mode='r')['0']
        ct=np.mean([np.asarray(g[k][:]).astype(np.float32) for k in range(31,36)],0)
        ink=tifffile.imread(R/'data/w040-v3'/dp/'depthpair.tif').astype(np.float32);bl=tifffile.imread(R/'data/w040-v3'/dp/'depthpair_blind.tif').astype(np.float32)
        parts.append(dict(name=name,x0=ox+sx,y0=oy+sy,ct=ct,ink=ink,bl=bl,ok=ct>0))
    ref=parts[0];a,b=np.percentile(ref['ink'][ref['ok']],[50,99])
    for p in parts:
        for k in ('ink','bl'):c,d=np.percentile(p[k][p['ok']],[50,99]);p[k]=np.clip((p[k]-c)/max(d-c,1e-6)*(b-a)+a,0,255)
    X0=min(p['x0'] for p in parts);Y0=min(p['y0'] for p in parts);X1=max(p['x0']+p['ct'].shape[1] for p in parts);Y1=max(p['y0']+p['ct'].shape[0] for p in parts)
    ct=np.zeros((Y1-Y0,X1-X0),np.float32);ink=np.zeros_like(ct);bl=np.zeros_like(ct);src=np.full(ct.shape,-1,np.int8)
    for i,p in enumerate(parts):
        ys,xs=p['y0']-Y0,p['x0']-X0;h,w=p['ct'].shape;sl=(slice(ys,ys+h),slice(xs,xs+w));m=p['ok']&(src[sl]<0)
        for arr,v in ((ct,p['ct']),(ink,p['ink']),(bl,p['bl'])):arr[sl][m]=v[m]
        src[sl][m]=i
    for n,v in (('ct',ct),('ink',ink),('ink_blind',bl),('source',src)):np.save(O/f'{n}.npy',v)
    info={'origin_flat_px':[int(X0),int(Y0)],'shape_hw':list(ct.shape),'sources':[{k:p[k] for k in ('name','x0','y0')}|{'shape_hw':list(p['ct'].shape)} for p in parts],
          'rule':__doc__.split('\n')[5].strip()}
    (O/'stitch.json').write_text(json.dumps(info,indent=1,default=int)+'\n');print(json.dumps(info,default=int))
if __name__=='__main__':main()
