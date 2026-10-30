"""Reader v3 on one tile's independently assembled pieces, on the assembly box (CT read from the public volume).
w040 copy of experiments/w073-scrollfiesta-full-v1/render_full.py: the reference is the joined w040+w041 grid
(select_w040.py reference) and normals are oriented away from the scroll axis at the umbilicus in calibration.json.

The reference w073 surface only chooses which output pieces correspond to the marked area; it never supplies
coordinates. Charts keep their holes. Adapted from experiments/w073-socratic-pilot-v1/render.py."""
from pathlib import Path
import argparse,json,os,sys,numpy as np,tifffile
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
R=Path(os.environ.get('SF_ROOT','/workspace/sf'));sys.path.insert(0,str(R/'tools'));import lab_inkwindow as L
sys.path.insert(0,str(R));import gpu_lock;gpu_lock.install(L,R)
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def dense_grid(piece):
    a=np.stack([tifffile.imread(piece/(c+'.tif')) for c in 'xyz'],-1).astype(np.float32)
    a[~np.isfinite(a).all(-1)|(a<=0).any(-1)]=np.nan;return a
def reference(tile):
    sel=json.loads((R/'selection-full.json').read_text());t=next(x for x in sel['tiles'] if x['tile']==tile);b=sel['box_flat_px']
    a=np.stack([tifffile.imread(R/'reference'/(c+'.tif')) for c in 'xyz'],-1);yy,xx=np.indices(a.shape[:2]);u0,u1=t['u_range_flat_px']
    ok=np.isfinite(a).all(-1)&(a>0).all(-1)&(xx*20>=max(u0,b[0]))&(xx*20<=min(u1,b[2]))&(yy*20>=b[1])&(yy*20<=b[3])
    return a[ok]
def select(tile,out,max_pieces):
    refs=reference(tile);ranked=[]
    for piece in sorted((out/'pieces').glob(tile+'_p*')):
        if not (piece/'x.tif').is_file():continue
        pts=dense_grid(piece)[::4,::4].reshape(-1,3);pts=pts[np.isfinite(pts).all(1)]
        if len(pts)<20:continue
        near=cKDTree(pts).query(refs,workers=8)[0]<5
        ranked.append({'piece':piece.name,'near_reference_nodes':int(near.sum()),'fraction':float(near.mean()),'_near':near})
    ranked.sort(key=lambda x:-x['near_reference_nodes']);covered=np.zeros(len(refs),bool);chosen=[]
    for row in ranked:
        if int((row['_near']&~covered).sum())<max(20,len(refs)*.03):continue
        chosen.append(row['piece']);covered|=row['_near']
        if len(chosen)>=max_pieces or covered.mean()>.95:break
    for row in ranked:row.pop('_near')
    report={'tile':tile,'reference_nodes':int(len(refs)),'chosen':chosen,'union_fraction':float(covered.mean()),'ranked':ranked[:20],
            'method':'post-hoc: pieces nearest the reference w040/w041 nodes of this tile (5 vox); comparison only, not identity certification'}
    save(out/'reader-selection.json',report);return report
def main():
    p=argparse.ArgumentParser();p.add_argument('tile');p.add_argument('--max-pieces',type=int,default=4);a=p.parse_args()
    out=R/f'out-{a.tile}';report=select(a.tile,out,a.max_pieces);print(json.dumps({k:report[k] for k in ['tile','chosen','union_fraction']}),flush=True)
    volume=L.lab_zarr.open_volume(L.VOLUMES['PHerc0306B']);level=volume.level(0);results=[]
    for name in report['chosen']:
        piece=out/'pieces'/name;target=out/'reader'/name;chart=target/'chart';chart.mkdir(parents=True,exist_ok=True)
        dense=dense_grid(piece);sx,sy=json.loads((piece/'meta.json').read_text())['scale']
        rr=np.arange(0,(dense.shape[0]-1)*sy+1e-6,1)/sy;cc=np.arange(0,(dense.shape[1]-1)*sx+1e-6,1)/sx
        yy,xx=np.meshgrid(rr,cc,indexing='ij');coords=np.array([yy,xx]);valid=np.isfinite(dense).all(-1)
        grid=np.stack([map_coordinates(np.nan_to_num(dense[:,:,k]),coords,order=1,mode='constant',cval=0,prefilter=False) for k in range(3)],-1)
        support=map_coordinates(valid.astype(float),coords,order=1,mode='constant',cval=0,prefilter=False)>.999999;grid[~support]=np.nan
        for k,c in enumerate('xyz'):tifffile.imwrite(chart/(c+'.tif'),grid[:,:,k].astype(np.float32))
        run=target/'run'
        for folder in ['maps','logs','png']:(run/folder).mkdir(parents=True,exist_ok=True)
        frame={'origin_flat_px':[0,0],'shape_hw':[int(np.ceil((grid.shape[0]-1)/64))*64,int(np.ceil((grid.shape[1]-1)/64))*64],'tile_origin_flat_px':[0,0],'snap_px':64,
               'pixel_rule':'native UV pixel (x,y) -> node (x+0.5,y+0.5); node spacing 1 UV voxel'}
        uy,ux=json.loads((R/'calibration.json').read_text())['umbilicus_yx'];normals,outward=L.render_normals(grid,(ux,uy));old=L.NODE
        try:
            L.NODE=1
            stats=L.render(grid,normals,frame,level,run/'render.zarr',progress=lambda s:print(s,flush=True),normal_mode='nearest')
        finally:L.NODE=old
        ink=L.infer(run/'render.zarr','readerv3',0,run/'maps',run/'logs','cuda',batch_size=1)
        import zarr
        valid_px=np.asarray(zarr.open_group(str(run/'render.zarr'),mode='r')['0'][33])>0
        stretch=L.write_png(ink['reading_tif'],run/'png/readerv3_d+0.png',valid_px,stretch=[59,201])
        L.write_png(ink['blind_tif'],run/'png/readerv3_d+0_blind.png',valid_px,stretch=stretch)
        save(run/'summary.json',{'schema':'scrollfiesta_full_reader/1','tile':a.tile,'piece':name,'frame':frame,'grid_shape':list(grid.shape[:2]),'render':stats,
             'outward_fraction':outward,'checkpoint_sha256':L.CHECKPOINTS['readerv3'][1],'volume':L.VOLUMES['PHerc0306B'],'ink':{k:str(v) for k,v in ink.items()}})
        results.append({'piece':name,'status':'reader_complete'});save(out/'reader-results.json',{'state':'running','results':results})
        level_cache=getattr(level,'chunk',None)
        if hasattr(level_cache,'cache_clear'):level_cache.cache_clear()
    save(out/'reader-results.json',{'state':'complete','results':results})
if __name__=='__main__':main()
