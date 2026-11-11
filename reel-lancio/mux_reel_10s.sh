#!/bin/bash
set -e
ffmpeg -y -loglevel error -i v2_video.mp4 -i marco.mov -i ref.mp4 \
 -f lavfi -i "anoisesrc=color=pink:d=2.0:a=0.9:r=48000" \
 -f lavfi -i "anoisesrc=color=pink:d=2.0:a=0.9:r=48000:seed=7" \
 -f lavfi -i "aevalsrc=(0.5*sin(2*PI*523*t)+0.45*sin(2*PI*1318*t)+0.4*sin(2*PI*2217*t)+0.3*sin(2*PI*3150*t)+0.2*sin(2*PI*4490*t))*exp(-16*t)+0.35*(sin(2*PI*880*max(t-0.09\,0))+sin(2*PI*2640*max(t-0.09\,0)))*exp(-22*max(t-0.09\,0))*gt(t\,0.09):d=0.8:s=48000" \
 -f lavfi -i "anoisesrc=color=pink:d=2.75:a=0.8:r=48000:seed=3" \
 -f lavfi -i "aevalsrc=0.22*sin(2*PI*(80*t+22*t*t))*pow(t/2.6\,1.5):d=2.6:s=48000" \
 -f lavfi -i "aevalsrc=0.9*sin(2*PI*46*t)*exp(-3*t)+0.16*(sin(2*PI*146.83*t)+sin(2*PI*220*t)+sin(2*PI*293.66*t)+0.6*sin(2*PI*440*t))*exp(-2.0*t):d=3.0:s=48000" \
 -filter_complex "
[3:a]bandpass=f=900:width_type=h:w=900,volume='2.8*pow(sin(PI*clip((t-0.10)/0.75,0,1)),2)':eval=frame,aformat=channel_layouts=stereo[b1];
[4:a]bandpass=f=1900:width_type=h:w=1500,volume='2.1*pow(sin(PI*clip((t-1.05)/0.75,0,1)),2)':eval=frame,aformat=channel_layouts=stereo[b2];
[5:a]aecho=0.8:0.6:35:0.25,volume=0.8,adelay=2000:all=1,aformat=channel_layouts=stereo[ck];
[1:a]atrim=1.80:3.00,asetpts=PTS-STARTPTS,aresample=48000,atempo=0.6,afade=t=in:d=0.08,afade=t=out:st=1.75:d=0.3,volume=2.0,adelay=2000:all=1,aformat=channel_layouts=stereo[gym];
[2:a]atrim=4.10:7.96,asetpts=PTS-STARTPTS,aresample=48000,atempo=1.55,afade=t=in:d=0.3,afade=t=out:st=2.25:d=0.25,volume=0.7,adelay=4000:all=1,aformat=channel_layouts=stereo[up];
[6:a]highpass=f=250,lowpass=f=4000,volume='0.75*pow(t/2.7,2.2)':eval=frame,afade=t=out:st=2.62:d=0.12,adelay=3800:all=1,aformat=channel_layouts=stereo[wh];
[7:a]afade=t=out:st=2.5:d=0.1,adelay=3900:all=1,aformat=channel_layouts=stereo[ri];
[8:a]aecho=0.8:0.7:60|140:0.3|0.2,adelay=6500:all=1,aformat=channel_layouts=stereo[ac];
[b1][b2][ck][gym][up][wh][ri][ac]amix=inputs=8:normalize=0:duration=longest,alimiter=limit=0.9,afade=t=out:st=9.0:d=0.5,apad=whole_dur=9.5,atrim=0:9.5[a]" \
 -map 0:v -map "[a]" -c:v libx264 -crf 17 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -movflags +faststart -t 9.5 "$1"
