"""Raio-X da referência (canal ou vídeo a modelar): histórico completo, pivô, outliers e material para análise de formato.

  python scripts/reference.py --run <pasta> <@handle|URL do canal|URL/ID de vídeo> [--max 300]
         [--transcripts 3] [--frames 2] [--thumbs 24] [--no-ytdlp]

Faz (custo típico: 5–15 unidades):
  1. Canal inteiro via playlistItems + videos.list (não usa search).
  2. Linha do tempo, mediana por fase, detecção de pivô (mudança de patamar de views), outliers (≥3× a mediana móvel).
  3. Com yt-dlp: transcrição dos N mais vistos, grade de thumbnails e prints de trechos dos M mais vistos.
Saída: data/reference.json (+ raw/reference/...). As fases podem ser renomeadas depois em analysis.json.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (MATURE_DAYS, SHORT_MAX, age_days, log, median, pct, protect_ids, read_json, set_run, vid_of,
                    write_json, yt_channel_url, yt_video_url)
import yt_api

try:
    import ytdlp_tools
except Exception:
    ytdlp_tools = None


def detect_pivot(vids, min_side=3):
    """Ponto em que a mediana de log(views) mais muda (vídeos em ordem cronológica, sem Shorts).

    Vídeos com menos de MATURE_DAYS dias ficam de fora: ainda acumulam views e fariam todo canal estável parecer
    em queda nos últimos uploads. `strength` é "forte" quando a mudança passa de 2× e as faixas interquartis dos dois
    lados não se sobrepõem; "fraco" é ruído provável (trate como ausência de pivô)."""
    v = [x for x in vids if x["dur"] > SHORT_MAX and (x.get("age") or 0) >= MATURE_DAYS]
    if len(v) < 2 * min_side:
        return None
    lv = [math.log10(max(x["views"], 10)) for x in v]
    best = None
    for k in range(min_side, len(v) - min_side + 1):
        a, b = median(lv[:k]), median(lv[k:])
        d = b - a
        if best is None or abs(d) > abs(best[1]):
            best = (k, d)
    k, d = best
    before, after = v[:k], v[k:]
    q_before, q_after = (pct(lv[:k], 0.25), pct(lv[:k], 0.75)), (pct(lv[k:], 0.25), pct(lv[k:], 0.75))
    separated = q_after[0] > q_before[1] if d > 0 else q_after[1] < q_before[0]
    return {"index": k, "date": v[k]["published"][:10], "first_video": v[k]["id"], "first_title": v[k]["title"],
            "median_before": int(median([x["views"] for x in before])), "median_after": int(median([x["views"] for x in after])),
            "factor": round(10 ** d, 1), "dur_before_min": round(median([x["dur"] for x in before]) / 60, 1),
            "dur_after_min": round(median([x["dur"] for x in after]) / 60, 1),
            "strength": "forte" if separated and abs(d) >= 0.3 else "fraco",
            "after_median_age_days": int(median([x["age"] for x in after]))}


def title_style(t):
    letters = [c for c in t if c.isalpha()]
    caps = sum(1 for c in letters if c.isupper()) / max(1, len(letters))
    leet = bool(re.search(r"[A-Za-z][0-9][A-Za-z]|[0-9][A-Za-z]{2,}[0-9]", t))
    return {"caps": round(caps, 2), "leet": leet, "len": len(t), "question": "?" in t, "exclaim": "!" in t}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("ref")
    ap.add_argument("--max", type=int, default=300)
    ap.add_argument("--transcripts", type=int, default=3)
    ap.add_argument("--frames", type=int, default=2)
    ap.add_argument("--thumbs", type=int, default=24)
    ap.add_argument("--langs", default="pt,en,es")
    ap.add_argument("--no-ytdlp", action="store_true")
    a = ap.parse_args(protect_ids(sys.argv[1:]))
    a.ref = a.ref[2:] if a.ref.startswith("v:") else a.ref
    run = Path(a.run)
    set_run(run)
    raw = run / "raw" / "reference"
    m = re.search(r"(?:v=|youtu\.be/|shorts/|live/)([\w-]{11})", a.ref)
    cand = m.group(1) if m else (a.ref if re.fullmatch(r"[\w-]{11}", a.ref) else None)
    focus_video, cid = None, None
    if cand and not a.ref.startswith("@"):
        v = yt_api.videos([cand])
        if v:
            focus_video, cid = cand, v[0]["snippet"]["channelId"]
    if not cid:
        cid = yt_api.resolve_channel(a.ref)
    channels = yt_api.channels([cid])
    if not channels:
        raise SystemExit(f"canal indisponível: {cid}")
    dump = {"channel": channels[0]}
    vs = yt_api.videos(yt_api.uploads(cid, a.max))
    dump["videos"] = [yt_api.video_row(x, dump["channel"]) for x in vs]
    write_json(raw / "channel.json", dump)
    ch = dump["channel"]
    vids = sorted(dump["videos"], key=lambda x: x["published"])
    for x in vids:
        x["title_style"] = title_style(x["title"])
        x["age"] = age_days(x["published"])
        x["vpd"] = int(x["views"] / x["age"]) if x["age"] else None
    pivot = detect_pivot(vids)
    longf = [x for x in vids if x["dur"] > SHORT_MAX]
    med_all = median([x["views"] for x in longf])
    tot = sum(x["views"] for x in vids) or 1
    top = sorted(vids, key=lambda x: -x["views"])
    s = ch["statistics"]
    phase_of = lambda x: ("depois" if pivot and x["published"][:10] >= pivot["date"] else "antes") if pivot else "único"
    ref = {
        "channel": {"id": cid, "url": yt_channel_url(cid), "title": ch["snippet"]["title"], "handle": ch["snippet"].get("customUrl"),
                    "country": ch["snippet"].get("country"), "created": ch["snippet"]["publishedAt"][:10],
                    "subs": int(s.get("subscriberCount", 0) or 0), "views": int(s.get("viewCount", 0) or 0), "videos": int(s.get("videoCount", 0) or 0),
                    "description": ch["snippet"].get("description", "")[:1200], "keywords": ch.get("brandingSettings", {}).get("channel", {}).get("keywords")},
        "focus_video": focus_video,
        "pivot": pivot,
        "median_long": int(med_all),
        "top3_share": round(sum(x["views"] for x in top[:3]) / tot, 3),
        "timeline": [{"id": x["id"], "title": x["title"], "date": x["published"][:10], "views": x["views"], "likes": x["likes"],
                      "comments": x["comments"], "dur": x["dur"], "vpd": x["vpd"], "phase": phase_of(x), "desc_links": x["desc_links"],
                      "lang": x["lang"], "style": x["title_style"], "url": yt_video_url(x["id"])} for x in vids],
        "top": [x["id"] for x in top[:10]],
    }
    if not a.no_ytdlp and ytdlp_tools is not None and ytdlp_tools.YTDLP:
        tdir = raw / "transcripts"
        ref["transcripts"] = {}
        for vid in ([focus_video] if focus_video else []) + [x["id"] for x in top if x["id"] != focus_video][: a.transcripts]:
            try:
                txt = ytdlp_tools.transcript(vid, a.langs, tdir)
                (tdir / f"{vid}.txt").write_text(txt, encoding="utf-8")
                ref["transcripts"][vid] = {"file": str((tdir / f"{vid}.txt").relative_to(run)), "words": len(txt.split())}
                if not txt:
                    log("sem legenda/transcrição para", vid, "(sem legendas, rede bloqueada ou idioma fora de --langs)")
            except (Exception, SystemExit) as e:  # ytdlp_tools sai com SystemExit quando falta yt-dlp ou ffmpeg
                log("transcrição falhou", vid, e)
        try:
            ids = [x["id"] for x in top[: a.thumbs]]
            ytdlp_tools.thumbs(ids, raw / "thumbs", sheet=raw / "thumbs_sheet.jpg")
            ref["thumbs_sheet"] = str((raw / "thumbs_sheet.jpg").relative_to(run))
        except (Exception, SystemExit) as e:
            log("thumbs falhou", e)
        ref["frames"] = {}
        for vid in [x["id"] for x in top[: a.frames]]:
            try:
                shots = ytdlp_tools.frames(vid, outdir=raw / "frames")
                if shots:
                    ref["frames"][vid] = str((raw / "frames" / f"{vid}_sheet.jpg").relative_to(run))
            except (Exception, SystemExit) as e:
                log("prints falharam", vid, e)
    else:
        log("yt-dlp indisponível: sem transcrição, thumbs e prints (use a skill `watch` ou rode no PC com yt-dlp + ffmpeg).")
    write_json(run / "data" / "reference.json", ref)
    print(f"{ref['channel']['title']} · {len(vids)} vídeos · mediana long {ref['median_long']:,} · top3 {ref['top3_share']:.0%}")
    if pivot:
        print(f"pivô {pivot['strength']} em {pivot['date']} ({pivot['first_title'][:60]}): mediana {pivot['median_before']:,} → {pivot['median_after']:,} (×{pivot['factor']}), duração {pivot['dur_before_min']} → {pivot['dur_after_min']} min"
              + ("  [fraco: provável ruído, não trate como mudança de formato]" if pivot["strength"] == "fraco" else ""))


if __name__ == "__main__":
    try:
        main()
    except yt_api.QuotaExceeded as e:
        log("QUOTA:", e)
        sys.exit(3)
