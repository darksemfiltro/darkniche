# DarkNiche no Google Colab: o caminho grátis

Para quem não tem um agente de código. O notebook faz a análise com uma IA gratuita (a IA do Colab ou a Gemini API na
faixa gratuita) e entrega o relatório HTML. CPU basta. Não usa servidor, túnel, keep-alive nem agente instalado. A
geração do plano, a leitura do mercado e a escrita da análise acontecem dentro do notebook: não há upload intermediário
de `plan.json` nem de `analysis.json`.

**Estado: experimental.** O fluxo e os notebooks passam em testes automáticos com uma IA simulada (`tests/`), mas
**não foram executados no Colab real** com a IA do Colab ou o Gemini. Teste com um nicho pequeno antes de confiar.

## Os dois caminhos

| | 1. Agente de código (SKILL.md) | 2. Colab grátis (este guia) |
|---|---|---|
| Quem escreve o julgamento | o agente (Claude Code, Codex, OpenCode, Antigravity) | a IA gratuita que você configurar |
| Pesquisa web em tempo real | sim (RPM, política, notícias, preços, com fonte e data) | **não**: receita, risco e preços saem do conhecimento do modelo e o relatório avisa nas limitações |
| Escolha do escopo | conversa com o agente | seletores no notebook |
| Custo | a assinatura do agente | grátis (Colab + faixa gratuita do Gemini, sujeita aos limites da sua conta) |
| Melhor para | decisão: veredito com receita e risco pesquisados | primeira passada e triagem de nichos; dá para aprofundar depois no caminho 1 |

Os dois usam os mesmos scripts, a mesma chave da YouTube Data API e o mesmo relatório.

## Modos de IA

- `colab`: `google.colab.ai`, quando o modelo estiver disponível na sua sessão. Acesso e limites são da conta e do
  ambiente; não presuma que funcione depois que o assistente do Colab esgotar.
- `gemini`: Gemini Developer API com `GEMINI_API_KEY` sua, em Secrets. Não depende do chat do Colab. A API tem limites e
  faturamento próprios; use um projeto na faixa gratuita para evitar cobrança. O programa não ativa faturamento nem
  troca de modelo ou de provedor sozinho. Modelo padrão: `gemini-3.5-flash-lite`; `AI_MODEL` troca.
- `dados`: sem modelo, sem chamadas de IA e sem novas buscas. Exige hipóteses e piloto já coletados; mostra estatísticas
  descritivas e gera um relatório técnico. Não inventa recortes, fit cultural, produção, ranking nem notas. Para uma
  análise estratégica completa é preciso um modelo ou um agente.

## Primeiro uso

1. Pegue o pacote de código: baixe `DarkNiche-Colab.zip` na página de Releases do repositório, ou gere no seu computador
   com `python analise-mercado-yt/extras/colab/package_colab.py` (cria `dist/DarkNiche-Colab.zip`). Para regenerar os
   notebooks depois de editar o código: `python analise-mercado-yt/extras/colab/build_notebook.py`.
2. No Colab: Arquivo → Fazer upload de notebook → `DarkNiche.ipynb`. Escolha o runtime CPU.
3. Execute a célula de upload e envie `DarkNiche-Colab.zip`. Depois, a célula de dependências.
4. Escolha se monta o Drive. Ligado: análises, cache e contador ficam em `MyDrive/DarkNiche-state/`. Desligado: baixe o
   trabalho antes de encerrar, porque a VM é temporária.
5. Em Secrets (ícone de chave), crie `YOUTUBE_API_KEY` e habilite o acesso ao notebook. Também vale uma variável de
   ambiente; sem nenhuma das duas há um prompt oculto. A chave fica só no ambiente da VM: não vai para o notebook, o
   Drive, o pacote nem o relatório.
6. Preencha título, idiomas (padrão `pt,en,es`) e o pedido; `REFERENCE` só se houver canal ou vídeo para modelar;
   `EXISTING_RUN` para retomar uma pasta. O notebook recusa referência placeholder e não a troca sozinho.
7. Configure `AI_BACKEND`, `AI_MODEL` (opcional) e o teto do piloto. Use Executar tudo: o notebook gera hipóteses,
   coleta o piloto, calcula as métricas, perfila uma amostra de canais e faz a leitura pela IA.
8. Escolha recortes e mercados nos seletores (começam vazios), veja o custo e clique em **Aprofundar seleção**. O botão
   coleta, analisa, valida e gera o relatório, e baixa o HTML e um ZIP de evidências. JSON inválido pode ser corrigido
   uma vez pela IA; falha de rede ou de cota não dispara fallback pago nem troca de chave.
9. Com `dados`, o botão é **Gerar relatório dos dados** e não faz aprofundamento por rede. Sem dados existentes, dá erro
   claro em vez de inventar nichos.

## Retomar uma análise

`DarkNiche-Retomar.ipynb` usa `AI_BACKEND='dados'` e `COLLECT_REFERENCE=False`: recupera o piloto, mostra as estatísticas
e gera o relatório técnico, sem IA, sem chaves e sem novas buscas. Preencha `EXISTING_RUN` com a pasta da análise no
Drive (`/content/drive/MyDrive/DarkNiche-state/analises/<pasta>`), envie o ZIP de código e execute tudo.

## Retomada e limites

Com Drive, use o mesmo título e mês ou o caminho da pasta existente; a seleção válida persiste. Nunca abra duas sessões
no mesmo `AMY_HOME`: os locks locais não coordenam máquinas nem garantem atomicidade no Drive. O Windows e o Colab têm
contadores locais distintos, e a cota do Google é compartilhada por projeto: confira o Cloud Console e reduza os tetos
locais se usar mais de um executor.

O Colab gratuito tem recursos e duração variáveis. A persistência ajuda a retomar e não garante execução contínua.
Transcrições e downloads podem falhar por restrições de rede do YouTube no datacenter; a análise por metadados da API
continua possível, com a limitação declarada. O `gemini_video.py` usa a Gemini API e pode gerar cobrança; o notebook não o executa.

O ZIP de evidências inclui plano, seleção, notas e dados da análise, inclusive o piloto; nunca o cache global, o `.env`
nem o perfil. Revise antes de compartilhar: comentários públicos podem ter nomes de usuários. O pacote de código é uma
lista explícita de arquivos, sem análises locais nem credenciais.

## Privacidade da IA

O modelo recebe o seu pedido, o plano, títulos, canais, views e comentários agregados do piloto, e as rubricas. Perfil e
chaves não vão. Leia a política de dados do provedor antes de usar, sobretudo em projeto gratuito.

Documentação: [FAQ do Colab](https://research.google.com/colaboratory/faq.html),
[Secrets (userdata)](https://github.com/googlecolab/colabtools/blob/main/google/colab/userdata.py),
[IA do Colab](https://github.com/googlecolab/colabtools/blob/main/google/colab/ai.py),
[Gemini API: preços e faixa gratuita](https://ai.google.dev/gemini-api/docs/pricing).
