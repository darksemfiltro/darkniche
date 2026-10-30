# Extras (opcionais, fora do fluxo principal)

A skill funciona sem esta pasta. Apague `extras/` se não for usar.

## colab/: o caminho grátis, sem agente

Notebooks e scripts para rodar a análise no Google Colab, com uma IA gratuita (IA do Colab ou Gemini API) no lugar do
agente de código. Guia: [`colab/colab.md`](colab/colab.md).

- `DarkNiche.ipynb`: análise com IA. `DarkNiche-Retomar.ipynb`: consulta uma análise já coletada, sem IA e sem
  novas buscas.
- `package_colab.py` cria o ZIP de código que o notebook pede; `build_notebook.py` e `flow_cells.py` regeneram os
  notebooks depois de qualquer edição no código.
- `notebook_flow.py`, `text_ai.py`, `technical.py` e `colab_support.py` fazem o fluxo; importam os scripts de
  `../../scripts/` (não precisam de cópia).

**Estado: experimental.** Os testes automáticos (`tests/`) cobrem o fluxo com uma IA simulada, o empacotamento e a
leitura do notebook. A sessão real do Colab (Drive, Secrets, widgets, IA do Colab, Gemini) não foi executada. Neste
caminho não há pesquisa web: receita, risco e preços saem do conhecimento do modelo e o relatório avisa nas limitações.
`text_ai.py` envia ao provedor de IA o pedido, o plano e os dados públicos do piloto; leia a política de dados do
provedor antes de usar em projeto gratuito.
