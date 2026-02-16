import discord
from discord.ext import commands
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. ВЕБ-СЕРВЕР ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_CHANNEL_ID = os.getenv("MOD_CHANNEL_ID")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # База данных в памяти
BAD_WORDS = ["банворд1", "оск2", "мат3"] # Добавь свои слова сюда

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "money": 0, "xp": 0, "lvl": 1, "warns": 0}
    return db[uid]

# --- 3. ФИЛЬТР МАТА И СИСТЕМА УРОВНЕЙ ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Анти-мат
    if any(w in msg.content.lower() for w in BAD_WORDS):
        await msg.delete()
        return await msg.channel.send(f"🚫 {msg.author.mention}, не используй банворды!", delete_after=5)

    # Опыт (XP)
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 10)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        await msg.channel.send(f"🆙 {msg.author.mention} достиг **{u['lvl']} уровня**!")

    await bot.process_commands(msg)

# --- 4. КАТЕГОРИЯ: ИГРА И РЕЗУЛЬТАТЫ (ДЛЯ ВСЕХ) ---
@bot.command()
async def result(ctx, score: str = "0-0"):
    """1. Отправить скрин: !result 13-5"""
    if not ctx.message.attachments: return await ctx.send("❌ Прикрепи скриншот!")
    try:
        w, l = map(int, score.split("-"))
        elo = random.randint(25, 30) if w > l else random.randint(-20, -15)
    except: elo = 20
    m_chan = bot.get_channel(int(MOD_CHANNEL_ID))
    emb = discord.Embed(title="⚔️ НОВЫЙ МАТЧ", color=0x2f3136)
    emb.add_field(name="Игрок", value=ctx.author.mention)
    emb.add_field(name="Счет", value=score)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo}")
    msg = await m_chan.send(embed=emb); await msg.add_reaction("✅"); await msg.add_reaction("❌")
    await ctx.send("📡 Результат отправлен на проверку!")

@bot.command()
async def profile(ctx, m: discord.Member = None):
    """2. Просмотр статистики"""
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль: {m.name}", color=0x00ff00)
    e.add_field(name="ELO", value=u['elo']); e.add_field(name="LVL", value=u['lvl'])
    e.add_field(name="Победы", value=u['wins']); e.add_field(name="Монеты", value=u['money'])
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    """3. Список лидеров"""
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП-10 ИГРОКОВ:**\n"
    for i, (uid, info) in enumerate(items, 1): res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Пусто")

# --- 5. КАТЕГОРИЯ: АДМИН-УПРАВЛЕНИЕ (ТОЛЬКО АДМИНЫ) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def give_elo(ctx, m: discord.Member, a: int):
    """4. Выдать ЭЛО вручную"""
    u = get_u(m.id); u['elo'] += a
    await ctx.send(f"✅ {m.mention} начислено {a} ELO. Итого: {u['elo']}")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, m: discord.Member, a: int):
    """5. Установить точное ЭЛО"""
    u = get_u(m.id); u['elo'] = a
    await ctx.send(f"⚙️ ELO {m.mention} установлено на {a}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, m: discord.Member):
    """6. Бан игрока"""
    await m.ban(); await ctx.send(f"🔨 {m.name} забанен!")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, a: int):
    """7. Очистить чат"""
    await ctx.channel.purge(limit=a+1)

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, t):
    """8. Сказать от имени бота"""
    await ctx.message.delete(); await ctx.send(t)

@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, m: discord.Member):
    """9. Выдать варн"""
    u = get_u(m.id); u['warns'] += 1
    await ctx.send(f"⚠️ {m.mention} получил варн! ({u['warns']}/3)")

# --- 6. КАТЕГОРИЯ: ЭКОНОМИКА И МАГАЗИН (ДЛЯ ВСЕХ) ---
@bot.command()
async def work(ctx):
    """10. Заработать монеты"""
    u = get_u(ctx.author.id); m = random.randint(50, 150); u['money'] += m
    await ctx.send(f"💰 Ты заработал {m} монет!")

