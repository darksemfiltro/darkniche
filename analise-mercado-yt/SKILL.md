---
name: analise-mercado-yt
description: Analisa nichos do YouTube com dados reais (YouTube Data API, yt-dlp, Wikipédia, autocomplete, "em alta") e pesquisa web em tempo real, com foco em canais faceless e automatizados. A partir de um nicho, ideia, canal ou vídeo, mede demanda, concorrência, porta de entrada para canais novos, fit por país e idioma e custo de produção, pesquisa receita e risco na web, e entrega um relatório HTML interativo em português com veredito (GO, TESTAR ou EVITAR), links em todo vídeo e canal citado e fontes datadas. Use quando o usuário quiser avaliar um nicho ou ideia de canal, saber se vale a pena abrir um canal, modelar um canal ou vídeo, comparar idiomas e países ou achar nichos pouco explorados.
---

# Análise de mercado do YouTube

A skill mede demanda, concorrência, porta aberta para um canal novo, fit com o país e o idioma, receita, risco e
custo de produção. Cada fato externo tem fonte e data de acesso; cada vídeo ou canal citado, link. O que foi
**medido** fica separado do que foi **julgado**. O relatório é sempre em português (pt-BR), com frases curtas.

Regras que valem em todas as fases:

1. **Leia o que os scripts medem.** A busca do YouTube traz ruído (outro tema, outro idioma, evento, TV, título que
   casa por acaso). Abra os vídeos que produziram um número antes de usá-lo como evidência.
2. **Fato externo exige fonte e data.** RPM, regra do YouTube, preço, notícia: pesquise na web agora, registre com
   `research.py` e cite. Número de memória não entra como fato (veja `references/pesquisa-web.md`).
3. **Gaste cota só depois do ok.** Buscas da API têm bucket próprio (padrão 100/dia); o resto custa 1 unidade do
   bucket geral (10.000/dia). Estime, mostre o custo, espere o ok. Não repita coleta para contornar o teto. A API é o
   padrão; o **yt-dlp é complemento**: use quando a API não basta (transcrição, thumbnails, bucket de buscas
   esgotado) ou quando ele é melhor e mais barato (metodologia §3 tem a regra de escolha).
4. **Nunca imprima, copie ou grave a chave de API.** Os scripts a leem sozinhos. Se ela vazar num log, avise o usuário.
5. **Registre a incerteza.** Topo saturado, amostra pequena e eixo julgado entram no veredito. Sem dado, escreva
   "inconclusivo", não "oceano azul".

## Onde estão as coisas

`$S` = a pasta que contém este SKILL.md. Rode os scripts com `python` (Windows; `py -3` também serve) ou `python3`,
com aspas nos caminhos: `python "$S/scripts/doctor.py"`. Cada análise vive numa pasta própria, por padrão
`./analises/<slug>-<AAAA-MM>/`, com `plan.json` (o que medir), `raw/` e `data/` (coletado), `analysis.json` (seu
julgamento) e o relatório. `AMY_HOME` muda a pasta da configuração (chave, perfil); `AMY_DATA` muda a do cache e da
cota (padrão: a mesma).

| Leia | Quando |
|---|---|
| `references/perguntas.md` | antes de perguntar ao usuário, ao gerar variações (bends, micronichos) e ao escolher idiomas |
| `references/selecao.md` | ao montar o plano: triagem, escolha do usuário ou aprovação direta, custo |
| `references/metodologia.md` | ao escrever consultas e antes de pontuar (métricas, ruído, contaminação, sinais) |
| `references/pesquisa-web.md` | na Fase 5: o que pesquisar na web, como registrar e como citar |
| `references/oceano-azul.md` | ao dar as notas (rubrica 1–5 por eixo, medido × julgado, travas, veredito) |
| `references/mercados.md` | ao julgar fit cultural e receita por país (perfis, teste de fit) |
| `references/producao.md` | ao dar A, K e S (automação, custo de IA, local e solo) conforme o perfil do usuário |
| `references/relatorio.md` | ao escrever o `analysis.json` (esquema, regra dos links, checklist, entrega) |
| `references/licoes.md` | para calibrar a profundidade e evitar as armadilhas que já custaram caro |

## Fluxo

Avise o usuário com uma linha curta a cada fase ("coletando 3 idiomas…", "lendo o topo das células…").

### Fase 0 · Ambiente e perfil

```bash
python "$S/scripts/doctor.py"
```

O doctor confere Python, yt-dlp, ffmpeg (opcional), Pillow (opcional), a chave da YouTube Data API (gasta 1 unidade)
e a cota local do dia. Se faltar algo, mostre o conserto que ele sugere. Leia o perfil (`doctor.py --profile`):
idiomas principais, foco, perfil de produção. O perfil evita perguntas repetidas. **Não preencha por conta própria**
hardware, ferramentas ou orçamento: pergunte quando for dar A, K e S (Fase 7) e grave a resposta no perfil.
Sem chave de API a análise roda em modo reduzido (yt-dlp: sem data, inscritos nem idioma declarado); diga isso e
o que se perde (`references/metodologia.md` §3).

