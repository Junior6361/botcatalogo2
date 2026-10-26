import os
import re
import sqlite3
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "0") or 0)
ADMIN_ROLE_IDS = {
    int(role_id.strip())
    for role_id in os.getenv("ADMIN_ROLE_ID", "").split(",")
    if role_id.strip().isdigit()
}
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)
DB_PATH = os.getenv("DB_PATH", "catalog.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("ports_catalog")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE,
            description TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            download_url TEXT NOT NULL,
            genre TEXT NOT NULL DEFAULT '',
            source_message_id INTEGER UNIQUE,
            created_at TEXT NOT NULL
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""")


def http_url(url):
    try:
        p = urlparse(url.strip())
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def is_image_url(url):
    return urlparse(url).path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"))


def urls(text):
    return re.findall(r"https?://[^\s<>()]+", text or "")


def parse_message(message):
    text = message.content or ""
    title = ""
    image_candidates = []
    download_candidates = []
    description_lines = []
    for embed in message.embeds:
        if embed.title and not title:
            title = embed.title.strip()
        if embed.description:
            description_lines.append(embed.description.strip())
        if embed.image and embed.image.url:
            image_candidates.append(embed.image.url)
        if embed.thumbnail and embed.thumbnail.url:
            image_candidates.append(embed.thumbnail.url)
        for field in embed.fields:
            field_urls = urls(field.value)
            label = field.name.lower()
            if any(k in label for k in ("download", "baixar", "link", "port")):
                download_candidates.extend(field_urls)
            if any(k in label for k in ("imagem", "image", "capa", "cover")):
                image_candidates.extend(field_urls)

    for attachment in message.attachments:
        if (attachment.content_type or "").startswith("image/") or is_image_url(attachment.url):
            image_candidates.append(attachment.url)

    image_candidates += re.findall(r"(?im)(?:imagem|image|capa|cover)\s*[:\-]?\s*(https?://[^\s<>()]+)", text)
    download_candidates += re.findall(
        r"(?im)(?:download|baixar|link(?:\s+de\s+download)?|port)\s*[:\-]?\s*(https?://[^\s<>()]+)", text
    )

    all_urls = urls(text)
    download_candidates += [u for u in all_urls if not is_image_url(u)]
    if not title:
        for line in text.splitlines():
            line = re.sub(r"https?://\S+", "", line).strip()
            line = re.sub(r"[*_`#>|]", "", line).strip()
            line = re.sub(r"(?i)^(?:nome\s+do\s+jogo|nome|jogo|game|t[ií]tulo)\s*[:\-]\s*", "", line).strip()
            if line and not re.match(r"(?i)^(download|baixar|link|imagem|image|capa|cover|descri[cç][aã]o)\s*[:\-]?", line):
                title = line[:100]
                break
    if not title and message.attachments:
        title = os.path.splitext(message.attachments[0].filename)[0][:100]

    image = next((u for u in image_candidates if http_url(u)), "")
    download = next((u for u in download_candidates if http_url(u) and not is_image_url(u)), "")
    desc = "\n".join(x for x in description_lines if x)
    if not desc:
        for line in text.splitlines():
            if re.search(r"(?i)(download|baixar|link|imagem|image|capa|cover)\s*[:\-]?\s*https?://", line):
                continue
            if urls(line):
                continue
            cleaned = re.sub(r"[*_`#>|]", "", line).strip()
            if cleaned and cleaned.lower() != title.lower():
                description_lines.append(cleaned)
        desc = "\n".join(description_lines)
    desc = desc[:1000]
    if not title or not download:
        return None, "Não consegui identificar o nome e o link. Use 'Nome do jogo:' e 'Download:' no post."
    return {
        "name": title,
        "description": desc,
        "image_url": image,
        "download_url": download,
        "genre": ""
    }, None


def save_game(data, source_message_id=None):
    with connect() as conn:
        existing = None
        if source_message_id:
            existing = conn.execute("SELECT id FROM games WHERE source_message_id=?", (source_message_id,)).fetchone()
        if existing:
            conn.execute("""
                UPDATE games SET name=?, description=?, image_url=?, download_url=?, genre=?
                WHERE source_message_id=?
            """, (data["name"], data["description"], data["image_url"], data["download_url"], data["genre"], source_message_id))
            return existing["id"], "atualizado"
        cur = conn.execute("""
            INSERT INTO games(name, description, image_url, download_url, genre, source_message_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (data["name"], data["description"], data["image_url"], data["download_url"], data["genre"],
              source_message_id, datetime.now(timezone.utc).isoformat()))
        return cur.lastrowid, "adicionado"


def get_game(game_id):
    with connect() as conn:
        return conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()


def find_games(query="", limit=100):
    with connect() as conn:
        if query:
            return conn.execute("SELECT * FROM games WHERE name LIKE ? ORDER BY name COLLATE NOCASE LIMIT ?",
                                (f"%{query}%", limit)).fetchall()
        return conn.execute("SELECT * FROM games ORDER BY name COLLATE NOCASE LIMIT ?", (limit,)).fetchall()


def count_games(query=""):
    with connect() as conn:
        if query:
            return conn.execute("SELECT COUNT(*) AS n FROM games WHERE name LIKE ?", (f"%{query}%",)).fetchone()["n"]
        return conn.execute("SELECT COUNT(*) AS n FROM games").fetchone()["n"]


def admin_user(user):
    perms = getattr(user, "guild_permissions", None)
    if perms and (perms.administrator or perms.manage_guild):
        return True
    return any(
        role.id in ADMIN_ROLE_IDS
        for role in getattr(user, "roles", [])
    )

def make_embed(game):
    embed = discord.Embed(title=game["name"], description=game["description"] or "Sem descrição cadastrada.",
                          color=discord.Color.blurple())
    if game["image_url"]:
        embed.set_image(url=game["image_url"])
    if game["genre"]:
        embed.add_field(name="Gênero", value=game["genre"], inline=True)
    embed.set_footer(text=f"ID do catálogo: {game['id']}")
    return embed


class GameButtons(discord.ui.View):
    def __init__(self, game_id):
        super().__init__(timeout=300)
        self.game_id = game_id
        game = get_game(game_id)
        if game:
            self.add_item(discord.ui.Button(label="Baixar jogo", style=discord.ButtonStyle.link, url=game["download_url"]))
        self.add_item(ActionButton("Anterior", "prev", game_id))
        self.add_item(ActionButton("Próximo", "next", game_id, style=discord.ButtonStyle.primary))
        self.add_item(ActionButton("Pesquisar", "search", game_id))


class ActionButton(discord.ui.Button):
    def __init__(self, label, action, game_id, style=discord.ButtonStyle.secondary):
        super().__init__(label=label, style=style)
        self.action = action
        self.game_id = game_id

    async def callback(self, interaction):
        if self.action == "search":
            return await interaction.response.send_modal(SearchModal())
        with connect() as conn:
            op = ">" if self.action == "next" else "<"
            order = "ASC" if self.action == "next" else "DESC"
            game = conn.execute(f"SELECT * FROM games WHERE id {op} ? ORDER BY id {order} LIMIT 1", (self.game_id,)).fetchone()
            if not game:
                order = "ASC" if self.action == "next" else "DESC"
                game = conn.execute(f"SELECT * FROM games ORDER BY id {order} LIMIT 1").fetchone()
        if not game:
            return await interaction.response.send_message("O catálogo está vazio.", ephemeral=True)
        await interaction.response.edit_message(embed=make_embed(game), view=GameButtons(game["id"]))


class SearchModal(discord.ui.Modal, title="Pesquisar jogos"):
    query = discord.ui.TextInput(label="Nome do jogo", placeholder="Digite o nome ou parte dele",
                                 required=False, max_length=100)

    async def on_submit(self, interaction):
        query = str(self.query).strip()
        rows = find_games(query)
        if not rows:
            return await interaction.response.send_message("Nenhum jogo encontrado.", ephemeral=True)
        view = ResultsView(query, rows)
        await interaction.response.send_message(
            f"Resultados para **{query or 'todos os jogos'}** — {count_games(query)} jogo(s).",
            embed=view.embed(), view=view, ephemeral=True
        )


class ResultButton(discord.ui.Button):
    def __init__(self, game):
        super().__init__(label=game["name"][:80], style=discord.ButtonStyle.primary)
        self.game_id = game["id"]

    async def callback(self, interaction):
        game = get_game(self.game_id)
        if not game:
            return await interaction.response.send_message("Jogo não encontrado.", ephemeral=True)
        await interaction.response.send_message(embed=make_embed(game), view=GameButtons(game["id"]), ephemeral=True)


class PageButton(discord.ui.Button):
    def __init__(self, delta, disabled):
        super().__init__(label="◀ Anterior" if delta < 0 else "Próxima ▶",
                         style=discord.ButtonStyle.secondary, disabled=disabled)
        self.delta = delta

    async def callback(self, interaction):
        self.view.page += self.delta
        self.view.rebuild()
        await interaction.response.edit_message(embed=self.view.embed(), view=self.view)


class ResultsView(discord.ui.View):
    def __init__(self, query, rows):
        super().__init__(timeout=300)
        self.query = query
        self.rows = list(rows)
        self.page = 0
        self.page_size = 5
        self.rebuild()

    def rebuild(self):
        self.clear_items()
        start = self.page * self.page_size
        for game in self.rows[start:start + self.page_size]:
            self.add_item(ResultButton(game))
        self.add_item(PageButton(-1, self.page <= 0))
        self.add_item(PageButton(1, (self.page + 1) * self.page_size >= len(self.rows)))

    def embed(self):
        start = self.page * self.page_size
        lines = []
        for i, game in enumerate(self.rows[start:start + self.page_size], start=start + 1):
            genre = f" — {game['genre']}" if game["genre"] else ""
            lines.append(f"`{i}.` **{game['name']}**{genre}")
        pages = max(1, (len(self.rows) + self.page_size - 1) // self.page_size)
        e = discord.Embed(title="Catálogo de ports para PC", description="\n".join(lines),
                          color=discord.Color.blurple())
        e.set_footer(text=f"Página {self.page + 1}/{pages} • Selecione um botão para abrir a ficha")
        return e


class CatalogPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pesquisar jogo", style=discord.ButtonStyle.primary, custom_id="ports:search")
    async def search(self, interaction, button):
        await interaction.response.send_modal(SearchModal())

    @discord.ui.button(label="Ver lista", style=discord.ButtonStyle.secondary, custom_id="ports:list")
    async def listing(self, interaction, button):
        rows = find_games(limit=100)
        if not rows:
            return await interaction.response.send_message("O catálogo ainda está vazio.", ephemeral=True)
        view = ResultsView("", rows)
        await interaction.response.send_message(f"Catálogo — {count_games()} jogo(s).",
                                                embed=view.embed(), view=view, ephemeral=True)

    @discord.ui.button(label="Painel administrativo", style=discord.ButtonStyle.secondary, custom_id="ports:admin")
    async def admin(self, interaction, button):
        if not admin_user(interaction.user):
            return await interaction.response.send_message("Apenas administradores podem abrir este painel.", ephemeral=True)
        await interaction.response.send_message("Use `/painel` para administrar e publicar o catálogo.", ephemeral=True)


class AddGameModal(discord.ui.Modal, title="Cadastrar jogo manualmente"):
    name = discord.ui.TextInput(label="Nome do jogo", max_length=100)
    download = discord.ui.TextInput(label="Link de download autorizado", max_length=400)
    image = discord.ui.TextInput(label="URL direta da imagem (opcional)", required=False, max_length=400)
    description = discord.ui.TextInput(label="Descrição (opcional)", required=False,
                                       style=discord.TextStyle.paragraph, max_length=1000)

    async def on_submit(self, interaction):
        if not admin_user(interaction.user):
            return await interaction.response.send_message("Sem permissão.", ephemeral=True)
        if not http_url(str(self.download)) or (str(self.image).strip() and not http_url(str(self.image))):
            return await interaction.response.send_message("Informe URLs HTTP/HTTPS válidas.", ephemeral=True)
        game_id, _ = save_game({"name": str(self.name), "download_url": str(self.download),
                                "image_url": str(self.image), "description": str(self.description), "genre": ""})
        await interaction.response.send_message(f"Jogo cadastrado. ID `{game_id}`.", ephemeral=True)


class AdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Adicionar jogo", style=discord.ButtonStyle.success)
    async def add(self, interaction, button):
        if not admin_user(interaction.user):
            return await interaction.response.send_message("Sem permissão.", ephemeral=True)
        await interaction.response.send_modal(AddGameModal())

    @discord.ui.button(label="Publicar painel neste canal", style=discord.ButtonStyle.primary)
    async def publish(self, interaction, button):
        if not admin_user(interaction.user):
            return await interaction.response.send_message("Sem permissão.", ephemeral=True)
        message = await interaction.channel.send(
            embed=discord.Embed(
                title="Catálogo de ports para PC",
                description="Pesquise jogos pelo nome, veja a lista ou abra uma ficha individual com imagem e link de download.",
                color=discord.Color.blurple()
            ),
            view=CatalogPanel()
        )
        with connect() as conn:
            conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         (f"panel_message:{interaction.guild_id}", str(message.id)))
            conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         (f"panel_channel:{interaction.guild_id}", str(interaction.channel_id)))
        await interaction.response.send_message(f"Painel publicado: {message.jump_url}", ephemeral=True)


