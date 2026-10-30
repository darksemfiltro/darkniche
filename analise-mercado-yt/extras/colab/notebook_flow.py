"""Fluxo automático do Colab: plano → piloto → leitura; escolha humana → aprofundamento → HTML."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SCRIPTS = _HERE if (_HERE / "common.py").exists() else _HERE.parents[1] / "scripts"  # extras/colab -> ../../scripts
sys.path.insert(0, str(SCRIPTS))
from common import read_json, set_run, write_json
from plan_tools import validate_plan
from selection import scope_hash, require_selection, require_triage, propose
from triage import prepare

SKILL = SCRIPTS.parent


def command(script, *args, capture=False):
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=capture, text=True, encoding="utf-8")
    if result.returncode:
        raise ValueError((result.stdout or "")[-6000:] if capture else f"{script} saiu com código {result.returncode}; veja a saída acima. Dados preservados.")
    return result.stdout if capture else None


def evidence(run):
    """Metadados, métricas e amostra explícita; exclui segredos, perfis locais e autores de comentários."""
    run = Path(run)
    out = {}
    for name in ("reference", "cells", "channels", "probes"):
        data = read_json(run / "data" / f"{name}.json")
        if data is not None:
            out[name] = data
    comments = read_json(run / "data/comments.json", {})
    if comments:
        out["comments"] = {k: {field: v.get(field) for field in ("n", "request_count", "format_praise_share", "political_share")} for k, v in comments.items()}
    # O modelo precisa ler resultados não nativos/ruído também; no máximo 15 por consulta.
    out["search_sample"] = [{"cell": d.get("cell"), "lang": d.get("lang"), "query": d.get("query"), "rows": d.get("rows", [])[:15]}
                            for d in (read_json(p, {}) for p in sorted((run / "raw/search").glob("*.json")))]
    return out


def known_ids(data):
    ids = set()
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("id", "channel_id", "video", "channel") and isinstance(v, str) and re.fullmatch(r"(?:UC[\w-]{22}|[\w-]{11})", v):
                    ids.add(v)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data)
    return ids


def initial_analysis(run, request, ai, duration="longform", pilot_budget=24):
    run = Path(run)
    set_run(run)
    ai.preflight()  # falta de IA é detectada antes de gastar buscas
    request_hash = hashlib.sha256(request.encode()).hexdigest()
    prior = read_json(run / "data/ai/request.json", {})
    if prior.get("request_hash") not in (None, request_hash):
        raise ValueError("O pedido mudou nesta pasta. Use outro TITLE/EXISTING_RUN para uma nova análise; a seleção anterior não autoriza outro pedido.")
    write_json(run / "data/ai/request.json", {"request_hash": request_hash})
    plan = read_json(run / "plan.json", {})
    state = read_json(run / "selection.json", {})
    if state.get("status") == "selected" and state.get("stage") != "triage":
        require_selection(run, plan)
        print("Seleção anterior encontrada. Retomando somente o aprofundamento já escolhido.")
        return "selected"
    base = read_json(run / "proposal.json") or plan
    ref = evidence(run)
    if getattr(ai, "backend", None) == "dados":
        if not base.get("cells"):
            raise ValueError("Sem IA, preciso de um plano com hipóteses já definidas e piloto coletado. Retome EXISTING_RUN; o modo dados não inventa recortes nem traduz consultas.")
        require_triage(run, base)
        command("metrics.py", "--run", run / "triage")
        from technical import review as descriptive_review
        review = descriptive_review(base, read_json(run / "triage/data/cells.json", []))
        by_id = {r["id"]: r for r in review["candidates"]}
        for c in base["cells"]:
            c.update({k: by_id[c["id"]][k] for k in ("priority", "rationale")})
        write_json(run / "data/market_review.json", review)
        write_json(run / "plan.json", base)
        propose(run)
        print(review["summary"])
        return "pending"
    if not base.get("cells"):
        prompt = f"""Leia o pedido e os vídeos da referência para formular 3 hipóteses ESPECÍFICAS, não oportunidades já recomendadas.
