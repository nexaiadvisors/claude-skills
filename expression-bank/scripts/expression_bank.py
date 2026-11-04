#!/usr/bin/env python3
"""Expression bank: turn a few good photos of ONE person into a vetted set of expression portraits.

  expression_bank.py setup                       # check keys + Python packages, download face models
  expression_bank.py check-refs  --refs DIR      # grade the reference photos; exit 2 if not good enough
  expression_bank.py plan        --refs DIR --out DIR [--engines gpt,gemini] [--shots FILE]
  expression_bank.py run         --refs DIR --out DIR --consent [--engines ...] [--max-usd 3] [--retries 1] [--yes]
  expression_bank.py sheet       --out DIR       # rebuild bank-sheet.jpg from scores.json

Keys come from the environment or from ~/.config/expression-bank/.env (override with EXPRESSION_BANK_ENV):
  OPENAI_API_KEY=...     (GPT Image)        GEMINI_API_KEY=...     (Gemini / Nano Banana Pro)
With neither key the script refuses to run. Keys are never printed or written anywhere.

Likeness is scored locally (OpenCV YuNet + SFace, downloaded once from opencv_zoo and checked against
pinned SHA-256 hashes). Each image is compared with the reference photos (median cosine):
  KEEP   >= 0.72     REVIEW 0.55-0.72 (check by eye)     REJECT < 0.55 (not the same person)
Calibrated 2026-11-04 on a real run: the rejected faces a person said "don't look like me" scored 0.08-0.53.
"""
import argparse, base64, hashlib, json, os, statistics, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

