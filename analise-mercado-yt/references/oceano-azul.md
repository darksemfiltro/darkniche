# Rubrica de oportunidade: oceano azul primeiro

A prioridade padrão do usuário é, nesta ordem: **(1) oportunidade no sentido de oceano azul** (muita demanda, pouca
ou nenhuma concorrência que importe, fit real com a cultura e os hábitos de consumo do país, formato subutilizado
naquele subnicho), **(2) automação e custo**, **(3) receita**, **(4) velocidade**. A fórmula traduz essa ordem em
pesos; o usuário muda a ordem no perfil (`prioridades`) ou em `analysis.weights`. A rubrica abaixo diz como dar cada
nota de 1 a 5 e o que precisa existir para chamá-la de **medida**.

Sumário: §1 fórmula, travas, tiers e veredito · §2 eixos do oceano (D, L, F, G) · §3 produção (A, K, S) · §4 receita,
velocidade e risco (M, V, R) · §5 como escrever o `why` · §6 checagem contra autoengano · §7 exemplos

---

## 1. Fórmula, travas, tiers e veredito (implementados em `scripts/score.py`)

```
Oceano   O = 0,30·D + 0,30·L + 0,25·F + 0,15·G
Produção P = (A + K + S) / 3
Nota       = 20 · (0,50·O + 0,25·P + 0,15·M + 0,10·V)        → 0 a 100, arredondada
```

- **Travas** (limitam ao tier B, qualquer que seja a nota): D ≤ 2 (oceano vazio) · L ≤ 2 (mar vermelho) ·
  F ≤ 2 (o tema não conversa com o país) · R ≥ 4 (risco alto). R = 5 limita ao C.
- **Incerteza** = fração dos eixos D, L, F, G sem medição. Acima de 50%, a oportunidade fica no máximo em B com a
  marca "validar": pode ser ótima, mas ainda é hipótese.
- **Tiers:** S ≥ 80 · A ≥ 70 · B ≥ 58 · C < 58.
- **Selo "oceano azul"** quando D ≥ 3, L ≥ 4, F ≥ 3, G ≥ 3, R < 4 e incerteza ≤ 50%.
- **Faixa da nota** = a nota se cada eixo do oceano ainda julgado estivesse 1 ponto pior ou melhor. Faixa larga
  significa que a decisão depende do que falta medir.
- **Confiança:** *alta* = incerteza ≤ 25% e 10+ vídeos long-form nas células que sustentam a oportunidade; *média* =
  incerteza ≤ 50% e 5+; *baixa* = o resto.
- **Veredito:**
  - **EVITAR**: D ≤ 2, ou F ≤ 2, ou (L ≤ 2 e G ≤ 3), ou R = 5, ou tier C. Em mar vermelho, um formato realmente
    diferente (G ≥ 4) tira da lista de evitar e manda para teste.
  - **GO**: tier S ou A, incerteza ≤ 50%, R < 4 e confiança média ou alta.
  - **TESTAR**: o resto. O relatório diz o que medir primeiro (`missing`) e o `plan` traz o experimento.
- Pesos ajustáveis em `analysis.weights` (ex.: `{"M": 0.25, "V": 0.0}`) quando o usuário disser que a prioridade
  mudou. Registre o motivo em `method.notes`.

## 2. Eixos do oceano

### D · Demanda
Base: **ritmo** da célula = mediana de views por dia dos vídeos long-form nativos com 14+ dias (`vpd_p50`), dividida
pelo tamanho do mercado do idioma (equivalente EN, `auto.vpd_en_equiv`). O ritmo troca o "quanto acumulou" por "quanto
rende por dia" e não depende da idade dos vídeos do topo.

| Nota | Âncora (views/dia equivalentes em EN) |
|---|---|
| 5 | ≥ 2.000 |
| 4 | 500–2.000 |
| 3 | 125–500, ou demanda forte com amostra pequena (n_long 3–4) |
| 2 | 25–125 |
| 1 | < 25, ou não há como medir (n_long < 3) |

Sem datas nos dados (modo yt-dlp), cai para a mediana de views equivalente EN (5 mil / 25 mil / 100 mil / 400 mil).
Teto 3 com n_long < 5, ou com tamanho de mercado assumido (idioma fora da tabela).

**Medido** = célula com n_long ≥ 5, topo lido e sem contaminação relevante. Demanda inferida de outro idioma, só da
sondagem ou de célula com ruído é **julgada**. Com a flag `cabeca_saturada`, D 5 diz "o nicho é grande", não "este
recorte é bom": desça um subnicho e meça de novo.

### L · Lacuna de oferta
Base: canais nativos ativos na célula (`m.active`), **quem** são, e a concentração (`n_eff`, `dominance`).