Pedido: {request}
Referência e dados: {json.dumps(ref, ensure_ascii=False)}
Plano base: {json.dumps(base, ensure_ascii=False)}
Retorne {{"cells":[{{"id":"slug_seguro", "label":"...", "niche":"...", "subniche":"...", "lens":"...",
"rationale":"hipótese a testar, ligada a vídeos da referência", "queries":{{"pt":["expressão nativa curta","variante"]}}}}], "probes":[]}}.
Inclua exatamente os idiomas do plano base em CADA célula; não acrescente países. Cada idioma usa lista de 1–2 consultas.
3 recortes; adapte-os à referência. Não copie os mesmos recortes para todo canal. Sem referência, use o briefing e declare a limitação.
O piloto usa a primeira expressão, uma página, duração {duration}, teto {pilot_budget} buscas. Não inclua ranking ou notas antes do mercado."""
        def validate(value):
            candidate = {**base, "cells": value.get("cells", []), "probes": []}
            validate_plan(candidate)
            if not 1 <= len(candidate["cells"]) <= 4:
                raise ValueError("Plano precisa de 1–4 hipóteses.")
            langs = {l["lang"] for l in base["languages"]}
            for c in candidate["cells"]:
                if set(c.get("queries", {})) != langs:
                    raise ValueError("Consultas devem cobrir exatamente os idiomas definidos.")
                if c.get("mode", "api") != "api" or c.get("filters") or c.get("filters_lang"):
                    raise ValueError("Não altere filtros/modos: o notebook controla o orçamento.")
            k = 2 if duration == "longform" else 1
            if len(candidate["cells"]) * len(langs) * k > pilot_budget:
                raise ValueError("Hipóteses excedem o teto do piloto; reduza a quantidade sem excluir idiomas.")
        result = ai.json("hypotheses", prompt, validate)
        base["cells"], base["probes"] = result["cells"], []
        base["defaults"].update(mode="api", probe_mode="api", duration=duration, pages=1)
        base["collection_limits"] = {"max_channels": 12, "uploads_per_channel": 60, "comment_videos": 0, "comments_per_video": 200}
        write_json(run / "plan.json", base)
    else:
        write_json(run / "plan.json", base)
    print("Hipóteses específicas preparadas; iniciando piloto de mercado.")
    prepare(run, duration=duration, budget=pilot_budget)
    command("scan.py", "--run", run / "triage", "--triage")
    command("metrics.py", "--run", run / "triage")
    command("profile_channels.py", "--run", run / "triage", "--max", 6, "--top-per-cell", 2, "--n", 50)
    set_run(run)
    market = evidence(run / "triage")
    allowed = known_ids(market)
    expected = {c["id"] for c in base["cells"]}
    prompt = f"""Pedido: {request}
Referência: {json.dumps(ref, ensure_ascii=False)}
Hipóteses e mercados: {json.dumps(base, ensure_ascii=False)}
PILOTO DE MERCADO REAL (amostral): {json.dumps(market, ensure_ascii=False)}
Leia títulos, canais dedicados, idioma, ruído, mediana, concentração e amostra. Não trate TV/hit isolado como crescimento replicável.
Ranqueie TODOS os recortes testados com evidências. Diferencie observado de inferido; não invente estatísticas nem concorrentes ausentes.
Evidência fraca/ruim: status inconclusivo; zero resultados não prova oceano azul. Não alegue ter assistido vídeos ou visto thumbnails.
Retorne {{"summary":"leitura preliminar e limitações", "candidates":[{{"id":"ID do recorte", "priority":1,
"rationale":"números observados + interpretação + limitações", "status":"promissor|cautela|inconclusivo",
"evidence":[{{"video":"ID coletado"}}], "markets":[{{"lang":"pt","verdict":"...","why":"dados e incerteza"}}]}}]}}.
Somente IDs coletados. Não altere consultas, filtros ou países. A escolha do aprofundamento pertence ao usuário."""
    def validate_review(value):
        rows = value.get("candidates", [])
        if len(rows) != len(expected) or {r.get("id") for r in rows} != expected:
            raise ValueError("Ranking deve cobrir exatamente todos os recortes testados.")
        priorities = []
        for row in rows:
            if type(row.get("priority")) is not int or row["priority"] < 1 or not row.get("rationale"):
                raise ValueError("Recorte precisa de prioridade inteira e justificativa.")
            priorities.append(row["priority"])
            if row.get("status") not in ("promissor", "cautela", "inconclusivo"):
                raise ValueError("Status de triagem inválido.")
            if row["status"] != "inconclusivo" and not row.get("evidence"):
                raise ValueError("Recomendação sem evidência coletada.")
            for ev in row.get("evidence", []):
                if not (ev.get("video") or ev.get("channel")) in allowed:
                    raise ValueError("Ranking citou ID não coletado.")
        if len(set(priorities)) != len(priorities):
            raise ValueError("Prioridades devem ser distintas.")
    review = ai.json("market_review", prompt, validate_review)
    by_id = {r["id"]: r for r in review["candidates"]}
    for c in base["cells"]:
        c.update({k: by_id[c["id"]][k] for k in ("priority", "rationale")})
    write_json(run / "data/market_review.json", review)
    write_json(run / "plan.json", base)
    propose(run)
    print("\n" + review.get("summary", ""))
    for row in sorted(review["candidates"], key=lambda x: x["priority"]):
        print(f"\n{row['priority']}. {row['id']} — {row['status']}\n{row['rationale']}")
        for ev in row.get("evidence", []):
            print("https://www.youtube.com/watch?v=" + ev["video"] if ev.get("video") else "https://www.youtube.com/channel/" + ev["channel"])
        for m in row.get("markets", []):
            print(f"  {m.get('lang')}: {m.get('verdict')} · {m.get('why')}")
    return "pending"


def finish_analysis(run, request, ai):
    run = Path(run)
    set_run(run)
    plan = read_json(run / "plan.json")
    require_selection(run, plan)
    ai.preflight()
    if getattr(ai, "backend", None) == "dados":
        from technical import analysis as technical_analysis
        technical_analysis(run)
        command("check_analysis.py", "--run", run)
        command("score.py", "--run", run)
        command("build_report.py", "--run", run, "--embed")
        print("Relatório técnico pronto; nenhuma chamada ao YouTube ou modelo de IA nesta etapa.")
        return run / "relatorio.html"
    command("scan.py", "--run", run)
    command("scan.py", "--run", run, "--probes")
    command("metrics.py", "--run", run)
    limits = plan.get("collection_limits", {})
    command("profile_channels.py", "--run", run, "--max", min(int(limits.get("max_channels", 12)), 30),
            "--n", min(int(limits.get("uploads_per_channel", 60)), 200))
    context = evidence(run)
    context["pilot"] = evidence(run / "triage")
    context["market_review"] = read_json(run / "data/market_review.json", {})
    allowed = known_ids(context)
    rubric = (SKILL / "references/oceano-azul.md").read_text(encoding="utf-8")
    report_spec = (SKILL / "references/relatorio.md").read_text(encoding="utf-8")
    prompt = f"""Escreva analysis.json completo em português conforme o esquema abaixo. Pedido: {request}