VERSION = "1.0.0"
CFG = Path(os.environ.get("EXPRESSION_BANK_HOME", Path.home() / ".config" / "expression-bank"))
ENV_FILE = Path(os.environ.get("EXPRESSION_BANK_ENV", CFG / ".env"))
MODELS = {
    "yunet.onnx": ("https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                   "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"),
    "sface.onnx": ("https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
                   "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"),
}
ENGINES = {  # price per image in USD, measured 2026-11; prices change, so the plan says "estimate"
    "gpt": {"key": "OPENAI_API_KEY", "model": "gpt-image-2.5-sunburst", "usd": 0.07},
    "gemini": {"key": "GEMINI_API_KEY", "model": "gemini-3-pro-image", "usd": 0.134},
}
KEEP, REVIEW = 0.72, 0.55
REF_MIN, REF_MAX = 3, 12
FACE_MIN_PX, SHARP_MIN, DET_MIN, SAME_MIN = 200, 20.0, 0.85, 0.45
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
DEFAULT_SHOTS = [
    ("skeptical", "one eyebrow raised, eyes slightly narrowed, mouth pulled to one side, chin resting on one hand", "a dark grey crew-neck sweater", "a soft yellow wall"),
    ("surprised", "genuinely surprised: eyebrows high, eyes wide, mouth open, both palms on the cheeks", "a navy t-shirt", "a light grey studio wall"),
    ("worried", "brows pulled together and up, one hand partly over the mouth", "a grey quarter-zip pullover", "a muted blue wall"),
    ("frustrated", "one palm pressed to the forehead, eyes half closed, jaw tight", "a dark green flannel shirt", "a warm beige wall"),
    ("exhausted", "slumped, head resting on folded arms on a wooden desk, eyes half open, looking toward camera", "a black hoodie", "a dim office at night"),
    ("excited", "big open smile, pointing with one index finger to the side of the frame", "a white oxford shirt, sleeves rolled", "a bright clean studio"),
    ("curious", "head tilted, both palms up at chest height, small half-smile", "a charcoal blazer over a t-shirt", "a cream wall"),
    ("confident", "confident small smile, holding a blank matte phone toward camera at chest height, screen blank", "a navy work jacket", "a soft orange wall"),
]


def die(msg, code=2):
    print(f"STOP: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------- keys ----------
def load_keys():
    vals = {}
    if ENV_FILE.exists():
        if ENV_FILE.stat().st_mode & 0o077:
            print(f"WARN: {ENV_FILE} is readable by other users; run: chmod 600 {ENV_FILE}", file=sys.stderr)
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip().strip('"').strip("'")
    for e in ENGINES.values():
        if os.environ.get(e["key"]):
            vals[e["key"]] = os.environ[e["key"]]
    return {name: vals[e["key"]] for name, e in ENGINES.items() if vals.get(e["key"])}


def need_keys(engines):
    keys = load_keys()
    if not keys:
        die(f"no API key found. Create {ENV_FILE} with OPENAI_API_KEY=... and/or GEMINI_API_KEY=... "
            f"(see references/setup.md), then chmod 600 it. Nothing was generated.")
    missing = [e for e in engines if e not in keys]
    if missing:
        die(f"no key for {', '.join(missing)}. Add {', '.join(ENGINES[m]['key'] for m in missing)} to {ENV_FILE} "
            f"or drop them with --engines {','.join(e for e in engines if e in keys) or '<engine>'}.")
    return keys


# ---------- face models ----------
def cv():
    try:
        import cv2, numpy  # noqa: F401
    except ImportError:
        die("missing Python packages. Run: python3 -m pip install --user opencv-python numpy")
    return __import__("cv2")


def models():
    cv2 = cv()
    d = CFG / "models"
    d.mkdir(parents=True, exist_ok=True)
    for name, (url, sha) in MODELS.items():
        p = d / name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            print(f"downloading {name} (one time) ...")
            data = urllib.request.urlopen(url, timeout=120).read()
            if hashlib.sha256(data).hexdigest() != sha:
                die(f"{name} failed its checksum; not using it")
            p.write_bytes(data)
    rec = cv2.FaceRecognizerSF.create(str(d / "sface.onnx"), "")
    return cv2, rec, str(d / "yunet.onnx")


class Faces:
    def __init__(self):
        self.cv2, self.rec, self.det_path = models()

    def find(self, path):
        cv2 = self.cv2
        img = cv2.imread(str(path))
        if img is None:
            return None, []
        h, w = img.shape[:2]
        det = cv2.FaceDetectorYN.create(self.det_path, "", (w, h), 0.6)
        _, fs = det.detect(img)
        return img, ([] if fs is None else sorted(fs, key=lambda f: -f[3]))

    def feat(self, img, f):
        return self.rec.feature(self.rec.alignCrop(img, f))

    def sim(self, a, b):
        return float(self.rec.match(a, b, self.cv2.FaceRecognizerSF_FR_COSINE))


# ---------- reference check ----------
def ref_files(d):
    d = Path(d).expanduser()
    if not d.is_dir():
        die(f"{d} is not a folder")
    return sorted(p for p in d.iterdir() if p.suffix.lower() in MIME)


def check_refs(refs_dir, quiet=False):
    files = ref_files(refs_dir)
    F = Faces()
    problems, rows = [], []
    if len(files) < REF_MIN:
        problems.append(f"only {len(files)} photo(s); give {REF_MIN}-{REF_MAX} clear photos of the same person")
    for p in files[:REF_MAX]:
        img, fs = F.find(p)
        r = {"file": p.name}
        if img is None:
            r["issue"] = "cannot read the file"
        elif len([g for g in fs if g[3] >= 0.35 * fs[0][3]]) != 1:  # small faces far behind are fine
            r["issue"] = "more than one main face; crop to just the one person"
        else:
            f = fs[0]
            x, y, w, h = [max(0, int(v)) for v in f[:4]]
            crop = F.cv2.cvtColor(img[y:y + h, x:x + w], F.cv2.COLOR_BGR2GRAY)
            sharp = float(F.cv2.Laplacian(crop, F.cv2.CV_64F).var()) if crop.size else 0.0
            r.update(face_px=h, sharp=round(sharp, 1), det=round(float(f[-1]), 2))
            le, re_, nose = f[4:6], f[6:8], f[8:10]  # landmark x,y pairs
            span = abs(re_[0] - le[0]) or 1
            r["frontal"] = round(1 - abs((nose[0] - le[0]) / span - 0.5) * 2, 2)
            issues = []
            if h < FACE_MIN_PX:
                issues.append(f"face only {h}px tall (need {FACE_MIN_PX}+); use a closer or larger photo")
            if sharp < SHARP_MIN:
                issues.append("face is blurry")
            if float(f[-1]) < DET_MIN:
                issues.append("face is hard to see (dark, covered or turned away)")
            if r["frontal"] < 0.4:
                issues.append("face is turned too far to the side")
            if issues:
                r["issue"] = "; ".join(issues)
            else:
                r["_feat"] = F.feat(img, f)
        rows.append(r)
    good = [r for r in rows if "_feat" in r]
    for r in good:  # same-person check: each photo against the others
        others = [F.sim(r["_feat"], o["_feat"]) for o in good if o is not r]
        r["same"] = round(statistics.median(others), 3) if others else 1.0
        if r["same"] < SAME_MIN:
            r["issue"] = f"does not match the other photos (score {r['same']}); is this the same person?"
    usable = [r for r in good if "issue" not in r]
    if len(usable) < REF_MIN:
        problems.append(f"only {len(usable)} usable photo(s) after the checks; need {REF_MIN}")
    if not quiet:
        for r in rows:
            tag = "OK  " if "issue" not in r else "FLAG"
            extra = f"face {r.get('face_px', '-')}px sharp {r.get('sharp', '-')} match {r.get('same', '-')}"
            print(f"{tag} {r['file']:<28} {extra}  {r.get('issue', '')}")
        for p in problems:
            print(f"STOP: {p}")
    best = sorted(usable, key=lambda r: -r["same"])
    return problems, [Path(refs_dir).expanduser() / r["file"] for r in best], [r["_feat"] for r in usable], F


# ---------- prompts + plan ----------
def load_shots(path):
    if not path:
        return [{"id": s[0], "expression": s[1], "clothes": s[2], "background": s[3]} for s in DEFAULT_SHOTS]
    shots = json.loads(Path(path).read_text())
    for s in shots:
        if not {"id", "expression"} <= set(s):
            die("each shot in --shots needs at least 'id' and 'expression'")
    return shots


def prompt(s, n):
    imgs = ", ".join(f"Image {i + 1}" for i in range(n))
    return (f"Ultra-photoreal portrait photo of the person in {imgs}: the same real person. Keep their exact face: "
            f"same face shape, eyes, nose, mouth, skin tone, hairline and hair. Do not beautify, de-age, slim or change "
            f"their ethnicity. Expression and pose: {s['expression']}. They wear {s.get('clothes', 'casual everyday clothes')}. "
            f"Background: {s.get('background', 'a plain studio wall')}, softly out of focus. Head and shoulders framing, "
            f"face large and sharp in the frame, natural light, 50mm lens. The reference photos only show identity; "
            f"their expression, outfit and pose are not part of this image. No text, letters, logos or watermarks.")


def estimate(engines, shots, retries):
    first = sum(ENGINES[e]["usd"] for e in engines) * len(shots)
    worst = first * (1 + retries)
    return round(first, 2), round(worst, 2)


# ---------- generation ----------
def call_gemini(key, refs, text, out):
    parts = [{"inline_data": {"mime_type": MIME.get(r.suffix.lower(), "image/jpeg"),
                              "data": base64.b64encode(r.read_bytes()).decode()}} for r in refs]
    parts.append({"text": text})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "3:4"}}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{ENGINES['gemini']['model']}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    resp = http_json(req)
    for part in resp.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        blob = part.get("inlineData") or part.get("inline_data")
        if blob and blob.get("data"):
            out.write_bytes(base64.b64decode(blob["data"]))
            return
    raise RuntimeError("Gemini returned no image (it may have refused the request)")


