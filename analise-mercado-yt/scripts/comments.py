"""Comentários como sinal: pedidos de pauta, elogio ao formato, militância/contaminação e perguntas.

  python scripts/comments.py --run <pasta> <videoId> [<videoId> ...] [--max 400] [--political "termo1,termo2"]

Saídas: raw/comments/<id>.json e data/comments.json (resumo por vídeo + citações mais curtidas).
O léxico é multilíngue e aproximado; use o resumo para triagem e leia as citações antes de concluir.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import log, protect_ids, read_json, set_run, vid_of, write_json
import yt_api

REQ = re.compile(
    r"faz(er)? (um|uma|v[ií]deo)|fa[çc]a (um|uma|v[ií]deo)|pr[oó]ximo v[ií]deo|v[ií]deo sobre|parte 2|"
    r"haz (un|una|video)|pr[oó]ximo video|video sobre|segunda parte|"
    r"make (a|one|video)|do a video|next video|part 2|video (on|about)|"
    r"fais (une|un) vid|prochaine vid|mach (ein|mal)|nächstes video|video über|fai un video|prossimo video|"
    r"zr[oó]b (film|odcinek)|fă un video|bir video yap|bikin video", re.I)
FORMAT = re.compile(
    r"edi[çc][aã]o|edici[oó]n|editing|edit\b|montage|schnitt|montaggio|anima[çcti]|animat|motion|"
    r"did[aá]tic|explica(ção|cion|tion)|qualidade|calidad|quality|qualit[ée]|visual|gr[aá]fic|infogr", re.I)
QUESTION = re.compile(r"\?\s*$|\b(como|cómo|how|comment|wie|come|por que|why|pourquoi|warum|perché)\b.*\?", re.I)
# Contaminação por militância: nomes e rótulos que só aparecem em briga política. Termos ambíguos ("direito", "pé
# esquerdo", "liberal", "magazine") ficam de fora de propósito; acrescente os do seu mercado com --political.
DEFAULT_POLITICAL = "|".join([
    r"\blula\b", r"\bbolsonar\w*", r"\bpetist\w*", r"\bcomunis\w*", r"\btrump\b", r"\bbiden\b", r"\bdemocrat\w*",
    r"\brepublican\w*", r"\bmaga\b", r"\bmilei\b", r"\bsheinbaum\b", r"\bamlo\b", r"\bperonis\w*", r"\bkirchner\b",
    r"\bmacron\b", r"\ble pen\b", r"\bafd\b", r"\bmeloni\b", r"\berdogan\b", r"extrema[- ]?(?:direita|esquerda)",
    r"far[- ]?(?:right|left)", r"\besquerdist\w*", r"\bdireitist\w*",
])


def summarize(cs, political_re):
    n = len(cs) or 1
    lk = sum(c["likes"] for c in cs) or 1
    pol = [c for c in cs if political_re.search(c["text"])]
    req = [c for c in cs if REQ.search(c["text"])]
    fmt = [c for c in cs if FORMAT.search(c["text"])]
    q = [c for c in cs if QUESTION.search(c["text"])]
    top = sorted(cs, key=lambda c: -c["likes"])[:8]
    return {
        "n": len(cs),
        "political_share": round(len(pol) / n, 3),
        "political_like_share": round(sum(c["likes"] for c in pol) / lk, 3),
        "format_praise_share": round(len(fmt) / n, 3),
        "request_count": len(req),
        "question_share": round(len(q) / n, 3),
        "requests": [{"text": c["text"][:280], "likes": c["likes"]} for c in sorted(req, key=lambda c: -c["likes"])[:12]],
        "format_quotes": [{"text": c["text"][:280], "likes": c["likes"]} for c in sorted(fmt, key=lambda c: -c["likes"])[:6]],
        "top": [{"text": c["text"][:280], "likes": c["likes"]} for c in top],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--max", type=int, default=400)
    ap.add_argument("--political", help="termos extras separados por vírgula (ex.: nomes de candidatos locais)")
    a = ap.parse_args(protect_ids(sys.argv[1:]))
    run = Path(a.run)
    set_run(run)
    a.ids = [vid_of(x) for x in a.ids]
    pat = DEFAULT_POLITICAL + ("|" + "|".join(re.escape(t.strip()) for t in a.political.split(",") if t.strip()) if a.political else "")
    political_re = re.compile(pat, re.I)
    out = read_json(run / "data" / "comments.json", {})
    quota_stopped, failed = False, []
    for vid in a.ids:
        f = run / "raw" / "comments" / f"{vid}.json"
        cs = read_json(f)
        if cs is None:
            try:
                cs = yt_api.comments(vid, a.max)
            except yt_api.QuotaExceeded as e:
                log("QUOTA:", e); quota_stopped = True; break
            except RuntimeError as e:  # um vídeo com erro não derruba o lote
                log("erro", vid, e); failed.append(vid); continue
            write_json(f, cs)
        out[vid] = summarize(cs, political_re)
        s = out[vid]
        log(f"{vid} n={s['n']} político={s['political_share']:.0%} (curtidas {s['political_like_share']:.0%}) formato={s['format_praise_share']:.0%} pedidos={s['request_count']}")
    write_json(run / "data" / "comments.json", out)
    if quota_stopped:
        sys.exit(3)
    if failed:
        log("SEM COMENTÁRIOS:", ", ".join(failed))
        sys.exit(2)


if __name__ == "__main__":
    main()
