import asyncio
import discord
from discord.ext import commands
import json
import os
import sys
import time
import traceback
import logging
import random
import aiohttp
from datetime import datetime, timezone
from collections import defaultdict
import functools

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s » %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
log = logging.getLogger("bot")

# ═══════════════════════════════════════════════════════════════
# PATCH GLOBAL — "by Koss"
# ═══════════════════════════════════════════════════════════════
_original_send = discord.abc.Messageable.send

@functools.wraps(_original_send)
async def _patched_send(self, content=None, **kwargs):
    embed = kwargs.get("embed")
    if embed is not None:
        footer = embed.footer
        if not footer or not footer.text:
            embed.set_footer(text="by Koss")
        elif "by Koss" not in footer.text:
            if footer.icon_url:
                embed.set_footer(text=footer.text + " | by Koss", icon_url=footer.icon_url)
            else:
                embed.set_footer(text=footer.text + " | by Koss")
    return await _original_send(self, content=content, **kwargs)

discord.abc.Messageable.send = _patched_send

# ─────────────────────────────────────────────────────────────
# CARGAR CONFIG.JSON
# ─────────────────────────────────────────────────────────────
CONFIG_FILE = "config.json"
def cargar_config() -> dict:
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    token_env = os.environ.get("DISCORD_TOKEN")
    if token_env:
        cfg["token"] = token_env
    if cfg.get("token") in ("", "TU_TOKEN_AQUÍ", None):
        log.critical("No se encontró token.")
        sys.exit(1)
    return cfg

CONFIG = cargar_config()
TOKEN = CONFIG["token"]
PREFIX = CONFIG.get("prefix", "!")
ROLES_STAFF_CFG = CONFIG.get("roles_staff", ["👑 Administración", "🛡️ Moderador"])

# ─────────────────────────────────────────────────────────────
# BOT
# ─────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
bot.remove_command("help")

# ─────────────────────────────────────────────────────────────
# PERMISOS
# ─────────────────────────────────────────────────────────────
def es_admin(ctx) -> bool:
    return ctx.author.guild_permissions.administrator

def es_staff(ctx) -> bool:
    return (
        ctx.author.guild_permissions.administrator
        or ctx.author.guild_permissions.manage_roles
        or any(r.name in ROLES_STAFF_CFG for r in ctx.author.roles)
    )

def es_owner_o_admin(ctx) -> bool:
    return ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator

def es_owner_an(ctx) -> bool:
    cfg = cargar_antinuke(ctx.guild.id)
    owner = cfg.get("owner_id")
    return (
        ctx.author.id == ctx.guild.owner_id
        or (owner and ctx.author.id == int(owner))
    )

# ═════════════════════════════════════════════════════════════
# 🛡️ ANTINUKE — SISTEMA COMPLETO (tu código original sin cambios)
# ═════════════════════════════════════════════════════════════
ANTINUKE_FILE = "antinuke.json"
ANTINUKE_DEFAULT = {
    "activo": True,
    "whitelist": [],
    "owner_id": None,
    "limites": {
        "ban": 3,
        "kick": 3,
        "roles": 3,
        "canales": 3,
        "webhooks": 3,
    },
    "ventana": 10,
    "accion": "ban",
    "log_channel": None,
    "antiraid": {
        "activo": False,
        "joins_limite": 10,
        "joins_ventana": 10,
        "accion": "kick",
    },
    "antilinks": {
        "activo": False,
        "whitelist_canales": [],
        "whitelist_roles": [],
    },
    "antispam": {
        "activo": False,
        "mensajes_limite": 5,
        "ventana": 5,
    },
    "antibot": {
        "activo": False,
    },
    "verificacion": {
        "activo": False,
        "rol_verificado": None,
        "rol_no_verificado": None,
        "canal": None,
        "emoji": "✅",
    },
    "warn_sistema": {},
    "mute_rol": None,
}

# (Aquí va todo tu código de AntiNuke: cargar_antinuke, guardar_antinuke, registrar_accion, es_seguro, ejecutar_castigo, log_antinuke y TODOS los @bot.event)

# ... Pega aquí todo tu código AntiNuke original (on_member_ban, on_member_remove, on_guild_role_delete, on_message, on_member_join, etc.) ...

# Todos tus comandos AntiNuke, warn, roleplay, horoscopo, trivia, lock, dar_rol, comando "v", etc. se mantienen exactamente igual.

# ═════════════════════════════════════════════════════════════
# AYUDA CON BOTONES - SOLO ESTA PARTE FUE CORREGIDA
# ═════════════════════════════════════════════════════════════

class MainHelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🌐 General", style=discord.ButtonStyle.gray, row=0)
    async def general(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🌐 Comandos Generales", color=discord.Color.blurple())
        embed.description = "`ping` `avatar` `banner` `userinfo` `serverinfo` `stats` `botinfo` `clima` `traducir` `calcular` `color`"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🛡️ AntiNuke", style=discord.ButtonStyle.red, row=0)
    async def antinuke(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛡️ AntiNuke", color=discord.Color.red())
        embed.description = "Sistema de protección completo.\nUsa `!an_ayuda` para ver todos los comandos."
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔒 Moderación", style=discord.ButtonStyle.blurple, row=1)
    async def mod(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🔒 Moderación", color=discord.Color.blurple())
        embed.description = "`ban` `kick` `mute` `limpiar` `lock` `unlock` `dar_rol` `quitar_rol` `v`"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎮 Juegos", style=discord.ButtonStyle.green, row=1)
    async def juegos(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎮 Juegos y Diversión", color=discord.Color.green())
        embed.description = "`trivia` `adivina` `8ball` `piedra` `dado` `horoscopo` `personalidad` `abrazar` `kiss` `frase` `chiste`"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎭 Roleplay", style=discord.ButtonStyle.pink, row=2)
    async def roleplay(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎭 Roleplay", color=discord.Color.pink())
        embed.description = "`casar` `aceptar` `divorcio` `adoptar` `familia`"
        await interaction.response.edit_message(embed=embed, view=self)


@bot.command(name="ayuda", aliases=["help", "h", "comandos"])
async def ayuda(ctx):
    embed = discord.Embed(
        title="📖 Menú Principal del Bot",
        description="Selecciona una categoría con los botones de abajo.",
        color=discord.Color.gold()
    )
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    view = MainHelpView()
    await ctx.send(embed=embed, view=view)

# ─────────────────────────────────────────────────────────────
# EVENTOS
# ─────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    log.info(f"Bot conectado: {bot.user} (ID: {bot.user.id})")
    bot.add_view(MainHelpView())   # ← Línea importante para que los botones funcionen
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{PREFIX}ayuda | by Koss")
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🔒 No tienes permisos.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Usuario no encontrado.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Falta argumento. Usa `{PREFIX}ayuda`")
    else:
        log.error(f"Error en '{ctx.command}': {error}")
        await ctx.send(f"⚠️ Error: `{error}`")

# ─────────────────────────────────────────────────────────────
# INICIO
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    while True:
        try:
            log.info("Iniciando bot...")
            bot.run(TOKEN, reconnect=True)
        except discord.LoginFailure:
            log.critical("TOKEN INVÁLIDO")
            sys.exit(1)
        except KeyboardInterrupt:
            log.info("Detenido.")
            sys.exit(0)
        except Exception:
            log.error(f"Error:\n{traceback.format_exc()}")
            log.info("Reiniciando en 5s...")
            time.sleep(5)
