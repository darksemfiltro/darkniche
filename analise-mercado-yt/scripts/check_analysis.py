"""Revisor automático do analysis.json antes de gerar o relatório.

  python scripts/check_analysis.py --run <pasta>

Erros (precisam ser corrigidos):
  - oportunidade sem eixo obrigatório, nota fora de 1–5 ou sem justificativa (why)
  - eixo do oceano (D, L, F, G) sem dizer se foi medido
  - evidência, concorrente ou exemplo sem link (url, video ou channel): toda menção a vídeo/canal precisa abrir a fonte
  - ID de vídeo/canal com formato inválido
Avisos (revise e decida):
  - link de busca do YouTube no lugar do link direto
  - D "medido" numa célula com menos de 5 vídeos long-form, ou célula citada que não existe em data/cells.json
  - oportunidade sem títulos, sem produção, sem riscos ou sem evidência
  - mercado sem evidência; fonte sem URL nem nota
  - sondagem com status "existe" cujo melhor resultado parece não ter relação (revise em probe_review)
  - ID de vídeo/canal citado que não aparece nos dados coletados (raw/, data/): provável erro de digitação
  - bends, format_gap e probe_review incompletos ou apontando para células/sondagens que não existem
Pesquisa em tempo real (research.py): evidência {"research": "r3"} precisa existir em data/research.json; falta de
pesquisa sobre monetização ou política do YouTube é erro, a menos que as limitações digam que não havia acesso à web.
Oportunidade sem nenhuma fonte externa datada (pesquisa web) vira aviso: receita (M) e risco (R) saíram só de memória.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import glob_files, read_json
from score import compute
import research

AXES = "DLFGAKSMVR"
AXES_HELP = "D demanda · L lacuna de oferta · F fit cultural · G formato subutilizado · A automação · K custo de IA (5 = barato) · S solo/local · M receita · V velocidade · R risco (5 = arriscado)"
VID = re.compile(r"^[\w-]{11}$")
CID = re.compile(r"^UC[\w-]{22}$")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    run = Path(a.run)
    try:
        an = read_json(run / "analysis.json")
    except ValueError as e:
        raise SystemExit(f"analysis.json inválido (JSON mal formado): {e}")
    if an is None:
        raise SystemExit("analysis.json não encontrado")
    cells = {f"{c['id']}__{c['lang']}": c for c in read_json(run / "data" / "cells.json", [])}
    plan = read_json(run / "plan.json", {})
    errs, warns = [], []

    # IDs que de fato aparecem nos dados coletados (para pegar ID inventado ou digitado errado)
    known_v, known_c = set(), set()
    def eat(rows):
        for r in rows or []:
            if r.get("id"):
                known_v.add(r["id"])
            if r.get("channel_id"):
                known_c.add(r["channel_id"])
    for c in cells.values():
        eat(c["m"].get("top")); eat(c["m"].get("foreign_top"))
    for f in glob_files(run / "raw" / "search") + glob_files(run / "raw" / "probes"):
        eat((read_json(f) or {}).get("rows"))
    ref = read_json(run / "data" / "reference.json") or {}
    eat(ref.get("timeline"))
    if ref.get("channel", {}).get("id"):
        known_c.add(ref["channel"]["id"])
    for ch in read_json(run / "data" / "channels.json", []):
        known_c.add(ch.get("id"))
        eat(ch.get("top")); eat(ch.get("recent"))
    known_v |= set(read_json(run / "data" / "comments.json", {}) or {})
    for p in plan.get("probes", []):
        if p.get("source", {}).get("id"):
            known_v.add(p["source"]["id"])
    have_data = bool(known_v)
    r_rows, r_errs, r_warns = research.check(run)
    research_ids = {r["id"] for r in r_rows}
    # Sem ferramenta de web (ex.: Colab) a falta de pesquisa é limitação declarada, não erro: `web_research: false` ou a frase nas limitações.
    no_web = an.get("web_research") is False or any(re.search(r"pesquisa web|sem acesso à web|sem acesso a web|web indispon", l, re.I)
                                                    for l in an.get("limitations", []) if isinstance(l, str))
    if an.get("analysis_mode") != "technical":  # o relatório técnico (sem IA) não usa pesquisa
        for m in r_errs:
            (warns if no_web else errs).append(f"pesquisa: {m}")
        warns.extend(f"pesquisa: {m}" for m in r_warns)

    def link_ok(e, where):
        if not isinstance(e, dict):
            errs.append(f"{where}: item não é objeto ({e!r:.60})")
            return
        if e.get("research"):  # fato da pesquisa em tempo real: o relatório monta o link e a data a partir de data/research.json
            if e["research"] not in research_ids:
                errs.append(f"{where}: pesquisa {e['research']!r} não existe em data/research.json (rode research.py list)")
            return
        if e.get("video") and not VID.match(e["video"]):
            errs.append(f"{where}: video ID inválido '{e['video']}'")
        elif e.get("video") and have_data and e["video"] not in known_v:
            near = [k for k in known_v if k.lower() == e["video"].lower()]
            hint = f" — você quis dizer {near[0]}? (IDs diferenciam maiúsculas)" if near else " (confira o ID)"
            warns.append(f"{where}: vídeo {e['video']} não aparece nos dados coletados{hint}")
        if e.get("channel") and not CID.match(e["channel"]):
            errs.append(f"{where}: channel ID inválido '{e['channel']}' (use o UC…, não o @handle)")
        elif e.get("channel") and have_data and e["channel"] not in known_c:
            warns.append(f"{where}: canal {e['channel']} não aparece nos dados coletados (confira o ID)")
        ident = e.get("id")
        if not (e.get("url") or e.get("video") or e.get("channel") or (isinstance(ident, str) and (VID.fullmatch(ident) or CID.fullmatch(ident)))):
            errs.append(f"{where}: sem link → '{(e.get('text') or e.get('title') or '')[:70]}'")
        u = e.get("url") or ""
        if u and (not isinstance(u, str) or urlsplit(u).scheme not in ("http", "https") or not urlsplit(u).netloc):
            errs.append(f"{where}: URL precisa ser http(s) válida")
        if "results?search_query" in u:
            warns.append(f"{where}: link de busca; prefira o link direto do vídeo/canal → '{(e.get('text') or '')[:60]}'")
        if re.search(r"watch\?v=$", u):
            errs.append(f"{where}: URL de vídeo sem ID")

    ops = an.get("opportunities", [])
    technical = an.get("analysis_mode") == "technical"
    if technical and (ops or not an.get("limitations") or not an.get("summary")):
        errs.append("modo técnico exige resumo, limitações e nenhuma oportunidade estratégica pontuada")
    if not ops and not technical:
        errs.append("nenhuma oportunidade em analysis.json")
    ids = set()
    for o in ops:
        oid = o.get("id") or o.get("name") or "?"
        if not o.get("id") or not re.fullmatch(r"[\w-]+", str(o.get("id"))):
            errs.append(f"oportunidade '{o.get('name', '?')}': falta um id curto sem espaços (ex.: \"financas-pt\"); ele vira a âncora do cartão")
        if oid in ids:
            errs.append(f"oportunidade '{oid}': id repetido")
        ids.add(oid)
        sc = o.get("scores", {})
        for k in AXES:
            x = sc.get(k)
            if x is None:
                errs.append(f"{oid}: falta o eixo {k}")
                continue
            v = x.get("v") if isinstance(x, dict) else x
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 1 <= v <= 5:
                errs.append(f"{oid}.{k}: nota {v!r} fora de 1–5")
            if not isinstance(x, dict) or not isinstance(x.get("why"), str) or not x["why"].strip():
                errs.append(f"{oid}.{k}: sem justificativa (why)")
            if k in "DLFG" and isinstance(x, dict) and type(x.get("measured")) is not bool:
                errs.append(f"{oid}.{k}: diga se foi medido (measured: true/false)")
        try:
            compute(o, an.get("weights"))
        except ValueError as e:
            errs.append(str(e))
        d = sc.get("D") if isinstance(sc.get("D"), dict) else {}
        l_ax = sc.get("L") if isinstance(sc.get("L"), dict) else {}
        for ck in o.get("cells") or []:
            c = cells.get(ck)
            if not c:
                warns.append(f"{oid}: célula '{ck}' não existe em data/cells.json")
                continue
            for k, ax in (("D", d), ("L", l_ax)):
                if ax.get("measured") and c["m"]["n_long"] < 5:
                    warns.append(f"{oid}: {k} marcado como medido, mas {ck} tem só {c['m']['n_long']} long-form (evidência fraca)")
            if "cabeca_saturada" in (c.get("auto") or {}).get("flags", []) and d.get("measured") and (d.get("v") or 0) >= 5:
                warns.append(f"{oid}: {ck} está com o topo saturado (nicho largo); D 5 não separa vencedores, confira um subnicho")
        if d.get("measured") and not o.get("cells"):
            warns.append(f"{oid}: D medido sem célula associada (cells: [])")
        for i, e in enumerate(o.get("evidence") or []):
            link_ok(e, f"{oid}.evidence[{i}]")
        if not any(isinstance(e, dict) and (e.get("research") or (e.get("url") and e.get("accessed"))) for e in o.get("evidence") or []):
            warns.append(f"{oid}: nenhuma fonte externa datada na evidência: receita (M) e risco (R) saíram só do que o modelo já sabia; pesquise (pesquisa-web.md) e cite {{\"research\": \"rN\"}}")
        for i, e in enumerate(o.get("competitors") or []):
            if not e.get("id"):
                errs.append(f"{oid}.competitors[{i}]: concorrente sem channel id → '{e.get('title', '')[:50]}'")
            elif not CID.match(e["id"]):
                errs.append(f"{oid}.competitors[{i}]: id '{e['id']}' não é um channel ID (UC…)")
        for f, label in (("evidence", "evidência"), ("titles", "títulos"), ("production", "produção"), ("risks", "riscos")):
            if not o.get(f):
                warns.append(f"{oid}: sem {label}")

    for m in an.get("markets", []):
        if not m.get("evidence"):
            warns.append(f"mercado {m.get('lang')}: sem evidência")
        for i, e in enumerate(m.get("evidence", [])):
            link_ok(e, f"mercado {m.get('lang')}.evidence[{i}]")
    ref = an.get("reference", {}) or {}
    for i, e in enumerate(ref.get("examples", [])):
        link_ok(e, f"reference.examples[{i}]")
    for i, e in enumerate((an.get("production") or {}).get("sources", [])):
        link_ok(e, f"production.sources[{i}]")
    for i, s in enumerate(an.get("sources", [])):
        if s.get("research"):  # referência à pesquisa web: o relatório monta texto, link e data
            if s["research"] not in research_ids:
                errs.append(f"sources[{i}]: pesquisa {s['research']!r} não existe em data/research.json")
            continue
        if not s.get("url") and not s.get("note"):
            warns.append(f"sources[{i}]: sem URL nem nota → '{s.get('label', '')[:60]}'")
    if not an.get("sources"):
        warns.append("sem lista de fontes")
    if len((an.get("summary") or {}).get("findings", [])) < 3:
        warns.append("resumo com menos de 3 achados")
    if not an.get("limitations"):
        warns.append("sem limitações declaradas (sempre há: diga o que não foi medido)")

    plan_cells = {c["id"] for c in plan.get("cells", [])}
    for i, b in enumerate(an.get("bends", [])):
        for k in ("axis", "from", "to"):
            if not b.get(k):
                warns.append(f"bends[{i}]: falta '{k}'")
        for ck in b.get("cells", []):
            if plan_cells and ck not in plan_cells:
                warns.append(f"bends[{i}]: célula '{ck}' não existe no plan.json")
    for i, g in enumerate(an.get("format_gap", [])):
        key = f"{g.get('cell')}__{g.get('lang')}"
        if cells and key not in cells:
            warns.append(f"format_gap[{i}]: célula {key} não existe em data/cells.json")
        tot = sum(x.get("share", 0) for x in g.get("styles", []))
        if g.get("styles") and not 0.9 <= tot <= 1.1:
            warns.append(f"format_gap[{i}] ({key}): as fatias somam {tot:.2f} (deveriam somar ~1)")
        if "proposed_present" not in g:
            warns.append(f"format_gap[{i}] ({key}): diga se o estilo proposto aparece (true/false/null)")
    probes_set = {(p["probe"], p["lang"]) for p in read_json(run / "data" / "probes.json", [])}
    for i, r in enumerate(an.get("probe_review", [])):
        if r.get("status") not in ("existe", "fraco", "lacuna", "inconclusivo"):
            errs.append(f"probe_review[{i}]: status '{r.get('status')}' (use existe, fraco, lacuna ou inconclusivo)")
        if probes_set and (r.get("probe"), r.get("lang")) not in probes_set:
            warns.append(f"probe_review[{i}]: sondagem {r.get('probe')}/{r.get('lang')} não existe em data/probes.json")
        if not r.get("note"):
            warns.append(f"probe_review[{i}]: explique a revisão em 'note'")

    rev = {(r.get("probe"), r.get("lang")) for r in an.get("probe_review") or [] if isinstance(r, dict)}
    for p in read_json(run / "data" / "probes.json", []):
        if p["status"] == "existe" and (p["probe"], p["lang"]) not in rev:
            warns.append(f"sondagem {p['probe']}/{p['lang']} = existe: confira se '{((p.get('best') or {}).get('title') or '')[:60]}' é mesmo o mesmo ângulo")

    for w in warns:
        print("AVISO", w)
    for e in errs:
        print("ERRO ", e)
    print(f"\n{len(errs)} erro(s), {len(warns)} aviso(s) em {len(ops)} oportunidades")
    if any(re.search(r"\.[DLFGAKSMVR]\b|eixo", e) for e in errs):
        print("Eixos:", AXES_HELP)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
