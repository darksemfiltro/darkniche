# Guia de instalação

Este guia leva você do zero até a primeira análise. Se você só quer o resumo, o [README](../README.md) tem os comandos.

Conteúdo:

- [Antes de começar](#antes-de-começar)
- [1. Pegue a chave da API](#1-pegue-a-chave-da-api)
- [2. Baixe o pacote](#2-baixe-o-pacote)
- [3. Instale a skill](#3-instale-a-skill)
- [4. Confira e faça a primeira análise](#4-confira-e-faça-a-primeira-análise)
- [Colab, sem agente](#colab-sem-agente)
- [Instalação manual](#instalação-manual)
- [Trocar ou revogar a chave](#trocar-ou-revogar-a-chave)
- [Atualizar e desinstalar](#atualizar-e-desinstalar)
- [Problemas comuns](#problemas-comuns)

## Antes de começar

Você precisa de:

- Python 3.10 ou mais novo. Confira com `python --version` (ou `python3 --version`). Windows: [python.org](https://www.python.org/downloads/) ou `winget install Python.Python.3.12`. macOS: `brew install python`. Debian e Ubuntu: `sudo apt install python3 python3-pip`.
- Um agente com suporte a skills (Claude Code, Codex, OpenCode ou Antigravity), ou uma conta Google para o [Colab](#colab-sem-agente).
- Uma chave da YouTube Data API v3. O passo 1 mostra como criar.
- Opcional: ffmpeg, para prints de vídeo e grades. Windows: `winget install ffmpeg`. macOS: `brew install ffmpeg`. Linux: `sudo apt install ffmpeg`.

A skill roda em Windows, macOS e Linux, sem GPU. O instalador de Windows foi o mais testado.

## 1. Pegue a chave da API

A chave é grátis e fica com você. A skill nunca a envia a ninguém além do YouTube.

1. Entre no [Google Cloud Console](https://console.cloud.google.com/) com a sua conta Google.
2. Crie um projeto (menu do projeto, no topo, e depois **Novo projeto**).
3. Abra **APIs e serviços > Biblioteca**, procure **YouTube Data API v3** e clique em **Ativar**.
4. Abra **APIs e serviços > Credenciais** e clique em **Criar credenciais > Chave de API**.
5. Abra a chave criada. Em **Restrições de API**, escolha **Restringir chave**, marque **YouTube Data API v3** e salve.
6. Copie a chave. Não a coloque em repositório, print, issue ou conversa com o agente.

Os nomes dos menus mudam de tempos em tempos. Se não achar um item, procure pelo nome da API.

A cota padrão tem dois limites por dia que a skill controla: 100 buscas e 10.000 unidades gerais (leitura de vídeos, canais e comentários). Um piloto de 3 recortes em 3 idiomas usa 18 buscas. A cota vira à meia-noite do Pacífico. Confira os valores do seu projeto no Cloud Console e veja o [custo de cada chamada](https://developers.google.com/youtube/v3/determine_quota_cost).

## 2. Baixe o pacote

Pelo navegador: na página do repositório, clique em **Code > Download ZIP** e descompacte.

Pelo terminal:

```bash
git clone https://github.com/darksemfiltro/darkniche.git
```

Abra a pasta baixada num terminal. Os próximos comandos partem dela.

## 3. Instale a skill

### Windows

No PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Agent claude
```

### macOS, Linux e WSL

```bash
bash install.sh --agent claude
```

Troque `claude` pelo seu agente: `codex`, `opencode` ou `antigravity`. Use `all` para instalar em todos de uma vez, ou uma lista (`claude,codex`).

O instalador faz quatro coisas, nesta ordem:

1. Confere o Python antes de mexer em qualquer arquivo.
2. Copia a skill para a pasta de cada agente escolhido. Se já existir uma versão, move a anterior para `~/.analise-mercado-yt/backups/`. Ela não fica ao lado da nova, para o agente não carregar duas.
3. Pede a chave da API, sem mostrá-la na tela, e a grava em `~/.analise-mercado-yt/.env`, legível só por você. Se o arquivo já existir, não o toca. A chave não é aceita como argumento, porque o histórico do terminal a guardaria.
4. Instala yt-dlp e Pillow com o pip e roda a checagem (`doctor.py`).

Opções:

| Windows | bash | Efeito |
|---|---|---|
| `-Agent claude,codex` | `--agent claude,codex` | agentes a atender; padrão `claude` |
| `-Dest "D:\skills"` | `--dest ~/skills` | pasta extra de skills (soma ao `-Agent`; no bash pode repetir) |
| `-SkipDeps` | `--skip-deps` | não roda o pip |
| `-NonInteractive` | `--non-interactive` | não pergunta a chave; usa a variável `YT_API_KEY`, se existir |
| `-ReplaceKey` | `--replace-key` | pede a chave de novo e troca a gravada |

### Onde cada agente procura skills

Conferido em 30/10/2026 nas páginas dos agentes. As pastas mudam com as versões.

| Agente | Pasta global | Instalador |
|---|---|---|
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/analise-mercado-yt` | `claude` |
| [Codex](https://developers.openai.com/codex/skills) | `~/.agents/skills/analise-mercado-yt` | `codex` |
| [OpenCode](https://opencode.ai/docs/skills/) | `~/.config/opencode/skills/analise-mercado-yt` (lê também `~/.claude/skills` e `~/.agents/skills`) | `opencode` |
| [Antigravity](https://antigravity.google/docs/skills) | app e IDE: `~/.gemini/config/skills/analise-mercado-yt`; CLI (`agy`): `~/.gemini/antigravity-cli/skills/analise-mercado-yt` | `antigravity` (as duas) |

Para um projeto só, copie a pasta `analise-mercado-yt` para `<projeto>/.claude/skills/` (Claude Code), `<projeto>/.agents/skills/` (Codex e Antigravity) ou `<projeto>/.opencode/skills/` (OpenCode). Mais detalhes em [analise-mercado-yt/references/hosts.md](../analise-mercado-yt/references/hosts.md).

Se você usa um agente que não está na tabela, ache a pasta de skills dele e passe-a com `-Dest` ou `--dest`.

## 4. Confira e faça a primeira análise

Os dois comandos abaixo não gastam cota (o `doctor.py` gasta 1 unidade ao testar a chave; `--no-api` evita isso):

```bash
python analise-mercado-yt/scripts/selftest.py
python analise-mercado-yt/scripts/doctor.py
```

O `selftest.py` confere os scripts, as métricas e o veredito com dados sintéticos e monta um relatório de teste, sem rede e sem chave. O `doctor.py` confere Python, dependências, pastas e a chave.

Depois abra o agente numa pasta de trabalho e peça:

> Analise o nicho de finanças pessoais em PT e EN.

Se o agente não escolher a skill sozinho, diga o nome: "Use a skill analise-mercado-yt para analisar...". A skill mostra o plano, o custo em buscas e espera o seu ok. Na primeira análise ela também pergunta as suas ferramentas, as horas por vídeo e o orçamento. O resultado fica em `analises/<tema>-<ano-mês>/relatorio.html`.

## Colab, sem agente

Para quem não tem um agente de código. O notebook usa uma IA gratuita (a IA do Colab ou a Gemini API na faixa gratuita) no lugar do agente. Ele não faz a pesquisa web do dia: receita e risco saem do conhecimento do modelo, e o relatório avisa isso. O caminho é **experimental**: passou em testes automáticos com uma IA simulada e ainda não foi executado no Colab real. Teste com um nicho pequeno antes de confiar.

1. Pegue o pacote de código do Colab. Na página de Releases do repositório, baixe `DarkNiche-Colab.zip`. Se preferir gerar, rode `python analise-mercado-yt/extras/colab/package_colab.py` e use `dist/DarkNiche-Colab.zip`.
2. Abra o [Colab](https://colab.research.google.com/) e escolha **Arquivo > Fazer upload de notebook**. Envie `analise-mercado-yt/extras/colab/DarkNiche.ipynb`. Outra opção: **Arquivo > Abrir notebook > GitHub** e cole o endereço do repositório.
3. Escolha o ambiente de execução **CPU**.
4. No menu de chaves (**Secrets**), crie `YOUTUBE_API_KEY` com a sua chave e ative o acesso ao notebook. Se for usar a Gemini API, crie também `GEMINI_API_KEY`.
5. Execute a célula de upload e envie o `DarkNiche-Colab.zip`. Depois execute a célula de dependências.
6. Escolha se monta o Google Drive. Ligado, as análises e o contador de cota ficam em `MyDrive/DarkNiche-state/`. Desligado, baixe o trabalho antes de encerrar, porque a máquina do Colab é temporária.
7. Preencha o título, os idiomas (padrão `pt,en,es`) e o pedido. Escolha `AI_BACKEND`: `colab`, `gemini` ou `dados` (sem IA, só estatísticas).
8. Use **Executar tudo**. Depois escolha recortes e mercados nos seletores e clique em **Aprofundar seleção**. O notebook baixa o HTML do relatório e um ZIP com as evidências.

Limites, modos de IA, retomada de análises e privacidade: [analise-mercado-yt/extras/colab/colab.md](../analise-mercado-yt/extras/colab/colab.md).

## Instalação manual

Use se não quiser rodar o instalador.

1. Copie a pasta `analise-mercado-yt` do pacote para a pasta de skills do seu agente (tabela acima). O nome da pasta precisa ser `analise-mercado-yt`.
2. Instale as dependências: `python -m pip install -r requirements.txt`.
3. Guarde a chave de um destes jeitos:
   - variável de ambiente `YT_API_KEY`;
   - arquivo `~/.analise-mercado-yt/.env` com a linha `YT_API_KEY=sua_chave`. Em macOS e Linux, restrinja o acesso com `chmod 600`.
4. Rode `python <pasta da skill>/scripts/doctor.py`.

Para guardar a chave e o cache em outro lugar, defina `AMY_HOME` (chave e perfil) e `AMY_DATA` (cache e contador de cota).

## Trocar ou revogar a chave

Se a chave vazou, revogue-a primeiro: no Cloud Console, em **APIs e serviços > Credenciais**, abra a chave e apague-a ou gere uma nova. Depois grave a nova no seu computador:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -SkipDeps -ReplaceKey
```

```bash
bash install.sh --skip-deps --replace-key
```

O instalador pede a chave nova sem mostrá-la e troca a gravada. Se você usa a variável de ambiente `YT_API_KEY`, atualize-a também.

## Atualizar e desinstalar

Para atualizar, baixe a versão nova e rode o instalador de novo, com os mesmos agentes. A versão anterior vai para `~/.analise-mercado-yt/backups/`. A chave e o perfil ficam como estavam.

Para desinstalar, apague a pasta `analise-mercado-yt` de cada pasta de skills da tabela. Para apagar também a chave, o perfil, o cache e os backups, apague `~/.analise-mercado-yt`. As análises ficam nas pastas `analises/` onde você as pediu.

## Problemas comuns

**Python não encontrado.** Instale o Python 3.10 ou mais novo e abra um terminal novo. No Windows, o `python` da Microsoft Store que ainda não foi instalado não conta.

**A skill não aparece no agente.** Confira se a pasta `analise-mercado-yt` está na pasta certa da tabela e se tem um `SKILL.md` dentro. Reabra o agente. Peça pelo nome: "Use a skill analise-mercado-yt".

**Erro `quotaExceeded` ou HTTP 403.** A cota do dia acabou. Espere a meia-noite do Pacífico ou use outro projeto do Google Cloud. O `scan.py` retoma de onde parou e sai com código 3 quando a cota esgota.

**Erro `API key not valid` ou `keyInvalid`.** A chave está errada, a YouTube Data API v3 não está ativada no projeto dela, ou a restrição da chave exclui essa API. Confira os três no Cloud Console e rode `doctor.py`.

**O pip recusa instalar (`externally-managed-environment`).** Acontece em macOS e Linux recentes. Crie um ambiente virtual (`python3 -m venv .venv`), ative-o e rode `pip install -r requirements.txt`. Abra o agente com o ambiente ativado, para que os scripts usem o mesmo Python.

**O yt-dlp parou de funcionar.** O YouTube muda e o yt-dlp acompanha. Atualize: `python -m pip install -U yt-dlp`.

**Sem Pillow ou sem ffmpeg.** Sem Pillow, a skill não monta grades de miniaturas. Sem ffmpeg, não tira prints de vídeo. O resto funciona. Instale com `python -m pip install Pillow` e o comando do seu sistema para o ffmpeg.

**O relatório abre com fontes diferentes.** Ele carrega as fontes do Google Fonts pela rede. Sem internet, usa as fontes do sistema, e o conteúdo é o mesmo.

**O Colab não acha a chave.** Confira o nome do segredo (`YOUTUBE_API_KEY`) e se o acesso ao notebook está ativo. Sem segredo, o notebook pede a chave num campo oculto.

Não achou o seu problema? Abra um issue com o sistema, a versão do Python, o agente e a saída do `doctor.py`. Apague a chave de qualquer texto antes de colar.
