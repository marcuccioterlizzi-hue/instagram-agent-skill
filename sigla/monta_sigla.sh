#!/bin/bash
# usage: build.sh <orbit.mp4> <out.mp4>
set -e
ORB=$1; OUT=$2
ffmpeg -y -loglevel error -i sigla1.mp4 -i "$ORB" -i title.mp4 -filter_complex "
[0:v]trim=0:1.5,setpts=(PTS-STARTPTS)/2.143,fps=30,scale=1080:1920:flags=lanczos,setsar=1[va];
[1:v]trim=0:3.04,setpts=(PTS-STARTPTS)/1.6,fps=30,scale=1080:1920:flags=lanczos,setsar=1[vm];
[2:v]trim=0.5:1.0,setpts=PTS-STARTPTS,fps=30,scale=1080:1920:flags=lanczos,setsar=1[vt1];
[2:v]trim=1.0:2.62,setpts=(PTS-STARTPTS)/1.8,fps=30,scale=1080:1920:flags=lanczos,setsar=1[vt2];
[va][vm][vt1][vt2]concat=n=4:v=1:a=0,fade=t=out:st=3.85:d=0.12[v];
[0:a]atrim=0:1.5,asetpts=PTS-STARTPTS,atempo=2.0,atempo=1.0715,afade=t=out:st=0.62:d=0.08[aa];
[1:a]atrim=0:3.04,asetpts=PTS-STARTPTS,atempo=1.6,afade=t=in:d=0.05,afade=t=out:st=1.82:d=0.08[am];
[2:a]atrim=0.5:1.0,asetpts=PTS-STARTPTS,afade=t=in:d=0.05[at1];
[2:a]atrim=1.0:2.62,asetpts=PTS-STARTPTS,atempo=1.8[at2];
[aa][am][at1][at2]concat=n=4:v=0:a=1,loudnorm=I=-14:TP=-1.5,afade=t=out:st=3.8:d=0.2[a]" \
 -map "[v]" -map "[a]" -t 4.0 -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$OUT"
