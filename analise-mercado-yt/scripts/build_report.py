"""Monta o relatório interativo a partir da pasta da análise.

  python scripts/build_report.py --run <pasta> [--embed] [--max-img-width 960]

Lê: plan.json, analysis.json (escrito pelo agente), data/cells.json, data/channels.json, data/probes.json,
    data/reference.json, data/comments.json, data/signals/*.json, visual/sheets.json
Gera:
  data.json                 — tudo consolidado (fonte única do relatório)
  relatorio.html            — página completa para abrir no navegador (imagens por caminho relativo)
  relatorio.artifact.html   — corpo para publicar como Artifact (sem <html>/<head>; com --embed as imagens
                              locais viram data: URI, porque o Artifact bloqueia imagens externas)
"""
from __future__ import annotations

import argparse
import base64
import glob
import io
import json
import os
import re
import sys
from pathlib import Path
import mimetypes
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import glob_files, log, read_json, write_json, normalize_quota
from score import compute, ORDER

SKILL = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL / "assets" / "report" / "template.html"
APPJS = SKILL / "assets" / "report" / "app.js"


def _b64(data):
    """Base64 sem a sequência barra, m, barra. O navegador ignora a quebra de linha dentro de um data URI; ela evita
    que verificadores de caminho (essa sequência é a unidade M do Git Bash) acusem texto ao acaso na imagem."""
    return re.sub(r"(?i)/(?=m/)", "/\n", base64.b64encode(data).decode())


def img_src(run, rel, embed, maxw):
    if not rel:
        return None
    if urlsplit(str(rel)).scheme in ("http", "https"):
        return rel
    if str(rel).startswith("data:image/"):
        return rel
    p = (run / rel).resolve()
    if not p.is_relative_to(run.resolve()):
        log("imagem fora da análise, ignorada:", rel)
        return None
    if not p.exists():  # imagem que não chegou a ser baixada: melhor nenhuma do que uma quebrada
        log("imagem ausente, ignorada:", rel)
        return None
    if not embed:
        return Path(rel).as_posix()
    try:
        from PIL import Image
        im = Image.open(p).convert("RGB")
        if im.width > maxw:
            im = im.resize((maxw, int(im.height * maxw / im.width)))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=72, optimize=True)
        data = buf.getvalue()
    except ImportError:
        data = p.read_bytes()
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    except Exception as e:  # arquivo que não é imagem (download cortado): melhor nenhuma imagem do que abortar o relatório
        log("imagem ilegível, ignorada:", rel, f"({type(e).__name__})")
        return None
    else:
        mime = "image/jpeg"
    return "data:" + mime + ";base64," + _b64(data)


