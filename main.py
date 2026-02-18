import discord
from discord.ext import commands, tasks
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СЕРВЕР ДЛЯ ПОДДЕРЖКИ ОНЛАЙНА ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # База данных

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, "k": 0, "a": 0, "d": 0, 
            "money": 1000, "xp": 0, "lvl": 1, "last_work": None
        }
    return db[uid]

# --- 3. АКТИВНОСТЬ 24/7 ---
@tasks.loop(minutes=2)
async def stay_active():
    # Статус стриминга лучше всего держит бота в приоритете хостинга
    await bot.change_presence(activity=discord.Streaming(name="EVOLUTION SYSTEM", url="https://twitch.tv/discord"))

# --- 4. КРАСИВОЕ МЕНЮ HELP ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📂 ГЛАВНОЕ МЕНЮ КОМАНД",
        description="Используйте префикс `!` для управления системой.",
        color=0x2f3136
    )
    
    embed.add_field(
        name="🎮 ГЕЙМИНГ",
        value="`!result K A D win/loss` — Отправить отчет\n`!profile` — Твой прогресс\n`!top` — Лидеры рейтинга",
        inline=False
    )
    
    embed.add_field(
        name="💰 ЭКОНОМИКА",
        value="`!work` — Пойти работать (КД 5-10 мин)\n`!casino [ставка]` — Играть на деньги\n`!shop` — Магазин ролей",
        inline=False
    )
    
    embed.add_field(
        name="🛠️ СЕРВИС",
        value="`!clear [число]` — Очистка чата\n`!ping` — Скорость ответа",
        inline=False
    )
    
    embed.set_footer(text=f"Запросил: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    embed.set_image(url="https://i.imgur.com/your_cool_line_image.png") # Можно вставить ссылку на разделитель
    
    await ctx.send(embed=embed)

# --- 5. КОМАНДА РАБОТЫ С КД (5-10 МИНУТ) ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    now = datetime.datetime.now()
    
    # Проверка КД
    if u['last_work'] is not None:
        delta = now - u['last_work']
        # Случайное КД от 300 до 600 секунд (5-10 мин) сохраняется в логике
        wait_time = u.get('next_cooldown', 300) 
        
        if delta.total_seconds() < wait_time:
            remaining = int(wait_time - delta.total_seconds())
            return await ctx.send(f"⏳ {ctx.author.mention}, ты слишком устал! Отдохни еще **{remaining // 60}м {remaining % 60}с**.")

    # Логика работы
    gain = random.randint(400, 1200)
    u['money'] += gain
    u['last_work'] = now
    u['next_cooldown'] = random.randint(300, 600) # Устанавливаем КД на следующий раз
    
    await ctx.send(f"💰 **{ctx.author.name}**, ты выполнил заказ и получил **{gain}$**!\nСледующая смена доступна через {u['next_cooldown'] // 60} мин.")

# --- 6. РЕЗУЛЬТАТЫ И ПРОВЕРКА ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот таблицы!")
    
    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan: return await ctx.send("❌ Настрой HUB_ID в Render!")

    emb = discord.Embed(title="⚔️ НОВАЯ ПРОВЕРКА", color=0x7289da)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=status.upper(), inline=True)
    emb.add_field(name="📊 K / A / D", value=f"**{k} / {a} / {d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Данные `{k}/{a}/{d}` отправлены в HUB на проверку.")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    data = dict(item.split(":") for item in emb.footer.text.split("|"))
    u = get_u(data['ID'])

    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K']); u['a'] += int(data['A']); u['d'] += int(data['D'])
        if int(data['ELO']) > 0: u['wins'] += 1
        else: u['losses'] += 1
        await reaction.message.channel.send(f"✅ Результат <@{data['ID']}> подтвержден!")
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Результат <@{data['ID']}> отклонен.")
    await reaction.message.delete()

# --- 7. ПРОФИЛЬ И КАЗИНО ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 ПРОФИЛЬ: {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="✨ Уровень", value=f"**{u['lvl']}**", inline=True)
    e.add_field(name="💰 Баланс", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def casino(ctx, bet: int):
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ Недостаточно средств!")
    if random.random() > 0.5:
        u['money'] += bet
        await ctx.send(f"🎰 **ПОБЕДА!** Ты выиграл **{bet}$**. Баланс: {u['money']}$")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 **ЛУЗ!** Ты проиграл **{bet}$**. Баланс: {u['money']}$")

# --- 8. ЗАПУСК ---
@bot.event
async def on_ready():
    print(f"🚀 СИСТЕМА ОНЛАЙН: {bot.user.name}")
    stay_active.start()

keep_alive()
bot.run(TOKEN)
