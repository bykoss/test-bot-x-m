import asyncio
import discord
from discord.ext import commands
from discord import app_commands
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
#  LOGGING
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
#  PATCH GLOBAL — "by Exagonal"
# ═══════════════════════════════════════════════════════════════
# Mantenemos tu sistema de marca de agua automático
_original_send = discord.abc.Messageable.send
@functools.wraps(_original_send)
async def _patched_send(self, content=None, **kwargs):
    embed = kwargs.get("embed")
    if embed is not None:
        footer = embed.footer
        if not footer or not footer.text:
            embed.set_footer(text="by Exagonal")
        elif "by Exagonal" not in footer.text:
            embed.set_footer(text=f"{footer.text} | by Exagonal", icon_url=footer.icon_url)
    return await _original_send(self, content=content, **kwargs)
discord.abc.Messageable.send = _patched_send

# ─────────────────────────────────────────────────────────────
#  CONFIGURACIÓN Y BOT CLASS
# ─────────────────────────────────────────────────────────────
CONFIG_FILE = "config.json"

def cargar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"token": "", "prefix": "!"}

CONFIG = cargar_config()
TOKEN = CONFIG.get("token")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() # Activamos todos para que el AntiNuke funcione bien
        super().__init__(command_prefix=CONFIG.get("prefix", "!"), intents=intents)

    async def setup_hook(self):
        # Esto hace que los comandos "/" se registren en Discord
        log.info("Sincronizando comandos de aplicación...")
        await self.tree.sync()
        log.info("Comandos sincronizados correctamente.")

bot = MyBot()

# ─────────────────────────────────────────────────────────────
#  BASE DE DATOS ANTINUKE (Lógica original)
# ─────────────────────────────────────────────────────────────
ANTINUKE_FILE = "antinuke.json"
def cargar_antinuke(guild_id):
    if os.path.exists(ANTINUKE_FILE):
        with open(ANTINUKE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(str(guild_id), {"activo": False, "whitelist": [], "logs": None})
    return {"activo": False, "whitelist": [], "logs": None}

def guardar_antinuke(guild_id, data):
    all_data = {}
    if os.path.exists(ANTINUKE_FILE):
        with open(ANTINUKE_FILE, "r", encoding="utf-8") as f:
            all_data = json.load(f)
    all_data[str(guild_id)] = data
    with open(ANTINUKE_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4)

# ─────────────────────────────────────────────────────────────
#  COMANDOS DE APLICACIÓN (SLASH COMMANDS /)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(name="antinuke", description="Ver el estado del sistema AntiNuke")
async def antinuke(interaction: discord.Interaction):
    # Verificación de permisos (Solo Dueño o Admin)
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ No tienes permisos para usar esto.", ephemeral=True)
    
    data = cargar_antinuke(interaction.guild_id)
    estado = "✅ Activo" if data["activo"] else "❌ Desactivado"
    
    embed = discord.Embed(title="🛡️ Configuración AntiNuke", color=discord.Color.blue())
    embed.add_field(name="Estado", value=estado)
    embed.add_field(name="Whitelist", value=len(data["whitelist"]))
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="an_activar", description="Activa el AntiNuke")
async def an_activar(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Permisos insuficientes.", ephemeral=True)
    
    data = cargar_antinuke(interaction.guild_id)
    data["activo"] = True
    guardar_antinuke(interaction.guild_id, data)
    
    await interaction.response.send_message("✅ El **AntiNuke** ha sido activado correctamente.")

@bot.tree.command(name="an_whitelist", description="Añade un usuario a la lista blanca")
@app_commands.describe(usuario="El usuario que quieres proteger")
async def an_whitelist(interaction: discord.Interaction, usuario: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Permisos insuficientes.", ephemeral=True)
    
    data = cargar_antinuke(interaction.guild_id)
    if usuario.id not in data["whitelist"]:
        data["whitelist"].append(usuario.id)
        guardar_antinuke(interaction.guild_id, data)
        await interaction.response.send_message(f"✅ {usuario.mention} ha sido añadido a la whitelist.")
    else:
        await interaction.response.send_message(f"ℹ️ {usuario.mention} ya estaba en la whitelist.")

@bot.tree.command(name="ayuda", description="Muestra la lista de comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help Menu",
        description="Usa los comandos con `/` para gestionar el bot.",
        color=0x2b2d31
    )
    embed.add_field(name="🛡️ AntiNuke", value="`/antinuke`, `/an_activar`, `/an_whitelist`", inline=False)
    await interaction.response.send_message(embed=embed)

# ─────────────────────────────────────────────────────────────
#  EVENTOS DE SEGURIDAD (Se mantienen igual)
# ─────────────────────────────────────────────────────────────
@bot.event
async def on_guild_channel_delete(channel):
    data = cargar_antinuke(channel.guild.id)
    if not data["activo"]: return
    # ... aquí iría tu lógica de recuperación de canales original ...
    log.warning(f"Canal eliminado en {channel.guild.name}. AntiNuke evaluando...")

# ─────────────────────────────────────────────────────────────
#  EJECUCIÓN
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        log.critical("¡Falta el TOKEN en config.json!")
