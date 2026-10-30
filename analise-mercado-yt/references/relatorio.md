# Relatório: o analysis.json, os links e a entrega

O relatório é gerado por `scripts/build_report.py` a partir dos dados coletados (`data/*.json`) e de um único
arquivo escrito pelo agente: **`analysis.json`**. Tudo que é julgamento (achados, fit, oportunidades, notas,
produção, riscos, plano) mora nele. Exemplo completo: `assets/analysis.example.json`; relatório pronto em
`exemplos/` na raiz do pacote.

Sumário: §1 regra dos links · §2 esquema do analysis.json · §3 o que cada seção do relatório mostra · §4 checklist
antes de gerar · §5 gerar, publicar e entregar

---

## 1. Regra dos links (inegociável)

**Todo vídeo ou canal citado precisa abrir a fonte.** O usuário clica no título para ver a referência. Por isso,
em `analysis.json` cite por ID e deixe o relatório montar o link:

```json
{"text": "Título do vídeo", "video": "<ID de 11 caracteres>", "views": 282759}
{"text": "Nome do canal (915 mil inscritos)", "channel": "UC<22 caracteres>"}
{"text": "Relatório do instituto X 2026", "url": "https://...", "accessed": "2026-10-29"}
{"research": "r3"}
```

- IDs de vídeo e canal saem dos dados coletados: `data/cells.json` (`top`, 15 por célula, e `foreign_top`),
  `raw/search/*.json` e `raw/probes/*.json` (todos os resultados, inclusive os que não entraram no `top`),
  `data/channels.json` (`top`, `recent`), `data/reference.json` e `data/comments.json`. Não invente: procure o ID
  nos dados (`grep -l "trecho do título" raw/search/*.json`). O `check_analysis.py` avisa quando um ID citado não
  aparece em nenhum desses arquivos e sugere o ID certo quando só a caixa difere (IDs diferenciam maiúsculas).