PLANO ESCOLHIDO: {json.dumps(plan, ensure_ascii=False)}
EVIDÊNCIAS REAIS: {json.dumps(context, ensure_ascii=False)}
RUBRICA: {rubric}
ESQUEMA: {report_spec}
Use somente recortes/idiomas escolhidos. Não invente IDs, views, observação visual, fit medido, RPM, custos ou fontes externas.
Sem visão/transcrição: F/G julgados, descreva limitação. Sem hardware/stack do usuário: produção é hipótese e custo não estimado.
Demanda pequena/contaminada é inconclusiva; D/L medidos somente quando amostra sustenta e contexto justifica.
Se não há oportunidade comprovada, apresente opções para validar com notas conservadoras e limites explícitos.
Inclua summary, method, opportunities, limitations e fontes efetivamente fornecidas; todos os 10 eixos com why,
DLFG com measured booleano. Cite vídeos/canais por IDs coletados, células como id__idioma. Sem campos de quota inventados.
Não use format_gap:null: omita campo quando não inspecionado. Entregue somente JSON, sem comentários."""
    def validate(value):
        langs = {l["lang"] for l in plan["languages"]}
        cells = {f"{c['id']}__{l}" for c in plan["cells"] for l in c["queries"]}
        if not value.get("summary") or not value.get("limitations") or not value.get("opportunities"):
            raise ValueError("Análise precisa de resumo, limitações e opções avaliadas.")
        for op in value["opportunities"]:
            if op.get("lang") not in langs or not op.get("cells") or not set(op["cells"]) <= cells:
                raise ValueError("Oportunidade fora do escopo escolhido.")
            for ch in op.get("competitors", []):
                if ch.get("id") not in allowed:
                    raise ValueError("Concorrente citado não foi coletado.")
            for axis in ("F", "G"):
                if op.get("scores", {}).get(axis, {}).get("measured") is not False:
                    raise ValueError("Sem inspeção visual/cultural independente, F e G devem ser julgados (measured:false).")
            measured_cells = {f"{c['id']}__{c['lang']}": c for c in context.get("cells", [])}
            if op.get("scores", {}).get("D", {}).get("measured") and any(measured_cells.get(k, {}).get("m", {}).get("n_long", 0) < 5 for k in op["cells"]):
                raise ValueError("Demanda marcada medida com menos de 5 long-form nativos; declare evidência fraca.")
        def links(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in ("video", "channel") and isinstance(v, str) and v not in allowed:
                        raise ValueError("Fonte citada não existe nos dados coletados.")
                    links(v)
            elif isinstance(x, list):
                for v in x:
                    links(v)
        links(value)
        # No Colab não há ferramenta de web: receita (M), risco (R) e preços saem do conhecimento prévio do modelo. Isso é
        # limitação declarada (o verificador aceita) e baixa a confiança dessas notas; não inventa fonte.
        value["web_research"] = False
        sem_web = ("Sem acesso à web nesta execução (Colab): receita (M), risco (R) e preços saíram do conhecimento prévio "
                   "do modelo e precisam de confirmação em fonte oficial antes de decidir.")
        if sem_web not in value["limitations"]:
            value["limitations"] = [*value["limitations"], sem_web]
        # Validação real do mesmo arquivo usado pelo relatório; até uma correção via IA.
        write_json(run / "analysis.json", value)
        command("check_analysis.py", "--run", run, capture=True)
    analysis = ai.json("analysis", prompt, validate)
    write_json(run / "analysis.json", analysis)
    command("check_analysis.py", "--run", run)
    command("score.py", "--run", run)
    command("build_report.py", "--run", run, "--embed")
    print("Relatório pronto:", run / "relatorio.html")
    return run / "relatorio.html"
