"""Cubes for a focused ScrollFiesta rebuild of PHerc0306B w040's letter row and its right continuation (box W; David
2026-10-30: "if we can stitch anything to the right to get more letters, maybe doing a reconstruction from scratch
focussed on that specific area"). Reference geometry only chooses cubes, as select_topright.py does:
  w040 (zeta route z6912-9216 flatten_CW) flat x 4850-6660 (just left of chi to the mesh's right edge), and
  w041 (same route) beyond the join, placed by the right-stitch translation [5466,187] flat px
  (experiments/0306b-w040-right-stitch-v1), joined x 6660-8300 (1.6 cm), both over joined y 2050-3000.
Two overlapping tiles along the text: Wa (joined x 4850-6900) and Wb (6400-8300). Also writes calibration-w040.json:
the scroll axis below the bundle's table (z < 8704) from the zeta-route umbilicus that fitted w040
(lab_holdings.axis_points), umbilicus at the region's z centre, pitch as the bundle. Writes selection-w040.json."""
from pathlib import Path
import hashlib,json,sys,numpy as np,tifffile
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent
sys.path.insert(0,str(R/'experiments/w073-scrollfiesta-full-v1'));sys.path.insert(0,str(R/'tools'))
from select_full import dilate,cid
import lab_holdings as H
B=R/'data/eta/zeta-route-a-eta-0306B-z6912/0306B_z6912-9216_flatten_CW_tifxyz';SHIFT=(5466,187)
X0,X1,Y0,Y1,JOIN=4850,8300,2050,3000,6660;TILES={'Wa':(4850,6900),'Wb':(6400,8300)};N_SLABS=6
BUNDLE=R/'data/w073-scrollfiesta-full-v1/full/bundle'
def mesh(w):
    d=B/w/'tifxyz/flatten.tifxyz';a=np.stack([tifffile.imread(d/f'{c}.tif') for c in 'xyz'],-1).astype(np.float64)
    return a,hashlib.sha256((d/'x.tif').read_bytes()).hexdigest()
def nodes(a,dx,dy,xlo,xhi):
    yy,xx=np.indices(a.shape[:2]);u=xx*20+dx;v=yy*20+dy
    ok=np.isfinite(a).all(-1)&(a>0).all(-1)&(u>=xlo)&(u<=xhi)&(v>=Y0)&(v<=Y1);return a[ok],u[ok]
