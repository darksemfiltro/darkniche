# Compatibilidade com agentes

A skill usa o formato padrão `SKILL.md` e scripts Python que só dependem da biblioteca padrão (mais yt-dlp e Pillow
opcional). Nada nos scripts chama a API do provedor do agente. A chave da YouTube Data API é do usuário e
independe da assinatura do agente.

## O que o agente precisa ter

| Ferramenta | Para quê | Sem ela |
|---|---|---|
| Terminal (Python 3.10+) | rodar os scripts | a skill não funciona |
| Ler e gravar arquivos | `plan.json`, `analysis.json`, relatório | a skill não funciona |
| Busca e leitura de páginas da web | pesquisa em tempo real (`pesquisa-web.md`) | M e R ficam julgados; diga na limitação |
| Pergunta ao usuário | escolha de escopo | pergunte em texto e espere a resposta |
| Leitura de imagem | classificar thumbnails e prints (eixo G) | G fica julgado |
| Navegador ou print do HTML | conferir o relatório | confira abrindo o arquivo e olhando o console |

## Onde instalar

Os locais abaixo foram conferidos em 30/10/2026 nas documentações dos agentes e mudam com as versões. Se a skill não
aparecer no seu agente, confira a página dele.

| Agente | Pasta global (todos os projetos) | Pasta do projeto | Instalador |
|---|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/analise-mercado-yt` | `<projeto>/.claude/skills/...` | `-Agent claude` |
| [Codex](https://developers.openai.com/codex/skills) | `~/.agents/skills/analise-mercado-yt` | `<projeto>/.agents/skills/...` | `-Agent codex` |
| [OpenCode](https://opencode.ai/docs/skills/) | `~/.config/opencode/skills/analise-mercado-yt`; lê também `~/.claude/skills` e `~/.agents/skills` | `<projeto>/.opencode/skills/...` | `-Agent opencode` |
| [Antigravity](https://antigravity.google/docs/skills) | app e IDE: `~/.gemini/config/skills/...`; CLI (`agy`): `~/.gemini/antigravity-cli/skills/...` | `<projeto>/.agents/skills/...` | `-Agent antigravity` |

No instalador de shell a opção é `--agent` (por exemplo, `--agent codex`). `-Agent all` instala nas cinco pastas globais
da tabela.

Detalhes que as páginas deixam em aberto:

- Codex: a página só cita `~/.agents/skills` (e `.agents/skills` dentro do repositório). A pasta antiga `~/.codex/skills`
  segue em uso em instalações existentes, mas a página não a menciona. `agents/openai.yaml`, dentro da skill, é opcional e
  dá o nome e o prompt do seletor.
- Antigravity: `~/.gemini/antigravity/skills` é a pasta antiga, ainda aceita pela IDE. `.agent/skills` (singular) também
  segue aceita no projeto.
- OpenCode: o nome da pasta precisa ser igual ao `name` do `SKILL.md`, e o nome deve ser único entre todas as pastas.

Defina `$S` como a pasta onde o seu agente carregou o `SKILL.md`. Em WSL, container ou nuvem, as variáveis do Windows
não são herdadas: configure `YT_API_KEY` no ambiente que roda os scripts (`doctor.py --no-api` confere sem gastar
cota).

## Sem agente: Google Colab

O DarkNiche também roda num notebook do Colab, com uma IA gratuita no lugar do agente (IA do Colab ou Gemini API na
faixa gratuita). Não há pesquisa web nesse caminho, e ele ainda não foi executado no Colab real. Guia:
`extras/colab/colab.md`; notebooks `extras/colab/DarkNiche.ipynb` e `DarkNiche-Retomar.ipynb`.

## Execução sem usuário

Sem ninguém para responder, o piloto limitado (até 24 buscas) pode rodar e preparar evidências. Aprofundamento exige
aprovação ou escolha registrada (`selection.py approve` ou `select`) que corresponda ao plano; perfil e "análise
completa" não substituem essa escolha. Entregue a proposta e a estimativa e pare.
