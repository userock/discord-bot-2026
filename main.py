import discord
from discord.ext import commands
import os
import requests

TOKEN = os.getenv("DISCORD_TOKEN")
FACEIT_KEY = os.getenv("FACEIT_TOKEN")
HUB_ID = os.getenv("HUB_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Project Evolution Bot онлайн!")

@bot.command()
async def hub(ctx):
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    res = requests.get(f"https://open.faceit.com/data/v4/hubs/{HUB_ID}", headers=headers)
    if res.status_code == 200:
        data = res.json()
        embed = discord.Embed(title=f"Хаб: {data.get('name')}", color=0xff5500)
        embed.add_field(name="Игроков", value=data.get("players_joined_count"))
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Ошибка связи с Faceit")

@bot.command()
async def stats(ctx, nickname):
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    res = requests.get(f"https://open.faceit.com/data/v4/players?nickname={nickname}", headers=headers)
    if res.status_code == 200:
        data = res.json()
        cs2 = data.get("games", {}).get("cs2", {})
        embed = discord.Embed(title=f"Инфо: {nickname}", color=0xff5500)
        embed.add_field(name="ELO", value=cs2.get("faceit_elo", "N/A"))
        embed.add_field(name="Level", value=cs2.get("skill_level", "N/A"))
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Игрок {nickname} не найден")

bot.run(TOKEN)