### Fase 1 · Entender o pedido

Identifique o ponto de partida: **nicho ou ideia** ("vale abrir um canal de X?"), **referência** (canal ou vídeo a
modelar) ou **descoberta** ("não sei o nicho; ache oportunidades"). Pergunte só o que a mensagem e o perfil não
respondem (`perguntas.md` §2; até 4 perguntas, recomendação primeiro; sem ferramenta de perguntas, pergunte em
texto). Defina o **escopo**: idiomas (padrão do perfil; sem perfil, pt, en e es; acrescente os que o usuário pedir),
país de cada idioma e o que fica de fora. Responda por escrito as perguntas do agente (`perguntas.md` §3) em
`notas.md` na pasta da análise: elas registram, antes do plano, o que gera as views, quem busca e quem atende.

- **Descoberta:** rode `signals.py trending` e `signals.py suggest --expand` para 5 a 10 sementes do interesse do
  usuário, agrupe as sugestões em subnichos e leve de 3 a 6 candidatos à triagem.
- **Referência:** Fase 2. **Nicho ou ideia:** pule para a Fase 3.

### Fase 2 · Raio-X da referência (só com canal ou vídeo de referência)

```bash
python "$S/scripts/init_run.py" "Título" --ref @handle --langs pt,en,es      # cria a pasta e o plan.json
python "$S/scripts/reference.py" --run <pasta> @handle --max 60 --no-ytdlp  # canal, pivô, outliers: ~7 unidades, 0 buscas
```

Leia `data/reference.json` (fases, pivô "forte" ou "fraco", top vídeos). Pivô fraco é ruído. Depois da escolha de
mercado (Fase 3), aprofunde: 1 a 3 transcrições cortadas em blocos com tempo (metodologia §14), grades de
thumbnails e prints, e o **vetor de formato** (`perguntas.md` §4). Descreva o motion como regras, não adjetivos.

### Fase 3 · Plano, custo e aprovação

`init_run.py "Título" --langs pt,en,es` cria a pasta (sem `--ref` quando não há referência). Preencha `plan.json`
(`cells`, `probes`, `competitors`; exemplo em `assets/plan.example.json`) com consultas **nativas, curtas, 2 ou 3
variantes** por célula (metodologia §2). Dois caminhos (`selecao.md`):

- **O usuário nomeou nicho(s) e idiomas** ("analise finanças pessoais em PT e EN"): estime, mostre a tabela de custo
  e peça **um** "ok".
  ```bash
  python "$S/scripts/scan.py" --run <pasta> --estimate
  python "$S/scripts/selection.py" approve --run <pasta>          # só depois do ok do usuário
  ```
- **A skill propõe os recortes** (ideia, referência, descoberta): faça a **triagem** (até 24 buscas; `--search-budget`
  até 60 com o usuário), leia o topo, ranqueie com evidência, mostre a tabela e peça a escolha.
  ```bash
  python "$S/scripts/triage.py" --run <pasta> --duration longform --estimate
  python "$S/scripts/triage.py" --run <pasta> --duration longform
  python "$S/scripts/scan.py" --run <pasta>/triage --triage
  python "$S/scripts/metrics.py" --run <pasta>/triage
  python "$S/scripts/profile_channels.py" --run <pasta>/triage --max 6 --top-per-cell 2 --n 50
  python "$S/scripts/selection.py" propose --run <pasta>
  python "$S/scripts/selection.py" select --run <pasta> --cells <ids> --langs <idiomas>   # só com a escolha do usuário
  ```

Peça aprovação ou escolha **uma vez**, com custo em buscas e unidades. Silêncio, perfil e "análise completa" não
contam como escolha. O scan recusa rodar sem registro (código 4).

### Fase 4 · Coleta

```bash
python "$S/scripts/scan.py" --run <pasta>                  # matriz nicho × idioma (retomável; código 3 = cota acabou)
python "$S/scripts/scan.py" --run <pasta> --probes         # sondagens de títulos de plan.probes (se o plano tiver)
python "$S/scripts/metrics.py" --run <pasta>               # métricas, notas automáticas D/L/V, flags
#   → leia o topo das células promissoras ANTES de perfilar e anote os canais dedicados ao nicho
python "$S/scripts/profile_channels.py" --run <pasta> --max 20 --extra <UC… dos dedicados>
python "$S/scripts/comments.py" --run <pasta> <id1> <id2> <id3>      # 3 a 6 vídeos-chave
python "$S/scripts/signals.py" suggest "<semente>" --lang fr --region FR --expand --out <pasta>/data/signals/suggest_fr_<slug>.json
python "$S/scripts/signals.py" wiki "<artigo>" --lang en --targets pt,es,fr --out <pasta>/data/signals/wiki_<slug>.json
python "$S/scripts/signals.py" trending --geo BR --youtube --out <pasta>/data/signals/trending_br.json
python "$S/scripts/visual.py" sheets --run <pasta> --cells <ids> --langs <langs>      # grades de thumbs do topo
```

