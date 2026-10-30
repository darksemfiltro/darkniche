# Escopo, custo e aprovação antes da coleta

A coleta gasta a cota do usuário. Por isso nada é coletado sem um registro de aprovação ou escolha, e o `scan.py`
recusa rodar sem ele (código 4). O registro é um checkpoint operacional, não autenticação: ele só impede o scan
acidental e invalida mudanças de coleta (consulta, filtro, idioma, região, modo) feitas depois do ok.

Há dois caminhos. Escolha pelo pedido.

## Caminho A · O usuário nomeou o escopo (aprovação direta)

"Analise finanças pessoais em PT e EN", "veja se acidentes aéreos explicados funciona em francês". O usuário já
escolheu nicho e idiomas; não há candidatos para ele escolher, só custo para aprovar.

1. `init_run.py "Título" --langs pt,en` e preencha `plan.json` (consultas curtas e nativas, 2 ou 3 variantes por
   célula; `keywords` e `exclude` quando o termo for genérico).
2. `scan.py --run <pasta> --estimate` e mostre uma tabela curta: células × idiomas, consultas de exemplo, buscas e
   unidades gerais, o que vai por yt-dlp.
3. Peça **um** "ok" ou ajuste. Com o ok:
   ```bash
   python "$S/scripts/selection.py" approve --run <pasta> [--search-budget 60 --unit-budget 500]
   ```
   `approve` registra o plano exatamente como está e recusa se a estimativa passar do teto.
4. `scan.py --run <pasta>` e siga o fluxo.

## Caminho B · A skill propõe os recortes (triagem, escolha)

Para ideia vaga, referência a modelar ou descoberta. Não recomende recortes só pelo julgamento da IA.

1. Formule 3 a 6 hipóteses testáveis em `plan.json` (`niche`, `subniche`, `lens`, `queries` por idioma). Diferencie
   nicho, subnicho e ângulo. Liste países explicitamente: FR não é toda a francofonia.
2. **Piloto**: uma expressão por recorte e idioma, uma página, `duration: longform` (2 buscas por célula). Teto padrão
   de **24 buscas**; com mais recortes ou idiomas, o usuário escolhe um teto maior (`--search-budget`, no máximo 60)
   depois de ver a estimativa. Não faça vários pilotos para contornar o teto e não descarte idiomas em silêncio.
   ```bash
   python "$S/scripts/triage.py" --run <pasta> --duration longform --estimate
   python "$S/scripts/triage.py" --run <pasta> --duration longform [--search-budget 40]
   python "$S/scripts/scan.py" --run <pasta>/triage --triage
   python "$S/scripts/metrics.py" --run <pasta>/triage
   python "$S/scripts/profile_channels.py" --run <pasta>/triage --max 6 --top-per-cell 2 --n 50
   ```
   Com chave de API o piloto usa a API; sem chave, yt-dlp (sem data, inscritos nem idioma declarado).
3. Leia o topo, confirme pertinência e idioma, ache os canais dedicados, remova ruído com `keywords`/`exclude` e rode
   `metrics.py` de novo (grátis). Só então preencha `priority` (inteiro, menor primeiro) e `rationale` com as
   evidências do piloto, separando observado de inferido. Amostra pequena ou ruim vira **inconclusivo**, nunca
   "oceano azul". Use as flags: `cabeca_saturada` pede subnicho; `idioma_nao_verificado`, `sem_datas` e `sem_inscritos`
   marcam a evidência como parcial.
4. `selection.py propose --run <pasta>` mostra os candidatos com custo. Apresente a tabela (IDs, evidência e link,
   justificativa, incerteza, idiomas e regiões, custo incremental, o que o piloto já gastou) e pergunte, por
   exemplo: "Quais IDs quer aprofundar? Quais idiomas e países? Quer sondagens de títulos? Recomendo A e C em
   FR/França: 10 buscas e ~60 gerais de perfis e comentários."
5. **Só depois da resposta**:
   ```bash
   python "$S/scripts/selection.py" select --run <pasta> --cells A,C --langs fr --probes titulo1 --search-budget 30 --unit-budget 200
   ```
   `proposal.json` guarda todos os candidatos; `plan.json` passa a ter só os escolhidos; `selection.json` registra a
   escolha, o hash do escopo e a estimativa. Resultados idênticos do piloto são reaproveitados (cache), então o
   aprofundamento não paga de novo o que o piloto já coletou.

## Regras comuns

- Silêncio, perfil, opções pré-marcadas e "análise completa" não escolhem candidatos que o usuário ainda não viu.
  Uma resposta que já escolhe exatamente os candidatos e mercados permite registrar sem nova pergunta.
- Uma consulta × uma página = 1 busca; `longform` = 2; sondagem em modo `api` = 1 por idioma (no padrão, yt-dlp, 0 buscas). Perfil de canal de 60
  uploads = até 5 unidades gerais. Comentários: ~4 unidades por vídeo. O teto do `select`/`approve` cobre scan +
  sondagens, não perfis, comentários nem retries: some-os na estimativa que você mostra.
- Para mudar consultas, filtros, modos, mercados ou escopo depois do registro: edite `proposal.json` (ou o plano),
  mostre o incremento, aguarde a nova escolha e registre de novo. `keywords`, `exclude` e texto editorial são locais e
  não exigem nova escolha.
- Execução sem usuário: prepare a proposta e a estimativa e aguarde. Uma escolha já persistida e igual ao plano pode
  retomar o trabalho.