| Nota | Âncora |
|---|---|
| 5 | 0–2 canais ativos; ou a busca no idioma devolve sobretudo conteúdo de fora |
| 4 | 3–5 ativos; ou mais, mas quase todos de outro formato caro (TV, documentário filmado) |
| 3 | 6–10 ativos |
| 2 | 11–20 ativos |
| 1 | > 20 ativos, ou um dono com o mesmo formato que você faria (fosso) |

Com 20+ ativos, todo mundo cai em 1. Use os **canais efetivos** (`n_eff`, 1 ÷ HHI) para separar: 8 efetivos entre 33
ativos é topo concentrado (poucos donos); 23 efetivos entre 61 é topo fragmentado (muitos disputando). Diga qual dos
dois lê melhor no `why`. **Medido** = contagem conferida no topo (os ativos são do tema). Ajustar por tipo de
concorrente é legítimo, mas explique.

### F · Fit cultural
Use o teste de 5 eixos de `mercados.md` §4.1 (âncora local do tema, formato nativo, registro e língua, monetização ×
regulação, timing de consumo; 0–2 cada).

| Nota | Soma do teste (0–10) |
|---|---|
| 5 | 9–10 |
| 4 | 8 |
| 3 | 6–7 |
| 2 | 4–5 |
| 1 | 0–3 |

**Medido** quando pelo menos dois eixos do teste têm dado: autocomplete mostrando a busca nativa, índice da Wikipédia
> 1,5 com tendência não negativa, entidades locais nos títulos do topo, comentários pedindo o tema, vídeos nativos
vencendo os traduzidos, regra local confirmada na pesquisa web. Só perfil de mercado e intuição = **julgado**.
Tradução pura de um tema sem âncora local raramente passa de 3: a dublagem automática do YouTube já entrega isso.

### G · Formato subutilizado
Base: fatia do estilo proposto entre as 15 thumbnails long-form do topo (grade do `visual.py sheets`).

| Nota | Fatia do estilo proposto no topo |
|---|---|
| 5 | 0%: ninguém faz assim |
| 4 | até 10% |
| 3 | até 25% |
| 2 | até 50% |
| 1 | > 50%: o formato já é o padrão |

**Medido** = grades lidas e classificadas. Julgado pelo tipo de canal vencedor (sem grade) = **julgado**.

## 3. Produção (para o perfil do usuário)

As notas valem para o estilo de produção que a oportunidade propõe, feito com as ferramentas, o hardware, o tempo e o
orçamento do **perfil** (`doctor.py --profile`). Perfil vazio: pergunte antes de pontuar e grave a resposta; não
invente ferramenta nem orçamento. `producao.md` traz os fatores e os cortes.

### A · Automação (5 = fácil)
`A = 6 − dificuldade`, com a dificuldade de `producao.md` §12.1 (base 1, +1 por fator: consistência de personagem,
assets exclusivos, checagem jurídica ou factual obrigatória, voz ou rosto humano, sincronia fina, dados instáveis).
Ex.: motion por código com dados públicos = dificuldade 2 → A 4; dossiê com checagem jurídica = 2–3 → A 3–4.

### K · Custo de IA por vídeo (5 = barato)
Custo variável de um vídeo de 20 min no modo que **escala**, com os preços **pesquisados hoje** (`pesquisa-web.md`
§2.5). Assinatura de agente que o usuário já paga baixa o custo marginal para perto de zero enquanto couber nos
limites do plano, mas não escala para vários canais: mostre os dois cenários no texto de produção e **não suba o K
por causa dela**.

| Nota | Custo por vídeo de 20 min |
|---|---|
| 5 | ≤ US$ 1 |
| 4 | ≤ US$ 3 |
| 3 | ≤ US$ 8 |
| 2 | ≤ US$ 25 |
| 1 | > US$ 25 (ex.: vídeo gerado por IA como base) |

Se o perfil tem `orcamento_video_usd`, desça uma nota por faixa que o custo passar do orçamento.

### S · Solo e local
Combina `producao.md` §12.2 (local) e §12.3 (solo) com o perfil: os dois "sim" → 5 · um "parcial" → 4 · os dois
"parcial" → 3 · um "não" → 2 · os dois "não" → 1. "Local" fala das etapas pesadas (voz, imagem, vídeo, render) no
hardware do perfil; o roteiro feito pelo agente não tira o "sim". "Parcial" quando uma etapa pesada exige nuvem ou
licença não comercial. "Solo" respeita `horas_max_video` e `videos_mes`. Idioma que o usuário não fala nem tem
revisor nativo (`revisores_nativos`) conta como "parcial"; TTS fraco no idioma desce mais um.

## 4. Receita, velocidade e risco

### M · Receita
Classe de RPM do mercado (`mercados.md` §1–§2) **confirmada na pesquisa web** (`pesquisa-web.md` §2.1) e ajustada
pelo nicho:

| Nota | Âncora |
|---|---|
| 5 | RPM muito alto ou alto em nicho que paga (finanças, tecnologia, negócios) |
| 4 | alto em nicho comum; ou médio em nicho que paga |
| 3 | médio em entretenimento e educação |
| 2 | médio-baixo ou baixo |
| 1 | muito baixo sem monetização alternativa |

