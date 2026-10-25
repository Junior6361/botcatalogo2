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
