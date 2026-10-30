# Perguntas e gerador de variações

Sumário: §1 perfil (uma vez) · §2 perguntas por análise · §3 perguntas que o agente faz a si mesmo · §4 vetor de
formato · §5 gerador de bends (nichebending) e micronichos · §6 escolha de idiomas e mercados · §7 escolha das
sondagens de títulos

---

## 1. Perfil do usuário (uma vez, não a cada análise)

`scripts/doctor.py` cria `~/.analise-mercado-yt/perfil.json` sem inventar hardware, ferramentas nem orçamento.
Leia antes de perguntar; o perfil sugere candidatos, não substitui a escolha do usuário. Campos:

- `idiomas_principais` (padrão pt, en, es: os que a skill pesquisa sem perguntar; o usuário acrescenta outros quando
  pedir), `idioma_relatorio` (pt-BR), `foco` (faceless) e `presenca` (sem_rosto, voz_propria ou rosto);
- `prioridades` (padrão: oportunidade > automação e custo > receita > velocidade);
- `producao`: `estilos` (motion_codigo, imagem_ia, stock, 2d, clipes_ia, apresentador, tela), `ferramentas` (llm, tts,
  imagem, edicao), `hardware` (gpu, vram_gb), `horas_max_video`, `videos_mes`, `orcamento_video_usd`, `moeda`,
  `revisores_nativos`.

**Pergunte o perfil de produção só quando for dar as notas A, K e S**, não na primeira mensagem: "Quais ferramentas
você usa para voz, imagem e edição? Roda algo local (GPU)? Quantas horas por vídeo e quantos vídeos por mês? Tem um
orçamento por vídeo? Fala ou tem revisor nativo em quais idiomas?" (até 4 perguntas). Grave as respostas no perfil.
Registre respostas duráveis; não infira modelo, GPU ou orçamento que o usuário não informou.

## 2. Perguntas por análise

Use a ferramenta de perguntas disponível no host e respeite seu limite; se ausente, pergunte em texto.
**Não pergunte o que a mensagem já respondeu.** Antes do piloto, esclareça somente o necessário para formular
hipóteses; a escolha de recortes/mercados acontece depois da triagem com dados, conforme selecao.md.

**Rodada 1**

1. *O que você quer levar desta referência?* (múltipla escolha)
   - Formato e estética (edição, motion, ritmo) · Ângulo ou lente (quem fala e com que promessa) ·
     Tema ou nicho · Tudo: mapear o máximo de variações
   - Se a referência tem fases (pivô), pergunte qual fase modelar: quase sempre a atual.
2. *Quais mercados já são obrigatórios e qual o teto de buscas?*
   - Se não informado, os idiomas do perfil (pt-BR/BR, en/US, es/MX) e até 24 buscas no piloto: 3 hipóteses × 3
     idiomas × longform = 18. O usuário acrescenta idiomas e países ("e francês da Bélgica") quando quiser; cada um
     soma 2 buscas por hipótese. Não prometa análise completa num dia sem estimar o plano. Se o usuário já nomeou
     nicho e idiomas, mostre o custo e peça um "ok" (selecao.md, caminho A); se a skill propõe os recortes, o piloto
     vem antes e o usuário escolhe depois (caminho B). Completo significa cobrir a decisão escolhida com evidências;
     não pesquisar obrigatoriamente 12 idiomas ou 25 nichos.
3. *Algum tema fica de fora?* (múltipla escolha)
   - Nenhum · Política e eleição · Saúde e finanças com recomendação (YMYL) · Apostas · Crime violento ·
     Religião
4. *Onde vai publicar?*
   - Long-form (Recomendado para TV e RPM) · Shorts · Os dois (análises separadas: as métricas não se comparam)

**Rodada 2 (só se necessário)**

- Mercados além do padrão (NL, KO, AR, HI, VI, SV, CS, HU, EL; ou um país específico de um idioma: ES da
  Espanha, FR do Canadá).
- Monetização-alvo além do AdSense (afiliado, produto próprio, patrocínio).
- Restrições de produção desta vez (prazo do primeiro vídeo, horas por semana, revisor nativo disponível).
- Nicho já descartado ou já testado antes (para não repetir).

