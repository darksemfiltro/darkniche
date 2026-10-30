# Como contribuir

Issues e pull requests são bem-vindos, em português ou em inglês.

## Antes de abrir um pull request

Rode os testes. Eles são offline e não gastam cota da API:

```bash
python -m unittest discover -s tests
python analise-mercado-yt/scripts/selftest.py
```

O GitHub Actions roda os mesmos comandos em Windows, macOS e Linux, com Python 3.10 e 3.13.

## Regras do projeto

- Os scripts usam só a biblioteca padrão do Python, mais yt-dlp e Pillow. Não acrescente outra dependência sem abrir um issue antes.
- Nenhum caminho da sua máquina, nenhuma chave, nenhum arquivo `.env` e nenhuma análise real no repositório. Use `.env.example` e os arquivos `*.example.json` como modelo.
- A chave da API só viaja em cabeçalho e passa por `redact()` antes de entrar em qualquer mensagem.
- Código que muda uma métrica, uma trava ou o veredito precisa de teste novo em `tests/`, e a explicação precisa entrar em `analise-mercado-yt/references/metodologia.md`.
- Textos do relatório e da documentação em português claro, com frases curtas e sem adjetivo de propaganda.

## Mercados e idiomas

A tabela de tamanho de mercado fica em `MARKET_SIZE`, em `analise-mercado-yt/scripts/common.py`. O texto de apoio (região, RPM e regras por mercado) fica em `analise-mercado-yt/references/mercados.md`. Ao acrescentar um idioma, inclua a fonte e a data da pesquisa.

## Relatório de exemplo

O exemplo em `exemplos/` traz dados reais da YouTube Data API. A [política de desenvolvedores da API](https://developers.google.com/youtube/terms/developer-policies) pede atualizar ou apagar dados guardados em até 30 dias. Não envie análises reais de terceiros em pull requests.

## Reportar problemas

Abra um issue com o sistema, a versão do Python, o agente que você usa e a saída de `python analise-mercado-yt/scripts/doctor.py --no-api`. Apague a chave de qualquer texto antes de colar. Falhas de segurança seguem o [SECURITY.md](SECURITY.md).