+1 quando há monetização fora do AdSense que encaixa no tema (afiliado, produto próprio, newsletter paga, patrocínio
comprovado no nicho); −1 só quando o conteúdo cai em "anúncios limitados" das diretrizes do YouTube (violência
gráfica, imagens chocantes, tragédia explorada de forma sensacionalista). Documentário técnico ou educativo sobre
temas difíceis, sem imagem chocante e com tom de explicação, não perde o ponto. Sem pesquisa web, M é julgado.

### V · Velocidade (porta aberta para canais novos)
`fresh_share` da célula (views de canais criados há ≤ 18 meses; metodologia §8), descontando canais novos de marcas
grandes: 5 ≥ 30% · 4 ≥ 15% · 3 ≥ 5% · 2 > 0 · 1 nenhum (ou amostra pequena). Sem datas de criação dos canais, o script
usa a fatia de views de canais com menos de 100 mil inscritos (`small_view_share`: ≥ 50% → 4, ≥ 30% → 3, ≥ 10% → 2) e
marca a flag `V_por_canais_pequenos`. Some o que o perfil de canais mostra: canais frescos com mediana recente ≥ 10 mil.

### R · Risco (5 = arriscado; entra como trava)
| Nota | Âncora |
|---|---|
| 1 | evergreen benigno (curiosidades, ciência, história antiga) |
| 2 | baixo: exige precisão de dados, sem pessoas reais acusadas |
| 3 | pessoas ou empresas reais (difamação possível), YMYL leve, risco de "conteúdo inautêntico" se o template variar pouco |
| 4 | política, saúde ou finanças com recomendação; apostas; leis locais de insulto ou desinformação |
| 5 | alto risco de strike ou ilegal no país (desinformação médica, ódio, apostas proibidas, voz clonada de pessoa real) |

Confirme a regra do YouTube e a lei local na pesquisa web antes de dar 4 ou 5, e antes de dar 1 ou 2 para formato
automatizado.

## 5. Como escrever o `why`

Cada eixo leva **número + fonte + leitura**, em uma frase. Bom: "Ritmo de 320 views/dia nos vídeos maduros (≈ 970 em
equivalente EN), 60 canais ativos e 15 efetivos". Ruim: "Alta demanda". Quando corrigir a nota automática, diga o
que o número cru mostrava e por que não vale. Fato da web entra com `{"research": "rN"}` na evidência e o número no
`why`. A evidência da oportunidade lista os vídeos e canais citados, com link (`{"video": ID}` / `{"channel": "UC…"}`).

## 6. Checagem contra autoengano (antes de fechar o ranking)

1. **Tire o maior vídeo de cada célula do top 3.** A conclusão muda? Se sim, a demanda é um hit, não um mercado.
2. **Evento ou calendário?** Rode a variante sem o nome do evento; olhe as datas dos vídeos do topo.
3. **Topo saturado?** Se quase tudo passa de 100 mil views, D 5 é do nicho largo. Desça um subnicho e meça.
4. **Os concorrentes contados fazem o mesmo formato?** TV filmada não compete com motion explainer pelo mesmo custo de
   produção, mas compete pela mesma atenção: isso pesa em G, não em L.
5. **Lacuna ou consulta ruim?** Veja `foreign_top`, a pureza e uma variante curta antes de chamar de lacuna.
6. **É só tradução?** Se a proposta é o mesmo vídeo em outro idioma, o F não passa de 3.
7. **Marca grande inflou "fresco"?** Desconte no V.
8. **O usuário faz isso com o perfil dele, sozinho, pelo custo dito?** Se precisa de revisor nativo, diga.
9. **Os eixos julgados estão marcados como julgados, e M e R têm fonte datada?** Hipótese bem rotulada vale mais que
   certeza falsa.

## 7. Exemplos (piloto real de finanças pessoais, 29/10/2026, 4 células)

- **Dívidas, PT** (`sair-dividas`): ritmo 320 views/dia (≈ 970 eq. EN) → **D 4**; 60 canais ativos, 15 efetivos → **L 1**;
  23% das views vêm de canais < 100 mil e 16% de canais frescos → **V 4**. Mar vermelho, mas com porta aberta: só vale
  com um formato diferente (G ≥ 4); sem isso, **EVITAR**; com formato medido, **TESTAR**.
- **Investir do zero, EN** (`invest-iniciantes`): ritmo 3.552 views/dia → **D 5**; 61 ativos, 22 efetivos → **L 1**;
  7% das views de canais pequenos e 0% de frescos → **V 1**; topo saturado (83 de 83 vídeos passam de 100 mil). Nicho
  gigante e fechado: **EVITAR** nesse recorte; o caminho é um subnicho.
- Regra de leitura: D alto com L 1 e V 1 não é oportunidade, é mercado maduro. O que pontua é D com porta aberta.