class PortsBot(commands.Bot):
    async def setup_hook(self):
        init_db()
        self.add_view(CatalogPanel())
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


intents = discord.Intents.default()
intents.message_content = True
bot = PortsBot(command_prefix="!", intents=intents)


def source_authorized(member):
    perms = getattr(member, "guild_permissions", None)
    if perms and (perms.administrator or perms.manage_guild):
        return True
    return any(
        role.id in ADMIN_ROLE_IDS
        for role in getattr(member, "roles", [])
    )



@bot.event
async def on_ready():
    log.info("Bot conectado como %s (ID: %s)", bot.user, bot.user.id)
    log.info("Canal de origem configurado: %s", SOURCE_CHANNEL_ID or "não configurado")
    log.info("Banco de dados: %s", DB_PATH)


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    if not SOURCE_CHANNEL_ID or message.channel.id != SOURCE_CHANNEL_ID:
        return
    if not source_authorized(message.author):
        log.warning("Post ignorado no canal de origem: autor sem permissão (user_id=%s)", message.author.id)
        return

    data, error = parse_message(message)
    if error:
        log.warning("Não foi possível importar a mensagem %s: %s", message.id, error)
        try:
            await message.reply(error, mention_author=False)
        except discord.HTTPException:
            pass
        return

    game_id, status = save_game(data, source_message_id=message.id)
    log.info("Jogo %s: %s (ID %s)", status, data["name"], game_id)
    try:
        await message.add_reaction("✅")
    except discord.HTTPException:
        pass


@bot.tree.command(name="painel", description="Abrir o painel administrativo do catálogo")
async def painel(interaction: discord.Interaction):
    if not admin_user(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    await interaction.response.send_message(
        "Painel administrativo do catálogo:",
        view=AdminView(),
        ephemeral=True
    )


def main():
    if not TOKEN:
        raise RuntimeError(
            "A variável DISCORD_TOKEN não está configurada na hospedagem. "
            "Adicione o token do bot nas variáveis de ambiente."
        )
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