def assemble(run, embed=False, maxw=960):
    plan = read_json(run / "plan.json", {})
    an = read_json(run / "analysis.json", {})
    cells = read_json(run / "data" / "cells.json", [])
    labels = {c["id"]: c for c in plan.get("cells", [])}
    for c in cells:
        c["label"] = labels.get(c["id"], {}).get("label", c.get("label", c["id"]))
        c["lens"] = c.get("lens") or labels.get(c["id"], {}).get("lens")
    cells_map = {f"{c['id']}__{c['lang']}": c for c in cells}
    opps = an.get("opportunities", [])
    for o in opps:
        o["computed"] = compute(o, an.get("weights"), cells_map)
    opps.sort(key=lambda o: (ORDER.index(o["computed"]["tier"]), -o["computed"]["total"]))

    # pesquisa em tempo real: {"research": "r3"} vira link + data de acesso + tipo e confiança da fonte
    research = read_json(run / "data" / "research.json", [])
    rindex = {r["id"]: r for r in research}

    def resolve(items):
        out = []
        for e in items or []:
            r = rindex.get(e.get("research")) if isinstance(e, dict) and e.get("research") else None
            if r:
                text = e.get("text") or r["claim"] + (f" ({r['value']}{(' ' + r['unit']) if r.get('unit') else ''})" if r.get("value") else "")
                out.append({**{k: v for k, v in e.items() if k != "research"}, "text": text, "url": r["url"], "accessed": r["accessed"],
                            "note": e.get("note") or f"{r.get('domain', '')} · {r['type']} · confiança {r['confidence']}"})
            else:
                out.append(e)
        return out
    for o in opps:
        o["evidence"] = resolve(o.get("evidence"))
    for mk in an.get("markets", []) or []:
        mk["evidence"] = resolve(mk.get("evidence"))
    if an.get("production"):
        an["production"]["sources"] = resolve(an["production"].get("sources"))
    if an.get("reference"):
        an["reference"]["examples"] = resolve(an["reference"].get("examples"))
    an["sources"] = resolve(an.get("sources"))
    for s in an["sources"]:  # fonte vinda da pesquisa: o rótulo é o fato
        if s.get("research") is None and s.get("text") and not s.get("label"):
            s["label"] = s["text"]

    titles = {}  # id → título, para rotular comentários e evidências
    for c in cells:
        for t in c["m"].get("top", []):
            titles.setdefault(t["id"], t.get("title"))
    for f in glob_files(run / "raw" / "search") + glob_files(run / "raw" / "probes"):
        for r in (read_json(f) or {}).get("rows", []):
            titles.setdefault(r["id"], r.get("title"))
    comments = read_json(run / "data" / "comments.json", {})

    ref = read_json(run / "data" / "reference.json")
    if not ref and an.get("reference"):  # modo ideia: sem canal de referência; o vetor de formato vem do agente
        ref = dict(an["reference"])
        if comments:
            ref["comments"] = {k: {**v, "title": v.get("title") or titles.get(k)} for k, v in comments.items()}
        ref["gallery"] = [x for x in ({**g, "src": img_src(run, g["src"], embed, maxw)} for g in (ref.get("gallery") or [])) if x["src"]] or None
    elif ref:
        ref.update(an.get("reference", {}))
        for t in ref.get("timeline", []):
            titles[t["id"]] = t["title"]
        if comments:
            ref["comments"] = {k: {**v, "title": v.get("title") or titles.get(k)} for k, v in comments.items()}
        gal = list(ref.get("gallery") or [])
        if not gal:
            if ref.get("thumbs_sheet"):
                gal.append({"src": ref["thumbs_sheet"], "caption": "Thumbnails mais vistas da referência"})
            for vid, sheet in (ref.get("frames") or {}).items():
                t = next((x["title"] for x in ref.get("timeline", []) if x["id"] == vid), vid)
                gal.append({"src": sheet, "caption": f"Prints de trechos · {t}"})
        ref["gallery"] = [x for x in ({**g, "src": img_src(run, g["src"], embed, maxw)} for g in gal) if x["src"]] or None
        if ref.get("phase_labels"):
            for v in ref.get("timeline", []):
                for p in ref["phase_labels"]:
                    if p["from"] <= v["date"] <= p.get("to", "9999"):
                        v["phase"] = p["key"]
            ref["phases"] = [{"key": p["key"], "label": p["label"]} for p in ref["phase_labels"]]

    sheets = read_json(run / "visual" / "sheets.json", {})
    fg = an.get("format_gap", [])
    for g in fg:
        key = f"{g.get('cell')}__{g.get('lang')}"
        if key in sheets and not g.get("sheet_src"):
            g["sheet_src"] = img_src(run, sheets[key]["sheet"], embed, maxw)
        elif g.get("sheet_src"):
            g["sheet_src"] = img_src(run, g["sheet_src"], embed, maxw)
        g.setdefault("label", labels.get(g.get("cell"), {}).get("label"))

    signals = {"wiki": [], "suggest": [], "trending": []}
    for f in glob_files(run / "data" / "signals", "wiki_*.json"):
        w = read_json(f)
        signals["wiki"].append({"concept": w.get("concept") or w.get("seed"), **w})
    for f in glob_files(run / "data" / "signals", "suggest_*.json"):
        s = read_json(f)
        signals["suggest"].append({"lang": s["lang"], "seed": s["seed"], "count": s.get("count", 0), "top": s.get("all", [])[:20]})
    for f in glob_files(run / "data" / "signals", "trending_*.json"):
        signals["trending"].append(read_json(f))

    probe_sources = [{"id": p["id"], "title": p.get("source", {}).get("title"), "video_id": p.get("source", {}).get("id"),
                      "views": p.get("source", {}).get("views"), "lang": p.get("source", {}).get("lang")} for p in plan.get("probes", [])]
    probes = read_json(run / "data" / "probes.json", [])
    review = {(r["probe"], r["lang"]): r for r in an.get("probe_review", [])}
    for p in probes:  # o agente corrige falsos positivos/negativos da comparação automática de títulos
        r = review.get((p["probe"], p["lang"]))
        if r:
            p["auto_status"], p["status"], p["reviewed"], p["note"] = p["status"], r.get("status", p["status"]), True, r.get("note")
    q = normalize_quota(read_json(run / "data" / "quota.json", {}))
    pilot_quota = normalize_quota(read_json(run / "triage" / "data" / "quota.json", {}))
    for bucket in ("searches", "units", "requests"):
        q[bucket] += pilot_quota[bucket]
    meta = {"title": plan.get("title", "Análise de mercado"), "date": plan.get("created") or an.get("date"),
            "languages": plan.get("languages", []), "reference": plan.get("reference_display") or (
                {"label": plan["reference"].get("value"), "url": plan["reference"].get("url")} if plan.get("reference") else None),
            "quota": normalize_quota(an.get("quota")) if an.get("quota") else q, **an.get("meta", {})}
    if (run / "triage" / "data" / "quota.json").exists():
        meta["quota"] = q  # contador real do piloto + análise prevalece sobre estimativa editorial
    channels = [c for c in read_json(run / "data" / "channels.json", []) if not c.get("error")]
    stamps = [c.get("fetched_at") for c in cells] + [c.get("fetched_at") for c in channels] + [r.get("added_at") for r in research]
    meta.setdefault("data_stamp", max([s for s in stamps if s], default=None))  # quando o dado mais recente foi coletado
    data = {
        "meta": meta, "summary": an.get("summary"), "method": an.get("method"), "reference": ref,
        "bends": an.get("bends"), "cells": cells, "markets": an.get("markets"), "research": research or None,
        "signals": signals if any(signals.values()) else None,
        "channels": channels,
        "format_gap": fg, "probes": probes, "probe_sources": probe_sources,
        "opportunities": opps, "production": an.get("production"), "risks": an.get("risks"), "plan": an.get("plan"),
        "limitations": an.get("limitations"), "sources": an.get("sources"),
    }
    return data