**Modo ideia** (sem referência): troque a pergunta 1 por *"Descreva em uma frase o canal que você imagina, ou
escolha um ponto de partida"* com opções: tema que você domina · formato que você quer usar · público que você
quer atingir · me surpreenda a partir do perfil.

## 3. Perguntas que o agente faz a si mesmo

Responda por escrito em `notas.md`, na pasta da análise, antes de montar o plano. São elas que impedem a análise
superficial. Use o mesmo arquivo para registrar decisões ao longo do caminho (consultas trocadas, filtros, notas
automáticas corrigidas e por quê).

**Sobre a referência**
- O que gera as views: o tema, a embalagem (título/thumb), o formato, a pessoa ou o timing?
- Houve pivô? O que mudou nele (formato, tema, duração, embalagem)? A fase atual é a que importa.
- Os hits são evergreen ou pegaram evento/calendário? Qual vídeo é o sinal limpo?
- Qual é o contrato com o espectador (a promessa que faz alguém confiar)? É isso que precisa sobreviver às trocas.
- O que é replicável por automação e o que depende de uma pessoa (voz, rosto, autoridade, comunidade)?

**Sobre demanda**
- Quem procura isso, em que momento da vida, em qual tela (TV, celular)? Como essa pessoa digitaria a busca?
- O tema tem âncoras locais (instituições, moeda, empresas, casos, leis) em cada país?
- A demanda é de base ou de pico?

**Sobre oferta**
- Quem atende hoje, com que formato e a que custo? Há demanda atendida só por formato caro (TV, documentário
  filmado, apresentador) que um formato barato atenderia bem?
- A falta de vídeos é lacuna ou é sinal de que ninguém quer isso? (Compare com a demanda em outros idiomas.)

**Sobre fit**
- O formato é nativo ou estranho no país? O registro de língua soa local? O TTS soa nativo?
- O tema esbarra em regulação local (apostas, saúde, difamação, insulto)?

**Sobre produção e o próprio viés**
- O que quebra a automação neste formato? O que exige um humano a cada vídeo?
- Estou apaixonado pela referência? Estou confundindo tradução com oportunidade?
- Que dado mudaria minha recomendação? Ele está no plano?

## 4. Vetor de formato

Decomponha a referência (ou a ideia) em variáveis independentes. Cada variável vira um eixo de troca.

| Variável | Pergunta | Exemplo (canal de dívidas pessoais) |
|---|---|---|
| Lente | Quem fala e de onde vem a autoridade? | consultor de endividamento que mostra as contas |
| Domínio | Sobre qual sistema/assunto? | cartão, financiamento e renegociação no Brasil |
| Promessa | Que contrato faz confiar e compartilhar? | sair do vermelho com passos que cabem no salário, sem milagre |
| Estrutura | Como o roteiro anda? | pergunta-âncora → fundamentos → passo a passo → casos → erros comuns → payoff |
| Embalagem | Título e thumbnail | número + dor concreta; 1 valor em reais + 1 objeto |
| Estética | O que se vê | fundo fixo claro, planilha animada, ícones, zoom como pontuação |
| Duração e cadência | Quanto e com que frequência | 12–15 min, 2 por semana |
| Idioma e mercado | Para quem | PT-BR |
| Monetização | Como paga | AdSense + afiliado de renegociação |

## 5. Gerador de bends (nichebending) e micronichos

**Regra:** troque **uma** variável por vez (o resultado fica atribuível); duas só quando a combinação é natural
(lente + domínio). Mantenha a promessa que faz a referência funcionar. Formule 3–4 hipóteses específicas para
testar no piloto. Uma exploração de 15–25 candidatos só faz sentido se solicitada e cabe em etapas/orçamento
próprios. Teste existência de consultas naturais, âncoras locais e fit com a produção; recomende e ranqueie
recortes somente depois de ler o mercado coletado. Não confunda essas hipóteses internas com oportunidades.

**Catálogos de troca** (pontos de partida, não lista fechada)

- **Lentes:** auditor forense · hacker/pentester · estatístico · economista · engenheiro (voo, civil, materiais,
  alimentos) · investigador de acidentes · médico legista · advogado · perito · historiador · psicólogo
  comportamental · cientista de dados · analista OSINT · ex-insider (ex-funcionário do setor) · urbanista · físico.
