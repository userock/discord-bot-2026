import discord
from discord.ext import commands, tasks
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СИСТЕМА ANTI-SLEEP (Чтобы бот не засыпал на Render) ---
app = Flask('')

@app.route('/')
def home():
    return "Evolution System: Online & Active"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. НАСТРОЙКИ БОТА ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # База данных в памяти

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "losses": 0, "k": 0, "a": 0, "d": 0, "money": 1000, "xp": 0, "lvl": 1}
    return db[uid]

# --- 3. ЦИКЛ АВТО-АКТИВНОСТИ (Тот самый "самописец") ---
@tasks.loop(minutes=5)
async def stay_active():
    """Бот будет раз в 5 минут обновлять свой статус, чтобы Render видел активность"""
    now = datetime.datetime.now().strftime("%H:%M")
    await bot.change_presence(activity=discord.Game(name=f"Evolution | Online: {now}"))
    print(f"[{now}] Пинг активности отправлен.")

# --- 4. ОСНОВНЫЕ СОБЫТИЯ ---
@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user.name} запущен и защищен от сна!")
    stay_active.start() # Запускаем бесконечный цикл активности

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Система уровней
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 15)
    if u['xp'] >= u['lvl'] * 150:
        u['lvl'] += 1
        u['xp'] = 0
        u['money'] += 2000
        await msg.channel.send(f"🎊 {msg.author.mention} апнул **{u['lvl']} LVL**! +2000$")
    
    await bot.process_commands(msg)

# --- 5. ГЛАВНАЯ КОМАНДА RESULT (БЕЗ ОШИБОК 'GET') ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """
    Использование: !result [К] [П] [С] [win/loss] + скрин
    Пример: !result 19 2 7 win
    """
    if not ctx.message.attachments:
        return await ctx.send("❌ Ты забыл прикрепить скриншот!")

    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan:
        return await ctx.send("❌ Ошибка HUB_ID! Проверь настройки в Render.")

    emb = discord.Embed(title="⚔️ НОВАЯ ПРОВЕРКА СТАТИСТИКИ", color=0x7289da)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=status.upper(), inline=True)
    emb.add_field(name="📊 Данные ввода", value=f"K/A/D: **{k}/{a}/{d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    # Прячем данные в футер для работы кнопок
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Статы `{k}/{a}/{d}` улетели в HUB на проверку!")

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
        await reaction.message.channel.send(f"✅ Стата игрока <@{data['ID']}> подтверждена! ELO: {u['elo']}")
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Заявка игрока <@{data['ID']}> отклонена.")
    
    await reaction.message.delete()

# --- 6. ЭКОНОМИКА И ПРОФИЛЬ ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль {m.name}", color=0x00ffcc)
    e.add_field(name="📈 Рейтинг", value=f"**{u['elo']} ELO**", inline=True)
    e.add_field(name="✨ Уровень", value=f"**{u['lvl']}**", inline=True)
    e.add_field(name="💰 Баланс", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    await ctx.send(embed=e)

@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    gain = random.randint(300, 800)
    u['money'] += gain
    await ctx.send(f"⛏️ Ты заработал **{gain}$**")

@bot.command()
async def help(ctx):
    await ctx.send("📜 **Команды:**\n`!result K A D win/loss` (со скрином)\n`!profile` - стата\n`!work` - деньги")

# --- ЗАПУСК ---
keep_alive()
bot.run(TOKEN)
