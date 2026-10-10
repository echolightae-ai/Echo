"""Build the EchoLight promo reel (9:16, ~31 s) from showcase clips. Usage: python3 -I make_reel.py"""
import subprocess, os
V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media", "v")
F = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
if not os.path.exists(F): F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
# (clip, start, label)
SEG = [("V102", 1.0, "3D MAPPING"), ("V67", 2.0, "LASER SHOWS"), ("V13", 3.0, "STAGE LIGHTING"), ("V104", 12.0, "3D MAPPING"),
       ("V63", 2.0, "LASER SHOWS"), ("V77", 1.0, "LED SCREENS"), ("V103", 3.0, "LASER SHOWS"), ("V30", 2.0, "STAGE LIGHTING"),
       ("V83", 0.5, "STAGE LIGHTING"), ("V122", 3.0, "LED SCREENS"), ("V58", 3.0, "LASER SHOWS")]
D = 2.8; W, H = 720, 1280
cmd = ["ffmpeg", "-v", "error", "-y"]; fl = []
for i, (c, s, lab) in enumerate(SEG):
    cmd += ["-ss", str(s), "-t", str(D + 0.2), "-i", f"{V}/{c}.mp4"]
    fl.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,fps=30,trim=0:{D},setpts=PTS-STARTPTS,"
              f"drawtext=fontfile={F}:text='{lab}':fontcolor=white:fontsize=44:x=(w-tw)/2:y=h-230:shadowcolor=black@0.8:shadowx=2:shadowy=2:alpha='min(1,t*4)',"
              f"fade=t=in:d=0.12,fade=t=out:st={D-0.12}:d=0.12[v{i}]")
n = len(SEG); T = n * D
fl.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[body]")
fl.append(f"color=c=0x05060a:s={W}x{H}:d=2.4:r=30,drawtext=fontfile={F}:text='ECHOLIGHT':fontcolor=white:fontsize=84:x=(w-tw)/2:y=h/2-90:alpha='min(1,t*2)',"
          f"drawtext=fontfile={F}:text='Lighting · LED · Sound · 3D Mapping · Lasers':fontcolor=0x7fd7ff:fontsize=26:x=(w-tw)/2:y=h/2+10:alpha='min(1,max(0,t-0.4)*2)',"
          f"drawtext=fontfile={F}:text='echolight.ae  |  Abu Dhabi':fontcolor=white:fontsize=34:x=(w-tw)/2:y=h/2+80:alpha='min(1,max(0,t-0.8)*2)',fade=t=in:d=0.2[end]")
fl.append("[body][end]concat=n=2:v=1:a=0,format=yuv420p[v]")
tot = T + 2.4
aud = f"aevalsrc='0.55*sin(2*PI*55*t)*exp(-7*mod(t,0.5))+0.08*sin(2*PI*110*t)*(0.5+0.5*sin(2*PI*t/{D}))+0.18*sin(2*PI*880*t)*exp(-30*mod(t+0.25,0.5))*0.3+0.06*sin(2*PI*220*t)':s=44100:d={tot}[a0]"
fl.append(aud); fl.append(f"[a0]afade=t=in:d=0.5,afade=t=out:st={tot-1.5}:d=1.5,volume=0.9[a]")
cmd += ["-filter_complex", ";".join(fl), "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-profile:v", "high", "-crf", "20", "-preset", "slow", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-t", f"{tot:.2f}", "EchoLight-Promo-Reel.mp4"]
subprocess.run(cmd, check=True); print("done", tot)