- **Domínios:** fraudes e golpes · preços e custo de vida · aviação e acidentes · indústria de alimentos · varejo e
  marcas · imobiliário · energia · esportes como negócio · games como negócio · big tech · segurança digital ·
  burocracia e Estado · transporte e logística · história econômica · ciência do cotidiano · trabalho e salários ·
  luxo · agro · crime real (risco) · saúde pública (YMYL) · apostas (regulado) · clima (polarizado).
- **Promessas:** como funciona por dentro · quanto custa de verdade · por que X é assim · o que deu errado · a
  verdade técnica sem lado · testamos/simulamos · o mito desmontado.
- **Estruturas:** explainer de sistema · dossiê cronológico de um caso · comparação A vs B · simulação "e se" ·
  linha do tempo · mapa/geografia · investigação OSINT · ranking com critério · "do zero" (construir o
  entendimento).
- **Estéticas:** motion de ícones sobre fundo fixo · dossiê documental (papéis, marca-texto, carimbo) · mapa 2D/3D
  · infográfico de dados · stick figure · colagem P&B · 3D low-poly · imagens de IA + Ken Burns · stock +
  narração · yukkuri/avatar.

**Bend inverso (muito produtivo):** mantenha o tema e procure onde a demanda é atendida só por formato caro (TV,
documentário filmado, apresentador); aplique o formato barato e automatizável. Foi assim que o melhor resultado de
um teste apareceu: um tema atendido quase só por reportagem de TV em um idioma, sem nenhum explainer animado.

**Descoberta** (o usuário não tem nicho): parta de 5 a 10 sementes do interesse, rode `signals.py suggest --expand` por
idioma e `signals.py trending`, agrupe as sugestões em subnichos e leve de 3 a 6 candidatos à triagem. Candidato bom
tem busca real (muitas sugestões), canal dedicado pequeno no topo e formato possível no perfil do usuário.

**Escada de micronicho:** nicho → subnicho → micronicho = tema + público + ângulo.
Ex.: finanças → fraudes corporativas → "fraudes contábeis explicadas por um auditor, para quem investe em ações".
Desça um degrau quando o nicho estiver saturado (L ≤ 2); suba quando a demanda for pequena demais (D ≤ 2).

**Saída desta etapa** (vai para `plan.json` e `analysis.bends`): para cada bend, eixo trocado, de → para, as
células que ele gera e por que pode funcionar.

## 6. Escolha de idiomas e mercados

- **Padrão:** os idiomas do perfil (pt, en, es). **Sob pedido** (nenhum entra sem o usuário pedir ou escolher na
  triagem): FR, DE, IT, JA, KO, ID, TR, PL, RU/UK, AR, HI, VI, TH, NL e os pequenos (RO, BG, CS, HU, EL, SV…).
  Cada idioma extra soma 2 buscas por hipótese no piloto. Idioma fora da tabela de tamanho de mercado entra com tamanho
  assumido e D limitado a 3 até haver número melhor.
- **Clusters de mesmo idioma** (uma consulta, vários países; troque a região para medir cada um): ES = MX, ES, AR,
  CO, EUA hispânico · FR = FR, BE, CH, CA-QC, África francófona · DE = DE, AT, CH · PT = BR, PT, AO, MZ · EN = US,
  UK, AU, CA, IN, NG.
- **Mercados pequenos** (NL, PL, RO, BG, CS, HU, EL, SV) têm pouca oferta nativa e RPM variado: bons para
  lacuna, ruins para escala. Use consultas curtas e 24 meses.
- **Cuidado:** RU (anúncios suspensos para usuários na Rússia desde 2022; confirme a situação atual), ZH (YouTube
  bloqueado na China continental; o público é TW, HK, MY e diáspora), idiomas em que o TTS do usuário é fraco
  (confira `producao.md` §1.1).
- Diga ao usuário quais idiomas ficaram de fora e por quê.

## 7. Escolha das sondagens de títulos

Escolha 2–6 títulos para transpor: o maior outlier evergreen da referência, o título mais forte achado na
varredura (de qualquer idioma) e 1–2 ângulos que você acha que viajam bem. Reescreva cada um como um nativo
escreveria (mesma promessa, palavras locais). Prefira títulos com promessa clara a títulos que dependem de um
nome próprio local.
