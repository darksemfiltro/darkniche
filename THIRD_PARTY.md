# Terceiros

Nada da tabela abaixo vem dentro do pacote. O instalador baixa o que for pip.

| Item | Uso | Licença ou termos |
|---|---|---|
| yt-dlp | busca e metadados sem chave, transcrições, thumbnails | Unlicense (domínio público). Instalado pelo pip |
| Pillow | grades de thumbnails e paleta | HPND (MIT-CMU). Instalado pelo pip |
| ffmpeg | prints de vídeo e grades (opcional) | LGPL/GPL, conforme a compilação. Instalação por conta do usuário; não vem no pacote |
| YouTube Data API v3 | busca, vídeos, canais, comentários | Termos de Serviço dos APIs do YouTube e da Google. A chave é do usuário |
| Autocomplete do YouTube (suggestqueries) | sinal de demanda | Endpoint não oficial do Google; uso leve e pessoal. Confira os termos do Google |
| Google Trends e Google Notícias (RSS) | sinais "em alta" e notícias | Feeds públicos do Google; uso leve e pessoal. Confira os termos do Google |
| Wikimedia REST API e Wikidata | pageviews e ligação entre idiomas | Dados sob CC0 (Wikidata) e licenças Wikimedia; a skill só lê contagens. A política de User-Agent da Wikimedia pede um contato: defina `AMY_CONTACT` (e-mail ou URL) no `.env`; sem isso a skill se identifica só pelo nome |
| Google Fonts: Big Shoulders Display, IBM Plex Sans e IBM Plex Mono | tipografia do relatório | SIL Open Font License 1.1. Carregadas da rede ao abrir o relatório; não vêm no pacote |

`references/mercados.md` e `references/producao.md` citam preços, licenças e regras de terceiros com a data da pesquisa
(12/10/2026). Servem para orientar a busca; confirme na fonte oficial antes de decidir.

`exemplos/relatorio-exemplo.html`, `exemplos/relatorio-exemplo.pdf`, as capturas em `docs/img/` e
`analise-mercado-yt/assets/*.example.json` trazem dados reais da YouTube Data API (títulos, canais e números públicos)
coletados em 29 e 30/10/2026, mais fatos de páginas da web com URL e data de acesso.
A [política de desenvolvedores da API do YouTube](https://developers.google.com/youtube/terms/developer-policies) pede
atualizar ou apagar dados guardados (título, nome do canal, contagens) em até 30 dias. Quem republicar o pacote depois
disso deve regerar o exemplo ou trocar por um sintético. As miniaturas das grades pertencem aos seus canais e aparecem
só como referência de análise.
