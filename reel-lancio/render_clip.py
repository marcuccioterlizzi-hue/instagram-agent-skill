import sys, math, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
src, out = sys.argv[1], sys.argv[2]
W,H,S = 1080,1920,2
page = Image.open(src).convert('RGB').crop((508,0,508+884,1512)).resize((W*S,H*S), Image.LANCZOS)
a = np.asarray(page).astype(int)
# ink colour: sample bluest dark pixels around MEGLIO
reg = a[880*S:1040*S, 180*S:620*S]
score = (reg[:,:,2]-reg[:,:,0]) - reg.sum(2)/6
idx = np.argsort(score.ravel())[-400:]
ink = tuple(int(v) for v in reg.reshape(-1,3)[idx].mean(0))
print('ink', ink)
# word box (page coords at 1x)
x_start, y_line, x_end = 185, 1040, W+20
random.seed(3)
def line_pts(n=400):
    pts=[]
    for i in range(n+1):
        u=i/n; x=x_start+(x_end-x_start)*u
        y=y_line - 10*u + 3*math.sin(u*7.0)+1.5*math.sin(u*23+1)
        pts.append((x*S,y*S))
    return pts
PTS=line_pts()
def ease(t): return t*t*(3-2*t)
fps, dur = 30, 5.0
N=int(fps*dur)
cx0,cy0,z0 = W/2,H/2,1.0
cx1,cy1,z1 = 420,985,1.6
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(fps),'-i','-',
  '-c:v','libx264','-crf','16','-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart',out],stdin=subprocess.PIPE)
for f in range(N):
    t=f/(N-1)
    e=ease(min(1,t/0.92))
    z=z0+(z1-z0)*e; cx=cx0+(cx1-cx0)*e; cy=cy0+(cy1-cy0)*e
    # line progress: starts 1.9s, ends 4.5s
    lt=(t*dur-1.9)/2.6; lp=0 if lt<=0 else min(1,1-(1-min(1,lt))**2.2)
    img=page
    if lp>0:
        k=max(2,int(lp*len(PTS)))
        ov=Image.new('L',page.size,0)
        ImageDraw.Draw(ov).line(PTS[:k],fill=215,width=int(4.2*S),joint='curve')
        ov=ov.filter(ImageFilter.GaussianBlur(0.9*S))
        img=Image.composite(Image.new('RGB',page.size,ink),page,ov)
    w=W/z; h=H/z
    x0=min(max(cx-w/2,0),W-w); y0=min(max(cy-h/2,0),H-h)
    fr=img.resize((W,H),Image.LANCZOS,box=(x0*S,y0*S,(x0+w)*S,(y0+h)*S))
    ff.stdin.write(fr.tobytes())
    if f in (0,75,110,149): fr.resize((405,720)).save(f'f{f}.jpg')
ff.stdin.close(); ff.wait()
