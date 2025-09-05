import discord
from discord.ext import tasks, commands
import itertools
import asyncio
import os

# ⚠️ Token desde variable de entorno permanente
TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = 1170123435691749517
ROLE_ID = 1413273099268522036

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Gradiente seguro: 4 pasos
color_steps = [
    0xFFFFFF,  # blanco
    0xFFCCCC,  # rojo muy claro
    0xFF6666,  # rojo medio
    0x990000   # rojo oscuro
]

color_cycle = itertools.cycle(color_steps)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    animate_role.start()

@tasks.loop(seconds=120)  # ⏱ Intervalo largo para que CMD y Discord no pierdan pasos
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
    await change_role(role, new_color)

async def change_role(role, color_value):
    try:
        await role.edit(color=discord.Color(color_value))
        await asyncio.sleep(3)  # espera que CMD registre
        print(f"Rol '{role.name}' color aplicado: #{color_value:06X}")
    except discord.Forbidden:
        print("El bot no tiene permisos para cambiar el color del rol")
    except discord.HTTPException as e:
        print(f"Error HTTP: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

bot.run(TOKEN)
