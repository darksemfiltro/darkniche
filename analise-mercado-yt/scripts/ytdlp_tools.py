"""Ferramentas sem cota via yt-dlp (+ ffmpeg): busca ampla, listagem de canal, transcrição, thumbs e prints.

Use para BREADTH (muitos idiomas, muitos títulos, sondagem de transposição) e deixe a YouTube Data API
para as buscas com filtros precisos (região, idioma, data, duração) e para dados confiáveis de canal.

Uso (python scripts/ytdlp_tools.py ...):
  search "<consulta>" [--n 40] [--sort views|relevance|date] [--upload year|month|week|any]
         [--duration long|medium|short|any] [--hl de] --out f.json
  channel <@handle|URL> [--n 200] --out f.json          -> uploads com views/duração (sem datas)
  transcript <videoId> [--langs pt,en] --out f.txt       -> texto limpo com marcas de tempo [mm:ss]
  thumbs <id> [<id>...] --dir pasta [--sheet grade.jpg]  -> baixa hqdefault + monta grade (contact sheet)
  frames <videoId> [--at 10,30,55,80] [--seg 8] --dir pasta  -> prints de trechos (480p) + grade
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import importlib.util
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import log, protect_ids, vid_of, write_json

_YTDLP_EXE = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
YTDLP = ([_YTDLP_EXE] if _YTDLP_EXE else
         [sys.executable, "-m", "yt_dlp"] if importlib.util.find_spec("yt_dlp") else None)
FFMPEG = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")


def _need(tool, name):
    if not tool:
        raise SystemExit(f"{name} não encontrado no PATH. Instale com: pip install -U yt-dlp  /  winget install Gyan.FFmpeg")


def _varint(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def make_sp(sort="views", upload="year", vtype="video", duration="any"):
    """Monta o parâmetro `sp` dos filtros da busca do YouTube (protobuf + base64).
    sort: relevance=0 · date=2 · views=3 · rating=1 | upload: hour=1 today=2 week=3 month=4 year=5
    duration: short(<4min)=1 · long(>20min)=2 · medium(4–20min)=3"""
    s = {"relevance": 0, "rating": 1, "date": 2, "views": 3}.get(sort, 3)
    up = {"any": 0, "hour": 1, "today": 2, "week": 3, "month": 4, "year": 5}.get(upload, 5)
    du = {"any": 0, "short": 1, "long": 2, "medium": 3}.get(duration, 0)
    filt = b""
    if up:
        filt += b"\x08" + _varint(up)
    if vtype == "video":
        filt += b"\x10\x01"
    if du:
        filt += b"\x18" + _varint(du)
    msg = (b"\x08" + _varint(s) if s else b"") + (b"\x12" + _varint(len(filt)) + filt if filt else b"")
    return base64.b64encode(msg).decode()


def _run_json(args):
    _need(YTDLP, "yt-dlp")
    try:
        p = subprocess.run([*YTDLP, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    except subprocess.TimeoutExpired:
        raise RuntimeError("yt-dlp excedeu o tempo limite (180 s). Confira rede e disponibilidade do vídeo.") from None
    out = p.stdout.strip()
    if p.returncode != 0 and not out:
        raise RuntimeError("yt-dlp falhou: " + p.stderr.strip()[-600:])
    data = json.loads(out) if out else None
    if data is None:
        raise RuntimeError("yt-dlp não retornou dados (rede bloqueada, vídeo indisponível ou yt-dlp desatualizado: pip install -U yt-dlp). " + p.stderr.strip()[-300:])
    return data


def search(query, n=40, sort="views", upload="year", duration="any", hl=None):
    sp = make_sp(sort, upload, "video", duration)
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query, "sp": sp})
    args = ["--flat-playlist", "-J", "--playlist-end", str(n), "--no-warnings"]
    if hl:
        args += ["--extractor-args", f"youtube:lang={hl}"]
    data = _run_json(args + [url])
    rows = []
    for e in data.get("entries", []) or []:
        if not e or not e.get("id"):
            continue
        rows.append({"id": e["id"], "title": e.get("title"), "views": e.get("view_count"), "dur": e.get("duration"),
                     "channel": e.get("channel") or e.get("uploader"), "channel_id": e.get("channel_id"),
                     "url": f"https://www.youtube.com/watch?v={e['id']}", "source": "ytdlp"})
    return rows


def channel(ref, n=200):
    ref = ref.strip()
    url = ref if ref.startswith("http") else (f"https://www.youtube.com/{ref}" if ref.startswith("@") else f"https://www.youtube.com/channel/{ref}")
    url = url.rstrip("/") + "/videos"
    data = _run_json(["--flat-playlist", "-J", "--playlist-end", str(n), "--no-warnings", url])
    return {"channel": data.get("channel") or data.get("uploader"), "channel_id": data.get("channel_id"),
            "subs": data.get("channel_follower_count"),
            "videos": [{"id": e["id"], "title": e.get("title"), "views": e.get("view_count"), "dur": e.get("duration")}
                       for e in data.get("entries", []) or [] if e and e.get("id")]}


def _vtt_to_text(vtt):
    out, last = [], ""
    for block in re.split(r"\n\n+", vtt):
        m = re.search(r"(\d+):(\d+):(\d+)\.\d+ -->", block)
        if not m:
            continue
        t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        lines = [re.sub(r"<[^>]+>", "", l).strip() for l in block.splitlines()[1:]]
        txt = " ".join(l for l in lines if l and "-->" not in l)
        if not txt or txt == last:
            last = txt if txt else last
            continue
        new = txt[len(last):].strip() if txt.startswith(last) else txt
        out.append(f"[{t // 60:02d}:{t % 60:02d}] {new}")
        last = txt
    return "\n".join(out)


def transcript(video_id, langs="pt,en,es", outdir=None):
    _need(YTDLP, "yt-dlp")
    outdir = Path(outdir or ".")
    outdir.mkdir(parents=True, exist_ok=True)
    pat = ",".join(f"{l}.*,{l}" for l in langs.split(","))
    subprocess.run([*YTDLP, "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", pat, "--sub-format", "vtt",
                    "--no-warnings", "-o", str(outdir / "%(id)s.%(ext)s"), f"https://www.youtube.com/watch?v={video_id}"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    files = sorted(glob.glob(str(outdir / f"{video_id}*.vtt")), key=lambda f: (".orig" in f, "-" in Path(f).stem.split(".")[-1]))
    if not files:
        return ""
    return _vtt_to_text(Path(files[0]).read_text(encoding="utf-8", errors="replace"))


def thumbs(ids, outdir, sheet=None, cols=5):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    got = []
    for vid in ids:
        f = outdir / f"{vid}.jpg"
        if not f.exists():
            try:
                urllib.request.urlretrieve(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", f)
            except Exception as e:
                log("thumb falhou", vid, e)
                continue
        got.append(f)
    if sheet and got:
        _sheet(got, sheet, cols)
    return [str(g) for g in got]


def _sheet(files, out, cols=5, w=320):
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageDraw
        ims = [Image.open(f).convert("RGB") for f in files]
        ims = [im.resize((w, int(im.height * w / im.width))) for im in ims]
        h = max(im.height for im in ims)
        rows = (len(ims) + cols - 1) // cols
        S = Image.new("RGB", (cols * (w + 6) + 6, rows * (h + 22) + 6), (17, 17, 17))
        d = ImageDraw.Draw(S)
        for i, (im, f) in enumerate(zip(ims, files)):
            x, y = 6 + (i % cols) * (w + 6), 6 + (i // cols) * (h + 22)
            S.paste(im, (x, y))
            d.text((x + 2, y + h + 4), f"{i + 1:02d} {Path(f).stem}", fill=(220, 220, 220))
        S.save(out, quality=85)
    except ImportError:
        _need(FFMPEG, "ffmpeg")
        lst = Path(out).with_suffix(".txt")
        lst.write_text("".join(f"file '{Path(f).resolve().as_posix()}'\n" for f in files), encoding="utf-8")
        rows = (len(files) + cols - 1) // cols
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-vf", f"scale={w}:-2,tile={cols}x{rows}:padding=6:margin=6", "-frames:v", "1", str(out)])


def frames(video_id, at_pct=(10, 30, 55, 80), seg=8, outdir="frames", every=2):
    """Baixa só trechos curtos em 480p (rápido) e tira 1 print a cada `every` s. Retorna lista de imagens."""
    _need(YTDLP, "yt-dlp"); _need(FFMPEG, "ffmpeg")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    info = _run_json(["-J", "--no-warnings", f"https://www.youtube.com/watch?v={video_id}"])
    dur = info.get("duration") or 600
    shots = []
    for p in at_pct:
        start = max(0, int(dur * p / 100))
        seg_file = outdir / f"{video_id}_{p:02d}.mp4"
        if not seg_file.exists():
            subprocess.run([*YTDLP, "-q", "--no-warnings", "-f", "bv*[height<=480]/b[height<=480]/b",
                            "--download-sections", f"*{start}-{start + seg}", "--force-keyframes-at-cuts",
                            "-o", str(seg_file), f"https://www.youtube.com/watch?v={video_id}"], check=True, timeout=300)
        if seg_file.exists():
            pat = outdir / f"{video_id}_{p:02d}_%02d.jpg"
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(seg_file), "-vf", f"fps=1/{every},scale=480:-2", str(pat)], check=True, timeout=120)
            shots += sorted(glob.glob(str(outdir / f"{video_id}_{p:02d}_*.jpg")))
    if shots:
        _sheet(shots, outdir / f"{video_id}_sheet.jpg", cols=4, w=360)
    return shots


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("q"); s.add_argument("--n", type=int, default=40); s.add_argument("--sort", default="views")
    s.add_argument("--upload", default="year"); s.add_argument("--duration", default="any"); s.add_argument("--hl"); s.add_argument("--out", required=True)
    c = sub.add_parser("channel"); c.add_argument("ref"); c.add_argument("--n", type=int, default=200); c.add_argument("--out", required=True)
    t = sub.add_parser("transcript"); t.add_argument("vid"); t.add_argument("--langs", default="pt,en,es"); t.add_argument("--out", required=True)
    h = sub.add_parser("thumbs"); h.add_argument("ids", nargs="+"); h.add_argument("--dir", required=True); h.add_argument("--sheet")
    f = sub.add_parser("frames"); f.add_argument("vid"); f.add_argument("--at", default="10,30,55,80"); f.add_argument("--seg", type=int, default=8)
    f.add_argument("--dir", required=True)
    sp = sub.add_parser("sp"); sp.add_argument("--sort", default="views"); sp.add_argument("--upload", default="year"); sp.add_argument("--duration", default="any")
    a = ap.parse_args(protect_ids(sys.argv[1:]))
    for k in ("vid", "ids"):
        if hasattr(a, k):
            setattr(a, k, [vid_of(x) for x in getattr(a, k)] if k == "ids" else vid_of(getattr(a, k)))
    if a.cmd == "search":
        write_json(a.out, search(a.q, a.n, a.sort, a.upload, a.duration, a.hl))
    elif a.cmd == "channel":
        write_json(a.out, channel(a.ref, a.n))
    elif a.cmd == "transcript":
        txt = transcript(a.vid, a.langs, Path(a.out).parent)
        Path(a.out).write_text(txt, encoding="utf-8")
        log(f"{len(txt.split())} palavras")
    elif a.cmd == "thumbs":
        print(json.dumps(thumbs(a.ids, a.dir, a.sheet)))
    elif a.cmd == "frames":
        print(json.dumps(frames(a.vid, [int(x) for x in a.at.split(",")], a.seg, a.dir)))
    elif a.cmd == "sp":
        print(make_sp(a.sort, a.upload, "video", a.duration))
