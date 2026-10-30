"""Calcula métricas por célula (nicho × idioma) e resume as sondagens de títulos.

  python scripts/metrics.py --run <pasta> [--long 480] [--fresh-days 540]

Saídas: data/cells.json · data/probes.json · data/channel_candidates.json

Métricas por célula. Só vídeos do idioma-alvo contam como oferta. Vídeo sem idioma identificável NÃO vira nativo: fica
em `n_unknown_lang` e, passando de 20% dos resultados, liga a flag `idioma_nao_verificado` (a lacuna fica limitada).
Exceção: idiomas que o título não consegue confirmar (fa, ur, bn, ta, sk, hr, sr…; `common.can_verify_lang`): ali o
sem-idioma entra como nativo provisório e a célula leva a flag `idioma_nao_verificavel`.
  Volume e demanda
    n, n_long, med / p90 / top_views (views long-form), k100 (≥100 mil), m1 (≥1 mi), saturation (k100 / n_long)
    vpd_p25 / vpd_p50 / vpd_p75 (views por dia, só vídeos com ≥ 14 dias: mede o ritmo, não o acúmulo),
    vpd_lo / vpd_hi (IC de 90% da mediana por bootstrap), med_vpd (mediana com todos os vídeos datados),
    supply_est (estimativa do YouTube de vídeos que casam com a busca; aproximada, teto 1.000.000)
    Tendência não sai desta amostra: o topo por views subrepresenta vídeos novos. Use signals.py (Wikipédia, autocomplete,
    em alta) e uploads_90d dos canais perfilados.
  Concorrência
    active (canais com views suficientes na célula), n_eff (canais efetivos = 1 ÷ HHI; 2 canais com 100% = 2),
    dominance (fatia dos 3 maiores), size_mix (fatia de vídeos e de views por faixa de inscritos),
    small_view_share (views vindas de canais < 100 mil inscritos), small_wins (≥ 100 mil views de canal < 100 mil insc.),
    outlier_density (views/inscritos ≥ 3), fresh_share (views de canais criados há ≤ fresh-days), recent_share
  Qualidade da amostra
    lang_purity (nativos entre os de idioma conhecido), short_share (Shorts nos resultados), offtopic, flags
  auto: D, L, V sugeridos (1–5) com a base usada. O agente revisa e justifica.
"""
from __future__ import annotations

import argparse
import glob
import os
import random
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (LONG_MIN, MATURE_DAYS, SHORT_MAX, _STOP, age_days, can_verify_lang, market_size, median, norm_text, pct,
                    glob_files, read_json, same_script, size_known, video_lang, write_json)
from plan_tools import raw_is_current

_norm = norm_text
TOP_N = 15  # vídeos guardados por célula (grade de thumbs, explorador, evidências)
BANDS = [("<10k", 0, 10_000), ("10k–100k", 10_000, 100_000), ("100k–1M", 100_000, 1_000_000), (">1M", 1_000_000, 10 ** 13)]
VPD_CUTS = (25, 125, 500, 2000)        # views/dia equivalentes em EN → D 1..5
MED_CUTS = (5e3, 25e3, 1e5, 4e5)       # views equivalentes em EN → D 1..5 (quando não há datas)


def ladder(x, cuts):
    """1 + quantos cortes x alcança: 4 cortes → nota 1..5."""
    return 1 + sum(1 for c in cuts if x >= c)


def _term(x):
    """Termo de filtro como regex sobre o título sem acentos e sem caixa. Espaço na ponta marca palavra inteira:
    " ia " casa no começo, no fim e antes de vírgula, e não casa "iate". Termo vazio não casa nada."""
    s = "" if x is None else str(x)
    core = _norm(s).strip()
    if not core:
        return None
    return re.compile((r"(?<!\w)" if s[:1].isspace() else "") + re.escape(core) + (r"(?!\w)" if s[-1:].isspace() else ""))


def relevant(row, cell, lang):
    """Filtro opcional por célula: `keywords` (o título deve conter ao menos um), `exclude` (o título não pode conter
    nenhum) e `exclude_channels` (nome ou ID de canal a descartar). Aceitam lista global ou dicionário por idioma
    ("*" vale para todos). Comparação sem acentos e sem caixa.

    `keywords` também aceita **grupos**: uma lista de listas exige um termo de CADA grupo (E entre grupos, OU dentro de
    cada um). Serve para cruzar dois temas, ex.: [["chatgpt", "claude", " ia "], ["financ", "planilha", "gastos"]]."""
    title = _norm(row.get("title"))
    def pick(v):
        if isinstance(v, dict):
            return v.get(lang) or v.get("*") or []
        return v or []
    kw, ex = pick(cell.get("keywords")), pick(cell.get("exclude"))
    if any(t.search(title) for t in map(_term, ex) if t):
        return False
    chan = _norm(row.get("channel")) + " " + (row.get("channel_id") or "").lower()
    if any(n and n in chan for n in map(_norm, pick(cell.get("exclude_channels")))):
        return False
    groups = kw if kw and all(isinstance(g, list) for g in kw) else ([kw] if kw else [])
    groups = [[t for t in map(_term, g) if t] for g in groups]
    return all(any(t.search(title) for t in g) for g in groups if g)