def call_gpt(key, refs, text, out):
    b = uuid.uuid4().hex
    body = bytearray()
    for k, v in {"model": ENGINES["gpt"]["model"], "prompt": text, "size": "1024x1536", "quality": "high", "n": "1"}.items():
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    for f in refs:
        body += (f"--{b}\r\nContent-Disposition: form-data; name=\"image[]\"; filename=\"{f.name}\"\r\n"
                 f"Content-Type: {MIME.get(f.suffix.lower(), 'image/jpeg')}\r\n\r\n").encode() + f.read_bytes() + b"\r\n"
    body += f"--{b}--\r\n".encode()
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=bytes(body), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={b}"})
    resp = http_json(req)
    item = (resp.get("data") or [{}])[0]
    if item.get("b64_json"):
        out.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        out.write_bytes(urllib.request.urlopen(item["url"], timeout=120).read())
    else:
        raise RuntimeError("OpenAI returned no image (it may have refused the request)")


def http_json(req):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode(errors="replace")
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code}: {msg}") from None
    raise RuntimeError("gave up after 3 tries")


def score(F, ref_feats, path):
    img, fs = F.find(path)
    if img is None or not fs:
        return None
    e = F.feat(img, fs[0])
    return round(statistics.median(F.sim(e, r) for r in ref_feats), 3)


