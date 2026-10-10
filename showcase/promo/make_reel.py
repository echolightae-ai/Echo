"""Build the EchoLight promo reel (9:16, ~28 s, cut on the beat of music.py). Usage: python3 -I make_reel.py
Edit SHOTS to change the cut: (file in media/v without .mp4, start second, length in beats)."""
import subprocess, os
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.join(HERE, "..", "media", "v")
F = next(f for f in ["/usr/share/fonts/opentype/inter/Inter-Bold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if os.path.exists(f))
B = 60 / 124; FPS = 30; W, H = 720, 1280; I0, D0 = 12, 24
SHOTS = [("full-V38", 36, 4), ("V100", 44, 4), ("full-V9", 24, 4),                                   # intro
         ("V108", 4, 2), ("V106", 3, 2), ("V104", 38, 2), ("V112", 44, 2), ("full-V97", 10, 2), ("V122", 4, 2),  # build
         ("V67", 5, 2), ("V103", 8, 2), ("V58", 11, 2), ("full-V38", 80, 1), ("full-V38", 100, 1), ("V13", 11, 2), ("V110", 12, 2),
         ("full-V6", 78, 1), ("full-V6", 104, 1), ("V30", 8, 2), ("full-V95", 11, 2), ("full-V93", 6, 2), ("V88", 6, 2), ("V100", 22, 2), ("V108", 16, 2),  # drop
         ("full-V9", 120, 4)]                                                                          # outro
NB = sum(s[2] for s in SHOTS); TAIL = 1.2
subprocess.run(["python3", "-I", f"{HERE}/music.py", str(NB), "/tmp/reel_music.wav"], check=True)
cmd = ["ffmpeg", "-v", "error", "-y"]; fl = []; beat = 0
for i, (c, s, nb) in enumerate(SHOTS):
    f0 = round(beat * B * FPS); last = i == len(SHOTS) - 1
    f1 = round((beat + nb) * B * FPS) + (round(TAIL * FPS) if last else 0); n = f1 - f0
    cmd += ["-ss", str(s), "-t", f"{n / FPS + 0.3:.2f}", "-i", f"{V}/{c}.mp4"]
    push = 0.10 if beat < D0 else 0.06
    v = (f"[{i}:v]fps={FPS},scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,"
         f"zoompan=z='1+{push}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},"
         f"trim=end_frame={n},setpts=PTS-STARTPTS,eq=contrast=1.07:saturation=1.12:gamma=0.97,vignette=PI/5")
    if i == 0: v += ",fade=t=in:d=0.6"
    if beat >= D0 and beat < NB - 4 and beat % 4 == 0: v += ",fade=t=in:d=0.12:color=white"
    if last: v += f",fade=t=out:st={n / FPS - 1.4:.2f}:d=1.4"
    fl.append(v + f"[v{i}]"); beat += nb
fl.append("".join(f"[v{i}]" for i in range(len(SHOTS))) + f"concat=n={len(SHOTS)}:v=1:a=0,"
          f"drawtext=fontfile={F}:text='E C H O L I G H T':fontcolor=white@0.55:fontsize=22:x=36:y=60,format=yuv420p[v]")
tot = NB * B + TAIL
cmd += ["-i", "/tmp/reel_music.wav", "-filter_complex", ";".join(fl), "-map", "[v]", "-map", f"{len(SHOTS)}:a",
        "-c:v", "libx264", "-profile:v", "high", "-crf", "19", "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-t", f"{tot + 0.6:.2f}", f"{HERE}/EchoLight-Promo-Reel.mp4"]
subprocess.run(cmd, check=True); print("done", round(tot, 1), "s,", NB, "beats")