def load_rows(run, plan=None):
    cells = {c["id"]: c for c in (plan or {}).get("cells", [])}
    by = defaultdict(lambda: {"rows": {}, "queries": set(), "modes": set(), "offtopic": 0, "total": None, "fetched": None})
    for f in glob_files(Path(run) / "raw" / "search"):
        d = read_json(f)
        if plan and not raw_is_current(d, plan):
            print(f"AVISO: resultado antigo ignorado: {Path(f).name}; rode scan.py para atualizar", file=sys.stderr)
            continue
        k = (d["cell"], d["lang"])
        by[k]["queries"].add(d["query"])
        by[k]["modes"].add(d["mode"])
        t = (d.get("meta") or {}).get("total_results")
        if t is not None:  # variantes da consulta se sobrepõem: vale a maior estimativa, não a soma
            by[k]["total"] = max(by[k]["total"] or 0, t)
        if d.get("fetched_at") and (by[k]["fetched"] or "") < d["fetched_at"]:
            by[k]["fetched"] = d["fetched_at"]
        for r in d["rows"]:
            if r["id"] in by[k]["rows"]:
                continue
            if not relevant(r, cells.get(d["cell"], {}), d["lang"]):
                by[k]["offtopic"] += 1
                continue
            by[k]["rows"][r["id"]] = r
    return by


def boot_ci(xs, n=300, seed=7, lo=0.05, hi=0.95):
    """Intervalo de 90% da mediana por bootstrap (determinístico). None com menos de 5 amostras."""
    xs = [x for x in xs if x is not None]
    if len(xs) < 5:
        return None
    rng = random.Random(seed)
    meds = sorted(st.median([rng.choice(xs) for _ in xs]) for _ in range(n))
    return [meds[int(lo * (n - 1))], meds[int(hi * (n - 1))]]


def size_mix(rows):
    """Fatia de vídeos e de views por faixa de inscritos do canal. None quando nenhum vídeo traz inscritos."""
    ws = [r for r in rows if r.get("subs")]
    if not ws:
        return None
    tv = sum(r.get("views") or 0 for r in ws) or 1
    out = {}
    for name, lo, hi in BANDS:
        sel = [r for r in ws if lo <= r["subs"] < hi]
        out[name] = {"videos": round(len(sel) / len(ws), 2), "views": round(sum(r.get("views") or 0 for r in sel) / tv, 2)}
    return out


