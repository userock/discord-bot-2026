import discord
from discord.ext import commands
import os
import requests

# Эти переменные бот сам возьмет из Render
TOKEN = os.getenv("DISCORD_TOKEN")
FACEIT_KEY = os.getenv("FACEIT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🚀 Бот {bot.user} запущен и видит ключ Faceit!")

@bot.command()
async def stats(ctx, nickname):
    if not FACEIT_KEY:
        await ctx.send("❌ Ошибка: FACEIT_TOKEN не найден в настройках Render!")
        return

    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    url = f"https://open.faceit.com/data/v4/players?nickname={nickname}"
    
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        data = res.json()
        # Достаем данные CS2 (статистика по эло и уровню)
        cs2 = data.get("games", {}).get("cs2", {})
        elo = cs2.get("faceit_elo", "Нет данных")
        lvl = cs2.get("skill_level", "—")
        avatar = data.get("avatar", "")
        
        embed = discord.Embed(title=f"Статистика игрока {nickname}", color=0xff5500)
        if avatar:
            embed.set_thumbnail(url=avatar)
        embed.add_field(name="ELO", value=f"📈 {elo}", inline=True)
        embed.add_field(name="Уровень", value=f"⭐ {lvl}", inline=True)
        embed.set_footer(text="Project Evolution | Faceit API")
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Игрок с ником `{nickname}` не найден на Faceit!")

bot.run(TOKEN)
