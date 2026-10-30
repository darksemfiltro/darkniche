# Changelog

## 1.0.0 (2026-10-30)

Primeira versão pública. Analisa nicho, ideia, canal ou vídeo.

- Veredito GO, TESTAR ou EVITAR por oportunidade, com confiança e faixa da nota.
- Métricas: ritmo em views por dia, canais efetivos, porta aberta para canais pequenos, topo saturado,
  intervalo de confiança da mediana, estimativa de oferta e carimbo de coleta.
- Pesquisa web em tempo real registrada com fonte e data (`research.py`) e citada no relatório.
- Sinais: "em alta" do Google Trends e do YouTube, notícias, autocomplete e Wikipédia com tendência relativa.
- Aprovação direta do escopo (`selection.py approve`) e triagem com teto configurável (até 60 buscas).
- Perfil de produção configurável, sem ferramentas nem hardware pressupostos.
- Chave de API só em cabeçalho, com máscara em mensagens de erro.
- Instaladores para Windows e bash: `-Agent` e `--agent` atendem Claude Code, Codex, OpenCode e Antigravity (ou `all`).
  A versão anterior vai para `backups/`, fora das pastas de skills, e `-ReplaceKey` troca a chave gravada.
- Documentação para publicar: guia de instalação, tour do relatório com imagens, exemplo em HTML e PDF, testes no GitHub Actions.
- Relatório: veredito no topo, sinais por célula, glossário, CSV, impressão e navegação por teclado.
- Cota esgotada nunca grava perfil vazio, idioma desconhecido não vira lacuna e o pivô de um canal ignora vídeo novo.
- `scripts/selftest.py`: autoteste offline.
- `extras/colab`: caminho experimental com IA gratuita.