def cell_metrics(rows, lang, long_min, fresh_days, active_min=10_000, window_days=365, total_est=None):
    rows = list(rows)
    vl = [video_lang(r) for r in rows]
    verifiable = can_verify_lang(lang)
    native = [r for r, l in zip(rows, vl) if l == lang]
    unknown = [r for r, l in zip(rows, vl) if not l]
    if not verifiable:  # a escrita não separa fa de ar: o rótulo genérico da escrita conta como idioma não identificado
        unknown += [r for r, l in zip(rows, vl) if l and l != lang and same_script(l, lang)]
    known_n = len(rows) - len(unknown)
    pool = native if verifiable else native + unknown  # sem detector por título: vale o metadado e o filtro da busca
    longn = [r for r in pool if (r.get("dur") or 0) >= long_min]
    v = sorted([r.get("views") or 0 for r in longn], reverse=True)
    big = [r for r in longn if (r.get("views") or 0) >= 100_000]
    ch_views = defaultdict(int)
    for r in longn:
        ch_views[r.get("channel_id") or r.get("channel")] += r.get("views") or 0
    active = sum(1 for c, s in ch_views.items() if s >= active_min)
    tot = sum(ch_views.values()) or 1
    hhi = sum((s / tot) ** 2 for s in ch_views.values()) if longn else None
    dom = sum(sorted(ch_views.values(), reverse=True)[:3]) / tot
    with_subs = [r for r in longn if r.get("subs")]
    outl = sum(1 for r in with_subs if (r.get("views") or 0) / max(r["subs"], 1000) >= 3)
    with_created = [r for r in longn if r.get("ch_created")]
    tot_created = sum(r.get("views") or 0 for r in with_created)
    fresh_v = sum(r.get("views") or 0 for r in with_created if (age_days(r["ch_created"]) or 9999) <= fresh_days)
    dated = [r for r in longn if age_days(r.get("published"))]
    recent = sum(1 for r in dated if age_days(r["published"]) <= 90)
    vpd = [(r.get("views") or 0) / age_days(r["published"]) for r in dated]
    vpd_mature = [(r.get("views") or 0) / age_days(r["published"]) for r in dated if age_days(r["published"]) >= MATURE_DAYS]
    ci = boot_ci(vpd_mature)
    mix = size_mix(with_subs)
    small_views = (mix["<10k"]["views"] + mix["10k–100k"]["views"]) if mix else None
    recent_share = recent / len(dated) if dated else None
    top = sorted(longn, key=lambda r: -(r.get("views") or 0))[:TOP_N]
    flags = []
    if not verifiable and unknown:
        flags.append("idioma_nao_verificavel")
    elif unknown and len(unknown) / max(1, len(rows)) >= 0.2:
        flags.append("idioma_nao_verificado")
    if longn and len(dated) / len(longn) < 0.5:
        flags.append("sem_datas")
    if longn and len(with_subs) / len(longn) < 0.5:
        flags.append("sem_inscritos")
    if len(longn) >= 30 and len(big) / len(longn) >= 0.8:
        flags.append("cabeca_saturada")
    if ci and ci[0] > 0 and ci[1] / ci[0] > 3:
        flags.append("mediana_instavel")
    if total_est is not None and total_est >= 1_000_000:
        flags.append("oferta_acima_do_teto")
    return {
        "n": len(rows), "n_native": len(native), "n_unknown_lang": len(unknown), "n_long": len(longn),
        "short_share": round(sum(1 for r in rows if 0 < (r.get("dur") or 0) <= SHORT_MAX) / len(rows), 2) if rows else 0,
        "lang_purity": round(len(native) / known_n, 2) if known_n else 0,
        "med": int(median(v)), "p90": int(pct(v, 0.9)), "top_views": v[0] if v else 0,
        "k100": len(big), "m1": sum(1 for x in v if x >= 1_000_000),
        "saturation": round(len(big) / len(longn), 2) if longn else None,
        "active": active, "dominance": round(dom, 2) if longn else None,
        "hhi": round(hhi, 3) if hhi is not None else None, "n_eff": round(1 / hhi, 1) if hhi else None,
        "small_wins": sum(1 for r in big if 0 < (r.get("subs") or 0) < 100_000),
        "small_view_share": round(small_views, 2) if small_views is not None else None,
        "size_mix": mix,
        "outlier_density": round(outl / len(with_subs), 2) if with_subs else None,
        "fresh_share": round(fresh_v / tot_created, 2) if tot_created else None,
        "recent_share": round(recent_share, 2) if recent_share is not None else None,
        "med_vpd": int(median(vpd)) if vpd else 0,
        "n_mature": len(vpd_mature),
        "vpd_p25": int(pct(vpd_mature, 0.25)) if vpd_mature else None,
        "vpd_p50": int(median(vpd_mature)) if vpd_mature else None,
        "vpd_p75": int(pct(vpd_mature, 0.75)) if vpd_mature else None,
        "vpd_lo": int(ci[0]) if ci else None, "vpd_hi": int(ci[1]) if ci else None,
        "supply_est": total_est,
        "avg_dur_min": round(sum(r.get("dur") or 0 for r in longn) / len(longn) / 60, 1) if longn else 0,
        "flags": flags,
        "top": [{"id": r["id"], "title": r.get("title"), "views": r.get("views"), "channel": r.get("channel"),
                 "channel_id": r.get("channel_id"), "subs": r.get("subs"), "published": (r.get("published") or "")[:10],
                 "dur": r.get("dur"), "lang": video_lang(r)} for r in top],
        "foreign_top": [{"id": r["id"], "title": r.get("title"), "views": r.get("views"), "lang": video_lang(r)}
                        for r in sorted([r for r in rows if r not in pool], key=lambda r: -(r.get("views") or 0))[:3]],
    }


