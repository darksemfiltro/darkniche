# Metodologia: como medir sem se enganar

Leia antes de montar o plano (§1–§4) e de novo antes de pontuar (§5–§10). O princípio é um só: **os scripts medem,
o agente lê**. Toda métrica sai de uma busca do YouTube, e busca tem ruído: vídeo fora do tema, outro idioma,
pico de evento, emissora de TV, título genérico que casa por acaso. Um número só vira evidência depois que você
olhou os vídeos que o produziram.

Sumário: §1 unidades · §2 como escrever consultas · §3 API vs yt-dlp · §4 cota · §5 métricas da célula ·
§6 normalização por mercado · §7 notas automáticas · §8 canais (frescos, reativados, marcas) · §9 contaminação ·
§10 sondagem de títulos · §11 comentários · §12 visual e lacuna de formato · §13 sinais grátis e em tempo real ·
§14 raio-X da referência · §15 segunda passada adaptativa · §16 pesquisa web

---

## 1. Unidades

- **Célula** = nicho derivado × idioma (ex.: `fraudes__fr`). É a unidade de medida: 1–3 consultas nativas, mesmas
  regras de filtro, métricas comparáveis entre idiomas.
- **Sondagem** (probe) = um título vencedor transposto de forma nativa para outros idiomas, para responder "alguém
  já fez isso lá?". Mede lacuna de ângulo, não demanda.
- **Oportunidade** = proposta de canal (lente + domínio + formato + idioma/mercado) que se apoia em 1+ células e
  sondagens. É o que recebe nota e vai para o ranking.

## 2. Como escrever consultas

A consulta decide a qualidade de tudo depois. Regras:

1. **Escreva como o público daquele país digita, não como um tradutor traduziria.** "Por que tudo está caro" vira
   `warum ist alles so teuer` (DE), `dlaczego wszystko jest takie drogie` (PL), `perché costa così tanto` (IT).
   Use o autocomplete (`signals.py suggest`) para descobrir a forma real: ele mostra gírias, empréstimos do inglês e
   a ordem das palavras.
2. **Curta vence longa**, sobretudo em mercados pequenos. Frases de 6+ palavras em BG, RO e TR devolveram 0–7
   vídeos em um teste real; 2–3 palavras-chave (`измама`, `фалит`, `схема`) devolvem o universo real.
3. **2–3 variantes por célula** (lista em `queries[lang]`): uma pelo tema (`fraude contábil`), uma pelo gancho
   (`maior golpe da história`), uma pelo formato (`explicado`). O scan junta e deduplica.
4. **Armadilhas de idioma:** japonês não separa palavras (use termos curtos: `統計の嘘`, `粉飾決算`); alemão aglutina
   (`Preiserhöhung` ≠ `Preis Erhöhung`: teste as duas); turco e polonês flexionam (use a raiz mais comum); em
   espanhol, a região muda o vocabulário (MX `estafa`, AR `estafa`/`curro`); em PT-PT ≠ PT-BR.
5. **Palavra genérica atrai ruído.** `teuer` puxou pesca e matcha; `números não mentem` puxou política e futebol.
   Defina `keywords` (precisa conter ao menos uma) e `exclude` (não pode conter nenhuma) por célula, por idioma se
   preciso. A comparação ignora acentos e caixa. O `metrics.py` conta o que foi descartado (`offtopic`). Para **cruzar
   dois temas** (ex.: finanças × IA), use grupos: `"keywords": [["chatgpt", "claude", " ia "], ["financ", "planilha"]]`
   exige um termo de cada grupo (E entre grupos, OU dentro de cada um). Sem isso, a célula enche de tutoriais de IA
   sem relação com finanças. Os filtros são locais: ajustar não gasta busca nem pede nova aprovação.
6. **Janela de tempo**: 12 meses (`after_days: 365`) mede a demanda atual. Para mercados pequenos ou temas
   evergreen, use 24 meses na célula (`"filters": {"after_days": 730}`). Para medir "está crescendo agora",
   rode uma variante de 90 dias.
