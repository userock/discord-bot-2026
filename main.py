import discord
from discord.ext import commands
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ И ПЕРЕМЕННЫЕ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") # Канал куда летят логи на проверку

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# База данных в оперативной памяти (сбросится при перезагрузке)
db = {}

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, 
            "k": 0, "a": 0, "d": 0, 
            "money": 500, "xp": 0, "lvl": 1, 
            "warns": 0, "inv": []
        }
    return db[uid]

# --- 3. ФИЛЬТР МАТА И СИСТЕМА УРОВНЕЙ ---
BAD_WORDS = ["хуй", "сука", "пидор", "гандон"]

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Авто-модерация
    if any(w in msg.content.lower() for w in BAD_WORDS):
        await msg.delete()
        return await msg.channel.send(f"🚫 {msg.author.mention}, не матерись!", delete_after=5)

    # Система опыта
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 12)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        u['money'] += 500 # Бонус за уровень
        await msg.channel.send(f"🆙 {msg.author.mention} поднял уровень до **{u['lvl']}** и получил 500 монет!")
    
    await bot.process_commands(msg)

# --- 4. ГЛАВНАЯ КОМАНДА: RESULT (БЕЗ КЛЮЧЕЙ ИИ) ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """Использование: !result [убийства] [помощь] [смерти] [win/loss] + СКРИН"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот таблицы результатов!")

    # Расчет ELO (можно менять числа под себя)
    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan:
        return await ctx.send("❌ Ошибка: Проверь HUB_ID в настройках Render!")

    # Красивый отчет для админа в HUB
    emb = discord.Embed(title="📊 НОВАЯ ЗАЯВКА НА ПРОВЕРКУ", color=0x7289da)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Результат", value=status.upper(), inline=True)
    emb.add_field(name="⚔️ Статистика", value=f"Убийства: **{k}**\nПомощь: **{a}**\nСмерти: **{d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    # Прячем данные в футер для кнопок
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Данные `{k}/{a}/{d}` отправлены в HUB! Жди подтверждения админом.")

# --- 5. ЛОГИКА АДМИН-КНОПОК ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    # Распаковка данных из футера
    try:
        data = dict(item.split(":") for item in emb.footer.text.split("|"))
    except: return

    uid = data['ID']
    u = get_u(uid)

    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K'])
        u['a'] += int(data['A'])
        u['d'] += int(data['D'])
        if int(data['ELO']) > 0: u['wins'] += 1
        else: u['losses'] += 1
        
        await reaction.message.channel.send(f"✅ Одобрено! Стата <@{uid}> обновлена. (ELO: {u['elo']})")
    
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Заявка <@{uid}> отклонена админом.")
    
    await reaction.message.delete()

# --- 6. КОМАНДЫ ЭКОНОМИКИ И ИГР ---
@bot.command()
async def work(ctx):
    """Заработать монеты"""
    u = get_u(ctx.author.id)
    gain = random.randint(100, 350)
    u['money'] += gain
    await ctx.send(f"💰 {ctx.author.mention}, ты отработал смену и получил **{gain}** монет!")

@bot.command()
async def profile(ctx, m: discord.Member = None):
    """Посмотреть профиль"""
    m = m or ctx.author
    u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"`{u['elo']}`", inline=True)
    e.add_field(name="✨ Уровень", value=f"`{u['lvl']}`", inline=True)
    e.add_field(name="💰 Баланс", value=f"`{u['money']}`", inline=True)
    e.add_field(name="⚔️ KDA", value=f"{u['k']} / {u['a']} / {u['d']}", inline=False)
    e.add_field(name="🏆 Wins/Losses", value=f"{u['wins']} / {u['losses']}", inline=False)
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    """Топ-10 по ELO"""
    sorted_db = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП-10 ИГРОКОВ СЕРВЕРА:**\n"
    for i, (uid, info) in enumerate(sorted_db, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO (Ур. {info['lvl']})\n"
    await ctx.send(res or "Топ пока пуст!")

@bot.command()
async def coin(ctx):
    """Орел или Решка"""
    res = random.choice(["Орел", "Решка"])
    await ctx.send(f"🎲 Выпало: **{res}**")

# --- 7. КОМАНДЫ МОДЕРАЦИИ ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    """Очистить чат"""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Удалено **{amount}** сообщений.", delete_after=3)

@bot.command()
@commands.has_permissions(administrator=True)
async def setelo(ctx, m: discord.Member, val: int):
    """Установить ELO игроку"""
    u = get_u(m.id)
    u['elo'] = val
    await ctx.send(f"⚙️ Игроку {m.mention} установлено `{val}` ELO.")

# --- 8. ВСПОМОГАТЕЛЬНЫЕ КОМАНДЫ ---
@bot.command()
async def ping(ctx):
    """Задержка бота"""
    await ctx.send(f"🏓 Понг! `{round(bot.latency * 1000)}ms`")

@bot.command()
async def help(ctx):
    """Меню команд"""
    e = discord.Embed(title="📜 МЕНЮ КОМАНД", color=0x5865f2)
    e.add_field(name="🎮 Игра", value="`!result K A D win/loss` (со скрином)\n`!profile`, `!top`", inline=False)
    e.add_field(name="💰 Экономика", value="`!work`, `!profile` (баланс)", inline=False)
    e.add_field(name="🛡️ Админ", value="`!clear [число]`, `!setelo @игрок [число]`", inline=False)
    e.add_field(name="✨ Разное", value="`!ping`, `!coin`")
    await ctx.send(embed=e)

# --- ЗАПУСК ---
keep_alive()
bot.run(TOKEN)