def auto_scores(cells, plan=None):
    """Sugestões automáticas de D (demanda), L (lacuna de oferta) e V (velocidade). O agente revisa e justifica.

    D usa o ritmo (mediana de views/dia dos vídeos maduros do topo) convertido em "equivalente EN" (÷ tamanho do
    mercado); sem datas, cai para a mediana de views. Pouca amostra limita a nota (n_long < 5 → máx. 3; < 3 → 1), e
    idioma sem tamanho de mercado conhecido também (máx. 3).
    L conta canais ativos (limiar de views proporcional ao mercado) e sobe se a busca no idioma devolve muito
    conteúdo estrangeiro (só com 10+ resultados de idioma conhecido). Concentração (n_eff, dominance) vai para o julgamento.
    V mede a fatia de views de canais frescos; sem datas de criação, usa a fatia de views de canais pequenos.
    """
    base = defaultdict(list)
    for c in cells:
        if c["m"]["n_long"] >= 5:
            base[c["lang"]].append(c["m"]["med"])
    base = {l: (median(v) or 1) for l, v in base.items()}
    for c in cells:
        m, lang = c["m"], c["lang"]
        size, flags = market_size(lang, plan), list(m["flags"])
        known = size_known(lang, plan)
        eq = m["med"] / size if size else m["med"]
        vpd_eq = m["vpd_p50"] / size if (m["vpd_p50"] is not None and size) else None
        if m["n_long"] < 3:
            D, basis = 1, "sem amostra"
        else:
            if vpd_eq is not None and m["n_mature"] >= 3:
                D, basis = ladder(vpd_eq, VPD_CUTS), "views/dia"
            else:
                D, basis = ladder(eq, MED_CUTS), "mediana de views"
            if m["n_long"] < 5:
                D = min(D, 3)
            if not known:
                D = min(D, 3)
                flags.append("tamanho_assumido")
        a = m["active"]
        L = 5 if a <= 2 else 4 if a <= 5 else 3 if a <= 10 else 2 if a <= 20 else 1
        if m["lang_purity"] < 0.5 and (m["n"] - m["n_unknown_lang"]) >= 10:
            L = min(5, L + 1)
        if "idioma_nao_verificado" in flags:
            L = min(L, 3)  # com o idioma de parte do topo sem confirmar, a oferta pode estar subestimada: não dá para chamar de lacuna
        fs = m["fresh_share"]
        if m["n_long"] < 5:
            V = 1
        elif fs is not None:
            V = 5 if fs >= 0.3 else 4 if fs >= 0.15 else 3 if fs >= 0.05 else 2 if fs > 0 else 1
        elif m["small_view_share"] is not None:
            V = ladder(m["small_view_share"], (0.1, 0.3, 0.5))
            flags.append("V_por_canais_pequenos")
        else:
            V = 1
            flags.append("V_sem_dados")
        c["auto"] = {"D": D, "L": L, "V": V, "d_basis": basis, "med_en_equiv": int(eq),
                     "vpd_en_equiv": int(vpd_eq) if vpd_eq is not None else None, "market_size": size,
                     "lang_baseline_med": int(base.get(lang, 0)),
                     "evidence": "fraca" if m["n_long"] < 5 else "parcial" if {"sem_datas", "sem_inscritos", "idioma_nao_verificado", "idioma_nao_verificavel"} & set(flags) else "ok",
                     "empty": m["n_long"] < 3, "flags": sorted(set(flags))}
    return cells


CJK = re.compile(r"[぀-ヿ一-鿿가-힯]")


def _tok(s, lang=None):
    """Palavras de conteúdo do título (sem palavras-função do idioma); bigramas de caracteres em CJK."""
    s = (s or "").lower()
    if lang in ("ja", "zh", "ko") or CJK.search(s):
        chars = "".join(CJK.findall(s))
        return {chars[i:i + 2] for i in range(len(chars) - 1)} | {w for w in re.findall(r"[a-z0-9]{3,}", s)}
    stop = _STOP.get(lang, set())
    return {w for w in re.findall(r"\w{3,}", s) if w not in stop}