def main():
    a40,h40=mesh('w040');a41,h41=mesh('w041')
    p40,u40=nodes(a40,0,0,X0,JOIN);p41,u41=nodes(a41,*SHIFT,JOIN,X1);P=np.concatenate([p40,p41]);U=np.concatenate([u40,u41])
    print('reference nodes w040',len(p40),'w041',len(p41),'xyz min',P.min(0).round(),'max',P.max(0).round())
    zyx=P[:,::-1];tiles=[]
    for t,(lo,hi) in TILES.items():
        m=(U>=lo)&(U<=hi);tiles.append({'tile':t,'u_range_flat_px':[float(lo),float(hi)],'reference_nodes':int(m.sum()),
            'mesh_cubes':[cid(c) for c in sorted(dilate(set(map(tuple,np.floor(zyx[m]/128).astype(int)))))]})
    meshc=set().union(*[{tuple(int(v[1:])//128 for v in c.split('_')) for c in t['mesh_cubes']} for t in tiles]);need=sorted(dilate(meshc))
    na=np.array(need);lo,hi=na.min(0),na.max(0)+1;cuts=np.linspace(lo[1],hi[1],N_SLABS+1).round().astype(int);boxes=[]
    for i in range(N_SLABS):
        c=na[(na[:,1]>=cuts[i])&(na[:,1]<cuts[i+1])]
        if not len(c):continue
        b0=c.min(0)*128;b1=(c.max(0)+1)*128
        boxes.append({'slab':f'W{i+1:02d}','bbox_zyx':[int(b0[0]),int(b1[0]),int(b0[1]),int(b1[1]),int(b0[2]),int(b1[2])],'cubes':int(np.prod((b1-b0)//128)),'gpu':0})
    full=json.loads((BUNDLE/'selection-full.json').read_text())
    sel={'schema':'w040_scrollfiesta_right/1','request':__doc__.split('\n')[1].strip(),'box_joined_flat_px':[X0,Y0,X1,Y1],'box_flat_px':[X0,Y0,X1,Y1],'join_x':JOIN,'w041_shift_flat_px':list(SHIFT),
         'tiles':tiles,'mesh_cubes':sorted(cid(c) for c in meshc),'prediction_needed_cubes':len(need),'prediction_boxes':boxes,
         **{k:full[k] for k in ('native_um','checkpoint_sha256','socratic_commit','scrollfiesta_commit') if k in full},
         'reference_role':'chooses cubes and, after assembly, which pieces to render; never supplies coordinates',
         'reference_geometry_sha256':{'w040_x':h40,'w041_x':h41}}
    (E/'selection-w040.json').write_text(json.dumps(sel,indent=1)+'\n')
    # axis: zeta-route points below the bundle table's first row, then the bundle's own rows
    pts=sorted(H.axis_points('PHerc0306B')[0],key=lambda p:p[2]);zc=float(np.median(P[:,2]))
    rows=[(int(p[2]),p[1],p[0]) for p in pts if 6400<=p[2]<8704]
    btab=[l for l in (BUNDLE/'ct-axis/axis.csv').read_text().splitlines() if l and l[0].isdigit()]
    csv='# z<8704: zeta-route umbilicus (lab_holdings.axis_points, fitted w040); z>=8704: bundle raw-CT structure-tensor frame\nz,y,x\n'+''.join(f'{z},{y:.8f},{x:.8f}\n' for z,y,x in rows)+'\n'.join(btab)+'\n'
    (E/'axis-w040.csv').write_text(csv);cx,cy=H.centre_xy('PHerc0306B',zc)[0]
    cal=json.loads((BUNDLE/'calibration.json').read_text())
    cal.update(axis_csv_sha256=hashlib.sha256(csv.encode()).hexdigest(),umbilicus_yx=[cy,cx],umbilicus_rule=f'zeta-route axis interpolated at z {zc:.0f} (median z of the reference nodes)')
    (E/'calibration-w040.json').write_text(json.dumps(cal,indent=2)+'\n')
    print(json.dumps({'tiles':{t['tile']:(t['reference_nodes'],len(t['mesh_cubes'])) for t in tiles},'mesh_cubes':len(meshc),'prediction_cubes':len(need),'slabs':[(b['slab'],b['cubes']) for b in boxes],'z_centre':zc,'umbilicus_yx':cal['umbilicus_yx'],'axis_rows_added':len(rows)}))
if __name__=="__main__" and len(sys.argv)==1:main()
def joined_reference():
    """reference/x,y,z.tif for render_w040.py: one grid in the joined flat frame (node = joined px / 20), w040 left of the
    join, w041 (bilinear at its fractional shift) right of it; NaN-free zeros where neither has support."""
    from scipy.ndimage import map_coordinates
    a40,_=mesh('w040');a41,_=mesh('w041');H_,W_=Y1//20+8,X1//20+8;yy,xx=np.indices((H_,W_)).astype(float);out=np.zeros((H_,W_,3),np.float32)
    m40=(xx*20<JOIN)&(yy<a40.shape[0])&(xx<a40.shape[1]);out[m40]=a40[yy[m40].astype(int),xx[m40].astype(int)]
    r=yy-SHIFT[1]/20;c=xx-SHIFT[0]/20;m41=(xx*20>=JOIN)&(r>=0)&(c>=0)&(r<a41.shape[0]-1)&(c<a41.shape[1]-1)
    ok41=((a41>0).all(-1)).astype(float);sup=map_coordinates(ok41,[r[m41],c[m41]],order=1)>.999
    v=np.stack([map_coordinates(a41[...,k],[r[m41],c[m41]],order=1) for k in range(3)],-1);v[~sup]=0;out[m41]=v
    d=E/'reference';d.mkdir(exist_ok=True)
    for k,ch in enumerate('xyz'):tifffile.imwrite(d/f'{ch}.tif',out[...,k])
    print('joined reference',out.shape,'valid',int((out>0).all(-1).sum()))
if __name__=='__main__' and len(sys.argv)>1 and sys.argv[1]=='reference':joined_reference()
