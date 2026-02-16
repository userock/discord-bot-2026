import discord
from discord.ext import commands
import os
import requests

# Загрузка настроек из Render
TOKEN = os.getenv("DISCORD_TOKEN")
FACEIT_KEY = os.getenv("FACEIT_TOKEN")
HUB_ID = os.getenv("HUB_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Бот Project Evolution запущен!")
    print(f"🔗 Подключен к хабу: {HUB_ID}")

@bot.command()
async def hub(ctx):
    """Показывает общую информацию о твоем хабе"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    url = f"https://open.faceit.com/data/v4/hubs/{HUB_ID}"
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        embed = discord.Embed(title=f"🏰 Хаб: {data.get('name')}", color=0xff5500)
        embed.add_field(name="Участников", value=data.get("players_joined_count", "0"), inline=True)
        embed.add_field(name="Организатор", value=data.get("organizer_id", "Project Evolution"), inline=True)
        embed.set_footer(text="Система Project Evolution")
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Ошибка: Не удалось получить данные хаба с FACEIT.")

@bot.command()
async def top(ctx):
    """Выводит топ-10 игроков твоего хаба по PTS"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    # Запрос лидерборда
    url = f"https://open.faceit.com/data/v4/leaderboards/hubs/{HUB_ID}/general?offset=0&limit=10"
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        items = data.get("items", [])
        
        if not items:
            return await ctx.send("📈 В хабе пока нет сыгранных матчей или активного рейтинга.")

        msg = "🏆 **ТОП-10 ИГРОКОВ PROJECT EVOLUTION:**\n"
        for i, player in enumerate(items, 1):
            nickname = player.get("player", {}).get("nickname", "Unknown")
            points = player.get("points", 0)
            msg += f"{i}. **{nickname}** — {points} PTS\n"
        
        await ctx.send(msg)
    else:
        await ctx.send("❌ Ошибка: Не удалось загрузить таблицу лидеров.")

@bot.command()
async def stats(ctx, nickname):
    """Показывает общее ELO и уровень игрока на FACEIT"""
    headers = {"Authorization": f"Bearer {FACEIT_KEY}"}
    url = f"https://open.faceit.com/data/v4/players?nickname={nickname}"
    
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        cs2 = data.get("games", {}).get("cs2", {}) # Статистика CS2/Общая
        elo = cs2.get("faceit_elo", "Нет данных")
        lvl = cs2.get("skill_level", "—")
        
        embed = discord.Embed(title=f"👤 Профиль: {nickname}", color=0xff5500)
        embed.set_thumbnail(url=data.get("avatar", ""))
        embed.add_field(name="FACEIT ELO", value=f"📈 {elo}", inline=True)
        embed.add_field(name="Уровень", value=f"⭐ {lvl}", inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ Игрок `{nickname}` не найден.")

@bot.command()
async def commands_list(ctx):
    """Список всех доступных команд"""
    msg = (
        "📜 **КОМАНДЫ БОТА:**\n"
        "`!hub` — Инфо о твоем хабе\n"
        "`!top` — Таблица лидеров хаба\n"
        "`!stats [ник]` — Посмотреть ELO игрока\n"
    )
    await ctx.send(msg)

bot.run(TOKEN)
