#!/usr/bin/env bash
# Instala a skill analise-mercado-yt (macOS / Linux / WSL)
#
#   bash install.sh                             # Claude Code
#   bash install.sh --agent codex               # claude, codex, opencode, antigravity ou all
#   bash install.sh --agent claude,codex        # mais de um
#   bash install.sh --dest ~/minhas-skills      # outra pasta (soma ao --agent, se houver; pode repetir)
#   --non-interactive: não pergunta a chave (usa YT_API_KEY, se existir). --skip-deps: não roda o pip.
#   --replace-key: pede a chave de novo e troca a que está gravada (use depois de revogar uma chave).
#
# Pasta de cada agente (conferidas em 30/10/2026; fontes em analise-mercado-yt/references/hosts.md):
#   claude       ~/.claude/skills
#   codex        ~/.agents/skills
#   opencode     ${XDG_CONFIG_HOME:-~/.config}/opencode/skills
#   antigravity  ~/.gemini/config/skills (app e IDE) e ~/.gemini/antigravity-cli/skills (CLI agy)
#
# 1. confere o Python (3.10+) antes de mexer em qualquer arquivo;
# 2. copia a skill para cada pasta escolhida; se já houver uma, move a anterior para
#    <dados>/backups/analise-mercado-yt-AAAAMMDD-HHMMSS-N (fora das pastas de skills, para o agente não carregar duas);
# 3. grava a chave da YouTube Data API em ~/.analise-mercado-yt/.env (modo 600, só se ainda não existir, ou com
#    --replace-key), pedindo sem mostrar o que você digita. A chave NÃO é aceita na linha de comando: o histórico do
#    shell a guardaria;
# 4. instala yt-dlp e Pillow com pip (requirements.txt) e roda a checagem (doctor.py).
set -euo pipefail

agents=""; dests=(); interactive=1; skip_deps=0; replace_key=0
while [ $# -gt 0 ]; do
  case "$1" in
    --agent) agents="${2:?use --agent claude|codex|opencode|antigravity|all (ou uma lista com vírgulas)}"; shift 2 ;;
    --dest) dests+=("${2:?use --dest <pasta>}"); shift 2 ;;
    --non-interactive) interactive=0; shift ;;
    --skip-deps) skip_deps=1; shift ;;
    --replace-key) replace_key=1; shift ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "Argumento desconhecido: $1"; exit 1 ;;
  esac
done

py=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then py="$c"; break; fi
done
[ -n "$py" ] || { echo "Python 3.10 ou mais novo não encontrado. Instale e rode de novo (macOS: brew install python; Debian/Ubuntu: apt install python3 python3-pip)."; exit 1; }

here="$(cd "$(dirname "$0")" && pwd)"
src="$here/analise-mercado-yt"
[ -f "$src/SKILL.md" ] || { echo "Não achei a pasta analise-mercado-yt ao lado deste script."; exit 1; }

agent_dirs() {
  case "$1" in
    claude) echo "$HOME/.claude/skills" ;;
    codex) echo "$HOME/.agents/skills" ;;
    opencode) echo "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills" ;;
    antigravity) echo "$HOME/.gemini/config/skills"; echo "$HOME/.gemini/antigravity-cli/skills" ;;
    *) return 1 ;;
  esac
}

names=()
if [ -n "$agents" ]; then
  IFS=',' read -r -a parts <<< "$agents"
  for p in "${parts[@]}"; do
    p="$(printf '%s' "$p" | tr 'A-Z' 'a-z' | tr -d ' ')"
    [ -n "$p" ] && names+=("$p")
  done
fi
for p in ${names[@]+"${names[@]}"}; do
  [ "$p" = "all" ] && { names=(claude codex opencode antigravity); break; }
