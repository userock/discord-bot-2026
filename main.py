import discord
from discord.ext import commands, tasks
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. ВЕЧНЫЙ ОНЛАЙН ---
app = Flask('')
@app.route('/')
def home(): return "Evolution System: 24/7 Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. КОНФИГ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # Наша база данных

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, "k": 0, "a": 0, "d": 0, 
            "money": 1000, "xp": 0, "lvl": 1, "last_work": 0 # last_work в секундах
        }
    return db[uid]

# --- 3. АКТИВНОСТЬ ---
@tasks.loop(minutes=2)
async def stay_active():
    await bot.change_presence(activity=discord.Streaming(name="EVOLUTION SYSTEM", url="https://twitch.tv/discord"))

# --- 4. САМЫЙ ОФИГЕННЫЙ HELP ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="✨ ПАНЕЛЬ УПРАВЛЕНИЯ EVOLUTION",
        description="Все команды системы разделены по категориям для удобства.",
        color=0x00ffcc
    )
    
    embed.add_field(
        name="🎮 ИГРОВОЙ МОДУЛЬ",
        value="`!result K A D win/loss` — Отчет матча\n`!profile` — Твоя статистика\n`!top` — Лидеры рейтинга",
        inline=False
    )
    
    embed.add_field(
        name="💰 ЭКОНОМИЧЕСКИЙ МОДУЛЬ",
        value="`!work` — Работа (**КД 5-10 минут**)\n`!casino [ставка]` — Рискнуть деньгами\n`!shop` — Магазин ролей",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ СИСТЕМНЫЕ КОМАНДЫ",
        value="`!clear [число]` — Удалить сообщения\n`!ping` — Скорость ответа",
        inline=False
    )
    
    embed.set_footer(text=f"Система активна | {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await ctx.send(embed=embed)

# --- 5. КОМАНДА WORK С ЖЕСТКИМ КД ---
@bot.command()
async def work(ctx):
    import time
    u = get_u(ctx.author.id)
    now = int(time.time()) # Текущее время в секундах
    
    # КД хранится в u['last_work'] (когда можно будет работать снова)
    if now < u['last_work']:
        remaining = u['last_work'] - now
        minutes = remaining // 60
        seconds = remaining % 60
        return await ctx.send(f"⏳ **{ctx.author.name}**, ты еще не восстановил силы! Приходи через **{minutes}м {seconds}с**.")

    # Если КД прошло:
    gain = random.randint(500, 1500)
    u['money'] += gain
    
    # Устанавливаем время следующей работы (сейчас + от 300 до 600 секунд)
    cooldown = random.randint(300, 600)
    u['last_work'] = now + cooldown
    
    await ctx.send(f"💰 **{ctx.author.name}**, ты выполнил сложный заказ и получил **{gain}$**!\n*Следующая смена будет доступна через {cooldown // 60} мин.*")

# --- 6. РЕЗУЛЬТАТЫ ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ Ты забыл прикрепить скриншот!")
    
    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan: return await ctx.send("❌ Настрой HUB_ID в Render!")

    emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА", color=0x5865f2)
    emb.add_field(name="Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="Итог", value=status.upper(), inline=True)
    emb.add_field(name="K / A / D", value=f"**{k} / {a} / {d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Статистика отправлена в HUB. Жди подтверждения!")

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
        await reaction.message.channel.send(f"✅ Стата игрока <@{data['ID']}> успешно обновлена!")
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Результат игро <@{data['ID']}> отклонен.")
    await reaction.message.delete()

# --- 7. ПРОФИЛЬ, КАЗИНО, ОЧИСТКА ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 ПРОФИЛЬ: {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="💰 БАЛАНС", value=f"**{u['money']}$**", inline=True)
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

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Удалено **{amount}** сообщений.", delete_after=3)

# --- 8. СТАРТ ---
@bot.event
async def on_ready():
    print(f"🔥 Система Evolution в сети под именем {bot.user.name}")
    stay_active.start()

keep_alive()
bot.run(TOKEN)
