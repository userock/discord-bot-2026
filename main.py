import discord
from discord.ext import commands
import os, random, datetime
from flask import Flask
from threading import Thread

# --- 1. СИСТЕМА ЖИЗНИ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Hyper-System Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("MOD_CHANNEL_ID")
LOG_ID = os.getenv("LOG_CHANNEL_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} 
BAD_WORDS = ["банворд1", "мат2", "оск3"] # Добавь сюда свои слова

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "money": 500, "xp": 0, "lvl": 1, "warns": 0}
    return db[uid]

# --- 3. АВТО-ФИЛЬТР И УРОВНИ ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Фильтр банвордов
    if any(w in msg.content.lower() for w in BAD_WORDS):
        await msg.delete()
        return await msg.channel.send(f"🚫 {msg.author.mention}, следи за языком!", delete_after=5)

    # Система XP
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 12)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        await msg.channel.send(f"🆙 {msg.author.mention} поднял уровень до **{u['lvl']}**!")

    await bot.process_commands(msg)

# --- 4. КОМАНДЫ ДЛЯ ВСЕХ (ИГРА И ИНФО) ---
@bot.command()
async def result(ctx, score: str = "0-0"):
    """1. Отправить результат: !result 13-5"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот!")
    
    try:
        w, l = map(int, score.split("-"))
        elo_val = random.randint(25, 30) if w > l else random.randint(-20, -15)
    except: elo_val = 20

    m_chan = bot.get_channel(int(MOD_ID))
    emb = discord.Embed(title="⚔️ НОВЫЙ МАТЧ", color=0x2f3136)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention)
    emb.add_field(name="📊 Счет", value=f"`{score}`")
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_val}")
    
    m = await m_chan.send(embed=emb)
    await m.add_reaction("✅"); await m.add_reaction("❌")
    await ctx.send("📡 Заявка отправлена модераторам!")

@bot.command()
async def profile(ctx, m: discord.Member = None):
    """2. Твой профиль"""
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=u['elo']); e.add_field(name="🏆 Wins", value=u['wins'])
    e.add_field(name="✨ LVL", value=u['lvl']); e.add_field(name="💰 Cash", value=u['money'])
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    """3. Лидеры сервера"""
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП-10 ХАБА:**\n"
    for i, (uid, info) in enumerate(items, 1): res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Список пуст")

@bot.command()
async def balance(ctx): """4. Баланс"""; u = get_u(ctx.author.id); await ctx.send(f"💵 Баланс: {u['money']} монет")

@bot.command()
async def work(ctx):
    """5. Работа"""; u = get_u(ctx.author.id); gain = random.randint(100, 300); u['money'] += gain
    await ctx.send(f"🔨 Ты заработал {gain} монет!")

@bot.command()
async def promo(ctx):
    """6. Промокод"""; u = get_u(ctx.author.id); u['money'] += 1000; await ctx.send("🎁 +1000 монет на счет!")

@bot.command()
async def shop(ctx): """7. Магазин"""; await ctx.send("🛒 **Магазин:**\n1. VIP (5000 монет) - `!buy 1`")

@bot.command()
async def buy(ctx, i: int):
    """8. Покупка"""; u = get_u(ctx.author.id)
    if i == 1 and u['money'] >= 5000: u['money'] -= 5000; await ctx.send("✅ VIP куплен!")
    else: await ctx.send("❌ Недостаточно средств.")

@bot.command()
async def coin(ctx): """9. Монетка"""; await ctx.send(f"🎲 {random.choice(['Орел', 'Решка'])}")

@bot.command()
async def roll(ctx): """10. Рандом"""; await ctx.send(f"🎲 Число: {random.randint(1, 100)}")

@bot.command()
async def hug(ctx, m: discord.Member): """11. Обнять"""; await ctx.send(f"🤗 {ctx.author.mention} обнял {m.mention}")

@bot.command()
async def ball(ctx, *, q): """12. Шар"""; await ctx.send(f"🔮 Ответ: {random.choice(['Да', 'Нет', 'Думаю, да'])}")

@bot.command()
async def avatar(ctx, m: discord.Member = None): """13. Ава"""; await ctx.send((m or ctx.author).display_avatar.url)

@bot.command()
async def server(ctx): """14. Инфо"""; await ctx.send(f"🏰 Участников: {ctx.guild.member_count}")

@bot.command()
async def ping(ctx): """15. Пинг"""; await ctx.send(f"🏓 `{round(bot.latency*1000)}ms`")

@bot.command()
async def rules(ctx): """16. Правила"""; await ctx.send("📜 Не спамить, не читерить, слушать админов.")

@bot.command()
async def ticket(ctx): """17. Помощь"""; await ctx.send("🆘 Пиши в канал #support для вызова админа.")

@bot.command()
async def check(ctx): """18. Статус"""; await ctx.send("🛰️ Система Evolution: **ONLINE**")

@bot.command()
async def admins(ctx): """19. Админы"""; await ctx.send("🛡️ Главный: @Owner. Модеры: @AdminTeam.")

# --- 5. КОМАНДЫ УПРАВЛЕНИЯ (ТОЛЬКО АДМИНЫ) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def give_elo(ctx, m: discord.Member, a: int):
    """20. Выдать ELO"""; u = get_u(m.id); u['elo'] += a; await ctx.send(f"✅ ELO {m.name} изменено на {a}")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, m: discord.Member, a: int):
    """21. Поставить ELO"""; u = get_u(m.id); u['elo'] = a; await ctx.send(f"⚙️ ELO {m.name} теперь {a}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, m: discord.Member): """22. Бан"""; await m.ban(); await ctx.send(f"🔨 {m.name} улетел в бан.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, a: int): """23. Очистка"""; await ctx.channel.purge(limit=a+1)

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, t): """24. От имени бота"""; await ctx.message.delete(); await ctx.send(t)

@bot.command()
async def help(ctx):
    """25. Меню команд"""
    emb = discord.Embed(title="🌌 Omega System Menu", color=0x5865f2)
    emb.add_field(name="🎮 Игра", value="`!result`, `!profile`, `!top`, `!promo`", inline=False)
    emb.add_field(name="💰 Эконом", value="`!work`, `!shop`, `!balance`, `!buy`", inline=False)
    emb.add_field(name="🛡️ Админ", value="`!give_elo`, `!set_elo`, `!ban`, `!clear`, `!say` ", inline=False)
    emb.add_field(name="✨ Разное", value="`!ping`, `!coin`, `!roll`, `!ball`, `!avatar`, `!server`, `!rules`, `!ticket`, `!check`, `!admins` ", inline=False)
    await ctx.send(embed=emb)

# --- 6. ЛОГИКА КНОПОК И ОШИБОК ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]; data = emb.footer.text.split("|")
    pid = data[0].replace("ID:", ""); elo = int(data[1].replace("ELO:", ""))
    u = get_u(pid)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo; u['wins'] += 1 if elo > 0 else 0
        await reaction.message.channel.send(f"✅ Начислено игроку <@{pid}>")
    await reaction.message.delete()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"🚫 {ctx.author.mention}, у тебя нет прав!")

keep_alive()
bot.run(TOKEN)
