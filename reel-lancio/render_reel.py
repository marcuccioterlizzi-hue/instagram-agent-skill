import sys, math, subprocess, numpy as np, cv2
W,H,FPS=1080,1920,30
T_START=6.55                       # output time where python-rendered part begins
out=sys.argv[1]
def sm(x): x=min(1,max(0,x)); return x*x*(3-2*x)
_cache={}
def load(path):
    if path not in _cache:
        if len(_cache)>40: _cache.clear()
        im=cv2.imread(path)
        if im.shape[1]!=W:
            im=cv2.resize(im,(W,H),interpolation=cv2.INTER_CUBIC)
            bl=cv2.GaussianBlur(im,(0,0),2.0); im=cv2.addWeighted(im,1.35,bl,-0.35,0)
        _cache[path]=im.astype(np.float32)
    return _cache[path]
def seq(fmt,idx,n):
    idx=min(max(idx,0),n-1); i=int(math.floor(idx)); f=idx-i
    a=load(fmt%(i+1))
    if f<0.02 or i+1>=n: return a
    return a*(1-f)+load(fmt%(i+2))*f
ref=lambda r: seq('ref_f/%04d.png', r*24, 192)
marco=lambda t: seq('m_f/%04d.jpg', round((t-1.3)*30), 57)
sigla=lambda t: seq('s_f/%04d.png', (t-6.5)*30, 16)

# ---- drop geometry (1080 scale), measured on ref frame index 35
BASE_IDX=35
C=np.array([573.,846.]); RX,RY=126.,156.
W0=330.; R0=np.array([C[0]-0.42*W0, C[1]-0.62*W0*16/9]); S=W/W0
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
rng=np.random.default_rng(7)
stars=np.zeros((H,W,3),np.float32)
for _ in range(900):
    x,y=rng.integers(0,W),rng.integers(0,H); b=rng.random()**3*200+25
    stars[y,x]=(b,b*0.92,b*0.85)
stars=cv2.GaussianBlur(stars,(0,0),0.9)*2.2

