import discord
import json
import os
import asyncio
import random
import string
import time
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

# --- CONFIGURACIÓN INICIAL ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Cargar configuración desde un archivo JSON
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    # Crear un config.json por defecto si no existe
    config = {
        "prefix": "!",
        "owner_id": "AQUI_TU_ID_DE_USUARIO",
        "guild_id": "AQUI_EL_ID_DE_UN_SERVIDOR_PARA_PROBAR_COMANDOS_SLASH",
        "embed_color": "2F3136",
        "error_color": "ED4245",
        "success_color": "57F287"
    }
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
    print("Se ha creado un archivo 'config.json'. Por favor, edítalo con tus IDs.")

# --- INTENTS Y BOT ---
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.bans = True
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.voice_states = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=config['prefix'],
            intents=intents,
            owner_ids={int(config['owner_id'])}
        )
        self._loaded = False

    async def setup_hook(self):
        # Cargar los Cogs
        await self.add_cog(Moderacion(self))
        await self.add_cog(Administracion(self))
        await self.add_cog(Antinuke(self))
        await self.add_cog(Utilidad(self))
        await self.add_cog(Informacion(self))
        await self.add_cog(Musica(self))
        await self.add_cog(Economia(self))
        await self.add_cog(Niveles(self))
        await self.add_cog(Welcome(self))
        
        # Sincronizar comandos para un guild específico (más rápido para desarrollo)
        # Para todos los servidores, usa: await self.tree.sync()
        guild = discord.Object(id=int(config['guild_id']))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"Comandos sincronizados para el guild: {guild.id}")
        self._loaded = True

    async def on_ready(self):
        if not self._loaded:
            return # Esperar a que setup_hook termine
        print(f'¡Bot conectado como {self.user}!')
        print(f'ID del Bot: {self.user.id}')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Slash Commands"))

bot = MyBot()

# --- ALMACENAMIENTO EN MEMORIA ---
warns = {}
muted_users = {}
tempbans = {}
economy_data = {}
levels_data = {}
snipe_message = {}
editsnipe_message = {}
raid_mode = {}
antinuke_config = {}
welcome_messages = {}
leave_messages = {}

# --- FUNCIONES AUXILIARES ---
def get_embed(title="", description="", color=None, footer=None):
    """Crea un embed con el estilo del bot."""
    color_val = int(color, 16) if color else int(config['embed_color'], 16)
    embed = discord.Embed(title=title, description=description, color=color_val)
    if footer:
        embed.set_footer(text=footer)
    return embed

# === COG DE MODERACIÓN ===
class Moderacion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Expulsa a un usuario del servidor.")
    @app_commands.describe(member="El usuario a expulsar", reason="La razón de la expulsión")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No especificada."):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(embed=get_embed("❌ Error", "No puedes expulsar a alguien con un rol igual o superior al tuyo.", config['error_color']), ephemeral=True)
        await member.kick(reason=reason)
        await interaction.response.send_message(embed=get_embed("🔨 Usuario Expulsado", f"{member.mention} ha sido expulsado.\n**Razón:** {reason}", config['success_color']))

    @app_commands.command(name="ban", description="Banea a un usuario del servidor.")
    @app_commands.describe(member="El usuario a banear", reason="La razón del baneo")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No especificada."):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(embed=get_embed("❌ Error", "No puedes banear a alguien con un rol igual o superior al tuyo.", config['error_color']), ephemeral=True)
        await member.ban(reason=reason)
        await interaction.response.send_message(embed=get_embed("⛔ Usuario Baneado", f"{member.mention} ha sido baneado.\n**Razón:** {reason}", config['success_color']))

    @app_commands.command(name="unban", description="Desbanea a un usuario del servidor.")
    @app_commands.describe(user_id="La ID del usuario a desbanear", reason="La razón del desbaneo")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No especificada."):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
            await interaction.response.send_message(embed=get_embed("✅ Usuario Desbaneado", f"{user.mention} ha sido desbaneado.\n**Razón:** {reason}", config['success_color']))
        except (ValueError, discord.NotFound):
            await interaction.response.send_message(embed=get_embed("❌ Error", "Usuario no encontrado o ya no está baneado.", config['error_color']), ephemeral=True)

    @app_commands.command(name="clear", description="Elimina una cantidad de mensajes.")
    @app_commands.describe(amount="El número de mensajes a eliminar (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 10):
        if amount <= 0 or amount > 100:
            return await interaction.response.send_message(embed=get_embed("❌ Error", "La cantidad debe estar entre 1 y 100.", config['error_color']), ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        msg = await interaction.followup.send(embed=get_embed("🧹 Mensajes Eliminados", f"Se eliminaron `{len(deleted)}` mensajes.", config['success_color']), ephemeral=True)
        await asyncio.sleep(5)
        await msg.delete()

    @app_commands.command(name="mute", description="Silencia
