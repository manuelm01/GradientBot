import discord
from discord.ext import tasks
import itertools
import asyncio
import os
from datetime import timedelta, datetime
from flask import Flask
from threading import Thread
import youtube_dl
import ffmpeg

# -------------------- CONFIG --------------------
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = 1170123435691749517
ROLE_ID = 1413273099268522036

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.Bot(intents=intents)

# -------------------- CONFIGURACIÓN DE MÚSICA --------------------
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Variables de música
music_queue = []
current_player = None

# -------------------- GRADIENTE --------------------
color_steps = [0xFFFFFF, 0xFFCCCC, 0xFF6666, 0x990000]
color_cycle = itertools.cycle(color_steps)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    animate_role.start()
    print(f"Slash commands sincronizados ({len(bot.pending_application_commands)} comandos)")

@tasks.loop(minutes=2)
async def animate_role():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("Servidor no encontrado")
        return
    role = guild.get_role(ROLE_ID)
    if not role:
        print("Rol no encontrado")
        return

    new_color = next(color_cycle)
    try:
        await role.edit(color=discord.Color(new_color))
        print(f"Rol '{role.name}' color aplicado: #{new_color:06X}")
    except discord.Forbidden:
        print("No tengo permisos para cambiar el color del rol")
    except discord.HTTPException as e:
        print(f"Error HTTP: {e}")

# -------------------- FUNCIÓN HELPER --------------------
async def verificar_permisos_bot(ctx, target_member):
    """Verifica si el bot puede actuar sobre el miembro objetivo"""
    # Verificar si el bot es el propietario del servidor
    if ctx.guild.owner_id == ctx.me.id:
        return True
    
    # Verificar si el rol más alto del bot es superior al del objetivo
    bot_top_role = ctx.me.top_role
    target_top_role = target_member.top_role
    
    if bot_top_role.position <= target_top_role.position:
        return False
    
    # Verificar si el objetivo es el propietario del servidor
    if target_member.id == ctx.guild.owner_id:
        return False
    
    return True

# -------------------- SLASH COMMANDS --------------------
@bot.slash_command(name="ping", description="Comprueba que el bot está activo")
async def ping(ctx):
    await ctx.respond("Pong! 🟢")

@bot.slash_command(name="ban", description="Banea a un usuario")
async def ban(ctx, usuario: discord.Member, razon: str = "No especificada"):
    try:
        # Verificar permisos del bot
        if not await verificar_permisos_bot(ctx, usuario):
            await ctx.respond(f"❌ No puedo banear a {usuario.mention} porque su rol es igual o superior al mío.")
            return
        
        # Verificar permisos específicos
        if not ctx.me.guild_permissions.ban_members:
            await ctx.respond("❌ No tengo el permiso 'Banear miembros' en este servidor.")
            return
        
        await usuario.ban(reason=f"Ban por {ctx.author}: {razon}")
        await ctx.respond(f"✅ {usuario.mention} ha sido baneado.\n**Razón:** {razon}")
    except discord.Forbidden:
        await ctx.respond(f"❌ No tengo permisos para banear a {usuario.mention}. Verifica que mi rol esté por encima del suyo.")
    except Exception as e:
        await ctx.respond(f"❌ Error: {e}")

@bot.slash_command(name="kick", description="Expulsa a un usuario")
async def kick(ctx, usuario: discord.Member, razon: str = "No especificada"):
    try:
        # Verificar permisos del bot
        if not await verificar_permisos_bot(ctx, usuario):
            await ctx.respond(f"❌ No puedo expulsar a {usuario.mention} porque su rol es igual o superior al mío.")
            return
        
        # Verificar permisos específicos
        if not ctx.me.guild_permissions.kick_members:
            await ctx.respond("❌ No tengo el permiso 'Expulsar miembros' en este servidor.")
            return
        
        await usuario.kick(reason=f"Kick por {ctx.author}: {razon}")
        await ctx.respond(f"✅ {usuario.mention} ha sido expulsado.\n**Razón:** {razon}")
    except discord.Forbidden:
        await ctx.respond(f"❌ No tengo permisos para expulsar a {usuario.mention}. Verifica que mi rol esté por encima del suyo.")
    except Exception as e:
        await ctx.respond(f"❌ Error: {e}")

@bot.slash_command(name="mute", description="Mutea a un usuario por tiempo determinado")
async def mute(ctx, usuario: discord.Member, minutos: int, razon: str = "No especificada"):
    try:
        # Verificar permisos del bot
        if not await verificar_permisos_bot(ctx, usuario):
            await ctx.respond(f"❌ No puedo mutear a {usuario.mention} porque su rol es igual o superior al mío.")
            return
        
        # Verificar permisos específicos
        if not ctx.me.guild_permissions.moderate_members:
            await ctx.respond("❌ No tengo el permiso 'Moderar miembros' en este servidor.")
            return
        
        if minutos <= 0 or minutos > 40320:  # Discord límite: 28 días
            await ctx.respond("❌ Los minutos deben estar entre 1 y 40320 (28 días).")
            return
        
        tiempo_fin = datetime.utcnow() + timedelta(minutes=minutos)
        await usuario.timeout(until=tiempo_fin, reason=f"Mute por {ctx.author}: {razon}")
        await ctx.respond(f"✅ {usuario.mention} ha sido muteado por {minutos} minutos.\n**Razón:** {razon}")
    except discord.Forbidden:
        await ctx.respond(f"❌ No tengo permisos para mutear a {usuario.mention}. Verifica que mi rol esté por encima del suyo.")
    except Exception as e:
        await ctx.respond(f"❌ Error al mutear: {e}")

