"""Assemble final events.json from the owner's labels + editorial source.

Usage: python3 -I assemble.py <scratch_dir> <labels_out_dir> <site_dir>
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(__file__))
import events_src as E
scratch, labels, site = sys.argv[1:4]
seed = json.load(open(f"{scratch}/label/seed_full.json")); shots = json.load(open(f"{scratch}/label/shots.json"))
items_meta = {i["id"]: i for i in json.load(open(f"{site}/data/items.json"))}
over = {}
for f in glob.glob(f"{labels}/items/*.json"):
    d = json.load(open(f)); over[os.path.basename(f)[:-5]] = d.get("data", d)
SV = {"stage": "lighting", "gobo": "lighting", "facade": "lighting", "beams": "laser", "laser": "laser", "sfx": "laser", "led": "led", "sound": "sound", "mapping": "mapping"}
def mapsvc(l): return sorted({SV[x] for x in l if x in SV})
clips = {}
for it in seed["items"]:
    c = dict(it); c.update(over.get(it["id"], {})); clips[it["id"]] = c
# promo-level project moves for shots
promo_keep = {}
for pid, (target, keep) in E.PROMO.items():
    for k in keep: promo_keep[k] = target
thin_keep = {s for lst in E.THIN.values() for s in lst}
parents = set(E.THIN) | {k[:k.index("s")] for k in promo_keep} | {"V97"}
out = {}
def is_shot(k): return "s" in k[1:] and k[1:].replace("s", "").isdigit() if False else (len(k) > 3 and "s" in k[1:] and k[k.rindex("s") + 1:].isdigit())
for k, c in clips.items():
    p = c["p"]
    if is_shot(k):
        par = k[:k.rindex("s")]
        if k in promo_keep: p = promo_keep[k]
        elif k in thin_keep and par != "V97":
            p = c["p"]
        else: continue
        if par in E.MOVES: p = E.MOVES[par]
        if par in ("V6",): p = "promo-V6"
    else:
        if k in parents and k not in ("V97",): continue      # parent replaced by its shots
        if k in E.MOVES: p = E.MOVES[k]
    if k == "V97": p = "p12"
    c["p"] = p; out[k] = c
# I28 replaces the logo shot in the ballroom build
out.setdefault("I28", dict(id="I28", p="promo-V95", svc=["gobo"], star=False, ex=False)); out["I28"]["p"] = "promo-V95"
events = []
byp = {}
for k, c in out.items():
    if c.get("ex"): continue
    byp.setdefault(c["p"], []).append(k)
def clip_obj(k):
    c = out[k]; svc = mapsvc(c.get("svc", []))
    if is_shot(k):
        par = k[:k.rindex("s")]; svc = svc or E.SHOT_SVC.get(par, ["lighting"]); svc = E.SHOT_SVC_OVERRIDE.get(k, svc)
        return dict(k=k, t="s", par=par, svc=svc, star=bool(c.get("star")))
    m = items_meta.get(k)
    if not m:
        return None
    return dict(k=k, t=m["t"], f=m["f"], w=m["w"], h=m["h"], d=m.get("d"), svc=svc or m["s"], star=bool(c.get("star") or m["ft"]), types=E.CLIP_TYPES.get(k))
for ev in E.EVENTS:
    ids = []
    for pid in ev["src"]:
        pid = "p34" if pid == "p34-b" else pid
        if pid == "p34": ids += [k for k in byp.get("p34", []) if k not in E.MOVES]
        else: ids += byp.get(pid, [])
    ids = sorted(set(ids))
    cl = [x for x in (clip_obj(k) for k in ids) if x]
    for x in cl:
        if ev.get("svc_force"): x["svc"] = list(ev["svc_force"])
    # order: starred videos, starred photos, then alternate video / photo
    vs = [x for x in cl if x["t"] != "p"]; ps = [x for x in cl if x["t"] == "p"]
    key = lambda x: (not x["star"], x["k"])
    vs.sort(key=key); ps.sort(key=key)
    ordered = []
    while vs or ps:
        if vs: ordered.append(vs.pop(0))
        if ps: ordered.append(ps.pop(0))
    CAP = 16
    if len(ordered) > CAP:
        keep = [x for x in ordered if x["star"]][:CAP // 2]; rest = [x for x in ordered if x not in keep]
        step = len(rest) / (CAP - len(keep)); keep += [rest[int(i * step)] for i in range(CAP - len(keep))]
        ordered = [x for x in ordered if x in keep]
    svc = sorted(set(ev["svc"]) | {s for x in ordered for s in x["svc"]}) if not ev.get("svc_force") else list(ev["svc_force"])
    e = {k: v for k, v in ev.items() if k not in ("src",)}; e["svc"] = svc; e["clips"] = ordered
    events.append(e)
json.dump(events, open(f"{site}/data/events.json", "w"), separators=(",", ":"))
n = sum(len(e["clips"]) for e in events); used = {c["k"] for e in events for c in e["clips"]}
print(len(events), "events", n, "clips; shots:", sum(1 for e in events for c in e["clips"] if c["t"] == "s"))
miss = [k for k in out if k not in used and not out[k].get("ex")]
print("unplaced:", miss)
for e in events: print(f'{e["slug"][:42]:44} {len(e["clips"]):3} {",".join(e["svc"])}')
