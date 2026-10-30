"""Material visual barato para julgar a LACUNA DE FORMATO (eixo G) e o DNA estético.

  python scripts/visual.py sheets --run <pasta> [--cells id1,id2] [--langs pt,es] [--n 15] [--min-score 0]
      -> uma grade de thumbnails por célula (top N long-form nativos) em visual/sheets/<celula>__<lang>.jpg
         Leia as grades (ferramenta Read de imagem) e classifique os estilos dominantes: rosto/apresentador,
         foto/stock, imagem de IA, 3D, motion/ícones, desenho/stick figure, texto gigante, mapa/infográfico.
  python scripts/visual.py palette <img1> [<img2> ...] [--k 8] [--out f.json]
      -> cores dominantes (hex + fração) de prints/thumbs, para a seção de identidade visual.

Requer Pillow para paleta (pip install pillow); as grades caem para ffmpeg se o Pillow faltar.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import log, read_json, write_json
import ytdlp_tools


def sheets(run, cells=None, langs=None, n=15, min_d=0):
    run = Path(run)
    data = read_json(run / "data" / "cells.json", [])
    out = read_json(run / "visual" / "sheets.json", {})  # acumula com execuções anteriores
    failed = []
    for c in data:
        if cells and c["id"] not in cells:
            continue
        if langs and c["lang"] not in langs:
            continue
        if c.get("auto", {}).get("D", 5) < min_d:
            continue
        ids = [t["id"] for t in c["m"]["top"]][:n]
        if not ids:
            continue
        name = f"{c['id']}__{c['lang']}"
        sheet = run / "visual" / "sheets" / f"{name}.jpg"
        got = ytdlp_tools.thumbs(ids, run / "visual" / "thumbs", sheet=sheet)
        if not got or not sheet.exists():
            failed.append(name)
            log("grade", name, "FALHOU: nenhuma thumbnail baixada (rede bloqueada para i.ytimg.com?)")
            out.pop(name, None)
            continue
        kept = [i for i in ids if any(Path(g).stem == i for g in got)]
        out[name] = {"sheet": str(sheet.relative_to(run)), "ids": kept, "missing": [i for i in ids if i not in kept]}
        log("grade", name, f"{len(kept)} de {len(ids)} thumbnails (ordem: da esquerda para a direita, de cima para baixo)")
    write_json(run / "visual" / "sheets.json", out)
    if failed:
        log(f"{len(failed)} grade(s) sem imagem: {', '.join(failed)}. Julgue o eixo G pelos canais e marque measured: false.")
    return out, failed


def palette(images, k=8):
    from PIL import Image
    c = Counter()
    for f in images:
        im = Image.open(f).convert("RGB").resize((96, 54))
        q = im.quantize(colors=k, method=Image.Quantize.MEDIANCUT).convert("RGB")
        for n, col in q.getcolors(96 * 54):
            c[tuple(v // 8 * 8 for v in col)] += n
    tot = sum(c.values()) or 1
    res = [{"hex": "#%02x%02x%02x" % col, "share": round(n / tot, 3)} for col, n in c.most_common(k * 2)]
    merged = []
    for r in res:  # junta tons quase iguais
        rgb = tuple(int(r["hex"][i:i + 2], 16) for i in (1, 3, 5))
        for m in merged:
            mrgb = tuple(int(m["hex"][i:i + 2], 16) for i in (1, 3, 5))
            if sum(abs(a - b) for a, b in zip(rgb, mrgb)) < 36:
                m["share"] = round(m["share"] + r["share"], 3)
                break
        else:
            merged.append(dict(r))
    dark = sum(r["share"] for r in merged if sum(int(r["hex"][i:i + 2], 16) for i in (1, 3, 5)) / 3 < 40)
    return {"colors": merged[:k], "dark_share": round(dark, 3)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheets"); s.add_argument("--run", required=True); s.add_argument("--cells"); s.add_argument("--langs")
    s.add_argument("--n", type=int, default=15); s.add_argument("--min-score", type=int, default=0)
    p = sub.add_parser("palette"); p.add_argument("images", nargs="+"); p.add_argument("--k", type=int, default=8); p.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "sheets":
        res, failed = sheets(a.run, set(a.cells.split(",")) if a.cells else None, set(a.langs.split(",")) if a.langs else None, a.n, a.min_score)
        if failed and not any(k for k in res if k not in failed):
            sys.exit(2)
    else:
        res = palette(a.images, a.k)
        print(json.dumps(res, ensure_ascii=False))
        if a.out:
            write_json(a.out, res)