@bot.slash_command(name="unmute", description="Quita el mute a un usuario")
async def unmute(ctx, usuario: discord.Member):
    try:
        # Verificar permisos específicos
        if not ctx.me.guild_permissions.moderate_members:
            await ctx.respond("❌ No tengo el permiso 'Moderar miembros' en este servidor.")
            return
        
        await usuario.remove_timeout(reason=f"Unmute por {ctx.author}")
        await ctx.respond(f"✅ {usuario.mention} ha sido desmuteado.")
    except discord.Forbidden:
        await ctx.respond(f"❌ No tengo permisos para desmutear a {usuario.mention}.")
    except Exception as e:
        await ctx.respond(f"❌ Error al desmutear: {e}")

@bot.slash_command(name="unban", description="Desbanea a un usuario por ID")
async def unban(ctx, user_id: str, razon: str = "No especificada"):
    try:
        # Verificar permisos específicos
        if not ctx.me.guild_permissions.ban_members:
            await ctx.respond("❌ No tengo el permiso 'Banear miembros' en este servidor.")
            return
        
        # Verificar que sea un ID válido
        try:
            user_id = int(user_id)
        except ValueError:
            await ctx.respond("❌ Debes proporcionar un ID de usuario válido.")
            return
        
        # Obtener la lista de usuarios baneados
        banned_users = [entry.user async for entry in ctx.guild.bans()]
        user_to_unban = discord.utils.get(banned_users, id=user_id)
        
        if not user_to_unban:
            await ctx.respond(f"❌ No se encontró un usuario baneado con ID: {user_id}")
            return
        
        await ctx.guild.unban(user_to_unban, reason=f"Unban por {ctx.author}: {razon}")
        await ctx.respond(f"✅ {user_to_unban.mention} ({user_to_unban.name}) ha sido desbaneado.\n**Razón:** {razon}")
    except discord.Forbidden:
        await ctx.respond("❌ No tengo permisos para desbanear usuarios.")
    except Exception as e:
        await ctx.respond(f"❌ Error al desbanear: {e}")

# -------------------- COMANDOS DE MÚSICA --------------------
@bot.slash_command(name="join", description="Une el bot al canal de voz")
async def join(ctx):
    if not ctx.author.voice:
        await ctx.respond("❌ Debes estar en un canal de voz para usar este comando.")
        return
    
    channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    
    await ctx.respond(f"✅ Conectado a {channel.mention}")

@bot.slash_command(name="leave", description="Desconecta el bot del canal de voz")
async def leave(ctx):
    if not ctx.voice_client:
        await ctx.respond("❌ No estoy conectado a ningún canal de voz.")
        return
    
    await ctx.voice_client.disconnect()
    music_queue.clear()
    await ctx.respond("✅ Desconectado del canal de voz.")

@bot.slash_command(name="play", description="Reproduce una canción de YouTube")
async def play(ctx, url: str):
    global current_player
    
    if not ctx.author.voice:
        await ctx.respond("❌ Debes estar en un canal de voz para reproducir música.")
        return
    
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
    
    await ctx.defer()
    
    try:
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        current_player = player
        
        if ctx.voice_client.is_playing():
            music_queue.append(player)
            await ctx.followup.send(f"🎵 **{player.title}** agregada a la cola (posición {len(music_queue)})")
        else:
            ctx.voice_client.play(player, after=lambda e: print(f'Error del reproductor: {e}') if e else None)
            await ctx.followup.send(f"🎵 Reproduciendo: **{player.title}**")
    except Exception as e:
        await ctx.followup.send(f"❌ Error al cargar la canción: {e}")

@bot.slash_command(name="pause", description="Pausa la reproducción")
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.respond("⏸️ Música pausada.")
    else:
        await ctx.respond("❌ No hay música reproduciéndose.")

@bot.slash_command(name="resume", description="Reanuda la reproducción")
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.respond("▶️ Música reanudada.")
    else:
        await ctx.respond("❌ La música no está pausada.")

@bot.slash_command(name="stop", description="Detiene la música y limpia la cola")
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        music_queue.clear()
        await ctx.respond("⏹️ Música detenida y cola limpiada.")
    else:
        await ctx.respond("❌ No hay música reproduciéndose.")

@bot.slash_command(name="skip", description="Salta a la siguiente canción")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        if music_queue:
            next_song = music_queue.pop(0)
            ctx.voice_client.play(next_song)
            await ctx.respond(f"⏭️ Saltando a: **{next_song.title}**")
        else:
            await ctx.respond("⏭️ Canción saltada. No hay más canciones en la cola.")
    else:
        await ctx.respond("❌ No hay música reproduciéndose.")

@bot.slash_command(name="queue", description="Muestra la cola de música")
async def queue_command(ctx):
    if not music_queue:
        await ctx.respond("📭 La cola está vacía.")
        return
    
    queue_text = "🎵 **Cola de música:**\n"
    for i, song in enumerate(music_queue, 1):
        queue_text += f"{i}. {song.title}\n"
    
    await ctx.respond(queue_text[:2000])  # Discord tiene límite de 2000 caracteres

@bot.slash_command(name="nowplaying", description="Muestra la canción actual")
async def nowplaying(ctx):
    if current_player and ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.respond(f"🎵 **Reproduciendo ahora:** {current_player.title}")
    else:
        await ctx.respond("❌ No hay música reproduciéndose.")

# -------------------- KEEP ALIVE --------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: DISCORD_TOKEN no está configurado en las variables de entorno")
