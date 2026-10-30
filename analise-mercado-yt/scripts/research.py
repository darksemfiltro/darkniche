"""Registro da pesquisa web em tempo real: cada fato externo (RPM, política do YouTube, notícia, preço) com fonte e data.

  python scripts/research.py add  --run <pasta> --topic monetizacao --claim "RPM de finanças no Brasil" --value "US$ 2–6"
                                  --url https://... --accessed 2026-10-29 --type dados --confidence media [--unit RPM]
                                  [--quote "até 25 palavras copiadas"] [--lang pt] [--note "..."]
  python scripts/research.py list --run <pasta> [--topic politica]
  python scripts/research.py check --run <pasta>           (cobertura, fontes fracas, datas velhas; sai 1 se houver erro)

O agente pesquisa com as ferramentas de busca e leitura de páginas do host (WebSearch/WebFetch ou equivalentes) e
registra aqui o que usou. Saída: data/research.json, que o relatório mostra como "Pesquisa em tempo real" e que o
analysis.json cita com {"research": "r3"}. Sem ferramenta de pesquisa, não registre nada de memória: anote a limitação.

Temas: monetizacao (RPM/CPM, afiliados, patrocínio) · politica (regras do YouTube para o formato) · tendencia (notícias,
eventos, calendário) · concorrencia (modelos de negócio, casos) · producao (preço de ferramentas, limites) ·
mercado (público, cultura, regulação do país) · outro.
Tipos de fonte: oficial (página do YouTube/Google/empresa) · dados (pesquisa, painel, estatística) · noticia ·
blog · comunidade (fórum, Reddit, comentário). Número só de blog ou comunidade sai como aviso: confirme com 2ª fonte.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_json, write_json

TOPICS = ["monetizacao", "politica", "tendencia", "concorrencia", "producao", "mercado", "outro"]
REQUIRED = ["monetizacao", "politica"]          # uma análise completa não fecha sem estes dois
RECOMMENDED = ["tendencia", "concorrencia", "mercado"]
TYPES = ["oficial", "dados", "noticia", "blog", "comunidade"]
CONF = ["alta", "media", "baixa"]
WEAK = {"blog", "comunidade"}
QUOTE_MAX_WORDS = 25  # citação curta: o registro guarda o fato e a fonte, não o texto da página
SECRET_PARAMS = {"key", "api_key", "apikey", "token", "access_token", "auth", "secret", "password", "passwd", "sig"}


def _url_has_secret(url):
    """True quando a URL leva usuário e senha, uma chave do Google ou sk-, ou um parâmetro típico de segredo."""
    p = urlparse(url)
    names = {k.lower().replace("-", "_") for k, _ in parse_qsl(p.query)}
    return bool(p.username or p.password or names & SECRET_PARAMS or re.search(r"AIza[0-9A-Za-z_-]{20,}|\bsk-[A-Za-z0-9_-]{20,}", url))


def _file(run):
    return Path(run) / "data" / "research.json"


def load(run):
    return read_json(_file(run), [])


def _problems(e):
    """Erros (bloqueiam) e avisos de uma entrada."""
    err, warn = [], []
    u = urlparse(e.get("url") or "")
    if u.scheme not in ("http", "https") or not u.netloc:
        err.append("url inválida (precisa de http/https)")
    try:
        d = date.fromisoformat(e.get("accessed") or "")
        if d > date.today():
            err.append("data de acesso no futuro")
        elif (date.today() - d).days > 90:
            warn.append(f"consultada há {(date.today() - d).days} dias: reconfirme se a decisão depende disso")
    except ValueError:
        err.append("accessed precisa ser AAAA-MM-DD")
    if _url_has_secret(e.get("url") or ""):
        err.append("a URL traz usuário, senha, chave ou token: remova antes de registrar (o arquivo vai para o relatório)")
    for k, allowed in (("topic", TOPICS), ("type", TYPES), ("confidence", CONF)):
        if e.get(k) not in allowed:
            err.append(f"{k} deve ser um de: {', '.join(allowed)}")
    if not (e.get("claim") or "").strip():
        err.append("falta o claim (o fato em uma frase)")
    if len((e.get("quote") or "").split()) > QUOTE_MAX_WORDS:
        err.append(f"quote com mais de {QUOTE_MAX_WORDS} palavras: resuma com as suas palavras")
    if e.get("value") and e.get("type") in WEAK:
        warn.append("número só de blog/comunidade: confirme com uma segunda fonte")
    return err, warn


def add(run, **kw):
    rows = load(run)
    n = max([int(re.sub(r"\D", "", r["id"]) or 0) for r in rows] + [0]) + 1
    e = {"id": f"r{n}", **{k: v for k, v in kw.items() if v not in (None, "")},
         "added_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    e["domain"] = (urlparse(e.get("url") or "").hostname or "").removeprefix("www.")
    err, warn = _problems(e)
    if err:
        raise ValueError("; ".join(err))
    rows.append(e)
    write_json(_file(run), rows)
    return e, warn


def check(run):
    rows = load(run)
    errors, warns = [], []
    for e in rows:
        err, warn = _problems(e)
        errors += [f"{e['id']}: {m}" for m in err]
        warns += [f"{e['id']}: {m}" for m in warn]
    have = {e.get("topic") for e in rows}
    errors += [f"sem pesquisa sobre {t}: pesquise e registre (ou documente a limitação em analysis.limitations)" for t in REQUIRED if t not in have]
    warns += [f"sem pesquisa sobre {t}" for t in RECOMMENDED if t not in have]
    return rows, errors, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("add")
    a_.add_argument("--run", required=True)
    for k in ("topic", "claim", "url", "accessed", "type", "confidence"):
        a_.add_argument(f"--{k}", required=True)
    for k in ("value", "unit", "quote", "lang", "note"):
        a_.add_argument(f"--{k}")
    l_ = sub.add_parser("list"); l_.add_argument("--run", required=True); l_.add_argument("--topic")
    c_ = sub.add_parser("check"); c_.add_argument("--run", required=True)
    a = ap.parse_args()
    if a.cmd == "add":
        try:
            e, warn = add(a.run, topic=a.topic, claim=a.claim, value=a.value, unit=a.unit, url=a.url, accessed=a.accessed,
                          type=a.type, confidence=a.confidence, quote=a.quote, lang=a.lang, note=a.note)
        except ValueError as err:
            raise SystemExit(f"não registrado: {err}")
        print(f"{e['id']} registrado · {e['topic']} · {e['domain']}")
        for w in warn:
            print("  aviso:", w)
    elif a.cmd == "list":
        for e in load(a.run):
            if not a.topic or e["topic"] == a.topic:
                print(f"{e['id']:<4} {e['topic']:<12} {e['type']:<10} {e['confidence']:<5} {e['accessed']}  {e['claim'][:70]}  [{e['domain']}]")
    else:
        rows, errors, warns = check(a.run)
        print(f"{len(rows)} registros · {len({e['domain'] for e in rows})} fontes distintas")
        for m in errors:
            print("ERRO ", m)
        for m in warns:
            print("aviso", m)
        sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
