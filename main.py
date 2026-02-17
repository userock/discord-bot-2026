import discord
from discord.ext import commands
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") # Канал HUB для проверки

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# База данных (в оперативной памяти)
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

# --- 3. СОБЫТИЯ И АВТО-МОДЕРАЦИЯ ---
BAD_WORDS = ["хуй", "сука", "пидор", "еблан"]

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user.name} успешно запущен!")
    await bot.change_presence(activity=discord.Game(name="Evolution | !help"))

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Фильтр чата
    if any(w in msg.content.lower() for w in BAD_WORDS):
        try:
            await msg.delete()
            return await msg.channel.send(f"🚫 {msg.author.mention}, не выражайся!", delete_after=5)
        except: pass

    # Система опыта за сообщения
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 15)
    if u['xp'] >= u['lvl'] * 150:
        u['lvl'] += 1
        u['xp'] = 0
        u['money'] += 1000
        await msg.channel.send(f"🎊 {msg.author.mention} апнул **{u['lvl']} уровень**! Награда: 1000$")
    
    await bot.process_commands(msg)

# --- 4. СИСТЕМА РЕЗУЛЬТАТОВ (БЕЗ КЛЮЧЕЙ ИИ) ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """
    Отправка результата: !result [К] [П] [С] [win/loss] + прикрепить скриншот
    Пример: !result 19 2 7 win
    """
    if not ctx.message.attachments:
        return await ctx.send("❌ Ошибка! Ты забыл прикрепить скриншот таблицы.")

    # Расчет изменения рейтинга
    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan:
        return await ctx.send("❌ Ошибка: Неверный HUB_ID в Render!")

    emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА НА ПРОВЕРКУ", color=0x7289da, timestamp=datetime.datetime.now())
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Результат", value=status.upper(), inline=True)
    emb.add_field(name="📊 Данные игрока", value=f"K/A/D: **{k}/{a}/{d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    # Прячем технические данные в футер для работы кнопок
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Твои статы `{k}/{a}/{d}` отправлены в HUB! Админы сверят их со скрином.")

# --- 5. ОБРАБОТКА ПОДТВЕРЖДЕНИЙ АДМИНАМИ ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return # Проверка прав админа
    
    emb = reaction.message.embeds[0]
    try:
        data = dict(item.split(":") for item in emb.footer.text.split("|"))
    except: return

    u = get_u(data['ID'])

    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K'])
        u['a'] += int(data['A'])
        u['d'] += int(data['D'])
        if int(data['ELO']) > 0: u['wins'] += 1
        else: u['losses'] += 1
        
        await reaction.message.channel.send(f"✅ Результат для <@{data['ID']}> подтвержден! ELO теперь: {u['elo']}")
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Результат для <@{data['ID']}> отклонен.")
    
    await reaction.message.delete()

# --- 6. ЭКОНОМИКА, КАЗИНО И ПРОФИЛЬ ---
@bot.command()
async def work(ctx):
    """Заработок денег"""
    u = get_u(ctx.author.id)
    gain = random.randint(200, 500)
    u['money'] += gain
    await ctx.send(f"⛏️ {ctx.author.mention}, ты отработал смену и заработал **{gain}$**!")

@bot.command()
async def casino(ctx, bet: int):
    """Азартная игра 50/50"""
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ У тебя нет столько денег!")
    
    if random.random() > 0.5:
        u['money'] += bet
        await ctx.send(f"🎰 **ПОБЕДА!** Ты выиграл **{bet}$**. Твой баланс: {u['money']}$")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 **ПРОИГРЫШ!** Ты потерял **{bet}$**. Твой баланс: {u['money']}$")

@bot.command()
async def profile(ctx, m: discord.Member = None):
    """Посмотреть полную статистику"""
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль — {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO рейтинг", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="✨ Уровень", value=f"**{u['lvl']}** ({u['xp']} XP)", inline=True)
    e.add_field(name="💰 Кошелек", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ Суммарный K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.add_field(name="📊 Матчи", value=f"Побед: `{u['wins']}` | Поражений: `{u['losses']}`", inline=False)
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    """Топ-10 игроков сервера"""
    s = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ЛИДЕРЫ СЕРВЕРА ПО ELO:**\n"
    for i, (uid, info) in enumerate(s, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO (LVL {info['lvl']})\n"
    await ctx.send(res or "Топ пока пуст.")

# --- 7. АДМИН-КОМАНДЫ ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setelo(ctx, m: discord.Member, val: int):
    """Установить ELO вручную"""
    get_u(m.id)['elo'] = val
    await ctx.send(f"⚙️ Рейтинг {m.mention} изменен на `{val}`.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    """Удаление сообщений"""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Очищено **{amount}** сообщений.", delete_after=3)

# --- 8. ПОМОЩЬ И ИНФО ---
@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Понг! `{round(bot.latency * 1000)}ms`")

@bot.command()
async def help(ctx):
    e = discord.Embed(title="📜 Список всех команд", color=0x5865f2)
    e.add_field(name="🎮 Игровые", value="`!result K A D win/loss` — отправить статсу\n`!profile` — твой профиль\n`!top` — топ игроков", inline=False)
    e.add_field(name="💰 Экономика", value="`!work` — заработать\n`!casino [ставка]` — рискнуть", inline=False)
    e.add_field(name="🛠️ Админские", value="`!clear [число]` — очистка\n`!setelo @игрок [число]` — выдать рейтинг", inline=False)
    await ctx.send(embed=e)

# --- ЗАПУСК ---
keep_alive()
bot.run(TOKEN)