Se a cota acabar, o scan retoma no dia seguinte (a cota vira à meia-noite do Pacífico); enquanto isso use cache,
yt-dlp (`--mode ytdlp`) e a leitura. A cota gasta fica em `data/quota.json` e vai para o relatório. Sinal que falhar
por rede (`signals.py`, `visual.py`) vira limitação: o eixo correspondente fica julgado.

### Fase 5 · Pesquisa em tempo real

Antes de dar nota de receita e risco, pesquise na web com a ferramenta de busca e leitura de páginas do host e
registre cada fato (`references/pesquisa-web.md`):

```bash
python "$S/scripts/research.py" add --run <pasta> --topic monetizacao --claim "…" --value "…" --url https://… --accessed AAAA-MM-DD --type dados --confidence media
python "$S/scripts/research.py" check --run <pasta>
```

Mínimo: **monetização** (RPM e outras fontes de receita do nicho e do país) e **política do YouTube** para o formato
(conteúdo repetitivo ou inautêntico, voz e imagem sintéticas, direitos). Desejável: tendência e notícias dos últimos
90 dias, concorrência qualitativa, mercado e regulação do país, preço das ferramentas que o perfil usa. Sem
ferramenta de web, não registre nada de memória: escreva a limitação em `analysis.limitations`.

### Fase 6 · Leitura crítica

- Para cada célula com D ≥ 3 ou número estranho, **abra o topo** (`data/cells.json` → `top`, `foreign_top`). Ruído?
  Ajuste `keywords`/`exclude` e rode `metrics.py` de novo (custo zero). Evento, política ou calendário? Rode uma
  variante sem o evento.
- Flag **cabeca_saturada**: o topo tem 30 vídeos ou mais e 80% deles passam de 100 mil views. O nicho é largo: desça
  um subnicho antes de decidir.
- Compare **canais efetivos**, **porta aberta** (views de canais pequenos) e **ritmo** entre células: separam o que
  o D e o L sozinhos não separam.
- Revise toda sondagem "existe" e "lacuna" (`probe_review`). Classifique as thumbnails do topo → `format_gap`.
- Julgue o fit cultural com `mercados.md` §4.1 e os sinais → `markets`.
- **Segunda passada** só onde a incerteza muda a decisão e dentro do escopo aprovado; consulta nova pede nova
  aprovação.

### Fase 7 · Oportunidades, notas e veredito

Escreva `analysis.json` (`relatorio.md` §2): resumo com 4 a 7 achados que mudam decisão e um `verdict_text` de uma
frase, método, markets, `format_gap`, **as oportunidades que o escopo sustenta** (não invente seis para parecer
completo), produção, riscos, plano e limitações. Cada oportunidade leva os 10 eixos com nota e `why` (número +
fonte + leitura); nos quatro do oceano, `measured`. Cite vídeos e canais por ID e fatos da web por
`{"research": "rN"}`. Notas A, K e S dependem do **perfil de produção do usuário** (`producao.md`): se ele estiver
vazio, pergunte e grave. Rubrica em `oceano-azul.md`.

```bash
python "$S/scripts/score.py" --run <pasta>             # nota, tier, faixa, confiança e veredito (GO · TESTAR · EVITAR)
python "$S/scripts/check_analysis.py" --run <pasta>    # links, eixos, pesquisa; corrija até 0 erros
```

Faça a checagem contra autoengano (`oceano-azul.md` §6) antes de aceitar o ranking.

### Fase 8 · Relatório e entrega

```bash
python "$S/scripts/build_report.py" --run <pasta> --embed
```

Abra o `relatorio.html` ou tire print e confira: sem erro de console, ranking igual ao do `score.py`, links
abrindo. Se a ferramenta Artifact existir, publique `relatorio.artifact.html`; senão, entregue o caminho do
`relatorio.html`. O relatório traz botões para baixar CSV e imprimir. A mensagem final é curta: veredito das 2 ou 3
melhores oportunidades (nota, confiança, por que, o que falta medir), o caminho ou link e o menor próximo passo.

## Delegação

Delegar é opcional e serve para trabalho repetitivo (classificar thumbnails, triar comentários, resumir
transcrições). Dê ao subagente só o arquivo, o critério e o formato de saída, e confira o resultado. Notas, veredito
e síntese ficam com o agente principal. Use o modelo e o esforço que o usuário definiu.

## Armadilhas (detalhes em `licoes.md` e `metodologia.md`)

- Views cruas não se comparam entre idiomas: use o equivalente EN. Idioma fora da tabela de tamanho vira "tamanho
  assumido" e limita D a 3.
- Mercado pequeno + frase longa = zero resultados. Consultas curtas, variantes, 24 meses.
- Topo da busca por views mede o teto do nicho, não o típico. Tendência não sai dessa amostra: use Wikipédia,
  autocomplete e "em alta".
- Canal novo de marca grande não prova que um novato cresce ali. Hit de evento não é demanda de base.
- yt-dlp quebra quando o YouTube muda: rode `pip install -U yt-dlp` antes de concluir que "não há resultados".
- Scripts gravam em UTF-8; acento quebrado no terminal do Windows é só a exibição.