def verdict(s):
    return "NO_FACE" if s is None else "KEEP" if s >= KEEP else "REVIEW" if s >= REVIEW else "REJECT"


def run(a):
    engines = [e.strip() for e in a.engines.split(",") if e.strip()]
    bad = [e for e in engines if e not in ENGINES]
    if bad:
        die(f"unknown engine(s) {bad}; use gpt and/or gemini")
    keys = need_keys(engines)
    if not a.consent:
        die("add --consent to confirm the photos are of you, or of someone who agreed to this. "
            "Do not use this on anyone else's face.")
    problems, refs, ref_feats, F = check_refs(a.refs)
    if problems:
        die("fix the reference photos above first; nothing was generated")
    shots = load_shots(a.shots)
    first, worst = estimate(engines, shots, a.retries)
    print(f"PLAN: {len(shots)} shots x {engines} = {len(shots) * len(engines)} images, about ${first} "
          f"(up to ${worst} with retries). Cap ${a.max_usd}.")
    if first > a.max_usd and not a.yes:
        die(f"the first pass alone (${first}) is over the ${a.max_usd} cap; use fewer shots or one engine, "
            f"or re-run with --yes after the user agrees to the cost")
    if worst > a.max_usd:
        print(f"note: retries stop when spending reaches the ${a.max_usd} cap")
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    use = refs[:4]  # the 4 most typical photos; more refs add cost and rarely help
    spent, results = 0.0, {}
    for s in shots:
        for e in engines:
            for t in range(1 + a.retries):
                if spent + ENGINES[e]["usd"] > a.max_usd and not a.yes:
                    print(f"cap reached at ${spent:.2f}; stopping")
                    break
                p = out / e / f"{s['id']}-{t + 1}.png"
                p.parent.mkdir(exist_ok=True)
                try:
                    (call_gpt if e == "gpt" else call_gemini)(keys[e], use, prompt(s, len(use)), p)
                    spent += ENGINES[e]["usd"]
                    sc = score(F, ref_feats, p)
                except Exception as ex:  # noqa: BLE001 - report and continue with the other shots
                    print(f"ERR  {e:6} {s['id']:<12} {ex}")
                    sc, p = None, None
                if p:
                    results.setdefault(s["id"], []).append({"engine": e, "file": str(p.relative_to(out)), "score": sc,
                                                            "verdict": verdict(sc)})
                    print(f"{verdict(sc):7} {sc if sc is not None else '-':>6}  {e:6} {s['id']}")
                if sc is not None and sc >= KEEP:
                    break
    manifest = {"version": VERSION, "refs_used": [r.name for r in use], "thresholds": {"keep": KEEP, "review": REVIEW},
                "spent_usd_estimate": round(spent, 2), "shots": shots, "results": results}
    (out / "scores.json").write_text(json.dumps(manifest, indent=1))
    make_sheet(out)
    return 0