7. **Long-form vs Shorts:** o padrão mede long-form (≥ 8 min em `metrics.py --long 480`). Busca por views sem
   filtro de duração volta cheia de Shorts (no teste de aviação, 47 de 50 resultados em francês), e a célula fica
   "vazia" por engano. Nas células que podem virar oportunidade, use `"filters": {"duration": "longform"}`: o scan
   faz duas buscas (médio 4–20 min + longo > 20 min) e junta, custando o dobro. O `metrics.py` avisa
   "⚠ x% Shorts: refaça com duration longform" quando a fatia de Shorts (`short_share`) passa de 40% com pouca
   amostra long-form. Se a proposta for Shorts, rode `"duration": "short"` e `metrics.py --long 0` numa análise
   separada: métricas de Shorts e de long-form não se comparam.
8. **Filtros por idioma, sem criar célula nova:** `"filters_lang": {"fr": {"duration": "longform", "after_days": 730}}`
   vale só para aquele idioma da célula. Para tirar um canal do cálculo (notícia, outro idioma, reupload), use
   `"exclude_channels": ["nome do canal", "UC…"]` (aceita lista ou dicionário por idioma). Variantes de consulta
   ficam na lista `queries[lang]` da mesma célula; célula nova só quando o **tema** muda.

## 3. API e yt-dlp: quando usar cada uma

**Regra:** a YouTube Data API é o padrão para o que decide o ranking. O yt-dlp é **complemento**: entra quando a API
não basta, ou quando ele é melhor e mais barato.

| | YouTube Data API (`mode: api`) | yt-dlp (`mode: ytdlp`) |
|---|---|---|
| Custo | 1 busca por página + até 2 unidades gerais por 50 resultados | 0 buscas; ~2 unidades gerais por 50 vídeos se enriquecer (vídeos + canais) |
| Filtros | idioma de relevância, **região**, data exata, duração, categoria, ordem | ordem, faixa de upload (ano/mês/semana), duração |
| Dados | datas, idioma declarado, inscritos, criação do canal | só o que a página mostra; o enriquecimento completa |
| Use para | células que vão decidir o ranking; mercados onde região importa | amplitude, sondagens, segunda passada, mercados pequenos |

A chave da API é o diferencial: só ela filtra por **região + idioma + data** ao mesmo tempo. Escolha assim:

| Situação | Use |
|---|---|
| Célula que decide o ranking e precisa de região, idioma de relevância e data exata | **API** |
| A API não cobre: transcrição, thumbnails, prints de vídeo | **yt-dlp** |
| O bucket de buscas do dia acabou (código 3) e ainda faltam consultas | **yt-dlp** com enriquecimento |
| Tema global, em que região e idioma de relevância não mudam o resultado (ex.: tema em EN) | **yt-dlp com enriquecimento**: mesmos campos por 0 buscas |
| Amplitude barata: sondagens de títulos, mercados pequenos, segunda passada, listar um canal inteiro | **yt-dlp** (as sondagens usam yt-dlp por padrão) |
| Célula decisiva em que você quer precisão **e** amplitude | `mode: both` (roda as duas e une) |
| O usuário não tem chave | **yt-dlp**, em modo reduzido (abaixo) |

Trocar o modo de uma coleta já aprovada é mudança de escopo: mostre a nova estimativa e registre a aprovação de novo
(a troca para yt-dlp custa 0 buscas, então é rápida).

