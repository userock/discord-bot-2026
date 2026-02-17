import discord
from discord.ext import commands
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System: Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# База данных в памяти
db = {}

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, 
            "k": 0, "a": 0, "d": 0, 
            "money": 500, "xp": 0, "lvl": 1, 
            "warns": 0, "last_work": None
        }
    return db[uid]

# --- 3. СОБЫТИЯ И АВТО-МОДЕРАЦИЯ ---
BAD_WORDS = ["хуй", "сука", "пидор", "еблан"]

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user.name} запущен!")
    await bot.change_presence(activity=discord.Game(name="Evolution | !help"))

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Фильтр чата
    if any(w in msg.content.lower() for w in BAD_WORDS):
        try:
            await msg.delete()
            return await msg.channel.send(f"🚫 {msg.author.mention}, следи за языком!", delete_after=5)
        except: pass

    # Система уровней
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 15)
    if u['xp'] >= u['lvl'] * 150:
        u['lvl'] += 1
        u['xp'] = 0
        u['money'] += 1000
        await msg.channel.send(f"🆙 {msg.author.mention} достиг **{u['lvl']} уровня**! +1000$")
    
    await bot.process_commands(msg)

# --- 4. СИСТЕМА РЕЗУЛЬТАТОВ (РУЧНАЯ ПРОВЕРКА) ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """Использование: !result [К] [П] [С] [win/loss] + прикрепить скрин"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Ошибка! Нужно прикрепить скриншот таблицы.")

    elo_val = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan:
        return await ctx.send("❌ Ошибка HUB_ID! Проверь настройки в Render.")

    emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА НА ПРОВЕРКУ", color=0x7289da, timestamp=datetime.datetime.now())
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Результат", value=status.upper(), inline=True)
    emb.add_field(name="📊 Ввод игрока", value=f"K/A/D: **{k}/{a}/{d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_val}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Данные `{k}/{a}/{d}` отправлены в HUB на проверку!")

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
        await reaction.message.channel.send(f"✅ Результат <@{data['ID']}> подтвержден! ELO: {u['elo']}")
    
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Результат <@{data['ID']}> отклонен.")
    
    await reaction.message.delete()

# --- 5. ЭКОНОМИКА И ИГРЫ ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    gain = random.randint(100, 400)
    u['money'] += gain
    await ctx.send(f"⛏️ {ctx.author.mention}, ты отработал смену и получил **{gain}$**!")

@bot.command()
async def casino(ctx, bet: int):
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ Недостаточно денег!")
    if random.random() > 0.55:
        u['money'] += bet
        await ctx.send(f"🎰 **ПОБЕДА!** Ты выиграл {bet}$. Теперь у тебя {u['money']}$.")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 **ПРОИГРЫШ!** Ты потерял {bet}$. Осталось {u['money']}$.")

# --- 6. ПРОФИЛЬ, ТОП И МЕНЮ ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль — {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="✨ LVL", value=f"**{u['lvl']}** ({u['xp']} XP)", inline=True)
    e.add_field(name="💰 Баланс", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.add_field(name="🏆 Wins/Losses", value=f"{u['wins']} / {u['losses']}", inline=False)
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    s = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ЛИДЕРЫ ПО ELO:**\n"
    for i, (uid, info) in enumerate(s, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Топ пуст.")

@bot.command()
async def help(ctx):
    e = discord.Embed(title="📜 Omega System Menu", color=0x5865f2)
    e.add_field(name="🎮 Игра", value="`!result K A D win/loss` (со скрином)\n`!profile`, `!top`", inline=False)
    e.add_field(name="💰 Эконом", value="`!work`, `!casino [ставка]`")
    e.add_field(name="🛠️ Разное", value="`!ping`, `!clear [число]`")
    await ctx.send(embed=e)

# --- 7. АДМИНКА ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Удалено **{amount}** сообщений.", delete_after=3)

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 `{round(bot.latency * 1000)}ms`")

keep_alive()
bot.run(TOKEN)