# ---------- sheet ----------
def make_sheet(out):
    cv2 = cv()
    import numpy as np
    m = json.loads((out / "scores.json").read_text())
    bank = out / "bank"
    bank.mkdir(exist_ok=True)
    tiles, summary = [], []
    for sid, rows in m["results"].items():
        rows = [r for r in rows if r["score"] is not None]
        if not rows:
            summary.append(f"{sid}: no usable image")
            continue
        best = max(rows, key=lambda r: r["score"])
        img = cv2.imread(str(out / best["file"]))
        dst = bank / f"{sid}.png"
        cv2.imwrite(str(dst), img)
        best["bank"] = str(dst.relative_to(out))
        h = 560
        img = cv2.resize(img, (int(img.shape[1] * h / img.shape[0]), h))
        color = {"KEEP": (60, 150, 40), "REVIEW": (0, 140, 230), "REJECT": (40, 40, 220)}[best["verdict"]]
        bar = np.full((56, img.shape[1], 3), 255, np.uint8)
        cv2.putText(bar, f"{sid}  {best['score']:.2f} {best['verdict']}", (12, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)
        tiles.append(np.vstack([img, bar]))
        summary.append(f"{sid}: {best['verdict']} {best['score']} ({best['engine']}) -> {best['bank']}")
    if not tiles:
        print("no images to put on a sheet")
        return
    w = max(t.shape[1] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 4, 4, 4, 4 + w - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    cols = min(4, len(tiles))
    while len(tiles) % cols:
        tiles.append(np.full_like(tiles[0], 255))
    rows_img = [np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    sheet = np.vstack(rows_img)
    if sheet.shape[1] > 2000:
        sheet = cv2.resize(sheet, (2000, int(sheet.shape[0] * 2000 / sheet.shape[1])))
    cv2.imwrite(str(out / "bank-sheet.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    (out / "scores.json").write_text(json.dumps(m, indent=1))
    print("\n".join(summary))
    print(f"SHEET {out / 'bank-sheet.jpg'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    c = sub.add_parser("check-refs"); c.add_argument("--refs", required=True)
    for name in ("plan", "run"):
        p = sub.add_parser(name)
        p.add_argument("--refs", required=True); p.add_argument("--out", required=True)
        p.add_argument("--engines", default="gpt,gemini"); p.add_argument("--shots")
        p.add_argument("--retries", type=int, default=1); p.add_argument("--max-usd", type=float, default=3.0)
        if name == "run":
            p.add_argument("--consent", action="store_true"); p.add_argument("--yes", action="store_true")
    s = sub.add_parser("sheet"); s.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.cmd == "setup":
        keys = load_keys()
        print(f"env file: {ENV_FILE} ({'found' if ENV_FILE.exists() else 'MISSING'})")
        for n, e in ENGINES.items():
            print(f"  {e['key']}: {'set' if n in keys else 'missing'}  ({n})")
        models()
        print("face models: ready")
        if not keys:
            die("no API key; see references/setup.md")
        print("SETUP OK")
    elif a.cmd == "check-refs":
        problems, refs, _, _ = check_refs(a.refs)
        if problems:
            sys.exit(2)
        print(f"REFS OK: will use {', '.join(r.name for r in refs[:4])}")
    elif a.cmd == "plan":
        engines = [e for e in a.engines.split(",") if e]
        need_keys(engines)
        problems, refs, _, _ = check_refs(a.refs)
        shots = load_shots(a.shots)
        first, worst = estimate(engines, shots, a.retries)
        print(f"PLAN: {len(shots)} shots ({', '.join(s['id'] for s in shots)}) x {engines}: about ${first}, "
              f"up to ${worst} with {a.retries} retry per failed shot. Cap ${a.max_usd}. Refs: {', '.join(r.name for r in refs[:4])}")
        sys.exit(2 if problems else 0)
    elif a.cmd == "run":
        sys.exit(run(a))
    elif a.cmd == "sheet":
        make_sheet(Path(a.out).expanduser())


if __name__ == "__main__":
    main()