def render(data, standalone):
    tpl = TEMPLATE.read_text(encoding="utf-8")
    app = APPJS.read_text(encoding="utf-8")
    title = re.sub(r"<[^>]+>", "", data["meta"].get("title_html") or "") or data["meta"].get("title", "Análise de mercado")
    desc = data["meta"].get("description") or (data.get("summary") or {}).get("lead_plain") or "Análise de mercado do YouTube por nicho e idioma."
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    # "<" vira <: "</script>" e também "<!--<script>" (que prende o fechamento do script) ficam inofensivos
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    # Insere o payload por último: texto do usuário pode conter os próprios marcadores do template.
    html = (tpl.replace("__TITLE__", esc(title)).replace("__DESCRIPTION__", esc(desc[:300]))
            .replace("/*__APP__*/", app).replace("/*__DATA__*/null", payload))
    if standalone:
        head, body = html.split("</style>", 1)
        html = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + head + "</style>\n</head>\n<body>" + body + "</body>\n</html>\n")
    return html


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--embed", action="store_true", help="embute imagens locais (necessário para Artifact)")
    ap.add_argument("--max-img-width", type=int, default=960)
    a = ap.parse_args()
    run = Path(a.run)
    if not (run / "plan.json").is_file() or not (run / "analysis.json").is_file():
        raise SystemExit("plan.json e analysis.json são obrigatórios para gerar o relatório")
    data = assemble(run, embed=a.embed, maxw=a.max_img_width)
    write_json(run / "data.json", data)
    (run / "relatorio.html").write_text(render(data, True), encoding="utf-8")
    data_art = assemble(run, embed=a.embed, maxw=a.max_img_width)
    art = render(data_art, False)
    (run / "relatorio.artifact.html").write_text(art, encoding="utf-8")
    mb = len(art.encode("utf-8")) / 1e6
    log(f"ok · relatorio.html + relatorio.artifact.html ({mb:.1f} MB) · {len(data['cells'])} células · {len(data['opportunities'])} oportunidades")
    if mb > 15:
        log("AVISO: acima de 15 MB; reduza --max-img-width ou o número de grades embutidas.")


if __name__ == "__main__":
    main()
