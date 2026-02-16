import discord
from discord.ext import commands
import os
import requests

# Бот сам возьмет эти данные из Render
TOKEN = os.getenv("DISCORD_TOKEN")
FACEIT_KEY = os.getenv("FACEIT_TOKEN")
HUB_ID = os.getenv("HUB_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} подключен к хабу Project Evolution!")

@bot.command()
async def hub(ctx):
    if not HUB_ID or not FACEIT_KEY:
        await ctx.send("❌ Настройки в Render не завершены!")
        return

    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    # Запрос данных именно твоего хаба
    url = f"https://open.faceit.com/data/v4/hubs/{HUB_ID}"
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        name = data.get("name", "Project Evolution")
        players = data.get("players_joined_count", "0")
        
        embed = discord.Embed(title=f"Статистика хаба {name}", color=0xff5500)
        embed.add_field(name="Всего игроков", value=f"👥 {players}", inline=True)
        embed.set_footer(text="Данные считаны с Project Evolution")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Ошибка: Бот не смог получить данные с FACEIT.")

bot.run(TOKEN)
