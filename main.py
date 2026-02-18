import discord
from discord.ext import commands, tasks
import os, random, datetime, time
from flask import Flask
from threading import Thread

# --- [ 1. АНТИ-СОН СЕРВЕР ] ---
app = Flask('')
@app.route('/')
def home(): return "Evolution System: v4.0 Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- [ 2. НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ ] ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # База данных (хранится, пока бот запущен)

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, "k": 0, "a": 0, "d": 0, 
            "money": 1000, "lvl": 1, "last_work": 0
        }
    return db[uid]

def get_rank(elo):
    if elo < 1100: return "🌑 Новичок"
    if elo < 1300: return "🌕 Боец"
    if elo < 1600: return "💎 Мастер"
    if elo < 2000: return "🔥 Элита"
    return "👑 ЛЕГЕНДА"

# --- [ 3. ЦИКЛ ОНЛАЙНА 24/7 ] ---
@tasks.loop(minutes=2)
async def stay_active():
    # Меняем статус, чтобы Render видел, что мы не зависли
    status_list = ["!help | Evolution", f"Admin: {len(db)} users", "Watching ELO"]
    await bot.change_presence(activity=discord.Streaming(name=random.choice(status_list), url="https://twitch.tv/discord"))

# --- [ 4. САМЫЙ КРАСИВЫЙ HELP В МИРЕ ] ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="💠 ЦЕНТР УПРАВЛЕНИЯ EVOLUTION",
        description="Добро пожаловать. Все модули системы работают в штатном режиме.\n━━━━━━━━━━━━━━━━━━━━",
        color=0x2b2d31
    )
    
    embed.add_field(
        name="⚔️ ИГРОВОЙ МОДУЛЬ", 
        value="> `!result` • Отчет матча + скрин\n> `!profile` • Твоя стата и ранг\n> `!top` • Таблица лидеров", 
        inline=False
    )
    
    embed.add_field(
        name="💰 ЭКОНОМИЧЕСКИЙ МОДУЛЬ", 
        value="> `!work` • Работа (**КД 5-10м**)\n> `!casino` • Игра на удачу\n> `!shop` • Магазин ролей", 
        inline=False
    )
    
    embed.add_field(
        name="🛠️ СЕРВИСНЫЕ КОМАНДЫ", 
        value="> `!clear` • Очистка чата\n> `!ping` • Проверка связи", 
        inline=False
    )
    
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text=f"Система Evolution v4.0 • Запросил {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

# --- [ 5. КОМАНДА WORK С КРАСИВЫМ КД ] ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    now = int(time.time())
    
    if now < u['last_work']:
        rem = u['last_work'] - now
        minutes = rem // 60
        seconds = rem % 60
        # Рисуем полоску загрузки
        bar_len = 10
        filled = bar_len - (rem // 60 if rem // 60 < bar_len else bar_len)
        bar = "🟦" * filled + "⬜" * (bar_len - filled)
        
        return await ctx.send(f"⏳ **Перезарядка:** {bar}\nДоступно через: **{minutes}м {seconds}с**")

    # Начисляем деньги
    gain = random.randint(500, 1500)
    u['money'] += gain
    
    # КД от 5 до 10 минут
    cooldown = random.randint(300, 600)
    u['last_work'] = now + cooldown
    
    emb = discord.Embed(description=f"✅ {ctx.author.mention}, ты успешно выполнил работу!\nНаграда: **{gain}$**", color=0x43b581)
    await ctx.send(embed=emb)

# --- [ 6. СИСТЕМА ПРОВЕРКИ МАТЧЕЙ ] ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, res: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ Ошибка! Нужно прикрепить скриншот таблицы.")
    
    elo_change = 25 if res.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    if not m_chan: return await ctx.send("❌ Ошибка: Канал HUB не найден (проверь HUB_ID).")

    emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА НА ПРОВЕРКУ", color=0x5865f2)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=res.upper(), inline=True)
    emb.add_field(name="📊 Статистика", value=f"`K: {k} | A: {a} | D: {d}`", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.message.add_reaction("📡")

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
        await reaction.message.channel.send(f"✅ Результат <@{data['ID']}> подтвержден админом!")
    
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Результат <@{data['ID']}> отклонен.")
    
    await reaction.message.delete()

# --- [ 7. ПРОФИЛЬ И КАЗИНО ] ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    rank = get_rank(u['elo'])
    
    e = discord.Embed(title=f"👤 ПРОФИЛЬ: {m.name}", color=0x00ffcc)
    e.add_field(name="🏆 Текущий Ранг", value=f"**{rank}**", inline=True)
    e.add_field(name="📈 Рейтинг ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="💰 Кошелек", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ Статистика K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def casino(ctx, bet: int):
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ У тебя недостаточно денег!")
    
    if random.random() > 0.55: # Шанс победы 45%
        u['money'] += bet
        await ctx.send(f"🎰 **ПОБЕДА!** Ты выиграл **{bet}$**. Твой баланс: {u['money']}$")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 **ПРОИГРЫШ!** Ты потерял **{bet}$**. Твой баланс: {u['money']}$")

# --- [ 8. АДМИН КОМАНДЫ ] ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Очищено сообщений: {amount}", delete_after=3)

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Понг! Задержка: `{round(bot.latency * 1000)}ms`")

# --- [ 9. ЗАПУСК ] ---
@bot.event
async def on_ready():
    print(f"[{datetime.datetime.now()}] СИСТЕМА EVOLUTION ЗАПУЩЕНА")
    stay_active.start()

keep_alive()
bot.run(TOKEN)
