import sys, math, subprocess, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
W,H,FPS=1080,1920,30
DUR=9.5
def sm(x): x=min(1,max(0,x)); return x*x*(3-2*x)
_c={}
def load(path):
    if path not in _c:
        if len(_c)>40: _c.clear()
        im=cv2.imread(path)
        if im.shape[1]!=W:
            im=cv2.resize(im,(W,H),interpolation=cv2.INTER_CUBIC)
            bl=cv2.GaussianBlur(im,(0,0),2.0); im=cv2.addWeighted(im,1.35,bl,-0.35,0)
        _c[path]=im.astype(np.float32)
    return _c[path]
def seq(fmt,idx,n):
    idx=min(max(idx,0),n-1); i=int(math.floor(idx)); f=idx-i
    a=load(fmt%(i+1))
    if f<0.02 or i+1>=n: return a
    return a*(1-f)+load(fmt%(i+2))*f
ref=lambda r: seq('ref_f/%04d.png', r*24, 192)
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
vig=(1-0.38*np.clip((np.sqrt(((xx-W/2)/(W*0.75))**2+((yy-H/2)/(H*0.75))**2)-0.45)/0.6,0,1)**1.5)[...,None]

# ---------- A: half face + sliding drop (generated from the owner's photo) ----------
F0,F1=6,43                                    # source frames used (24 fps): the drop is already moving
KEYS=np.array([[0,700,972],[11,702,985],[22,710,1045],[33,695,1150],[43,680,1255]],np.float32)
KEND=2.2; TGT=np.array([560.,1010.])
def seg_face(x):
    f=F0+(F1-F0)*x
    d=np.array([np.interp(f,KEYS[:,0],KEYS[:,1]),np.interp(f,KEYS[:,0],KEYS[:,2])])
    k=math.exp(math.log(KEND)*x**1.4); t=d+(TGT-d)*sm(x)
    M=np.float32([[k,0,t[0]-k*d[0]],[0,k,t[1]-k*d[1]]])
    img=cv2.warpAffine(seq('d_f/%04d.png',f,73),M,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    # rack focus: eye sharp at first, then only the area around the drop stays sharp
    w=sm((x-0.25)/0.5)
    if w>0:
        dist=np.sqrt((xx-t[0])**2+(yy-t[1])**2)
        mk=(np.clip((dist-230)/420,0,1)*w)[...,None]
        img=img*(1-mk)+cv2.GaussianBlur(img,(0,0),9)*mk
    return img*vig

# ---------- B: real squat footage, slow motion, graded toward the cold palette ----------
def grade(img):
    g=img.mean(axis=2,keepdims=True)
    img=g+(img-g)*0.80
    img=img*np.array([1.07,1.0,0.92],np.float32)            # BGR: cooler
    img=(img-128)*1.10+122
    return img*vig
def vblur(img,k):
    k=int(k); return img if k<3 else cv2.blur(img,(1,k))
def seg_squat(tau):
    img=grade(seq('ms_f/%04d.jpg', 5+(tau-2.0)*30, 67))
    q=(tau-3.68)/0.32
    if q>0:
        q=min(q,1); d=H*1.15*q**2.4
        img=cv2.warpAffine(img,np.float32([[1,0,0],[0,1,d]]),(W,H),borderMode=cv2.BORDER_REPLICATE)
        img=vblur(img,10+420*q**1.6)
    return img
# ---------- C: ascent (city, clouds, Earth) ----------
R0,R1=4.10,191/24
def seg_up(tau):
    x=(tau-4.0)/2.5
    r=R0+(R1-R0)*min(1,max(0,x))**0.9
    img=ref(r)
    b=1-(tau-3.85)/0.5
    if b>0: img=vblur(img,300*b**1.5)
    return img
# ---------- D: brand signature over the Earth ----------
mask=np.load('meglio_mask.npy'); mh,mw=mask.shape
grain=np.load('grain.npy'); grain=cv2.resize(np.tile(grain,(2,2)),(mw,mh),interpolation=cv2.INTER_CUBIC)[:mh,:mw]
MX,MY=(W-mw)//2,930
INK=np.array([125.,72.,63.],np.float32)                    # pen blue sampled from the sting (BGR)
INK_HI=np.array([255.,150.,105.],np.float32)               # same hue, lit
def font(sz,name='/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'):
    return ImageFont.truetype(name,sz)
def name_layer():
    im=Image.new('L',(W,160),0); d=ImageDraw.Draw(im); f=font(58); txt='MARCO TERLIZZI'; sp=9
    wd=sum(d.textlength(ch,font=f) for ch in txt)+sp*(len(txt)-1); x=(W-wd)/2
    for ch in txt: d.text((x,40),ch,font=f,fill=255); x+=d.textlength(ch,font=f)+sp
    return np.asarray(im).astype(np.float32)/255
NAME=name_layer(); NY=MY-190
last=ref(R1)
def put(img,layer_a,color,x0,y0):
    h,w=layer_a.shape; a=layer_a[...,None]
    img[y0:y0+h,x0:x0+w]=img[y0:y0+h,x0:x0+w]*(1-a)+color*a
def seg_title(tau):
    u=tau-6.5
    z=1.0+0.035*u/3.0
    bg=cv2.warpAffine(last,np.float32([[z,0,555*(1-z)],[0,z,945*(1-z)]]),(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    dim=1-0.45*sm(u/0.6)
    img=bg*dim
    # soft dark plate behind the text for contrast
    plate=np.exp(-(((xx-W/2)/520)**2+((yy-(MY+40))/300)**2)**2)[...,None]*0.45*sm(u/0.6)
    img=img*(1-plate)
    # write-on reveal, left to right
    wr=sm(u/0.65); edge=(np.arange(mw,dtype=np.float32)[None,:]/mw)
    rev=np.clip((wr*1.15-edge)/0.08,0,1)
    m=mask*rev
    depth=sm((u-0.75)/0.55)                       # 0 = flat ink on paper grain, 1 = 3D letters
    if depth>0:
        E=int(round(9*depth))
        sh=cv2.GaussianBlur(np.pad(m,((30,30),(30,30))),(0,0),10)[30-14:30-14+mh,30-12:30-12+mw]     # drop shadow
        put(img,np.clip(sh*0.75*depth,0,1),np.array([0,0,0],np.float32),MX,MY)
        for e in range(E,0,-1):                   # extrusion, down-right
            ex=np.zeros_like(m); ex[e:,e:]=m[:mh-e,:mw-e]
            put(img,ex,INK*0.45,MX,MY)
    g=1+0.16*grain*(1-depth)                      # paper grain inside the stroke, fading
    face=INK*(1-0.65*depth)+INK_HI*(0.65*depth)+ (INK_HI-INK)*0.25
    col=np.clip(face[None,None,:]*g[...,None],0,255)
    if depth>0:                                   # bevel light from the top-left
        bl=cv2.GaussianBlur(m,(0,0),2.2); gx=cv2.Sobel(bl,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(bl,cv2.CV_32F,0,1,ksize=3)
        lit=np.clip((gx+gy)*3.0,-1,1)[...,None]*depth
        col=np.clip(col+lit*90,0,255)
    a=m[...,None]
    img[MY:MY+mh,MX:MX+mw]=img[MY:MY+mh,MX:MX+mw]*(1-a)+col*a
    na=sm((u-0.9)/0.45)
    if na>0:
        shn=cv2.GaussianBlur(NAME,(0,0),6)
        put(img,np.clip(shn*0.8*na,0,1),np.array([0,0,0],np.float32),0,NY+3)
        put(img,NAME*na,np.array([255,255,255],np.float32),0,NY)
    return img

def frame(tau):
    if tau<2.0: return seg_face(tau/2.0)
    if tau<3.85: return seg_squat(tau)
    if tau<4.15:
        a=sm((tau-3.85)/0.30); return seg_squat(min(tau,3.999))*(1-a)+seg_up(tau)*a
    if tau<6.5: return seg_up(tau)
    return seg_title(tau)
only=[float(v) for v in sys.argv[2:]]
if only:
    for t in only: cv2.imwrite('c2_%05.2f.jpg'%t,np.clip(frame(t),0,255).astype(np.uint8))
    sys.exit()
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
   '-c:v','libx264','-crf','15','-preset','medium','-pix_fmt','yuv420p',sys.argv[1]],stdin=subprocess.PIPE)
N=int(round(DUR*FPS))
for i in range(N): ff.stdin.write(np.clip(frame(i/FPS),0,255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait(); print('frames',N)