done
if [ ${#names[@]} -eq 0 ] && [ ${#dests[@]} -eq 0 ]; then names=(claude); fi

targets=()
add_target() {
  local t
  for t in ${targets[@]+"${targets[@]}"}; do [ "$t" = "$1" ] && return 0; done
  targets+=("$1")
}
for p in ${names[@]+"${names[@]}"}; do
  if ! d="$(agent_dirs "$p")"; then echo "Agente desconhecido: '$p'. Use: claude, codex, opencode, antigravity, all, ou --dest <pasta>."; exit 1; fi
  while IFS= read -r line; do add_target "$line"; done <<< "$d"
done
for d in ${dests[@]+"${dests[@]}"}; do add_target "$d"; done

data="${AMY_HOME:-$HOME/.analise-mercado-yt}"
stamp="$(date +%Y%m%d-%H%M%S)"; n=0; installed=()
for t in "${targets[@]}"; do
  dst="$t/analise-mercado-yt"
  mkdir -p "$t"
  if [ -e "$dst" ]; then
    n=$((n + 1)); bak="$data/backups/analise-mercado-yt-$stamp-$n"
    mkdir -p "$(dirname "$bak")"; mv "$dst" "$bak"
    echo "Versão anterior de $t guardada em $bak (fora das pastas de skills, para o agente não carregar duas; apague quando quiser)."
  fi
  cp -R "$src" "$dst"; find "$dst" -name __pycache__ -type d -prune -exec rm -rf {} +
  echo "Skill copiada para $dst"
  installed+=("$dst")
done

mkdir -p "$data"
alias_env=""
for v in YT_API_KEY YOUTUBE_API_KEY YOUTUBE_DATA_API_KEY YOUTUBE_DATA_API_V3_KEY; do
  if [ -n "${!v:-}" ]; then alias_env="$v"; break; fi
done
has_file=0; [ -f "$data/.env" ] && has_file=1
if [ "$has_file" = 1 ] && [ "$replace_key" = 0 ]; then
  echo "Mantive o $data/.env que já existia (para trocar a chave: --replace-key)."
elif [ "$has_file" = 0 ] && [ "$replace_key" = 0 ] && [ -n "$alias_env" ] && [ "$alias_env" != "YT_API_KEY" ]; then
  echo "Encontrei a chave na variável de ambiente $alias_env; não gravei arquivo (a skill lê a variável)."
else
  key="${YT_API_KEY:-}"
  if [ -z "$key" ] && [ -t 0 ] && [ "$interactive" = 1 ]; then read -r -s -p "Cole sua YT_API_KEY (YouTube Data API v3; Enter para pular): " key; echo; fi
  if [ -n "$key" ]; then
    case "$key" in AIza*) ;; *) echo "Aviso: a chave não parece uma chave do Google (começa com AIza). Gravei mesmo assim; o doctor testa." ;; esac
    (umask 077; printf 'YT_API_KEY=%s\n' "$key" > "$data/.env")
    echo "Chave gravada em $data/.env (modo 600). Dica: no Google Cloud, restrinja a chave à YouTube Data API v3."
  elif [ "$has_file" = 1 ]; then
    echo "Nenhuma chave nova: mantive o $data/.env que já existia."
  else
    echo "Sem chave por enquanto. Depois crie $data/.env com a linha YT_API_KEY=... (o modo sem chave é reduzido)."
  fi
fi

if [ "$skip_deps" = 1 ]; then
  echo "Dependências puladas (--skip-deps). Instale: $py -m pip install --upgrade -r \"$here/requirements.txt\""
else
  "$py" -m pip install --upgrade --quiet -r "$here/requirements.txt" || echo "Aviso: o pip falhou. Rode: $py -m pip install --upgrade -r \"$here/requirements.txt\" (em Linux com Python do sistema, use um venv ou --user)."
fi
command -v ffmpeg >/dev/null || echo "Aviso: ffmpeg não encontrado (opcional; necessário para prints de vídeo e grades): brew install ffmpeg / apt install ffmpeg."

# a checagem roda sem gravar __pycache__ dentro da skill instalada
if PYTHONDONTWRITEBYTECODE=1 "$py" "${installed[0]}/scripts/doctor.py"; then
  echo; echo "Pronto. No seu agente, peça: 'analise o nicho de finanças pessoais em PT e EN' ou 'quero modelar o canal @exemplo'."
else
  echo; echo "Instalado, mas o doctor apontou pendências (acima). Resolva e rode de novo: $py \"${installed[0]}/scripts/doctor.py\""; exit 2
fi
