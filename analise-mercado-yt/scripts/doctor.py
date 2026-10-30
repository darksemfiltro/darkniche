"""Checa se o PC está pronto para a análise e mostra como consertar o que faltar.

  python scripts/doctor.py            -> checagem rápida (testa a chave da YouTube API gastando 1 unidade)
  python scripts/doctor.py --full     -> também testa a busca do yt-dlp (sem cota, ~5 s)
  python scripts/doctor.py --profile  -> mostra o perfil salvo (idiomas, foco, perfil de produção, prioridades)

A configuração (chave no .env e perfil.json) fica em ~/.analise-mercado-yt/ (ou AMY_HOME). Cache e contador de cota
ficam no mesmo lugar, a menos que AMY_DATA aponte para outra pasta (útil quando o disco do perfil é pequeno).
O perfil guarda as respostas que não mudam entre análises, para a skill não repetir perguntas. Edite à mão ou peça
para a skill atualizar. A chave nunca é impressa.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, HOME, load_env, env_config, read_json, write_json, redact

PROFILE = HOME / "perfil.json"
# Perfil neutro: nada de hardware, ferramentas ou orçamento inventados. A skill pergunta o que falta quando for dar nota
# de produção (A, K, S) e grava aqui. Veja perfil.example.json para um perfil preenchido.
DEFAULT_PROFILE = {
    "schema": 2,
    "idioma_relatorio": "pt-BR",
    "idiomas_principais": ["pt", "en", "es"],
    "idiomas_triagem": ["pt", "en", "es"],
    "foco": "faceless",
    "presenca": "sem_rosto",
    "prioridades": ["oportunidade", "automacao_custo", "receita", "velocidade"],
    "producao": {
        "estilos": [],
        "ferramentas": {"llm": "", "tts": "", "imagem": "", "edicao": ""},
        "hardware": {"gpu": "", "vram_gb": None},
        "horas_max_video": None, "videos_mes": None, "orcamento_video_usd": None, "moeda": "USD",
        "revisores_nativos": [],
    },
    "assistir_video": "transcrição + prints",
    "notas": "Edite à mão ou deixe a skill atualizar. Ela lê este arquivo antes de perguntar.",
}

OK, BAD, WARN = "✓", "✗", "!"


def line(sym, label, detail=""):
    print(f" {sym} {label}" + (f": {detail}" if detail else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--no-api", action="store_true", help="não gasta a unidade de teste da API")
    a = ap.parse_args()
    problems = 0

    if not PROFILE.exists():
        write_json(PROFILE, DEFAULT_PROFILE)
        print(f"Perfil criado em {PROFILE} com os padrões. Revise quando puder.")
    if a.profile:
        import json
        print(json.dumps(read_json(PROFILE), ensure_ascii=False, indent=1))
        return

    print("analise-mercado-yt · checagem do ambiente")
    v = sys.version_info
    line(OK if v >= (3, 10) else BAD, "Python", f"{v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 10) else " (precisa ≥ 3.10)"))
    problems += v < (3, 10)

    import ytdlp_tools
    has_key = bool(load_env(Path.cwd()).get("YT_API_KEY"))
    if ytdlp_tools.YTDLP:
        try:
            ver = subprocess.run([*ytdlp_tools.YTDLP, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:
            ver = "?"
        old = False
        try:
            from datetime import date
            y, m, d = (int(x) for x in ver.split(".")[:3])
            old = (date.today() - date(y, m, d)).days > 60
        except Exception:
            pass
        line(WARN if old else OK, "yt-dlp", ver + (" (velho: o YouTube muda e quebra o yt-dlp; rode `yt-dlp -U` ou `pip install -U yt-dlp`)" if old else ""))
    elif has_key:  # complemento: sem ele faltam sondagens, transcrições, thumbnails e o plano B quando a busca da API acaba
        line(WARN, "yt-dlp", "não encontrado (complemento da API: sondagens, transcrições, thumbnails e plano B). Instale: pip install -U yt-dlp")
    else:
        line(BAD, "yt-dlp", "não encontrado, e sem chave de API não há como buscar. Instale: pip install -U yt-dlp")
        problems += 1
    line(OK if ytdlp_tools.FFMPEG else WARN, "ffmpeg", ytdlp_tools.FFMPEG or "não encontrado (opcional: prints de vídeo e grades de quadros). Windows: winget install ffmpeg")
    pil = importlib.util.find_spec("PIL") is not None
    line(OK if pil else WARN, "Pillow", "ok" if pil else "ausente: grades caem para ffmpeg e a paleta não roda (pip install pillow)")

    env = load_env(Path.cwd())
    _, sources = env_config(Path.cwd())
    k = env.get("YT_API_KEY")
    if not k:
        line(BAD, "YT_API_KEY", f"ausente. Crie um arquivo .env em {HOME} (ou na pasta da análise) com a linha YT_API_KEY=...")
        problems += 1
    elif a.no_api:
        line(OK, "YT_API_KEY", f"presente via {sources.get('YT_API_KEY')} (não testada)")
    else:
        import yt_api
        try:
            r = yt_api.api("channels", use_cache=False, part="id", id="UCBR8-60-B28hp2BmDPdntcQ")
            line(OK if r.get("items") else WARN, "YouTube Data API", f"a chave respondeu (1 unidade); fonte: {sources.get('YT_API_KEY')}")
        except yt_api.QuotaExceeded as e:
            line(WARN, "YouTube Data API", f"limite atingido (local ou Google): {redact(e)[:120]}")
            problems += 1
        except Exception as e:
            msg = str(e)
            hint = ""
            if "API_KEY_INVALID" in msg or "keyInvalid" in msg:
                hint = " → chave inválida; gere outra no Google Cloud Console (APIs e serviços › Credenciais)"
            elif "accessNotConfigured" in msg or "SERVICE_DISABLED" in msg or "has not been used" in msg:
                hint = " → ative a 'YouTube Data API v3' no projeto da chave"
            elif "referer" in msg.lower() or "restrict" in msg.lower():
                hint = " → a chave tem restrição de referer/IP; libere para uso local"
            line(BAD, "YouTube Data API", msg[:160] + hint)
            problems += 1
    import yt_api
    status = yt_api.quota_status()
    q, remaining = status['used_local'], status['remaining_local']
    line(OK, "Uso local hoje (Pacífico)", f"{q['units']} unidades gerais · {q['searches']} buscas (buckets separados)")
    line(OK, "Orçamento local restante", f"{remaining['units']} unidades gerais · {remaining['searches']} buscas")
    line(WARN, "Saldo real no Google", "não disponível com chave de API; consulte Google Cloud → YouTube Data API v3 → Quotas")
    g = env.get("GEMINI_API_KEY")
    line(OK if g else WARN, "GEMINI_API_KEY", "presente (opcional)" if g else "ausente (opcional: só para análise de motion mais fina)")

    if a.full and ytdlp_tools.YTDLP:
        try:
            rows = ytdlp_tools.search("documentary", n=3)
            if rows:
                line(OK, "Busca via yt-dlp", f"{len(rows)} resultados")
            else:
                line(BAD, "Busca via yt-dlp", "0 resultados: atualize (yt-dlp -U); se persistir, a rede bloqueia youtube.com. Use mode: api")
                problems += 1
        except Exception as e:
            line(BAD, "Busca via yt-dlp", f"{str(e)[:160]} (atualize o yt-dlp; se persistir, a rede bloqueia youtube.com)")
            problems += 1

    prof = read_json(PROFILE, {})
    prod = prof.get("producao") or {}
    falta = [k for k, v in (("estilos de produção", prod.get("estilos")), ("ferramentas", any((prod.get("ferramentas") or {}).values())),
                            ("horas por vídeo", prod.get("horas_max_video"))) if not v]
    line(OK if not falta else WARN, "Perfil de produção", "completo" if not falta else "falta " + ", ".join(falta) + " (a skill pergunta antes de dar as notas A, K e S)")
    print(f"\nPerfil: {PROFILE}" + (f" · cache e cota em {DATA}" if DATA != HOME else ""))
    print("Dica: no Google Cloud, restrinja a chave à YouTube Data API v3. Se ela vazar, só essa API fica exposta.")
    print("Pronto." if not problems else f"{problems} problema(s) para resolver antes de começar.")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
