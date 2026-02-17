import discord
from discord.ext import commands
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СЕРВЕР ДЛЯ RENDER (ЧТОБЫ НЕ СПАЛ) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") # Канал HUB из твоих настроек Render

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# База данных (в памяти)
db = {}

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, 
            "k": 0, "a": 0, "d": 0, 
            "money": 500, "xp": 0, "lvl": 1, 
            "warns": 0, "inv": [], "daily": None
        }
    return db[uid]

# --- 3. СОБЫТИЯ И АВТО-МОДЕРАЦИЯ ---
BAD_WORDS = ["хуй", "сука", "пидор", "гандон", "еблан"]

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user.name} запущен и готов к работе!")
    await bot.change_presence(activity=discord.Game(name="Evolution Hub | !help"))

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Фильтр чата
    if any(w in msg.content.lower() for w in BAD_WORDS):
        try:
            await msg.delete()
            return await msg.channel.send(f"🚫 {msg.author.mention}, соблюдайте правила приличия!", delete_after=5)
        except: pass

    # Начисление опыта за сообщения
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 15)
    xp_needed = u['lvl'] * 120
    if u['xp'] >= xp_needed:
        u['lvl'] += 1
        u['xp'] = 0
        u['money'] += 1000
        await msg.channel.send(f"🎊 {msg.author.mention} достиг **{u['lvl']} уровня**! Награда: 1000$")
    
    await bot.process_commands(msg)

# --- 4. СИСТЕМА РЕЗУЛЬТАТОВ (БЕЗ КЛЮЧЕЙ ИИ) ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """Отправка результата: !result [К] [П] [С] [win/loss] + скрин"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Ошибка! Нужно прикрепить скриншот таблицы.")

    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan:
        return await ctx.send("❌ Ошибка! Проверь HUB_ID в настройках Render.")

    emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА НА ПРОВЕРКУ", color=0x7289da, timestamp=datetime.datetime.now())
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=status.upper(), inline=True)
    emb.add_field(name="📊 Статистика ввода", value=f"K/A/D: **{k}/{a}/{d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Данные `{k}/{a}/{d}` отправлены. Админы проверят скриншот в HUB!")

# --- 5. ОБРАБОТКА ПОДТВЕРЖДЕНИЙ ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    try:
        data = dict(item.split(":") for item in emb.footer.text.split("|"))
    except: return

    u = get_u(data['ID'])

    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K']); u['a'] += int(data['A']); u['d'] += int(data['D'])
        if int(data['ELO']) > 0: u['wins'] += 1
        else: u['losses'] += 1
        
        await reaction.message.channel.send(f"✅ Результат для <@{data['ID']}> подтвержден! ELO: {u['elo']}")
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Результат для <@{data['ID']}> отклонен.")
    
    await reaction.message.delete()

# --- 6. ЭКОНОМИКА И ИГРЫ ---
@bot.command()
async def work(ctx):
    """Работа (раз в 10 минут)"""
    u = get_u(ctx.author.id)
    gain = random.randint(150, 400)
    u['money'] += gain
    await ctx.send(f"⛏️ {ctx.author.mention}, ты отработал смену и заработал **{gain}$**")

@bot.command()
async def daily(ctx):
    """Ежедневная награда"""
    u = get_u(ctx.author.id)
    u['money'] += 2000
    await ctx.send(f"🎁 {ctx.author.mention}, ты получил ежедневный бонус **2000$**!")

@bot.command()
async def casino(ctx, bet: int):
    """Казино (50/50)"""
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ Недостаточно средств!")
    
    if random.random() > 0.5:
        u['money'] += bet
        await ctx.send(f"🎰 Победа! Ты выиграл **{bet}$**. Теперь у тебя {u['money']}$")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 Проигрыш! Ты потерял **{bet}$**. Осталось {u['money']}$")

# --- 7. ПРОФИЛЬ, ТОП И ИНФО ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    """Посмотреть профиль"""
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль — {m.name}", color=0x00ffcc)
    e.add_field(name="📈 Рейтинг (ELO)", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="✨ Уровень", value=f"**{u['lvl']}** ({u['xp']} XP)", inline=True)
    e.add_field(name="💰 Кошелек", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ Статистика K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.add_field(name="📊 Матчи", value=f"Побед: `{u['wins']}` | Поражений: `{u['losses']}`", inline=False)
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    """Топ-10 по ELO"""
    s = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ЛИДЕРЫ СЕРВЕРА:**\n"
    for i, (uid, info) in enumerate(s, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO (LVL {info['lvl']})\n"
    await ctx.send(res or "Список пуст.")

# --- 8. МОДЕРАЦИЯ И АДМИНКА ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    """Очистка чата"""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Удалено **{amount}** сообщений.", delete_after=3)

@bot.command()
@commands.has_permissions(administrator=True)
async def give_money(ctx, m: discord.Member, amount: int):
    """Выдать деньги игроку"""
    get_u(m.id)['money'] += amount
    await ctx.send(f"✅ Игроку {m.mention} начислено **{amount}$**")

# --- 9. ВСПОМОГАТЕЛЬНЫЕ ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Понг! Задержка: `{round(bot.latency * 1000)}ms`")

@bot.command()
async def help(ctx):
    e = discord.Embed(title="📜 Список команд бота", color=0x5865f2)
    e.add_field(name="🎮 Гейминг", value="`!result K A D win/loss` — отправить статсу\n`!profile` — твой профиль\n`!top` — лидеры", inline=False)
    e.add_field(name="💰 Экономика", value="`!work`, `!daily`, `!casino [ставка]`")
    e.add_field(name="🛠️ Сервис", value="`!ping`, `!clear [число]`")
    await ctx.send(embed=e)

# --- ЗАПУСК ---
keep_alive()
bot.run(TOKEN)
