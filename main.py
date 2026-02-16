import discord
from discord.ext import commands
import os
import requests

# Бот берет эти данные из раздела Environment в Render
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
    """Информация о твоем хабе"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    url = f"https://open.faceit.com/data/v4/hubs/{HUB_ID}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        name = data.get("name", "Project Evolution")
        players = data.get("players_joined_count", "0")
        await ctx.send(f"🏰 **Хаб:** {name}\n👥 **Игроков:** {players}")
    else:
        await ctx.send("❌ Ошибка: Неверный HUB_ID или FACEIT_TOKEN в Render.")

@bot.command()
async def top(ctx):
    """Топ-10 игроков твоего хаба"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    url = f"https://open.faceit.com/data/v4/leaderboards/hubs/{HUB_ID}/general?limit=10"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        items = res.json().get("items", [])
        if not items:
            return await ctx.send("📈 В хабе пока нет сыгранных матчей.")
        msg = "🏆 **ТОП-10 ИГРОКОВ ХАБА:**\n"
        for i, p in enumerate(items, 1):
            msg += f"{i}. **{p['player']['nickname']}** — {p['points']} PTS\n"
        await ctx.send(msg)
    else:
        await ctx.send("❌ Ошибка: Не удалось загрузить таблицу лидеров.")

@bot.command()
async def stats(ctx, nickname):
    """Статистика любого игрока на FACEIT"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    res = requests.get(f"https://open.faceit.com/data/v4/players?nickname={nickname}", headers=headers)
    if res.status_code == 200:
        data = res.json()
        cs2 = data.get("games", {}).get("cs2", {})
        elo = cs2.get("faceit_elo", "N/A")
        lvl = cs2.get("skill_level", "N/A")
        await ctx.send(f"👤 **Игрок:** {nickname}\n📈 **ELO:** {elo}\n⭐ **Level:** {lvl}")
    else:
        await ctx.send(f"❌ Игрок `{nickname}` не найден.")

@bot.command()
async def help_me(ctx):
    """Список всех команд"""
    msg = (
        "📜 **КОМАНДЫ БОТА:**\n"
        "`!hub` — Инфо о хабе\n"
        "`!top` — Лидерборд проекта\n"
        "`!stats [ник]` — Узнать ELO игрока\n"
    )
    await ctx.send(msg)

bot.run(TOKEN)