**Medido (30/10/2026):** a mesma consulta em PT (12 meses, long-form) pela API e pelo yt-dlp com enriquecimento. 84% dos
resultados coincidiram e o top 15 foi idêntico. Canais efetivos (3,7), concentração (75%), fatia de canais pequenos
(8%), frescor (2%) e vídeos ≥ 100 mil (8) saíram iguais. A mediana de views divergiu (9,1 mil na API, 6,5 mil no
yt-dlp, porque o filtro "este ano" da interface não cobre 12 meses corridos), o que mexeu a nota D em um degrau. Só a
API trouxe a estimativa de oferta (≈ 50 mil vídeos) e o filtro de região. Custo: API 2 buscas + 4 unidades; yt-dlp
0 buscas + 4 unidades. Para decidir a estrutura do mercado, o yt-dlp enriquecido basta; para a nota de demanda e para
a região, a API.

**Sem chave de API (modo reduzido).** O yt-dlp devolve só id, título, views, duração e canal: sem data, inscritos,
data de criação do canal nem idioma declarado. O que isso muda: ritmo (views/dia), frescor, tamanho de canal e
perfil de canais ficam **sem medição** (as flags `sem_datas` e `sem_inscritos` aparecem e o V cai para "sem dados");
D usa a mediana de views; o idioma sai só do título (por isso `idioma_nao_verificado`). A análise ainda separa nicho
vivo de nicho morto, mas não sustenta veredito GO: diga isso ao usuário e peça a chave para fechar. Transcrição,
thumbnails e sinais (`signals.py`) funcionam sem chave.

## 4. Cota

