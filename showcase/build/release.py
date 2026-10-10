"""Publish the showcase: commit media, pin the CDN link to that commit, rebuild every block, commit again, print what to paste.
Run from anywhere inside the repo, on the branch you are working on:  python3 -I showcase/build/release.py"""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); REPO = subprocess.run(["git", "-C", ROOT, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
def sh(*c, check=True): r = subprocess.run(c, cwd=REPO, capture_output=True, text=True); print(" ".join(c[:3]), "->", (r.stdout + r.stderr).strip()[-200:]); assert r.returncode == 0 or not check, r.stderr; return r.stdout.strip()
br = sh("git", "rev-parse", "--abbrev-ref", "HEAD")
sh("git", "add", "-A", "showcase/media", "showcase/content", "showcase/content/events.json"); sh("git", "commit", "-m", "Showcase: add media and content", check=False); sh("git", "push", "-u", "origin", br)
sha = sh("git", "rev-parse", "HEAD"); base = f"https://cdn.jsdelivr.net/gh/echolightae-ai/Echo@{sha}/showcase/media/"
subprocess.run([sys.executable, "-I", f"{HERE}/build_embed.py", ROOT, base], check=True)
sh("git", "add", "-A", "showcase"); sh("git", "commit", "-m", "Showcase: rebuild blocks", check=False); sh("git", "push", "-u", "origin", br); sha2 = sh("git", "rev-parse", "HEAD")
for L in ("en", "ar"):
    src = f"{ROOT}/embed/showcase-{L}.loader.html"
    t = open(src).read(); t = re.sub(r"Echo@[0-9a-f]{40}/showcase/embed", f"Echo@{sha2}/showcase/embed", t); open(src, "w").write(t)
sh("git", "add", "-A", "showcase"); sh("git", "commit", "-m", "Showcase: point loaders at the new build", check=False); sh("git", "push", "-u", "origin", br)
print("\nDONE. In Squarespace replace the Code Block with showcase/embed/showcase-en.html (and -ar for the Arabic page).")
print("Or, if you use the small loader, replace it with showcase/embed/showcase-en.loader.html.")