@bot.command()
async def shop(ctx):
    """11. Магазин"""
    await ctx.send("🛒 **Магазин:**\n1. Роль VIP (5000 монет) - `!buy 1`")

@bot.command()
async def buy(ctx, i: int):
    """12. Купить товар"""
    u = get_u(ctx.author.id)
    if i == 1 and u['money'] >= 5000: u['money'] -= 5000; await ctx.send("✅ Куплено!")
    else: await ctx.send("❌ Нет денег")

@bot.command()
async def balance(ctx):
    """13. Твой баланс"""
    u = get_u(ctx.author.id); await ctx.send(f"💵 Монеты: {u['money']}")

@bot.command()
async def promo(ctx):
    """14. Промокод для новичков"""
    u = get_u(ctx.author.id); u['money'] += 1000; await ctx.send("🎁 +1000 монет!")

# --- 7. КАТЕГОРИЯ: ФАН И ИНФО (ДЛЯ ВСЕХ) ---
@bot.command()
async def coin(ctx): """15. Монетка"""; await ctx.send(f"🎲 {random.choice(['Орел', 'Решка'])}")
@bot.command()
async def roll(ctx): """16. Рандом"""; await ctx.send(f"🎲 {random.randint(1, 100)}")
@bot.command()
async def hug(ctx, m: discord.Member): """17. Обнять"""; await ctx.send(f"🤗 Обнял {m.mention}")
@bot.command()
async def ball(ctx, *, q): """18. Шар судьбы"""; await ctx.send(f"🔮 {random.choice(['Да', 'Нет'])}")
@bot.command()
async def avatar(ctx, m: discord.Member = None): """19. Аватар"""; await ctx.send((m or ctx.author).display_avatar.url)
@bot.command()
async def ping(ctx): """20. Пинг"""; await ctx.send(f"🏓 `{round(bot.latency*1000)}ms`")
@bot.command()
async def server(ctx): """21. Инфо сервера"""; await ctx.send(f"🏰 Участников: {ctx.guild.member_count}")
@bot.command()
async def rules(ctx): """22. Правила"""; await ctx.send("📜 1. Не спамить. 2. Не абузить.")
@bot.command()
async def check(ctx): """23. Статус"""; await ctx.send("🛰️ Система: **ACTIVE**")
@bot.command()
async def admins(ctx): """24. Список админов"""; await ctx.send("🛡️ Обратись к @Owner по вопросам.")

@bot.command()
async def help(ctx):
    """25. Меню команд"""
    e = discord.Embed(title="📖 Меню Evolution", color=0x5865f2)
    e.add_field(name="🎮 Игра", value="`!result`, `!profile`, `!top`", inline=False)
    e.add_field(name="⚙️ Админ", value="`!give_elo`, `!set_elo`, `!ban`, `!clear`, `!say`, `!warn`", inline=False)
    e.add_field(name="💰 Экономика", value="`!work`, `!shop`, `!balance`, `!buy`, `!promo` ", inline=False)
    e.add_field(name="✨ Разное", value="`!ping`, `!coin`, `!roll`, `!ball`, `!hug`, `!avatar`, `!server`, `!rules`, `!check`, `!admins` ", inline=False)
    await ctx.send(embed=e)

# --- 8. ОБРАБОТКА РЕАКЦИЙ И ОШИБОК ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_CHANNEL_ID: return
    emb = reaction.message.embeds[0]; data = emb.footer.text.split("|")
    pid = int(data[0].replace("ID:", "")); elo = int(data[1].replace("ELO:", ""))
    u = get_u(pid)
    if str(reaction.emoji) == "✅":
        u['elo'] += elo; u['wins'] += 1 if elo > 0 else 0
        await reaction.message.channel.send(f"✅ Одобрено для <@{pid}>")
    await reaction.message.delete()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"🚫 {ctx.author.mention}, у тебя нет прав!")

keep_alive()
bot.run(TOKEN)
