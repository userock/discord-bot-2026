import discord
from discord.ext import commands
import os
import requests

# Бот тянет эти данные из Environment в Render
TOKEN = os.getenv("DISCORD_TOKEN")
FACEIT_KEY = os.getenv("FACEIT_TOKEN")
HUB_ID = os.getenv("HUB_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен и готов к работе!")

@bot.command()
async def hub(ctx):
    """Показать инфо о хабе"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    url = f"https://open.faceit.com/data/v4/hubs/{HUB_ID}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        await ctx.send(f"🏰 **Хаб:** {data.get('name')}\n👥 **Игроков:** {data.get('players_joined_count')}")
    else:
        await ctx.send("❌ Ошибка: Бот не видит хаб. Проверь настройки в Render.")

@bot.command()
async def top(ctx):
    """Топ-10 игроков хаба"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    # Запрос лидерборда
    url = f"https://open.faceit.com/data/v4/leaderboards/hubs/{HUB_ID}/general?limit=10"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        items = res.json().get("items", [])
        if not items:
            return await ctx.send("📉 Рейтинг пока пуст.")
        msg = "🏆 **ТОП-10 ИГРОКОВ ХАБА:**\n"
        for i, p in enumerate(items, 1):
            msg += f"{i}. **{p['player']['nickname']}** — {p['points']} PTS\n"
        await ctx.send(msg)
    else:
        await ctx.send("❌ Не удалось загрузить топ.")

@bot.command()
async def stats(ctx, nickname):
    """Проверить ELO любого игрока"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    res = requests.get(f"https://open.faceit.com/data/v4/players?nickname={nickname}", headers=headers)
    if res.status_code == 200:
        data = res.json()
        cs2 = data.get("games", {}).get("cs2", {})
        await ctx.send(f"👤 **{nickname}**\n⭐ Level: {cs2.get('skill_level', 'N/A')}\n📈 ELO: {cs2.get('faceit_elo', 'N/A')}")
    else:
        await ctx.send(f"❌ Игрок `{nickname}` не найден.")

bot.run(TOKEN)
