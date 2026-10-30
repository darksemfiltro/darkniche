# Segurança

Se você achar uma falha de segurança, como um caminho que expõe a chave da API, não abra um issue público. Use o relato privado do GitHub: aba **Security**, botão **Report a vulnerability**. Descreva o que aconteceu, como repetir e o que você acha que a falha permite.

Se a sua própria chave da YouTube Data API vazou, revogue-a no Google Cloud Console antes de qualquer outra coisa e grave a nova com `install.ps1 -ReplaceKey` (Windows) ou `bash install.sh --replace-key`. O [guia de instalação](docs/instalacao.md#trocar-ou-revogar-a-chave) tem o passo a passo.

O que a skill faz com a sua chave:

- A chave fica só na variável de ambiente `YT_API_KEY` ou em `~/.analise-mercado-yt/.env`.
- A chave viaja em cabeçalho, nunca na URL.
- As mensagens de erro e os logs mascaram a chave, e o registro de pesquisa recusa URLs que a contenham.
- O pacote do Colab, o relatório e o ZIP de evidências não levam a chave.
