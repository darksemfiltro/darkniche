"""Cria a pasta de uma análise com um plan.json inicial (idiomas, regiões e padrões já preenchidos).

  python scripts/init_run.py "Título da análise" [--ref @handle|URL] [--langs pt,en,es-AR,...] [--dir analises]
                             [--after 365] [--mode api|ytdlp|both]

Saída: <dir>/<slug>-<AAAA-MM>/plan.json  (imprime o caminho). Depois o agente preenche `cells` e `probes`.

Idiomas: --langs; senão o perfil (idiomas_principais; perfis antigos: idiomas_triagem); sem perfil, pt, en e es.
Aceita idioma-REGIÃO (es-AR, pt-PT, en-GB, fr-CA): a região vira o regionCode da busca. Idioma fora da tabela de
regiões fica sem região (a busca omite regionCode) e com tamanho de mercado assumido: confira os dois no plan.json.
Cada idioma tem uma região por plano; para medir outro país do mesmo idioma, faça outra análise.

Modo padrão: api quando existe chave da YouTube Data API; sem chave, ytdlp (sem data, inscritos e idioma
declarado: as métricas de frescor e de tamanho de canal ficam sem medição).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HOME, MARKET_SIZE, load_env, parse_lang_spec, read_json, slug, write_json, vid_of, yt_video_url


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("title")
    ap.add_argument("--ref", help="@handle, URL de canal ou de vídeo (omita no modo ideia ou nicho)")
    ap.add_argument("--langs")
    ap.add_argument("--dir", default="analises")
    ap.add_argument("--after", type=int, default=365)
    ap.add_argument("--mode", choices=["api", "ytdlp", "both"])
    a = ap.parse_args()
    prof = read_json(HOME / "perfil.json", {})
    given = a.langs.split(",") if a.langs else prof.get("idiomas_principais") or prof.get("idiomas_triagem") or []
    specs = [s for s in given if str(s).strip()] or ["pt", "en", "es"]  # "pt,en," não cria um idioma vazio
    mode = a.mode or ("api" if load_env().get("YT_API_KEY") else "ytdlp")
    today = date.today()
    run = Path(a.dir) / f"{slug(a.title, 40)}-{today:%Y-%m}"
    if (run / "plan.json").exists():
        raise SystemExit(f"Já existe: {run / 'plan.json'} (edite esse ou escolha outro título)")
    ref = None
    if a.ref:
        kind = "video" if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid_of(a.ref)) else "channel"
        url = yt_video_url(vid_of(a.ref)) if kind == "video" else a.ref if a.ref.startswith("http") else f"https://www.youtube.com/{a.ref if a.ref.startswith('@') else 'channel/' + a.ref}"
        ref = {"type": kind, "value": a.ref, "url": url}
    languages, seen = [], set()
    for spec in specs:
        lang, region, label = parse_lang_spec(spec)
        if lang in seen:
            continue
        seen.add(lang)
        languages.append({"lang": lang, "region": region, "label": label, "size": MARKET_SIZE.get(lang),
                          "size_assumed": lang not in MARKET_SIZE})
    plan = {
        "title": a.title, "slug": run.name, "created": today.isoformat(),
        "reference": ref, "reference_display": {"label": a.ref, "url": ref["url"]} if ref else None,
        "defaults": {"after_days": a.after, "order": "viewCount", "duration": "longform", "pages": 1, "mode": mode,
                     "probe_mode": "ytdlp", "probe_after_days": 730},  # sondagens: yt-dlp (0 buscas); com chave, ele é enriquecido pela API
        "languages": languages,
        "cells": [],
        "probes": [],
        "competitors": [],
        "_exemplo_celula": {"id": "invest-iniciantes", "label": "Investimentos para iniciantes", "niche": "finanças pessoais",
                            "subniche": "investimentos", "lens": "explicador didático", "bend": "novo ângulo",
                            "queries": {"pt": ["como começar a investir", "investir para iniciantes"], "en": "how to start investing"},
                            "keywords": {"pt": ["invest"]}, "exclude": ["bitcoin ao vivo"]},
        "_exemplo_sondagem": {"id": "titulo-exemplo", "source": {"id": "<videoId>", "title": "<título original>", "views": 0, "lang": "en"},
                              "queries": {"pt": "<mesma promessa, escrita como um nativo escreveria>", "es": "<idem>"}},
    }
    write_json(run / "plan.json", plan)
    print(run)
    pend = [l["label"] for l in languages if not l["region"]] + [f"{l['label']} (tamanho assumido)" for l in languages if l["size_assumed"]]
    if pend:
        print("Confira no plan.json: " + ", ".join(pend), file=sys.stderr)


if __name__ == "__main__":
    main()