- Canal se cita pelo ID `UC…`, não pelo @handle.
- Link de busca do YouTube (`results?search_query=`) só quando não existe um vídeo específico (ex.: "a busca X
  devolve zero"), e mesmo assim prefira citar o vídeo mais próximo.
- **Fato da web** (RPM, política, preço, notícia) entra por `{"research": "rN"}`: o relatório monta o texto do fato,
  o link, a data de acesso e o tipo e a confiança da fonte a partir de `data/research.json` (`research.py`). Fonte
  externa fora desse registro entra com `url` e `accessed`; lida só via busca, com `note: "via busca"`.
- As tabelas geradas a partir dos dados (mapa, concorrência, explorador, sondagens, referência, pesquisa) já saem
  com link.

## 2. Esquema do analysis.json

Campos opcionais podem faltar; a seção correspondente some do relatório. Texto em português (pt-BR), frases curtas.

Exceção explícita para modo sem IA: `analysis_mode: "technical"`, `meta.analysis_mode: "technical"`,
`opportunities: []`, resumo descritivo e limitações obrigatórias. O verificador aceita somente relatório
técnico sem oportunidades pontuadas; a interface identifica o modo e oculta o ranking estratégico. Nunca use
essa exceção para apresentar como completa uma avaliação de oceano azul que não foi feita.

```jsonc
{
  "meta": {
    "title_html": "Finanças pessoais · <span class=\"acc\">PT × EN</span>",  // opcional; senão usa plan.title
    "stamp": "ANÁLISE DE NICHO",       // carimbo do topo (opcional)
    "description": "uma frase para o card do Artifact",
    "footer": "rodapé"
  },
  "summary": {
    "lead": "parágrafo de abertura (pode ter <strong>)",
    "lead_plain": "versão sem HTML",
    "verdict_text": "uma frase com a resposta: o que fazer e por quê",     // aparece no topo, acima dos cartões de veredito
    "findings": [{"title": "Achado em uma frase.", "text": "Número + leitura."}]   // 4–7 achados
  },
  "method": {"scan": "...", "fit": "...", "format": "...", "score": "(opcional, texto da fórmula)", "notes": ["..."]},
  "reference": {                      // mesclado com data/reference.json; no modo ideia é a própria referência
    "phase_labels": [{"key": "animado", "label": "100% animado", "from": "2026-09-15", "to": "9999-12-31"}],
    "notes_html": "leitura do canal e do pivô",
    "format_vector": [{"var": "Lente", "value": "…", "swaps": "…"}],
    "script_source": {"id": "<videoId>", "title": "…"},
    "script_blocks": [{"label": "Gancho", "start": 0, "end": 28, "kind": "gancho", "note": "…"}],
                      // kind: gancho | contrato | didatico | escalada | midroll | outro (segundos)
    "palette": [{"hex": "#120202", "label": "fundo"}],
    "aesthetic_notes": ["…"], "motion": ["regra 1", "regra 2"],
    "gallery": [{"src": "raw/reference/frames/x_sheet.jpg", "caption": "…"}],   // opcional; senão usa thumbs/prints
    "title": "…", "examples": [/* evidências */]          // só no modo ideia
  },
  "bends": [{"axis": "Lente + domínio", "from": "…", "to": "…", "cells": ["dividas"], "note": "por que pode funcionar"}],
  "markets": [{
    "lang": "pt", "label": "Português", "countries": "BR", "rpm_class": "médio-baixo", "yt_users": "~140 mi",
    "fit": 4, "fit_notes": "…", "consumption": "…", "queries": "como o país busca", "risks": "…",
    "evidence": [/* evidências com link, inclusive {"research": "rN"} */]
  }],
  "format_gap": [{"cell": "dividas", "lang": "pt", "styles": [{"style": "apresentador", "share": 0.7}],
                  "proposed_present": false, "note": "…"}],   // null = não deu para conferir
  "opportunities": [{
    "id": "dividas-pt", "name": "Nome do canal", "lang": "pt", "markets": "BR",
    "lens": "quem fala e de onde vem a autoridade", "domain": "o assunto", "oneliner": "a tese em uma linha",
    "bend": {"label": "nova lente + novo idioma", "from": "…", "to": "…"},
    "cells": ["dividas__pt"],                               // células que sustentam a demanda: <id da célula>__<idioma>
    "scores": {
      "D": {"v": 4, "measured": true,  "why": "número + fonte + leitura"},
      "L": {"v": 2, "measured": true,  "why": "…"}, "F": {"v": 4, "measured": false, "why": "…"},
      "G": {"v": 4, "measured": false, "why": "…"},
      "A": {"v": 4, "why": "…"}, "K": {"v": 4, "why": "…"}, "S": {"v": 3, "why": "…"},
      "M": {"v": 3, "why": "…"}, "V": {"v": 3, "why": "…"}, "R": {"v": 3, "why": "…"}
    },
    "evidence": [/* vídeos e canais que sustentam os whys + {"research": "rN"} */],
    "aesthetic": "como a estética se adapta", "format": "duração e estrutura",
    "titles": ["5–8 títulos nativos prontos"], "signature": "assinatura de embalagem",
    "production": {"automation": "4/5 …", "cost": "US$ 3–6 (20 min, híbrido)", "local": "sim/parcial/não + motivo",
                   "solo": "sim/parcial/não + motivo", "stack": "ferramentas do perfil"},
    "monetization": "…", "risks": "…", "why_now": "(opcional) por que a janela é agora",
    "first_videos": ["3 primeiras pautas"], "competitors": [{"id": "UC…", "title": "…"}]
  }],
  "probe_review": [{"probe": "id-da-sondagem", "lang": "ja", "status": "lacuna", "note": "falso positivo: …"}],
  "production": {
    "intro": "…",
    "pipeline": [{"name": "Roteiro", "desc": "…", "tool": "…", "gate": false}],   // gate = etapa com revisão humana
    "costs": [{"style": "(a) Motion · 20 min", "local": "US$ …", "hybrid": "US$ …", "cloud": "US$ …", "hours": "4–8 h", "note": "…"}],
    "stack": ["…"], "notes": ["…"], "sources": [/* evidências com url ou research */]
  },
  "risks": [{"risk": "…", "level": "alto|médio|baixo", "mitigation": "…", "source": "https://… (opcional)"}],
  "plan": [{"when": "Dias 1–3", "what": "…", "success": "critério mensurável"}],   // a 1ª linha vira "Próximo passo" no veredito
  "limitations": ["o que não foi medido e por quê"],
  "sources": [{"label": "…", "url": "…", "note": "via busca", "accessed": "AAAA-MM-DD"}],
  "weights": {},                                        // opcional: muda os pesos da nota
  "quota": {"schema": 2, "units": 0, "searches": 0}     // opcional: senão usa data/quota.json desta análise
}
```

`score.py` calcula nota, tier, **faixa**, **confiança** e **veredito** de cada oportunidade; o relatório mostra o que
o script calculou, então não escreva esses campos à mão.

## 3. O que cada seção mostra

| # | Seção | Vem de |
|---|---|---|
| — | Topo: título, data da coleta e do dado mais recente, idiomas, células, canais, cota; botões para baixar CSV e imprimir | plan + meta + contadores |
| 00 | **Veredito**: cartões GO · TESTAR · EVITAR das 3 melhores oportunidades (nota com faixa, confiança, motivos, o que medir) e o próximo passo | opportunities (calculado), plan, summary.verdict_text |
| 01 | Resumo, ranking ordenável com veredito, quadrante oceano azul (ritmo × concorrentes, clique abre a célula) | summary, opportunities, cells |
| 02 | Raio-X da referência: tiles, linha do tempo com fases e pivô (forte ou fraco), top vídeos, vetor de formato, anatomia do roteiro, paleta e motion, comentários | data/reference.json + reference |
| 03 | Bends gerados | bends |
| 04 | Mapa nicho × idioma (troca de métrica, hachura = pouca amostra, painel da célula com sinais do nicho, faixas de inscritos e vídeos; link direto `#cell=<id>__<idioma>`) | data/cells.json |
| 05 | Fit cultural por mercado + sinais (autocomplete, Wikipédia com tendência, em alta agora) | markets + data/signals |
| 06 | **Pesquisa em tempo real**: fatos da web por tema, com fonte, tipo, confiança e data de acesso | data/research.json |
| 07 | Concorrência: canais perfilados, filtro "só frescos" | data/channels.json |
| 08 | Lacuna de formato (+ grades de thumbnails) | format_gap + visual/sheets |
| 09 | Transposição de títulos (matriz existe/fraco/lacuna com forma e cor, revisões marcadas) | data/probes.json + probe_review |
| 10 | Oportunidades: cartão por oportunidade com veredito, barras por eixo, travas, motivos, o que medir, notas por eixo (medido/julgado), evidência, títulos, produção | opportunities |
| 11 | Produção: pipeline, custo por vídeo, stack | production |
| 12–13 | Riscos · plano do menor experimento | risks, plan |
| 14 | Explorador de todos os vídeos (busca, ordenação) | cells.top |
| 15 | **Glossário**: como ler cada número | fixo |
| 16 | Limitações, método e fontes | limitations, method.notes, sources |

Filtros globais (idiomas, tiers, busca) valem para todas as seções e ficam salvos no navegador. Tema escuro com
acento vermelho (e versão clara) automáticos. Seções sem dado somem, então a numeração do índice muda de um
relatório para outro. O CSV usa `;` e BOM: abre direto no Excel em português. Para PDF, use "imprimir" (os blocos
recolhidos abrem sozinhos na impressão).

## 4. Checklist antes de gerar

1. `python scripts/check_analysis.py --run <pasta>` sem erros. Leia os avisos e resolva os que forem reais.
2. Cada oportunidade tem `id` curto, os 10 eixos com `why`, os 4 do oceano com `measured`, evidência com link,
   títulos nativos (não traduções literais), produção para o perfil do usuário e riscos.
3. Os achados do resumo têm número e trazem uma conclusão que muda decisão, não uma descrição. O `verdict_text`
   responde em uma frase.
4. Toda revisão manual de nota automática está explicada no `why`.
5. Limitações dizem o que **não** foi medido (rede bloqueada, cota, mercados com pouca amostra, sem acesso à web).
6. M e R citam fonte datada da pesquisa web (`{"research": "rN"}`); fontes externas com data; preços e políticas com
   a data da consulta.

## 5. Gerar, publicar e entregar

```bash
python scripts/score.py --run <pasta>               # imprime o ranking e os vereditos (confira se fazem sentido)
python scripts/build_report.py --run <pasta> --embed
```

Saídas: `relatorio.html` (abre direto no navegador; imagens por caminho relativo) e `relatorio.artifact.html`
(corpo sem `<html>`/`<head>`, imagens embutidas: é o formato para publicar como Artifact). Só as fontes do Google
Fonts vêm da rede; sem internet o relatório abre com fontes do sistema.

- Se a ferramenta **Artifact** estiver disponível, publique `relatorio.artifact.html` (privado por padrão) e
  entregue o link. Senão, entregue o caminho do `relatorio.html`.
- Antes de entregar, abra o relatório (navegador ou print) e confira: nenhum erro no console, o ranking bate com o
  `score.py`, os links abrem.

**Mensagem final ao usuário** (curta; o relatório é o detalhe):
1. As 2–3 melhores oportunidades em uma linha cada (veredito, nota com faixa, confiança, por que, o que falta medir).
2. O link ou o caminho do relatório.
3. O que não foi medido e o menor próximo passo (o experimento do plano).
