# Discord Ports Catalog

Bot de catálogo de ports para PC no Discord, com pesquisa, lista, ficha individual, imagem, link de download, painel administrativo e importação automática de um canal privado.

## Requisitos
- Python 3.10+
- Aplicação/bot criado no Discord Developer Portal
- Permissões: View Channels, Send Messages, Embed Links, Read Message History, Use Application Commands e Add Reactions (opcional)

## Instalação — Windows
1. Extraia o ZIP.
2. Copie `.env.example` para `.env`.
3. Preencha `DISCORD_TOKEN` e `SOURCE_CHANNEL_ID`.
4. No terminal, dentro da pasta do projeto:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Instalação — Linux/macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edite .env e configure as variáveis
python main.py
```

## Configuração do Discord
1. Abra https://discord.com/developers/applications e crie uma aplicação.
2. Na seção Bot, crie o bot e copie o token. Não compartilhe o token.
3. Ative **Message Content Intent** em Bot > Privileged Gateway Intents.
4. Em OAuth2 > URL Generator, selecione `bot` e `applications.commands` e convide-o ao servidor.
5. Dê ao bot acesso ao canal privado de origem e ao canal onde o catálogo será publicado.
6. Opcionalmente configure `GUILD_ID` para sincronizar os comandos rapidamente em um servidor de teste.

## Uso
- `/painel`: abre a administração.
- `/catalogo`: abre a interface de pesquisa/lista.
- `/jogo ID`: abre a ficha de um jogo.

No painel administrativo, use **Adicionar jogo** para cadastro manual ou **Publicar painel neste canal** para criar o painel público.

## Importação automática do canal privado
Defina `SOURCE_CHANNEL_ID` com o ID do canal que será usado como fonte. O bot só importa posts enviados por administradores, membros com `Manage Server` ou membros com o cargo indicado em `ADMIN_ROLE_ID`.

Formato recomendado:
```text
Nome do jogo: Exemplo Port
Descrição: Breve descrição.
Download: https://seu-link-autorizado.example/arquivo
Imagem: https://seu-site.example/capa.jpg
```

O bot também tenta reconhecer embeds e anexos de imagem. Posts novos são importados; editar o post atualiza o registro existente. Apagar o post de origem não apaga o registro do catálogo. Para imagens, prefira uma URL direta que o Discord consiga incorporar.

## Limitações
- A extração de mensagens livres é heurística; use os rótulos indicados para maior precisão.
- A listagem carrega até 100 resultados por busca nesta versão.
- O projeto foi verificado quanto à sintaxe, mas precisa ser testado conectado ao seu servidor.
- Use apenas links de downloads que você tenha autorização para compartilhar. O bot não hospeda arquivos: apenas apresenta o link cadastrado.
- Mantenha `catalog.db` e não publique o arquivo `.env`.


**IDs de cargos:** `ADMIN_ROLE_ID` aceita vários IDs separados por vírgula, por exemplo `ADMIN_ROLE_ID=111111111111111111,222222222222222222`.


## Correção de inicialização

Esta versão inclui os eventos `on_ready` e `on_message`, o comando `/painel` e a chamada `bot.run()` que mantém o processo do bot conectado ao Discord. Sem a chamada `bot.run()`, o Python terminava logo após definir as classes e funções.

Na hospedagem, configure `DISCORD_TOKEN`, `SOURCE_CHANNEL_ID`, `ADMIN_ROLE_ID` (IDs de cargos separados por vírgula) e, opcionalmente, `GUILD_ID`. No portal do Discord Developer, habilite **Message Content Intent** para o bot. O bot precisa ter permissão para ler mensagens e adicionar reações no canal de origem.


## Erro `403 Forbidden: Missing Permissions`

Esse erro ocorre quando o Discord não permite que o bot publique no canal selecionado. Nas configurações do servidor, abra **Editar canal → Permissões**, selecione o bot (ou seu cargo) e habilite **Ver canal**, **Enviar mensagens** e **Inserir links**. Para usar comandos, habilite também **Usar comandos de aplicativos**. Verifique se nenhuma permissão negada sobrescreve essas permissões. Depois execute `/painel` e publique em um canal onde o bot tenha acesso.


## Erro `50001: Missing Access`

Confirme que o bot está no mesmo servidor do canal e que o canal não está inacessível por permissões. Teste em um canal de texto comum. A versão atual do `main.py` mostra uma resposta explicativa no Discord em vez de deixar o callback do botão falhar sem mensagem.


## Separação entre canal de origem e canal do painel

- `SOURCE_CHANNEL_ID`: ID do canal privado onde os administradores publicam nome do jogo, imagem e link de download. O bot importa as mensagens desse canal.
- `PANEL_CHANNEL_ID`: ID do canal público onde o comando `/painel` publica o painel interativo para os usuários.
- Os dois IDs devem ser diferentes. O bot precisa conseguir ler o canal de origem e enviar mensagens/embeds no canal público.
