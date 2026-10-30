"""Perfil de canais sem search.list (~3 unidades por canal): idade, ritmo, mediana, outliers e "frescor".

  python scripts/profile_channels.py --run <pasta> [--top-per-cell 4] [--max 60] [--extra @handle UC... ] [--n 60]

Lê data/channel_candidates.json (gerado por metrics.py) + plan.competitors + --extra.
Saída: data/channels.json

Campos: created (data de criação da conta), first_upload (vídeo mais antigo na amostra; se a amostra cobre o canal
inteiro, é a estreia real), age_days, subs, views, videos, lang (idioma dominante), median_long, median_90d, uploads_90d,
avg_dur_min, top3_share, outliers (vídeos com ≥3× a mediana), fresh (criado ou reativado há ≤ 540 dias e mediana
recente ≥ 10 mil), desc_links_top (links na descrição do vídeo mais visto: proxy de "cita fontes"), top/recent.
Canais antigos reativados (conta velha que muda de formato e decola) aparecem com `reactivated: true`.
`topic_share` = fatia dos uploads amostrados cujo título casa com os termos da célula (keywords ou palavras da consulta):
perto de 1 = canal dedicado ao nicho (concorrente real); perto de 0 = canal gigante de outro tema que só apareceu na busca.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from math import ceil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (LONG_MIN, _STOP, age_days, log, median, norm_text, read_json, set_run, video_lang, write_json,
                    yt_channel_url)
import yt_api


def topic_matchers(plan, cell_keys):
    """Um critério por célula ("id/idioma"): lista de grupos de termos (E entre grupos, OU dentro de cada um), vinda das
    keywords da célula (com ou sem grupos) ou, na falta delas, das palavras de conteúdo da consulta."""
    cells = {c["id"]: c for c in plan.get("cells", [])}
    out, basis = [], "consulta"
    for key in cell_keys:
        cid, _, lang = key.partition("/")
        c = cells.get(cid) or {}
        kw = c.get("keywords")
        kw = (kw.get(lang) or kw.get("*") or []) if isinstance(kw, dict) else (kw or [])
        if kw:
            groups = kw if all(isinstance(g, list) for g in kw) else [kw]
            out.append([[norm_text(t) for t in g] for g in groups])
            basis = "keywords"
            continue
        qs = (c.get("queries") or {}).get(lang) or []
        words = set()
        for q in (qs if isinstance(qs, list) else [qs]):
            words |= {w for w in re.findall(r"\w{4,}", norm_text(q)) if w not in _STOP.get(lang, set())}
        if words:
            out.append([sorted(words)])
    return out, basis


def profile(cid, n=60, fresh_days=540, long_min=LONG_MIN, matchers=None, basis=None, lang=None):
    ch = yt_api.channels([cid])
    if not ch:
        return {"id": cid, "error": "não encontrado"}
    ch = ch[0]
    vids = [yt_api.video_row(v, ch) for v in yt_api.videos(yt_api.uploads(cid, n))]
    longf = [v for v in vids if v["dur"] >= long_min]
    for v in vids:
        v["age"] = age_days(v["published"])
    titles = [norm_text(v["title"]) for v in vids]
    cjk = lang in ("ja", "zh", "ko")
    hit = lambda t: any(all(any(w in t for w in g) for g in groups) for groups in (matchers or []))
    topic_share = round(sum(1 for t in titles if hit(t)) / len(titles), 2) if matchers and titles and not cjk else None
    med = median([v["views"] for v in longf])
    last90 = [v for v in longf if (v["age"] or 999) <= 90]
    s = ch["statistics"]
    created = ch["snippet"]["publishedAt"][:10]
    first = min((v["published"][:10] for v in vids), default=None)
    covers_all = len(vids) >= int(s.get("videoCount", 0) or 0) - 1
    gap_days, regime_start = None, None
    if vids:
        dates = sorted(v["published"][:10] for v in vids)
        from datetime import date
        ds = [date.fromisoformat(x) for x in dates]
        gaps = [(b - a).days for a, b in zip(ds, ds[1:])]
        gap_days = max(gaps) if gaps else 0
        if gaps and gap_days >= 365:  # hiato de um ano ou mais: o regime novo começa no vídeo seguinte
            regime_start = ds[gaps.index(gap_days) + 1].isoformat()
    old = bool(age_days(created) and age_days(created) > fresh_days)
    # reativado = conta velha cujo primeiro vídeo é recente, ou com hiato longo seguido de regime novo recente
    reactivated = bool(old and ((first and covers_all and (age_days(first) or 0) <= fresh_days)
                                or (regime_start and (age_days(regime_start) or 9999) <= fresh_days)))
    langs = Counter(video_lang(v) for v in vids if video_lang(v))
    top = sorted(longf, key=lambda v: -v["views"])[:5]
    med90 = median([v["views"] for v in last90])
    young = (age_days(created) or 9999) <= fresh_days or reactivated
    return {
        "id": cid, "url": yt_channel_url(cid), "title": ch["snippet"]["title"], "handle": ch["snippet"].get("customUrl"),
        "country": ch["snippet"].get("country"), "created": created, "first_upload": first if covers_all else None,
        "age_days": age_days(created), "reactivated": reactivated, "max_gap_days": gap_days,
        "subs": int(s.get("subscriberCount", 0) or 0), "views": int(s.get("viewCount", 0) or 0), "videos": int(s.get("videoCount", 0) or 0),
        "lang": langs.most_common(1)[0][0] if langs else None, "sample": len(vids), "n_long": len(longf),
        "median_long": int(med), "median_90d": int(med90), "uploads_90d": len(last90),
        "uploads_90d_all": sum(1 for v in vids if (v["age"] or 999) <= 90),
        "topic_share": topic_share, "topic_basis": basis if topic_share is not None else None,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "avg_dur_min": round(sum(v["dur"] for v in longf) / len(longf) / 60, 1) if longf else 0,
        "top3_share": round(sum(sorted([v["views"] for v in vids], reverse=True)[:3]) / max(1, sum(v["views"] for v in vids)), 2),
        "outliers": sum(1 for v in longf if med and v["views"] >= 3 * med),
        "fresh": bool(young and max(med90, med) >= 10_000),
        "desc_links_top": top[0]["desc_links"] if top else None,
        "top": [{"id": v["id"], "title": v["title"], "views": v["views"], "published": v["published"][:10], "dur": v["dur"]} for v in top],
        "recent": [{"id": v["id"], "title": v["title"], "views": v["views"], "published": v["published"][:10], "dur": v["dur"]}
                   for v in sorted(longf, key=lambda v: v["age"] or 0)[:5]],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--top-per-cell", type=int, default=4)
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--n", type=int, default=60, help="uploads analisados por canal")
    ap.add_argument("--extra", nargs="*", default=[])
    a = ap.parse_args()
    run = Path(a.run)
    set_run(run)
    plan = read_json(run / "plan.json", {})
    cands = read_json(run / "data" / "channel_candidates.json", [])
    # rodízio por célula: o 1º de cada célula, depois o 2º de cada uma... (células com mais views primeiro).
    # Assim um canal gigante de notícia numa célula não tira a vaga dos canais dedicados das outras.
    by_cell = {}
    for c in cands:
        for cell, v in (c.get("by_cell") or {x: c["views_in_results"] for x in c["cells"]}).items():
            by_cell.setdefault(cell, []).append((v, c["channel_id"]))
    order = sorted(by_cell, key=lambda k: -sum(v for v, _ in by_cell[k]))
    for k in order:
        by_cell[k].sort(reverse=True)
    picked = []
    for rank in range(a.top_per_cell):
        for k in order:
            if rank < len(by_cell[k]) and by_cell[k][rank][1] not in picked and len(picked) < a.max:
                picked.append(by_cell[k][rank][1])
    refs = list(plan.get("competitors", [])) + a.extra
    if (plan.get("reference") or {}).get("type") == "channel":
        refs.insert(0, plan["reference"]["value"])
    for r in refs:
        try:
            cid = yt_api.resolve_channel(r)
            if cid not in picked:
                picked.insert(0, cid)
        except SystemExit as e:
            log(e)
        except yt_api.QuotaExceeded as e:
            log("QUOTA:", e)
            sys.exit(3)
    out_f = run / "data" / "channels.json"
    done = {c["id"]: c for c in read_json(out_f, [])}
    log(f"{len(picked)} canais (~{(1 + 2 * ceil(a.n / 50)) * sum(cid not in done for cid in picked)} unidades gerais; {len(done)} já perfilados)")
    cells_of = {c["channel_id"]: c.get("cells", []) for c in cands}
    all_cells = [f"{c['id']}/{l}" for c in plan.get("cells", []) for l in c.get("queries", {})]
    failed = False
    for cid in picked:
        if cid in done and "error" not in done[cid]:
            continue
        keys = cells_of.get(cid) or all_cells
        matchers, basis = topic_matchers(plan, keys)
        try:
            done[cid] = profile(cid, a.n, matchers=matchers, basis=basis, lang=(keys[0].partition("/")[2] if keys else None))
        except yt_api.QuotaExceeded as e:
            log("QUOTA:", e)
            write_json(out_f, list(done.values()))
            sys.exit(3)
        except Exception as e:
            log("erro", cid, e)
            failed = True
            continue
        p = done[cid]
        if "error" not in p:
            log(f"{p['title'][:28]:<28} {p['lang'] or '-':<3} criado {p['created']} {p['subs']:>10,} insc · med {p['median_long']:>9,} · 90d {p['uploads_90d']:>2} up / med {p['median_90d']:>9,} {'FRESCO' if p['fresh'] else ''}")
        write_json(out_f, list(done.values()))
    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()
