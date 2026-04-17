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
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")]
)
log = logging.getLogger("bot")

# ═══════════════════════════════════════════════════════════════
# PATCH GLOBAL — "by Koss" en embeds
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
# CARGAR CONFIG
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
def es_admin(ctx):
    return ctx.author.guild_permissions.administrator

def es_staff(ctx):
    return (
        ctx.author.guild_permissions.administrator or
        ctx.author.guild_permissions.manage_roles or
        any(r.name in ROLES_STAFF_CFG for r in ctx.author.roles)
    )

def es_owner_o_admin(ctx):
    return ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator

def es_owner_an(ctx):
    cfg = cargar_antinuke(ctx.guild.id)
    owner = cfg.get("owner_id")
    return ctx.author.id == ctx.guild.owner_id or (owner and ctx.author.id == int(owner))

# ═════════════════════════════════════════════════════════════
# 🛡️ ANTINUKE + TODO EL RESTO DE TU CÓDIGO (sin cambios en lógica)
# ═════════════════════════════════════════════════════════════
# (Aquí va TODO tu código anterior de AntiNuke, eventos, funciones, comandos, etc.)
# Lo mantengo igual, solo agrego botones en los comandos principales.

# ─────────────────────────────────────────────────────────────
# VISTAS CON BOTONES (NUEVO)
# ─────────────────────────────────────────────────────────────

class MainHelpView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=120)
        self.ctx = ctx

    @discord.ui.button(label="🌐 General", style=discord.ButtonStyle.gray, row=0)
    async def general(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Solo el que usó el comando.", ephemeral=True)
        await interaction.response.edit_message(embed=self.general_embed(), view=self)

    @discord.ui.button(label="🛡️ AntiNuke", style=discord.ButtonStyle.red, row=0)
    async def antinuke(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.send_message("❌ No permitido.", ephemeral=True)
        await interaction.response.edit_message(embed=self.antinuke_embed(), view=self)

    @discord.ui.button(label="🔒 Moderación", style=discord.ButtonStyle.blurple, row=1)
    async def mod(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.send_message("❌ No permitido.", ephemeral=True)
        await interaction.response.edit_message(embed=self.mod_embed(), view=self)

    @discord.ui.button(label="🎮 Juegos & Fun", style=discord.ButtonStyle.green, row=1)
    async def fun(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.send_message("❌ No permitido.", ephemeral=True)
        await interaction.response.edit_message(embed=self.fun_embed(), view=self)

    @discord.ui.button(label="🎭 Roleplay", style=discord.ButtonStyle.pink, row=2)
    async def rp(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.send_message("❌ No permitido.", ephemeral=True)
        await interaction.response.edit_message(embed=self.rp_embed(), view=self)

    # Embeds por categoría
    def general_embed(self):
        embed = discord.Embed(title="🌐 Comandos Generales", color=discord.Color.blurple())
        embed.description = f"Prefix actual: `{PREFIX}`"
        embed.add_field(name="Utilidad", value="`ping` `avatar` `banner` `userinfo` `serverinfo` `stats` `botinfo` `clima` `traducir` `calcular` `color`", inline=False)
        return embed

    def antinuke_embed(self):
        embed = discord.Embed(title="🛡️ AntiNuke — Panel", color=discord.Color.red())
        embed.description = "Usa `!an_ayuda` para ver todos los comandos de protección."
        embed.add_field(name="Comandos principales", value="`!antinuke` `!an_activar` `!an_desactivar` `!an_whitelist` `!an_logs`", inline=False)
        return embed

    def mod_embed(self):
        embed = discord.Embed(title="🔒 Moderación", color=discord.Color.blurple())
        embed.add_field(name="Acciones", value="`ban` `kick` `mute` `unmute` `limpiar` `lock` `unlock` `dar_rol` `quitar_rol` `v`", inline=False)
        return embed

    def fun_embed(self):
        embed = discord.Embed(title="🎮 Juegos y Diversión", color=discord.Color.green())
        embed.add_field(name="Juegos", value="`trivia` `adivina` `acertijo` `8ball` `piedra` `dado` `moneda`", inline=False)
        embed.add_field(name="Anime & RP", value="`abrazar` `kiss` `pat` `slap` `horoscopo` `personalidad`", inline=False)
        return embed

    def rp_embed(self):
        embed = discord.Embed(title="🎭 Roleplay", color=discord.Color.pink())
        embed.add_field(name="Comandos", value="`casar` `aceptar` `divorcio` `adoptar` `familia`", inline=False)
        return embed


# ─────────────────────────────────────────────────────────────
# COMANDO AYUDA MEJORADO CON BOTONES
# ─────────────────────────────────────────────────────────────
@bot.command(name="ayuda", aliases=["help", "h", "comandos"])
async def ayuda(ctx):
    embed = discord.Embed(
        title="📖 Menú Principal del Bot",
        description="Selecciona una categoría con los botones de abajo:",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else bot.user.display_avatar.url)
    embed.set_footer(text=f"Pedido por {ctx.author} • by Koss")

    view = MainHelpView(ctx)
    await ctx.send(embed=embed, view=view)


# ═════════════════════════════════════════════════════════════
# AQUÍ PEGA TODO EL RESTO DE TU CÓDIGO ORIGINAL
# (AntiNuke completo, eventos, comandos de roleplay, juegos, etc.)
# ═════════════════════════════════════════════════════════════

# ... [Pega aquí todo tu código desde ANTINUKE_FILE hasta el final] ...

# Solo reemplaza el comando @bot.command(name="ayuda"... ) antiguo por el nuevo de arriba.

# ─────────────────────────────────────────────────────────────
# EVENTOS
# ─────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    log.info(f"Bot conectado: {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{PREFIX}ayuda | by Koss")
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CheckFailure):
        await ctx.send("🔒 No tienes permisos suficientes.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Usuario no encontrado.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Falta argumento. Usa `{PREFIX}ayuda`")
    else:
        log.error(f"Error en {ctx.command}: {error}")
        await ctx.send(f"⚠️ Ocurrió un error: `{error}`")

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
        except Exception as e:
            log.error(f"Error crítico: {e}")
            time.sleep(5)