def seg_zoom(p):
    e=sm(p/0.82)**1.15
    s=math.exp(math.log(S)*e); g=(1-1/s)/(1-1/S); tl=R0*g
    M=np.float32([[s,0,-s*tl[0]],[0,s,-s*tl[1]]])
    base=cv2.warpAffine(load('ref_f/%04d.png'%(BASE_IDX+1)),M,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    c=s*(C-tl); grow=1+3.6*sm((p-0.40)/0.60)**2
    rx,ry=s*RX*grow,s*RY*grow
    rho=np.sqrt(((xx-c[0])/rx)**2+((yy-c[1])/ry)**2)
    k=0.55*max(0,1-p/0.8)**1.5
    f=1+k*np.clip(rho,0,1.3)**4
    sx=c[0]+(xx-c[0])*f; sy=c[1]+(yy-c[1])*f           # refracted lookup in output coords
    ix0=s*(R0[0]-tl[0]); iy0=s*(R0[1]-tl[1]); isc=W/(s*W0)
    mx=((sx-ix0)*isc).astype(np.float32); my=((sy-iy0)*isc).astype(np.float32)
    mt=1.45+0.80*p
    ins=cv2.remap(marco(mt),mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    q=max(0,1-p/0.85)**1.3
    tint=np.array([1.0,0.93,0.86],np.float32)                 # BGR: slightly cool
    ins=ins*(1-0.30*q)*(1-q+q*tint) + q*np.array([26,16,8],np.float32)
    ins*= (1-0.55*q*np.clip(rho,0,1)**6)[...,None]            # darker rim
    lum=base.max(axis=2); spec=np.clip((lum-190)/50,0,1)[...,None]*q
    ins=ins*(1-spec)+base*spec                                # keep the drop's own highlights
    feather=0.10+0.10*p
    m=np.clip((1-rho)/feather,0,1)[...,None]
    m=m*m*(3-2*m)*sm(p/0.12)                                  # reflection fades in
    return base*(1-m)+ins*m

def vblur(img,k):
    k=int(k)
    if k<3: return img
    return cv2.blur(img,(1,k))
def seg_marco(tau):
    t=2.25+(tau-9.85); img=marco(t)
    q=(tau-10.22)/0.33
    if q>0:
        q=min(q,1); d=H*1.15*q**2.4
        M=np.float32([[1,0,0],[0,1,d]])
        img=cv2.warpAffine(img,M,(W,H),borderMode=cv2.BORDER_REPLICATE)
        img=vblur(img,10+420*q**1.6)
    return img
def seg_ref_up(tau):
    r=4.10+max(0,tau-10.55)
    img=ref(min(r,191/24))
    b=1-(tau-10.40)/0.55
    if b>0: img=vblur(img,300*b**1.5)
    return img
EC=np.array([555.,945.]); ET=np.array([540.,880.])
rr=np.sqrt((xx-555.)**2+(yy-945.)**2); edge=np.clip((545-rr)/70,0,1); edge=(edge*edge*(3-2*edge))
BG=np.median(cv2.imread('ref_f/0192.png')[:40,:40].reshape(-1,3),axis=0).astype(np.float32)
last=ref(191/24)
def seg_recede(u):
    e=sm(u)
    k=math.exp(math.log(0.011)*e)
    c=EC+(ET-EC)*e
    M=np.float32([[k,0,c[0]-k*EC[0]],[0,k,c[1]-k*EC[1]]])
    fr=cv2.warpAffine(last,M,(W,H),flags=cv2.INTER_AREA if k<0.5 else cv2.INTER_LINEAR,borderValue=0)
    m=cv2.warpAffine(edge,M,(W,H),flags=cv2.INTER_LINEAR,borderValue=0)[...,None]
    inside=cv2.warpAffine(np.ones((H,W),np.float32),M,(W,H),borderValue=0)[...,None]
    w=sm(u/0.06); m=inside*(1-w)+m*w
    img=(stars*1.6+BG)*(1-m)+fr*m
    gl=sm((u-0.55)/0.4)
    if gl>0:
        d2=(xx-c[0])**2+(yy-c[1])**2
        glow=(np.exp(-d2/(2*4.0**2))*255+np.exp(-d2/(2*16.0**2))*70)[...,None]*np.array([1.0,0.72,0.42],np.float32)
        img=img+glow*gl
    return img

# highlight position for the sigla->drop speck match
g=cv2.GaussianBlur(ref(0.70).max(axis=2),(0,0),6); g[:300]=0; g[1300:]=0
hy,hx=np.unravel_index(np.argmax(g),g.shape)
def frame(tau):
    if tau<8.55:
        r=(tau-6.55)*0.75; img=ref(r)
        a=(tau-6.55)/0.40
        if a<1:
            a=sm(a); img=sigla(tau)*(1-a)+img*a
        bell=math.exp(-((tau-6.80)/0.16)**2)
        if bell>0.02:
            d2=(xx-hx)**2+(yy-hy)**2
            img=img+(np.exp(-d2/(2*5.0**2))*230+np.exp(-d2/(2*22.0**2))*45)[...,None]*np.array([1.0,0.85,0.7],np.float32)*bell
        return img
    if tau<9.85: return seg_zoom((tau-8.55)/1.30)
    if tau<14.45:
        a=sm((tau-10.40)/0.30)
        if a<=0: return seg_marco(tau)
        if a>=1: return seg_ref_up(tau)
        return seg_marco(min(tau,10.549))*(1-a)+seg_ref_up(tau)*a
    if tau<16.65: return seg_recede((tau-14.45)/2.20)
    return seg_recede(1.0)
T_END=17.15
N=int(round((T_END-T_START)*FPS))
only=[float(x) for x in sys.argv[2:]]
if only:
    for t in only: cv2.imwrite('chk_%05.2f.jpg'%t,np.clip(frame(t),0,255).astype(np.uint8))
    sys.exit()
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
   '-c:v','libx264','-crf','14','-preset','medium','-pix_fmt','yuv420p',out],stdin=subprocess.PIPE)
for i in range(N):
    ff.stdin.write(np.clip(frame(T_START+i/FPS),0,255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait(); print('frames',N)