- Regra oficial verificada em 12/10/2026: bucket de **100 buscas/dia** e bucket geral de **10.000 unidades/dia**.
  `search.list` consome 1 do bucket de buscas; `videos/channels/playlistItems/commentThreads.list`, 1 geral.
  [Google: quota](https://developers.google.com/youtube/v3/determine_quota_cost).
- Virada à meia-noite do Pacífico; em 12/10/2026 corresponde a 04h de Brasília. Use America/Los_Angeles para
  outras datas (05h de Brasília fora do horário de verão dos EUA).
- O contador local não conhece outras ferramentas, máquinas, chaves do mesmo projeto nem a alocação concedida
  pelo Google. O saldo remoto fica desconhecido até consultar o projeto autenticado no Google Cloud.
- Orçamentos locais: 95 buscas (`YT_SEARCH_DAILY_BUDGET`) e 9.500 unidades gerais (`YT_DAILY_BUDGET`).
  Reserva cada tentativa HTTP antes do envio, incluindo falhas/retries; isso pode superestimar uso real.
  Cache válido não gasta quota. Locks evitam perda de contagem entre processos que compartilham AMY_HOME.
- Uma consulta de 1 página: até **1 busca + 2 gerais**; `longform` duplica para **2 buscas + 4 gerais**.
  Perfil de canal com 60 uploads: até **5 gerais**, mais resolução do handle se necessária.
  Comentários: 1 geral por página de até 100. Referência com 300 uploads: ~13–15 gerais. Doctor online: 1 geral.
- Estimativas são máximos sem cache, sem retries e com páginas cheias. O scan mostra buscas, unidades gerais e
  chamadas HTTP separadamente. `--probes --estimate` calcula sondagens, inclusive `longform` e enriquecimento.
- Matriz completa de 15–25 nichos × 12 idiomas × 2 variantes × longform: **720–1.200 buscas + até 1.440–2.400
  gerais**, antes de perfis/comentários. Com orçamento de 95 buscas/dia, são ~8–13 dias; use yt-dlp para amplitude.
- `data/quota.json` contém somente esta análise (schema 2). Contadores antigos são migrados como estimativas;
  `units` passa a excluir buscas. HTMLs de exemplo preservados podem exibir a convenção antiga.
- Saída 3 = quota interrompeu a coleta; 2 = falha parcial de rede/coleta. Retome após corrigir.
- O scan compara assinatura de consulta + filtros + região + modo. Mudanças invalidam o resultado anterior;
  `keywords`/`exclude` são filtros locais e não exigem novas chamadas. `--refresh` refaz os resultados usando
  o cache HTTP válido. `--mode` explícito prevalece sobre modos de células.
- yt-dlp não oferece período exato de dois anos; usa busca sem limite temporal e filtra datas conhecidas após
  enriquecimento. A amostra pode omitir resultados. Sem enriquecimento, datas/idiomas desconhecidos não provam
  ausência de concorrência. Sondagem sem dados suficientes recebe `inconclusivo`.

## 5. Métricas da célula (`data/cells.json`)

Só contam como **oferta nativa** os vídeos no idioma-alvo e long-form (8 min ou mais). O idioma vem dos metadados
do YouTube, corrigido pelo título só quando a evidência é forte: título em escrita própria (japonês marcado como
"en"), metadado "en"/"hi" (padrão comum de canal) com título claramente em outro idioma (pega reupload dublado e
hindi escrito em alfabeto latino) ou título com 3+ palavras-função de outro idioma e nenhuma do declarado. Vídeo
sem idioma identificável **não vira nativo**: fica em `n_unknown_lang` e, passando de 20% dos resultados, liga a flag
`idioma_nao_verificado` (a nota L automática não passa de 3, porque a oferta pode estar subestimada). O título confirma
o idioma em pt, en, es, fr, de, it, nl, pl, ro, tr, id, hi, sv, da, no, fi, cs, hu, vi, ja, ko, zh, ar, th, el, he, ru,
uk e bg. **Nos demais idiomas** (fa, ur, bn, ta, sk, hr, sr, ms, fil…) o título não confirma nada: vale o metadado do
YouTube e o filtro de relevância da busca, o sem-idioma entra como nativo provisório e a célula leva a flag
`idioma_nao_verificavel`. Confira o topo: dublagens com título em inglês continuam fora da oferta nativa, e isso pode
ser exatamente a lacuna.

| Métrica | O que é | Como ler |
|---|---|---|
| `n`, `n_native`, `n_long` | resultados, nativos, nativos long-form | `n_long < 5` = evidência fraca; `< 3` = não dá para medir |
| `short_share` | fração de Shorts (≤ 3 min) nos resultados | alta com `n_long` baixo = consulta poluída: refaça com `longform` |
| `lang_purity` | fração dos resultados de idioma conhecido que estão no idioma-alvo | < 0,5 = a busca no idioma traz muito conteúdo de fora: oferta local rala (bom sinal de lacuna) ou consulta ruim |
| `med`, `p90`, `top_views` | mediana, p90 e máximo de views long-form nativas | a mediana de um topo por views mede o **teto** do nicho; compare p90/med para ver se é "1 hit e o resto nada" |
| `vpd_p25`, `vpd_p50`, `vpd_p75` | views por dia dos vídeos maduros (14+ dias) | **ritmo**: base do D. Não depende da idade dos vídeos do topo |
| `vpd_lo`, `vpd_hi` | intervalo de 90% da mediana do ritmo (bootstrap) | faixa larga (hi > 3 × lo) liga a flag `mediana_instavel` |
| `k100`, `m1`, `saturation` | nº de vídeos ≥ 100 mil e ≥ 1 mi; fatia do topo acima de 100 mil | `saturation ≥ 0,8` com 30+ vídeos = `cabeca_saturada`: o nicho é largo, desça um subnicho |
| `active` | canais nativos cuja soma de views long-form na célula passa de 10 mil × tamanho do mercado (mínimo 500) | concorrência real (limitada pelo tamanho da amostra) |
| `n_eff`, `hhi` | canais efetivos = 1 ÷ Σ(fatia de views por canal)² | 2 canais com tudo = 2; 60 iguais = 60. Separa topo concentrado de fragmentado quando `active` já passou de 20 |
| `dominance` | fatia de views dos 3 maiores canais | > 0,8 = um dono; pode ser lacuna (só um atende) ou fosso (ele é imbatível): leia quem é |
| `size_mix`, `small_view_share` | fatia de vídeos e de views por faixa de inscritos (< 10 mil, 10–100 mil, 100 mil–1 mi, > 1 mi); views de canais < 100 mil | **porta aberta**: se canais pequenos aparecem no topo, o algoritmo entrega para quem chega |
| `small_wins` | vídeos ≥ 100 mil de canais < 100 mil inscritos | idem, em contagem |
| `outlier_density` | fração com views/inscritos ≥ 3 | idem, mais fino |
| `fresh_share` | fatia de views de canais criados há ≤ 540 dias (só entre os com data de criação) | porta aberta para novatos (ver §8) |
| `recent_share`, `med_vpd` | publicados nos últimos 90 dias; mediana de views/dia de todos os datados | descritivo: o topo por views subrepresenta vídeo novo, então **não é tendência** |
| `supply_est` | estimativa do YouTube de quantos vídeos casam com a busca (`pageInfo.totalResults`, soma de médio e longo) | aproximada, com teto de 1 milhão (flag `oferta_acima_do_teto`); serve para comparar células |
| `avg_dur_min` | duração média | formato dominante |
| `top`, `foreign_top` | 15 maiores nativos long-form; 3 maiores de outro idioma | **leia sempre** |
| `offtopic` | descartados pelo filtro da célula | se for alto, a consulta está ruim |
| `flags` | `idioma_nao_verificado`, `idioma_nao_verificavel`, `sem_datas`, `sem_inscritos`, `cabeca_saturada`, `mediana_instavel`, `oferta_acima_do_teto`, `tamanho_assumido` | `idioma_nao_verificado`, `idioma_nao_verificavel`, `sem_datas` e `sem_inscritos` marcam a evidência como parcial (`auto.evidence`: ok · parcial · fraca); todas as flags vão para o relatório |

## 6. Normalização por tamanho de mercado

Views cruas não se comparam entre idiomas: 50 mil em búlgaro é um sucesso enorme; 50 mil em inglês é pouco.
`common.MARKET_SIZE` dá um tamanho relativo de público por idioma (EN = 1,0; ES 0,70; PT 0,33; FR 0,20; DE 0,18;
JA 0,17; IT 0,10; PL 0,07; RO 0,03; BG 0,011…). A demanda vira **views equivalentes em EN** (`med / size`).
É uma aproximação de ordem de grandeza; se você tiver número melhor para um país (mercados.md), sobrescreva em
`plan.languages[].size`. Quando o país-alvo for um subconjunto (ex.: ES só da Espanha), reduza o `size`. Idioma fora da
tabela recebe 0,05 e a marca `size_assumed` no plano; o `metrics.py` liga a flag `tamanho_assumido` e limita D a 3.
`init_run.py` aceita idioma-região (`es-AR`, `pt-PT`, `en-GB`) e avisa o que ficou sem região ou sem tamanho.

## 7. Notas automáticas (sugestões, não veredito)

`metrics.py` sugere D, L e V em `cell.auto`:

- **D (demanda)** pelo **ritmo** equivalente EN (`vpd_p50 ÷ tamanho do mercado`, views/dia): < 25 → 1 · < 125 → 2 ·
  < 500 → 3 · < 2.000 → 4 · ≥ 2.000 → 5. Sem datas, pela mediana de views equivalente EN: < 5 mil → 1 · < 25 mil → 2 ·
  < 100 mil → 3 · < 400 mil → 4 · ≥ 400 mil → 5 (`auto.d_basis` diz qual base valeu). Teto 3 com `n_long < 5` ou
  tamanho de mercado assumido; 1 com `n_long < 3`.
- **L (lacuna)** pelos canais nativos ativos: ≤ 2 → 5 · ≤ 5 → 4 · ≤ 10 → 3 · ≤ 20 → 2 · mais → 1. +1 se
  `lang_purity < 0,5` com 10+ resultados de idioma conhecido. Concentração (`n_eff`, `dominance`) fica para o julgamento.
- **V (velocidade)** por `fresh_share` (só com `n_long ≥ 5`): ≥ 30% → 5 · ≥ 15% → 4 · ≥ 5% → 3 · > 0 → 2. Sem datas
  de criação, por `small_view_share`: ≥ 50% → 4 · ≥ 30% → 3 · ≥ 10% → 2 (flag `V_por_canais_pequenos`).

Revise à mão (e marque `measured: false` com o motivo no `why`) quando: o topo tem ruído que o filtro não pegou;
os "ativos" são de outro tema; o canal fresco é marca grande; a demanda vem de um evento; a célula está vazia por
consulta ruim. Uma nota medida tem número **e** leitura humana do topo.

## 8. Canais: frescos, reativados, marcas e anomalias

`profile_channels.py` perfila (sem search) os maiores canais **de cada célula, em rodízio** (o 1º de cada
célula, depois o 2º…), só com vídeos nativos long-form, mais `plan.competitors` e `--extra`. Canais gigantes de
notícia ou de outro tema ainda podem entrar: leia o topo antes e passe com `--extra` os canais dedicados ao nicho
que você quer medir (eles são a concorrência real).

- **Fresco** = conta criada (ou reativada) há ≤ 540 dias **e** mediana recente ≥ 10 mil. É a prova de que o
  algoritmo está entregando aquele tema/formato para quem chega agora.
- **Reativado** = conta velha cujo primeiro vídeo da amostra é recente, ou com hiato longo seguido de regime novo
  (conta de 2013 que muda de formato em 2026 e decola). Conte como fresco: é o mesmo fenômeno.
- **Marcas grandes não provam porta aberta.** Um canal novo de emissora de TV ou de editora nasce com distribuição e
  catálogo. Desconte no V e cite como concorrente, não como evidência de que um solo cresce ali.
- **Canal dedicado × canal gigante de outro tema.** `topic_share` (fatia dos uploads cujo título casa com os termos
  da célula) separa quem concorre de fato (perto de 1) de quem só apareceu na busca (perto de 0). Perfile os
  dedicados com `--extra`; leia os gigantes como contexto, não como concorrência.
- **Cadência:** `uploads_90d` e `uploads_90d_all` mostram quantos vídeos por semana os concorrentes publicam. É o
  esforço que um entrante precisa igualar.
- **Anomalias de engajamento:** likes/views < 0,3% com views/inscritos muito alto, comentários desativados ou
  genéricos em massa podem indicar views pagas ou embed/anúncio. Não use esses vídeos como prova de demanda.
- **Fosso vs lacuna:** um canal que domina (dominance alto) com produção cara (documentário filmado, equipe) deixa
  espaço para outro formato; um canal que domina **com o mesmo formato que você faria** é fosso.

## 9. Contaminação

Antes de pontuar, pergunte: este número existiria sem um fato externo?

- **Política/eleição:** em um teste real, 2 dos 3 maiores hits de um canal pegaram o calendário eleitoral e uma
  consulta genérica em PT voltou quase só comentário político. Use os comentários (§11) para medir a fatia política e
  prefira o vídeo evergreen como sinal limpo.
- **Evento único:** um lançamento de produto fez três vídeos de 0,6 a 1,35 mi em ES; é pico, não demanda de base.
  Rode uma variante sem o nome do evento para ver o que sobra.
- **Calendário:** eleição, copa, olimpíadas, Black Friday, declaração de imposto, volta às aulas, balanços
  trimestrais (mercados.md §4.4). Uma janela de 12 meses pega um ciclo inteiro; uma de 90 dias pode pegar só o pico.
  Confirme as datas na pesquisa web (§16): calendário de memória vence.
- **Reuploads, compilações e conteúdo infantil** inflam views sem dizer nada sobre o formato.

## 10. Sondagem de títulos (transposição)

1. Escolha 2–6 títulos-fonte: os outliers da referência e os títulos mais fortes que a varredura encontrar (em
   qualquer idioma).
2. Reescreva cada um de forma **nativa** em cada idioma (mesma promessa, não mesmas palavras).
3. `scan.py --probes` busca cada versão (yt-dlp por padrão, 24 meses). `metrics.py` compara por sobreposição de
   palavras de conteúdo (sem palavras-função; bigramas de caracteres em CJK) e marca: **existe** (2+ palavras em comum,
   ao menos um terço das palavras da consulta e ≥ 10 mil views), **fraco** (parecido, com poucas views), **lacuna**
   (nada parecido), **inconclusivo** (sem resultados, ou 20% ou mais deles sem idioma ou duração).
4. **Revise todo "existe" e toda "lacuna" antes de reportar.** O comparador é lexical: em um teste, "manipular" em
   japonês deu "existe" por causa de um corte de idol que usava a mesma palavra. Registre a correção em
   `analysis.probe_review` (o relatório mostra o automático e o revisado).
5. Leitura: "existe em EN e FR, lacuna em IT e PL" = ângulo provado com espaço; "lacuna em todos" = ângulo não
   provado (ou consulta ruim).

## 11. Comentários

`comments.py` lê até 400 comentários por vídeo e resume: fatia de militância política (por contagem e por likes;
o léxico só pega nomes e rótulos inequívocos, e `--political "termo1,termo2"` acrescenta os do seu mercado), elogio
ao formato, pedidos de pauta ("faz um sobre…"), perguntas. Use para:
- separar demanda pelo **tema** de demanda pela **briga** (militância nos likes = contaminação);
- achar pautas pedidas (viram títulos e primeiros vídeos);
- confirmar que o formato é parte do valor ("a edição", "a animação", "didático").
O léxico é aproximado: leia as citações mais curtidas antes de concluir.

## 12. Visual e lacuna de formato (eixo G)

`visual.py sheets` monta, por célula, uma grade com as thumbnails dos 15 maiores long-form nativos. Leia cada grade
(ferramenta de leitura de imagem; a ordem é da esquerda para a direita, de cima para baixo, igual a `ids` em
`visual/sheets.json`) e classifique cada thumb em um estilo:
`rosto/apresentador` · `reação` · `reportagem/TV/filmado` · `foto/stock` · `imagem de IA` · `3D` ·
`motion/ícones/infográfico` · `desenho/stick figure` · `texto gigante` · `mapa` · `yukkuri/avatar`.
Grave em `format_gap` as fatias e se o estilo proposto aparece. A delegação para um modelo pequeno (Haiku) funciona
bem aqui: é classificação visual repetitiva. Sem as grades (rede bloqueada: o `visual.py` avisa e sai com código 2,
sem gravar grade falsa), julgue pelo tipo de canal que vence e marque G como `measured: false`.

## 13. Sinais grátis e em tempo real (eixos F e D, leitura de tendência)

Sem chave de API e sem gastar buscas. Grave cada saída em `data/signals/` para o relatório mostrar.

- `signals.py suggest "<semente>" --lang de --region DE --expand` → como o país digita o tema e a cauda longa
  (`suggest_<lang>_<slug>.json`). Quantas sugestões o tema rende, sozinho, já compara sementes.
- `signals.py wiki "<artigo>" --lang en --targets pt,es,fr,de,it,ja,pl,ro,bg,tr,id` → interesse relativo pelo
  conceito em cada Wikipédia (partes por milhão do tráfego daquele idioma; `wiki_<slug>.json`). `rel` > 1,5 (× a
  mediana dos idiomas) = o tema pesa mais naquela cultura; `index` 100 = o idioma de maior interesse. **Tendência**:
  últimos 12 meses contra os 12 anteriores, **descontada a queda da própria Wikipédia** (`yoy_rel`; ±15% =
  subindo ou caindo). Idioma sem artigo ou sem dado vem `null`, não zero.
- `signals.py trending --geo BR --youtube --out data/signals/trending_br.json` → buscas em alta no Google Trends
  (RSS, com as notícias ligadas) e o gráfico "em alta" do YouTube no país (2 unidades gerais, nenhuma busca). Retrato
  do momento: acha tema quente e separa demanda de base de pico. Nem toda categoria tem gráfico; o script cai para o geral.
- `signals.py news "<tema>" --lang pt --region BR --days 30 --out data/signals/news_<slug>.json` → manchetes recentes
  do Google Notícias e o ritmo da última semana contra a anterior (`ratio` ≥ 1,5 acelera; ≤ 0,67 esfria). O RSS corta
  em ~100 itens: em tema enorme o ritmo não é calculado, e isso já é informação (cobertura intensa).
- Sem rede para esses serviços, o comando sai com erro e mensagem clara em segundos: registre a limitação e siga (F
  fica julgado).
- Nenhum mede consumo de vídeo: são apoio ao fit cultural e à leitura de tendência, junto com o perfil do mercado e
  os temas locais que aparecem no topo das células. Tendência de verdade pede 2 sinais concordando.

## 14. Raio-X da referência

`reference.py` baixa o canal inteiro (playlistItems, barato), calcula mediana long-form, fatia do top 3, outliers
e **pivô** (ponto em que a mediana de log(views) mais muda, com ao menos 3 vídeos de cada lado). Vídeos com menos de
14 dias ficam de fora (ainda acumulam views e fariam todo canal estável parecer em queda). O pivô vem marcado
`forte` (mudança de 2× ou mais e faixas interquartis sem sobreposição) ou `fraco` (provável ruído: não trate como
mudança de formato). Um pivô forte costuma coincidir com troca de formato, tema ou duração; nomeie as fases em
`analysis.reference.phase_labels`.
Com yt-dlp: transcrições dos mais vistos, grade de thumbs e prints de 4 trechos de 8 s dos 2 mais vistos.

- **Anatomia do roteiro:** leia a transcrição com marcas de tempo e corte em blocos (gancho, contrato/promessa,
  fundamentos, virada, mid-roll, escada, casos, mito, outro lado, síntese, payoff). Cada bloco com início, fim,
  `kind` (gancho, contrato, didatico, escalada, midroll, outro) e uma nota de como é feito.
- **Gramática do motion:** dos prints (e da skill `watch`, se existir, ou `gemini_video.py` em 2–3 trechos),
  descreva regras: o que é fixo, o que entra quando, como a fala dispara objetos, como a cena troca, o que é
  pontuação visual. Regras, não adjetivos.
- **Paleta:** `visual.py palette` nos prints e thumbs; nomeie as cores pelo papel (fundo, acento, alerta).

## 15. Segunda passada adaptativa

Depois da primeira leitura, gaste o que sobrou de cota onde a incerteza muda a decisão:
1. Células promissoras com `n_long < 5` → variantes curtas (yt-dlp primeiro).
2. Células com ruído → `keywords`/`exclude` e `metrics.py` de novo (custo zero).
3. Oportunidade no topo apoiada em eixos julgados → a medição que falta (grade de thumbs para G, sinais para F).
4. Mercado vizinho do vencedor (FR → BE/CA-QC; DE → AT/CH; ES → AR/CO) → mesma consulta com outra região.
Pare quando a ordem do top 3 não mudaria com mais dados.

## 16. Pesquisa web em tempo real

Receita, política do YouTube, preço de ferramenta, calendário e notícia não saem dos scripts de coleta: saem de
páginas abertas hoje. `pesquisa-web.md` lista o que pesquisar por tema, como registrar com `research.py` (URL, data
de acesso, tipo e confiança da fonte) e como citar no `analysis.json`. O relatório mostra tudo na seção "Pesquisa em
tempo real". Dado coletado (YouTube) e fato pesquisado (web) são evidências de natureza diferente: mantenha os dois
rotulados.