def probe_summary(run, long_min, plan=None):
    out = []
    for f in glob_files(Path(run) / "raw" / "probes"):
        d = read_json(f)
        if plan and not raw_is_current(d, plan, probe=True):
            continue
        q = _tok(d["query"], d["lang"])
        native = [r for r in d["rows"] if video_lang(r) == d["lang"] and (r.get("dur") or 0) >= long_min]
        scored = []
        for r in native:
            shared = len(q & _tok(r.get("title"), d["lang"]))
            sim = shared / max(1, len(q))
            # uma palavra em comum não prova que o ângulo existe (era a causa dos falsos "existe")
            scored.append((sim if shared >= min(2, len(q)) else 0.0, r.get("views") or 0, r))
        scored.sort(key=lambda x: (-x[0], -x[1]))
        best = scored[0][2] if scored else None
        strong = [r for s, vw, r in scored if s >= 0.34 and vw >= 10_000]
        weak = [r for s, vw, r in scored if s >= 0.34]
        unknown = sum(1 for r in d["rows"] if not video_lang(r) or not r.get("dur"))
        unknown_share = unknown / len(d["rows"]) if d["rows"] else 1.0  # uma linha sem duração não invalida a sondagem
        status = "existe" if strong else ("fraco" if weak else "inconclusivo" if unknown_share >= 0.2 else "lacuna")
        out.append({"probe": d["probe"], "lang": d["lang"], "query": d["query"], "status": status,
                    "n": len(d["rows"]), "n_native": len(native),
                    "best": {"id": best["id"], "title": best.get("title"), "views": best.get("views"), "channel": best.get("channel")} if best else None})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--long", type=int, default=LONG_MIN)
    ap.add_argument("--fresh-days", type=int, default=540)
    a = ap.parse_args()
    run = Path(a.run)
    plan = read_json(run / "plan.json", {})
    labels = {c["id"]: c for c in plan.get("cells", [])}
    by = load_rows(run, plan)
    if not by and (run / "triage" / "raw" / "search").exists():
        print(f"AVISO: dados do piloto estão em {run / 'triage'}. Para métricas do piloto, use --run '{run / 'triage'}'; selection.py propose/select recebe '{run}'.")
    cells, cands = [], defaultdict(lambda: {"views": 0, "cells": set(), "title": None, "by_cell": defaultdict(int)})
    for (cid, lang), d in sorted(by.items()):
        meta = labels.get(cid, {})
        window = int(((plan.get("defaults") or {}).get("after_days", 365)) or 365)
        window = int(({**(meta.get("filters") or {}), **((meta.get("filters_lang") or {}).get(lang) or {})}).get("after_days", window) or 0)
        m = cell_metrics(d["rows"].values(), lang, a.long, a.fresh_days, max(500, int(10_000 * market_size(lang, plan))),
                         window or 730, d["total"])
        m["offtopic"] = d["offtopic"]
        cells.append({"id": cid, "label": meta.get("label", cid), "lens": meta.get("lens"), "bend": meta.get("bend"),
                      "niche": meta.get("niche"), "subniche": meta.get("subniche"),
                      "lang": lang, "queries": sorted(d["queries"]), "modes": sorted(d["modes"]),
                      "fetched_at": d["fetched"], "window_days": window, "m": m})
        for r in d["rows"].values():  # só canais com vídeo nativo long-form na célula: perfilar outro idioma desperdiça cota
            vl = video_lang(r)
            if (r.get("dur") or 0) >= a.long and r.get("channel_id") and (vl == lang or (not can_verify_lang(lang) and (vl is None or same_script(vl, lang)))):
                k = r["channel_id"]
                cands[k]["views"] += r.get("views") or 0
                cands[k]["cells"].add(f"{cid}/{lang}")
                cands[k]["by_cell"][f"{cid}/{lang}"] += r.get("views") or 0
                cands[k]["title"] = r.get("channel")
                cands[k]["subs"] = r.get("subs")
    cells = auto_scores(cells, plan)
    write_json(run / "data" / "cells.json", cells)
    cl = sorted(({"channel_id": k, "title": v["title"], "subs": v.get("subs"), "views_in_results": v["views"], "cells": sorted(v["cells"]),
                  "by_cell": dict(v["by_cell"])}
                 for k, v in cands.items()), key=lambda x: -x["views_in_results"])
    write_json(run / "data" / "channel_candidates.json", cl)
    probes = probe_summary(run, a.long, plan)
    write_json(run / "data" / "probes.json", probes)
    print(f"{len(cells)} células · {len(cl)} canais candidatos · {len(probes)} sondagens")
    for c in cells:
        m, au = c["m"], c["auto"]
        warn = ""
        if m["short_share"] >= 0.4 and m["n_long"] < 8:
            warn = "  ⚠ {:.0%} Shorts: refaça com duration longform".format(m["short_share"])
        vp = au["vpd_en_equiv"]
        print("{:<18} {:<3} long={:>3} med={:>9,} vpd={:>6} k100={:>2} ativos={:>2} efet={:>5} dom={} frescos={} peq={} → D{} L{} V{} [{}]{}{}{}".format(
            c["id"], c["lang"], m["n_long"], m["med"], m["vpd_p50"] if m["vpd_p50"] is not None else "-", m["k100"], m["active"],
            m["n_eff"] if m["n_eff"] is not None else "-", m["dominance"], m["fresh_share"], m["small_view_share"],
            au["D"], au["L"], au["V"], au["d_basis"], " (vazio)" if au["empty"] else "",
            ("  flags: " + ",".join(au["flags"])) if au["flags"] else "", warn))


if __name__ == "__main__":
    main()
