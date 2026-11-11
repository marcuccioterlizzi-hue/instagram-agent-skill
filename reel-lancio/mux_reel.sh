#!/bin/bash
set -e
ffmpeg -y -loglevel error -i sigla.mp4 -i part2.mp4 -i ref.mp4 -i marco.mov \
 -f lavfi -i "aevalsrc=0.9*sin(2*PI*48*t)*exp(-4*t)+0.4*sin(2*PI*95*t)*exp(-9*t):d=1.6:s=48000" \
 -f lavfi -i "anoisesrc=color=pink:d=6.2:a=0.7:r=48000" \
 -filter_complex "
[0:v]trim=0:6.55,setpts=PTS-STARTPTS,fps=30,scale=1080:1920:flags=lanczos,setsar=1[v1];
[1:v]setpts=PTS-STARTPTS,fps=30,setsar=1[v2];
[v1][v2]concat=n=2:v=1:a=0[v];
[0:a]atrim=0:7.1,asetpts=PTS-STARTPTS,aresample=48000,afade=t=out:st=6.6:d=0.5,aformat=channel_layouts=stereo[a0];
[2:a]atrim=0:2.0,asetpts=PTS-STARTPTS,aresample=48000,atempo=0.75,afade=t=in:d=0.4,afade=t=out:st=2.0:d=0.65,volume=0.9,adelay=6550:all=1,aformat=channel_layouts=stereo[a1];
[3:a]atrim=1.2:3.0,asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.7,afade=t=out:st=1.5:d=0.3,volume=2.2,adelay=8750:all=1,aformat=channel_layouts=stereo[a2];
[4:a]aformat=channel_layouts=stereo,adelay=9550:all=1[a3];
[2:a]atrim=4.10:8.04,asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.2,afade=t=out:st=3.3:d=0.64,volume=0.8,adelay=10550:all=1,aformat=channel_layouts=stereo[a4];
[5:a]highpass=f=250,lowpass=f=3500,volume='if(lt(t,1.7),pow(t/1.7,2.5),exp(-(t-1.7)*1.0))*0.8':eval=frame,afade=t=out:st=5.2:d=1.0,adelay=10150:all=1,aformat=channel_layouts=stereo[a5];
[a0][a1][a2][a3][a4][a5]amix=inputs=6:normalize=0:duration=longest,alimiter=limit=0.9,afade=t=out:st=15.9:d=0.7,apad=whole_dur=17.15,atrim=0:17.15[a]" \
 -map "[v]" -map "[a]" -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart -t 17.15 "$1"
