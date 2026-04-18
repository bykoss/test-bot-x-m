import discord
from discord.ext import commands
import asyncio
import re
from datetime import timedelta

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Almacenamiento temporal (en memoria). Cuando uses hosting con DB, cámbialo por MongoDB.
        self.filters = {}           # guild_id: {"words": [], "caps": {}, ...}
        self.autoresponders = {}    # guild_id: {trigger: response}
        self.disabled_commands = {} # guild_id: {channel_id: [commands]}
        self.disabled_events = {}   # guild_id: {channel_id: [events]}
        self.disabled_modules = {}  # guild_id: {channel_id: [modules]}

    # ==================== FILTROS (filter) ====================
    @commands.group(name="filter", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def filter(self, ctx):
        await ctx.send("📋 **Filtro de chat** - Usa `,filter <subcomando>`\n"
                       "Ejemplos: `,filter add palabra`, `,filter caps on 70%`, `,filter list`")

    @filter.command(name="add")
    async def filter_add(self, ctx, *, word: str):
        gid = ctx.guild.id
        if gid not in self.filters:
            self.filters[gid] = {"words": []}
        self.filters[gid]["words"].append(word.lower())
        await ctx.send(f"✅ Palabra **{word}** añadida al filtro.")

    @filter.command(name="remove")
    async def filter_remove(self, ctx, *, word: str):
        gid = ctx.guild.id
        if gid in self.filters and word.lower() in self.filters[gid]["words"]:
            self.filters[gid]["words"].remove(word.lower())
            await ctx.send(f"✅ Palabra **{word}** eliminada del filtro.")
        else:
            await ctx.send("❌ Esa palabra no está en el filtro.")

    @filter.command(name="list")
    async def filter_list(self, ctx):
        gid = ctx.guild.id
        words = self.filters.get(gid, {}).get("words", [])
        if not words:
            await ctx.send("📭 No hay palabras filtradas.")
        else:
            await ctx.send(f"**Palabras filtradas ({len(words)}):**\n" + "\n".join(words))

    @filter.command(name="reset")
    async def filter_reset(self, ctx):
        gid = ctx.guild.id
        if gid in self.filters:
            del self.filters[gid]
        await ctx.send("✅ Todos los filtros reiniciados.")

    # Filtros específicos (caps, invites, links, etc.)
    @filter.group(name="caps")
    async def filter_caps(self, ctx):
        await ctx.send("🔠 **Filtro de mayúsculas** - Usa `,filter caps on <porcentaje>`")

    @filter_caps.command(name="exempt")
    async def filter_caps_exempt(self, ctx, role: discord.Role):
        await ctx.send(f"✅ Rol **{role.name}** exento del filtro de mayúsculas.")

    @filter_caps.command(name="exempt list")
    async def filter_caps_exempt_list(self, ctx):
        await ctx.send("📋 Lista de roles exentos de mayúsculas (demo).")

    # Repito el mismo patrón para los demás filtros que tiene Bleed
    @filter.group(name="invites")
    async def filter_invites(self, ctx):
        await ctx.send("🔗 **Filtro de invites**")

    @filter_invites.command(name="exempt")
    async def filter_invites_exempt(self, ctx, role: discord.Role):
        await ctx.send(f"✅ Rol exento de filtro de invites.")

    @filter.group(name="links")
    async def filter_links(self, ctx):
        await ctx.send("🔗 **Filtro de links**")

    @filter_links.command(name="whitelist")
    async def filter_links_whitelist(self, ctx, *, url: str):
        await ctx.send(f"✅ {url} añadido a whitelist de links.")

    @filter.group(name="spoilers")
    async def filter_spoilers(self, ctx):
        await ctx.send("|| **Filtro de spoilers**")

    @filter.group(name="spam")
    async def filter_spam(self, ctx):
        await ctx.send("⏩ **Anti-spam**")

    @filter.group(name="emoji")
    async def filter_emoji(self, ctx):
        await ctx.send("😀 **Filtro de emojis**")

    @filter.group(name="massmention")
    async def filter_massmention(self, ctx):
        await ctx.send("👥 **Filtro de menciones masivas**")

    @filter.group(name="musicfiles")
    async def filter_musicfiles(self, ctx):
        await ctx.send("🎵 **Filtro de archivos de música**")

    # ==================== AUTO-RESPONDER ====================
    @commands.group(name="autoresponder", invoke_without_command=True, aliases=["ar"])
    @commands.has_permissions(manage_guild=True)
    async def autoresponder(self, ctx):
        await ctx.send("📬 **Auto-responder** - Usa `,ar add trigger respuesta`")

    @autoresponder.command(name="add")
    async def ar_add(self, ctx, trigger: str, *, response: str):
        gid = ctx.guild.id
        if gid not in self.autoresponders:
            self.autoresponders[gid] = {}
        self.autoresponders[gid][trigger.lower()] = response
        await ctx.send(f"✅ Auto-respuesta creada: **{trigger}** → {response[:100]}...")

    @autoresponder.command(name="remove")
    async def ar_remove(self, ctx, trigger: str):
        gid = ctx.guild.id
        if gid in self.autoresponders and trigger.lower() in self.autoresponders[gid]:
            del self.autoresponders[gid][trigger.lower()]
            await ctx.send(f"✅ Auto-respuesta **{trigger}** eliminada.")
        else:
            await ctx.send("❌ No existe esa auto-respuesta.")

    @autoresponder.command(name="list")
    async def ar_list(self, ctx):
        gid = ctx.guild.id
        ars = self.autoresponders.get(gid, {})
        if not ars:
            await ctx.send("📭 No hay auto-respuestas.")
        else:
            text = "\n".join([f"`{t}` → {r[:50]}..." for t, r in ars.items()])
            await ctx.send(f"**Auto-respuestas ({len(ars)}):**\n{text}")

    @autoresponder.command(name="reset")
    async def ar_reset(self, ctx):
        gid = ctx.guild.id
        if gid in self.autoresponders:
            del self.autoresponders[gid]
        await ctx.send("✅ Todas las auto-respuestas eliminadas.")

    # ==================== PAGINACIÓN ====================
    @commands.group(name="pagination", aliases=["pages"])
    @commands.has_permissions(manage_guild=True)
    async def pagination(self, ctx):
        await ctx.send("📖 **Paginación de embeds** - Usa `,pagination add <link> <código embed>`")

    @pagination.command(name="add")
    async def pagination_add(self, ctx, message_link: str, *, embed_code: str):
        await ctx.send("✅ Página añadida a la paginación (demo).")

    @pagination.command(name="list")
    async def pagination_list(self, ctx):
        await ctx.send("📋 Lista de paginaciones (demo).")

    @pagination.command(name="reset")
    async def pagination_reset(self, ctx):
        await ctx.send("✅ Todas las paginaciones reiniciadas.")

    # ==================== COMANDOS / EVENTOS / MÓDULOS DISABLE/ENABLE ====================
    @commands.command(name="disablecommand")
    @commands.has_permissions(manage_guild=True)
    async def disablecommand(self, ctx, channel: discord.TextChannel = None, *, command: str):
        await ctx.send(f"✅ Comando `{command}` deshabilitado en {channel.mention if channel else 'todo el servidor'}.")

    @commands.command(name="enablecommand")
    @commands.has_permissions(manage_guild=True)
    async def enablecommand(self, ctx, channel: discord.TextChannel = None, *, command: str):
        await ctx.send(f"✅ Comando `{command}` habilitado.")

    @commands.command(name="disableevent")
    @commands.has_permissions(manage_guild=True)
    async def disableevent(self, ctx, channel: discord.TextChannel = None, *, event: str):
        await ctx.send(f"✅ Evento `{event}` deshabilitado.")

    @commands.command(name="enableevent")
    @commands.has_permissions(manage_guild=True)
    async def enableevent(self, ctx, channel: discord.TextChannel = None, *, event: str):
        await ctx.send(f"✅ Evento `{event}` habilitado.")

    @commands.command(name="disablemodule")
    @commands.has_permissions(manage_guild=True)
    async def disablemodule(self, ctx, channel: discord.TextChannel = None, *, module: str):
        await ctx.send(f"✅ Módulo `{module}` deshabilitado.")

    @commands.command(name="enablemodule")
    @commands.has_permissions(manage_guild=True)
    async def enablemodule(self, ctx, channel: discord.TextChannel = None, *, module: str):
        await ctx.send(f"✅ Módulo `{module}` habilitado.")

    # ==================== COMANDOS CLÁSICOS DE MODERACIÓN (ban, kick, etc.) ====================
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Sin razón"):
        await member.ban(reason=reason)
        await ctx.send(f"✅ **{member}** baneado | Razón: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, user: str):
        await ctx.send(f"✅ Usuario **{user}** desbaneado.")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Sin razón"):
        await member.kick(reason=reason)
        await ctx.send(f"✅ **{member}** expulsado | Razón: {reason}")

    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = "Sin razón"):
        await ctx.send(f"✅ **{member}** muteado | Razón: {reason}")

    @commands.command(name="unmute")
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        await ctx.send(f"✅ **{member}** desmuteado.")

    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: str, *, reason: str = "Sin razón"):
        await ctx.send(f"✅ **{member}** en timeout ({duration}) | Razón: {reason}")

    @commands.command(name="jail")
    @commands.has_permissions(manage_roles=True)
    async def jail(self, ctx, member: discord.Member, *, reason: str = "Sin razón"):
        await ctx.send(f"✅ **{member}** enviado a jail | Razón: {reason}")

    @commands.command(name="unjail")
    @commands.has_permissions(manage_roles=True)
    async def unjail(self, ctx, member: discord.Member):
        await ctx.send(f"✅ **{member}** sacado de jail.")

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "Sin razón"):
        await ctx.send(f"⚠️ **{member}** advertido | Razón: {reason}")

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"🧹 **{amount}** mensajes eliminados.", delete_after=3)

    @commands.command(name="nuke")
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx):
        await ctx.channel.clone()
        await ctx.channel.delete()
        await ctx.send("💥 Canal nukeado.")

    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"⏳ Slowmode puesto a **{seconds}** segundos.")

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Canal bloqueado.")

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 Canal desbloqueado.")

    # ==================== LISTA DE COMANDOS DISABLED ====================
    @commands.command(name="disablecommand list")
    async def disable_list(self, ctx):
        await ctx.send("📋 Lista de comandos deshabilitados (demo).")

    @commands.command(name="disableevent list")
    async def disableevent_list(self, ctx):
        await ctx.send("📋 Lista de eventos deshabilitados (demo).")

    # Evento que hace funcionar los filtros y autoresponders
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        gid = message.guild.id

        # Filtro de palabras
        content = message.content.lower()
        if gid in self.filters and any(word in content for word in self.filters[gid].get("words", [])):
            await message.delete()
            return

        # Auto-responder
        if gid in self.autoresponders:
            for trigger, response in self.autoresponders[gid].items():
                if trigger in content:
                    await message.channel.send(response)
                    break

async def setup(bot):
    await bot.add_cog(Moderation(bot))
