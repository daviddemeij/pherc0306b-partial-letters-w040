"""The w040 progress-prize figure from the stitched strip (stitch_w040.py): reading orientation, one 1 cm scale bar, and
stacked panels on the same pixels:
  A  Reader v3 depth pair over CT (light yellow over the mean of CT layers 31-35, dimmed to 32%; same display curve as
     our W073 page);
  B  raw ink score, grey, 0..1, and C windowed 0.30..0.75 (no threshold; Sean: show raw probabilities at several windows);
  D  the same rule on the blind face (reversed layer order): the control;
  E  labels: the human letter boxes (David de Meij, 2026-10-22; provenance in data/w040-submission-appendix-v1) on a
     dimmed copy of A. Boxes never sit on panels A-D.
Writes data/w040-v3/figure/PHerc0306B_w040-letters.png (+ per-panel PNGs) and letters.json (boxes in the strip frame
and in mm)."""
from pathlib import Path
import json,sys,numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[2];S=R/'data/w040-v3/stitch';O=R/'data/w040-v3/figure';O.mkdir(parents=True,exist_ok=True)
sys.argv=[sys.argv[0]];sys.path.insert(0,str(R/'experiments/w073-submission-scrollfiesta-v1'));import build_flat_page as P
UM=8.64;CROP_PAD=160
def main():
    info=json.loads((S/'stitch.json').read_text());X0,Y0=info['origin_flat_px']
    ct=np.load(S/'ct.npy');ink=np.load(S/'ink.npy');bl=np.load(S/'ink_blind.npy');ok=ct>0
    prov=json.loads((R/'data/w040-submission-appendix-v1/provenance.json').read_text());L=prov['active_human_letters']
    boxes=[(l['letter'],l['confidence'],[l['box_flat_px'][0]-X0,l['box_flat_px'][1]-Y0,l['box_flat_px'][2]-X0,l['box_flat_px'][3]-Y0]) for l in L]
    # crop: the letter row (union of boxes) +- 1.4 mm vertically, full strip width where there is papyrus
    yb0=min(b[1] for _,_,b in boxes);yb1=max(b[3] for _,_,b in boxes);ys=max(0,yb0-CROP_PAD);ye=min(ct.shape[0],yb1+CROP_PAD)
    cols=np.flatnonzero(ok[ys:ye].mean(0)>.3);xs,xe=int(cols[0]),int(cols[-1])+1;sl=(slice(ys,ye),slice(xs,xe))
    A=Image.fromarray(P.compose(ct[sl],np.where(ok[sl],ink[sl],0)))
    def grey(v,lo,hi):g=np.clip((v[sl]/255-lo)/(hi-lo),0,1);g[~ok[sl]]=0;return Image.fromarray((g*255).astype(np.uint8)).convert('RGB')
    B=grey(ink,0,1);C=grey(ink,.30,.75);D=Image.fromarray(P.compose(ct[sl],np.where(ok[sl],bl[sl],0)))
    E=Image.fromarray((np.asarray(A).astype(np.float32)*.55).astype(np.uint8));dr=ImageDraw.Draw(E);F=ImageFont.truetype(str(P.FONT),40);out=[]
    for let,conf,(a,b,c,d) in boxes:
        a-=xs;c-=xs;b-=ys;d-=ys;col=(90,220,120) if conf=='sure' else (255,170,60)
        dr.rectangle([a,b,c,d],outline=col,width=5);dr.text((a+6,max(0,b-46)),{'chi':'χ','theta':'θ','pi':'π','lambda':'λ','gamma':'γ'}.get(let,let)+('' if conf=='sure' else '?'),fill=col,font=F)
        out.append({'letter':let,'confidence':conf,'box_strip_px':[a+xs,b+ys,c+xs,d+ys],'box_w040_flat_px':[a+xs+X0,b+ys+Y0,c+xs+X0,d+ys+Y0],
                    'width_mm':round((c-a)*UM/1000,2),'height_mm':round((d-b)*UM/1000,2)})
    panels=[('A  Reader v3, depth pair (d-4..+2, flip TTA at d-2, d0, d+1), over CT',A),('B  raw ink score, 0 to 1',B),('C  raw ink score, window 0.30 to 0.75',C),
            ('D  control: same rule on the blind face (reversed layer order)',D),('E  human letter labels (green sure, orange maybe) on a dimmed copy of A',E)]
    for i,(t,im) in enumerate(panels):im.save(O/f'panel_{"ABCDE"[i]}.png')
    w,h=A.size;TOP,GAP,BOT=110,70,170;fig=Image.new('RGB',(w+80,TOP+len(panels)*(h+GAP)+BOT),'#111111');d=ImageDraw.Draw(fig)
    T=ImageFont.truetype(str(P.FONT),54);S_=ImageFont.truetype(str(P.FONT),38)
    d.text((40,28),'PHerc. 0306B  |  winding w040, letter row with its continuations  |  reading orientation',fill='white',font=T)
    for i,(t,im) in enumerate(panels):
        y=TOP+i*(h+GAP);d.text((40,y+8),t,fill='white',font=S_);fig.paste(im,(40,y+GAP-4))
    bar=round(10000/UM);by=fig.height-BOT+60;d.line((40,by,40+bar,by),fill='white',width=8);d.text((40,by+18),'1 cm (8.64 µm/px)',fill='white',font=S_)
    for s in info['sources']:
        x=s['x0']-X0-xs+40
        if 40<x<w+40:d.line((x,TOP-10,x,TOP+10),fill=(120,180,255),width=4)
    d.text((40+bar+60,by-12),'Sources (blue ticks at their left edges): '+', '.join(s['name'] for s in info['sources'])+'; w041 placed by one integer translation',fill='#bbbbbb',font=S_)
    fig.save(O/'PHerc0306B_w040-letters.png');(O/'letters.json').write_text(json.dumps({'crop_strip_px':[xs,ys,xe,ye],'strip_origin_w040_flat_px':[X0,Y0],'letters':out},indent=1)+'\n')
    print(fig.size,[(o['letter'],o['width_mm'],o['height_mm']) for o in out])
if __name__=='__main__':main()
