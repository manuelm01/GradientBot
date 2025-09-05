import discord
from discord import app_commands
from discord.ext import commands, tasks
import itertools
import asyncio
import os
from flask import Flask
from threading import Thread

# ⚠️ Token desde variable de entorno
TOKEN = os.environ.get("DISCORD_TOKEN")

# ---------------- Configuración ----------------
GUILD_ID = 1170123435691749517   # Tu servidor
ROLE_ID = 1413273099268522036    # Rol a animar

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# ---------------- Gradiente ----------------
color_steps = [0xFFFFFF, 0xFFCCCC, 0xFF6666, 0x990000]  # blanco → rojo oscuro
color_cycle = itertools.cycle(color_steps)

# ---------------- Eventos ----------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Error sincronizando comandos: {e}")
    animate_role.start()

# ---------------- Slash Command ----------------
@bot.tree.command(
    name="ping",
    description="Comprueba si el bot está activo",
    guild=discord.Object(id=GUILD_ID)
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"¡Estoy vivo, {interaction.user.mention}! 😎")

# ---------------- Animación del rol ----------------
@tasks.loop(seconds=120)  # Intervalo seguro (2 minutos)
async def animate_role():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("No se encontró el servidor")
        return
    role = guild.get_role(ROLE_ID)
    if not role:
        print("No se encontró el rol")
        return
    new_color = next(color_cycle)
    try:
        await role.edit(color=discord.Color(new_color))
        print(f"Rol '{role.name}' color aplicado: #{new_color:06X}")
    except discord.Forbidden:
        print("No tengo permisos para cambiar el color del rol")
    except discord.HTTPException as e:
        print(f"Error HTTP: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

# ---------------- Keep Alive para Replit ----------------
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
bot.run(TOKEN)
