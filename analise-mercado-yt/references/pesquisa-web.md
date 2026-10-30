# Pesquisa web em tempo real

Sumário: §1 por quê e regras · §2 o que pesquisar (6 temas) · §3 como registrar · §4 como citar · §5 qualidade
da fonte · §6 sem ferramenta de web

---

## 1. Por quê e regras

RPM, regras do YouTube, preço de ferramenta e notícia mudam em meses. O que o modelo sabe de memória vira fato
velho sem aviso. Por isso, registre cada afirmação externa que mexe em nota ou veredito com a URL e a data de acesso
de uma página **aberta hoje** (`scripts/research.py`).

1. Use a busca e a leitura de páginas do host (WebSearch, WebFetch ou equivalentes). Prefira fonte oficial e dado
   primário a blog que repete blog.
2. **Só registre URL que você abriu ou viu nos resultados.** Nunca complete URL de cabeça.
3. Número de dinheiro precisa de 2 fontes independentes ou vem marcado `confiança baixa`. Calculadora de RPM é
   estimativa; declaração de criador é amostra pequena; os dois ainda ajudam a ordenar mercados.
4. Cite com poucas palavras: `quote` tem no máximo 25 palavras e é opcional. O registro guarda o fato e a fonte,
   não o texto da página.
5. Fonte que contradiz outra: registre as duas e diga qual pesa mais e por quê.
6. Orçamento de tempo: 6 a 12 buscas por análise, mais a leitura das 3 a 5 páginas que decidem. Faça só a busca que
   pode mudar uma nota.

## 2. O que pesquisar

Mínimo para fechar uma análise: **monetizacao** e **politica**. O `research.py check` reprova sem eles.

### 2.1 monetizacao (eixo M)

- RPM e CPM do nicho **no país-alvo** (não só nos EUA). Consultas: `RPM <nicho> <país> <ano>`, `CPM <categoria>
  <país>`, `quanto ganha canal de <nicho>` (idioma do país). Guarde faixa e unidade (RPM por mil views
  monetizadas × CPM por mil impressões de anúncio) e se o dado é do criador, de calculadora ou de pesquisa.
- Requisitos de monetização do YouTube hoje: página oficial do Programa de Parcerias (Partner Program). Anote
  inscritos, horas ou views de Shorts exigidos e a data da página.
- Fontes além do AdSense que o nicho tem: afiliados, patrocínio, produto próprio, assinatura. Um exemplo real com
  link vale mais que uma lista genérica.

### 2.2 politica (eixo R)

- Páginas oficiais do YouTube sobre **conteúdo inautêntico ou repetitivo**, **conteúdo alterado ou sintético**
  (rótulo de divulgação), spam e práticas enganosas, direitos autorais e uso justo. Anote a data de "última
  atualização" da página.
- Notícias dos últimos 90 dias sobre fiscalização, desmonetização em massa ou mudança de regra para canais
  automatizados. Procure o nome do nicho junto (`<nicho> canal desmonetizado`, `faceless channels demonetized`).
- Temas sensíveis do nicho: saúde e finanças com recomendação (YMYL), política, apostas, menores. Para cada um,
  a regra do YouTube e a lei local que se aplicam.

### 2.3 tendencia

- Notícias recentes: `python scripts/signals.py news "<tema>" --lang pt --region BR --out <pasta>/data/signals/news_<slug>.json`
  traz manchetes e o ritmo da última semana contra o mês, sem chave. Complete com 1 ou 2 buscas na web.
- Eventos agendados nos próximos 6 meses (eleição, copa, feriado de consumo, lançamento) que inflam ou murcham a
  demanda. Fonte oficial do calendário, não lista de blog.
- O que está subindo agora: `signals.py trending` e a Wikipédia (tendência relativa). Diga se a demanda é de base
  ou de pico.

### 2.4 concorrencia

- Como os canais dedicados ganham dinheiro (patrocínio, curso, afiliado, produto) e há quanto tempo estão no ar.
- Relatos de canais faceless no nicho: o que funcionou, o que foi desmonetizado, o que saturou. Fóruns e
  comunidades valem como **sinal qualitativo** (tipo `comunidade`); não sustentam número.

### 2.5 producao (eixos A, K, S)

- Preço **oficial** das ferramentas do perfil do usuário (LLM, voz, imagem, vídeo, edição): página de preços,
  não resenha. Anote o plano, o limite e a data. Licença comercial da voz e das imagens.
- Limites de uso das assinaturas que o usuário já paga (cota, uso comercial).

### 2.6 mercado (eixo F)

- Hábito de consumo e regulação do país para o tema (apostas, saúde, finanças, difamação, anúncios
  políticos). Fonte oficial ou instituto de pesquisa do país.
- Tamanho do público de YouTube do país (para conferir `MARKET_SIZE` quando o idioma tiver região específica).

## 3. Como registrar

```bash
python "$S/scripts/research.py" add --run <pasta> --topic monetizacao \
  --claim "RPM de finanças pessoais no Brasil" --value "US$ 2–6" --unit RPM \
  --url https://exemplo.org/pagina --accessed 2026-10-29 --type dados --confidence media \
  --note "faixa de calculadora; confirmar com criadores do nicho"
python "$S/scripts/research.py" list  --run <pasta>
python "$S/scripts/research.py" check --run <pasta>
```

- `--type`: `oficial` (YouTube, Google, empresa) · `dados` (pesquisa, painel, estatística) · `noticia` · `blog` ·
  `comunidade`.
- `--confidence`: `alta` (fonte primária, atual, consistente) · `media` · `baixa` (blog, snippet sem abrir a página,
  dado velho ou contraditório).
- Página que só apareceu no resultado de busca e não foi aberta: `--confidence baixa` e `--note "via busca"`.
- O arquivo é `data/research.json`. O relatório mostra tudo na seção "Pesquisa em tempo real", com data de acesso.

## 4. Como citar

No `analysis.json`, coloque `{"research": "r3"}` em `evidence` da oportunidade, do mercado ou da produção; o
`build_report.py` troca pelo texto do fato, o link, a data de acesso e o tipo da fonte. No `why` do eixo, escreva
o **número e a leitura**: "RPM BR de US$ 2–6 (r3, r7): classe média-baixa; vira M 2 porque não há afiliado forte no
nicho". O verificador avisa quando uma oportunidade não cita nenhuma fonte externa datada.

## 5. Qualidade da fonte

| Tipo | Serve para | Cuidado |
|---|---|---|
| oficial | regra, preço, requisito | confira a data da página; regra muda |
| dados | tamanho de público, hábito, RPM agregado | veja o método e o ano |
| noticia | evento, fiscalização, calendário | prefira veículo com data e autor |
| blog | pista de onde procurar | nunca sozinho para número de dinheiro |
| comunidade | relato qualitativo | é amostra de quem posta; não generalize |

## 6. Sem ferramenta de web

Se o host não tem busca nem leitura de páginas, **não registre nada de memória**. Escreva em
`analysis.limitations`: "Sem acesso à web nesta execução: receita (M), risco (R) e preços saíram de conhecimento
prévio e precisam de confirmação." O `check_analysis.py` aceita essa frase e rebaixa a falta de pesquisa a aviso. M e
R ficam julgados e a confiança do veredito cai.
