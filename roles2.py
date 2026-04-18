import discord
from discord.ext import commands
import discord.app_commands as app_commands
import asyncio
import json
import os
import random
import time
import traceback
import sys
import aiohttp
from datetime import datetime, timezone
import logging

log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.FileHandler(filename="bot.log", encoding="utf-8", mode="a")
handler.setFormatter(logging.Formatter("%(asctime)s: %(message)s"))
log.addHandler(handler)

TOKEN = "TU_TOKEN_AQUI"
PREFIX = "!"

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.bans = True
intents.messages = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True,
    strip_after_prefix=True
)

# Decoradores de verificación
def es_admin(ctx):
    return ctx.author.guild_permissions.administrator

def es_staff(ctx):
    return ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.moderate_members

def es_owner_o_admin(ctx):
    return ctx.author == ctx.guild.owner or ctx.author.guild_permissions.administrator

# Función de carga/guardado de configuración de antinuke
ANTINUKE_FILE = "antinuke.json"

def cargar_antinuke(guild_id: int) -> dict:
    if os.path.exists(ANTINUKE_FILE):
        with open(ANTINUKE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(str(guild_id), {})
    return {}

def guardar_antinuke(guild_id: int, cfg: dict):
    data = {}
    if os.path.exists(ANTINUKE_FILE):
        with open(ANTINUKE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    data[str(guild_id)] = cfg
    with open(ANTINUKE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ═════════════════════════════════════════════════════════════
#  🛡️ ANTINUKE
# ═════════════════════════════════════════════════════════════

@bot.command(name="antinuke")
@commands.check(es_admin)
async def antinuke_cmd(ctx):
    cfg = cargar_antinuke(ctx.guild.id)
    embed = discord.Embed(title="🛡️ AntiNuke Panel", color=discord.Color.red())
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    # Anti-Raid
    ar = cfg.get("anti_raid", {})
    ar_status = "🟢 Activo" if ar.get("enabled", False) else "🔴 Inactivo"
    ar_limit = ar.get("limit", 5)
    ar_time = ar.get("time", 60)
    ar_punish = ar.get("punishment", "kick")
    embed.add_field(name="🚨 Anti-Raid", value=f"{ar_status}\nLímite: {ar_limit} joins/{ar_time}s\nCastigo: {ar_punish}", inline=False)
    
    # Anti-Links
    al = cfg.get("anti_links", {})
    al_status = "🟢 Activo" if al.get("enabled", False) else "🔴 Inactivo"
    al_exempt = ", ".join([ctx.guild.get_role(r).mention for r in al.get("exempt_roles", []) if ctx.guild.get_role(r)]) or "Ninguno"
    embed.add_field(name="🔗 Anti-Links", value=f"{al_status}\nExentos: {al_exempt}", inline=False)
    
    # Anti-Spam
    asp = cfg.get("anti_spam", {})
    asp_status = "🟢 Activo" if asp.get("enabled", False) else "🔴 Inactivo"
    asp_limit = asp.get("limit", 5)
    asp_time = asp.get("time", 10)
    embed.add_field(name="💬 Anti-Spam", value=f"{asp_status}\nLímite: {asp_limit} msgs/{asp_time}s", inline=False)
    
    # Anti-Bot
    ab = cfg.get("anti_bot", {})
    ab_status = "🟢 Activo" if ab.get("enabled", False) else "🔴 Inactivo"
    embed.add_field(name="🤖 Anti-Bot", value=f"{ab_status}", inline=False)
    
    # Verificación
    verif = cfg.get("verification", {})
    verif_status = "🟢 Activo" if verif.get("enabled", False) else "🔴 Inactivo"
    verif_role = ctx.guild.get_role(verif.get("role")).mention if verif.get("role") and ctx.guild.get_role(verif.get("role")) else "No configurado"
    embed.add_field(name="✅ Verificación", value=f"{verif_status}\nRol: {verif_role}", inline=False)
    
    # Log channel
    log_ch = cfg.get("log_channel")
    log_ch_mention = ctx.guild.get_channel(int(log_ch)).mention if log_ch and ctx.guild.get_channel(int(log_ch)) else "No configurado"
    embed.add_field(name="📋 Canal de Logs", value=log_ch_mention, inline=False)
    
    embed.set_footer(text=f"Usa {PREFIX}an_ayuda para ver todos los comandos.")
    await ctx.send(embed=embed)

# Comando de ayuda para AntiNuke
@bot.command(name="an_ayuda", aliases=["an_help"])
@commands.check(es_admin)
async def antinuke_ayuda(ctx):
    embed = discord.Embed(title="🛡️ Comandos AntiNuke", color=discord.Color.red())
    embed.add_field(name=f"{PREFIX}antinuke", value="Muestra el panel de configuración", inline=False)
    embed.add_field(name=f"{PREFIX}an_raid <on/off> [límite] [tiempo] [castigo]", value="Configura anti-raid", inline=False)
    embed.add_field(name=f"{PREFIX}an_links <on/off> [@rol1 @rol2...]", value="Configura anti-links", inline=False)
    embed.add_field(name=f"{PREFIX}an_spam <on/off> [límite] [tiempo]", value="Configura anti-spam", inline=False)
    embed.add_field(name=f"{PREFIX}an_bot <on/off>", value="Configura anti-bot", inline=False)
    embed.add_field(name=f"{PREFIX}an_verif <on/off> [@rol]", value="Configura verificación", inline=False)
    embed.add_field(name=f"{PREFIX}an_logs <#canal>", value="Establece canal de logs", inline=False)
    await ctx.send(embed=embed)

# Configuración Anti-Raid
@bot.command(name="an_raid")
@commands.check(es_admin)
async def antinuke_raid(ctx, estado: str, limite: int = 5, tiempo: int = 60, castigo: str = "kick"):
    cfg = cargar_antinuke(ctx.guild.id)
    if estado.lower() in ["on", "activar", "enable"]:
        cfg["anti_raid"] = {"enabled": True, "limit": limite, "time": tiempo, "punishment": castigo}
        await ctx.send(f"✅ Anti-Raid activado: {limite} joins/{tiempo}s → {castigo}")
    elif estado.lower() in ["off", "desactivar", "disable"]:
        cfg["anti_raid"] = {"enabled": False}
        await ctx.send("❌ Anti-Raid desactivado")
    else:
        await ctx.send("❌ Usa `on` o `off`")
    guardar_antinuke(ctx.guild.id, cfg)

# Configuración Anti-Links
@bot.command(name="an_links")
@commands.check(es_admin)
async def antinuke_links(ctx, estado: str, *roles: discord.Role):
    cfg = cargar_antinuke(ctx.guild.id)
    if estado.lower() in ["on", "activar", "enable"]:
        exempt_roles = [r.id for r in roles] if roles else []
        cfg["anti_links"] = {"enabled": True, "exempt_roles": exempt_roles}
        await ctx.send(f"✅ Anti-Links activado. Roles exentos: {', '.join([r.mention for r in roles]) if roles else 'Ninguno'}")
    elif estado.lower() in ["off", "desactivar", "disable"]:
        cfg["anti_links"] = {"enabled": False}
        await ctx.send("❌ Anti-Links desactivado")
    else:
        await ctx.send("❌ Usa `on` o `off`")
    guardar_antinuke(ctx.guild.id, cfg)

# Configuración Anti-Spam
@bot.command(name="an_spam")
@commands.check(es_admin)
async def antinuke_spam(ctx, estado: str, limite: int = 5, tiempo:
