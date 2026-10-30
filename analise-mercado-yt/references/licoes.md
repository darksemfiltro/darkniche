# Lições que viraram regra

Leia antes de montar o plano e de novo antes de dar as notas. Depois de cada seta (→) vem o ponto em que o código
já aplica a regra.

## Busca e amostra

1. **Busca crua engana.** Termo genérico traz outro assunto (pesca no lugar de preço, política no lugar de
   estatística, jogo no lugar de tema). → `keywords` e `exclude` por célula, leitura obrigatória do topo, `offtopic`
   contado.
2. **Shorts tomam a busca.** Em um teste, 47 de 50 resultados em francês eram Shorts e a célula parecia vazia. →
   `duration: longform` (duas buscas: médio e longo), alerta de `short_share`, `filters_lang` para corrigir um
   idioma sem criar célula.
3. **Mercado pequeno + frase longa = zero resultados.** Búlgaro, romeno e turco devolveram 0 a 7 vídeos com frases
   de 6 palavras. → consultas curtas, 2 ou 3 variantes, janela de 24 meses, autocomplete para ver como o país digita.
4. **O topo por views mede o teto do nicho.** A mediana dos 50 mais vistos de um nicho grande passa de 100 mil
   mesmo nos subtemas, e a nota de demanda não separa as células. → ritmo em views por dia dos vídeos maduros, flag
   `cabeca_saturada` (desça um subnicho), canais efetivos e porta aberta para separar o que a mediana não separa.
5. **Vídeo novo ainda está acumulando views.** O topo por views subrepresenta lançamentos recentes, e compará-los
   com vídeos velhos faz todo canal parecer em queda. → `MATURE_DAYS`; o pivô de um canal ignora vídeos com menos de
   14 dias e vem marcado "forte" ou "fraco".
6. **Tendência não sai dessa amostra.** → Wikipédia (relativa à queda da própria Wikipédia), autocomplete, "em
   alta" e notícias.
7. **Views cruas não se comparam entre idiomas.** 50 mil em búlgaro é sucesso enorme; em inglês é pouco. →
   equivalente EN (÷ tamanho do mercado). Idioma fora da tabela vira "tamanho assumido" e D fica no máximo 3.
8. **Idioma desconhecido não é nativo, e também não é lacuna.** Vídeo sem idioma identificável fica fora da oferta
   nativa, e uma célula cheia deles parecia vazia. → a flag `idioma_nao_verificado` limita a nota L a 3. Em idioma que
   o título não confirma (fa, ur, bn, ta…), o sem-idioma entra como nativo provisório (`idioma_nao_verificavel`),
   senão toda célula desses idiomas ficaria vazia.

## Leitura

9. **Marca grande não é porta aberta.** O canal novo de uma emissora nasce com distribuição e catálogo. → desconte
   em V; cite como concorrente, não como prova de que um solo cresce ali.
10. **Hit de evento não é demanda de base.** Eleição, copa, lançamento e feriado inflam o topo. → rode a variante sem o
    evento, olhe as datas, prefira o vídeo evergreen como sinal limpo e use os comentários para medir militância.
11. **Dublagem herda o idioma do original** e hindi em alfabeto latino vem marcado como inglês. → `video_lang` usa o
    título quando a evidência é forte.
12. **Canal gigante de outro tema entra no top.** Perfilar os maiores canais de cada célula gasta cota com canais
    que não concorrem. → rodízio por célula, `topic_share` (canal dedicado ao nicho), `--extra` para os dedicados.
13. **O comparador de títulos é lexical.** Uma palavra em comum ("manipular", "preço") não prova que o ângulo
    existe. → pede 2 palavras de conteúdo em comum e um terço da consulta, e todo "existe" e "lacuna" passa por `probe_review`.
14. **Japonês não tem espaços.** → bigramas de caracteres em CJK.
15. **Falha silenciosa esconde o problema.** Grade de thumbnails sem imagem não pode sair "ok", e cota esgotada não
    pode gravar perfil vazio como pronto. → códigos de saída, relatório sem imagem quebrada, `QuotaExceeded` nunca é
    engolido.

## Fatos externos e relatório

16. **RPM, regra e preço envelhecem em meses.** Tabelas de memória viram fato velho. → `research.py` e
    `pesquisa-web.md`: fonte aberta hoje, URL e data de acesso em cada fato.
17. **Link de busca não serve como evidência.** Quem lê quer abrir o vídeo citado. → evidência por ID e
    `check_analysis.py`.
18. **Eixo julgado precisa dizer que é julgado.** → `measured`, incerteza, faixa da nota e confiança no veredito.
19. **Chave de API em URL vaza em log e traceback.** → chave só em cabeçalho, `redact()` em toda mensagem de erro.
20. **Cota de busca acaba antes da geral.** → buckets separados, scan retomável, teto por análise aprovado pelo
    usuário, yt-dlp para amplitude.

## Calibração de profundidade

- Um piloto de 3 a 4 hipóteses × 3 idiomas (até 24 buscas) separa nicho vivo de nicho morto e mostra se o topo está
  saturado. Aprofunde só o que o piloto não decidiu.
- Procure a oportunidade fora do idioma e do tema de partida: ela aparece onde só um formato caro atende a demanda
  (TV, documentário filmado, apresentador) e um formato barato e automatizável cabe. Teste esse "bend inverso".
- Uma oportunidade com nota alta e quase tudo julgado recebe "TESTAR", não "GO" (`score.py` aplica a trava).
