import discord
from discord.ext import commands
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СИСТЕМА АНТИ-СОН ---
app = Flask('')
@app.route('/')
def home(): return "Evolution System: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# База данных
db = {}

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, 
            "k": 0, "a": 0, "d": 0, 
            "money": 1000, "xp": 0, "lvl": 1, 
            "inv": []
        }
    return db[uid]

# --- 3. АВТО-МОДЕРКА И УРОВНИ ---
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
        await msg.channel.send(f"🎊 {msg.author.mention} поднял **{u['lvl']} уровень**! Лови бонус **2000$**")
    
    await bot.process_commands(msg)

# --- 4. КОМАНДА RESULT (БЕЗ ОШИБОК ИИ) ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, res: str = "win"):
    """Использование: !result [К] [П] [С] [win/loss] + скрин"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Сначала прикрепи скриншот таблицы!")

    elo_val = 25 if res.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan:
        return await ctx.send("❌ Ошибка HUB_ID! Проверь настройки в Render.")

    emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА НА ПРОВЕРКУ", color=0x7289da)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=res.upper(), inline=True)
    emb.add_field(name="📊 Стата игрока", value=f"K/A/D: **{k}/{a}/{d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    # Прячем данные в футер для кнопок
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_val}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Данные `{k}/{a}/{d}` улетели в HUB! Жди подтверждения.")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    try: data = dict(item.split(":") for item in emb.footer.text.split("|"))
    except: return

    u = get_u(data['ID'])
    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K']); u['a'] += int(data['A']); u['d'] += int(data['D'])
        if int(data['ELO']) > 0: u['wins'] += 1
        else: u['losses'] += 1
        await reaction.message.channel.send(f"✅ Стата игрока <@{data['ID']}> подтверждена! ELO: {u['elo']}")
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Заявка <@{data['ID']}> отклонена.")
    await reaction.message.delete()

# --- 5. ЭКОНОМИКА И МАГАЗИН ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id); gain = random.randint(300, 700); u['money'] += gain
    await ctx.send(f"⛏️ Ты отработал смену и получил **{gain}$**")

@bot.command()
async def casino(ctx, bet: int):
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ Мало денег!")
    if random.random() > 0.55:
        u['money'] += bet
        await ctx.send(f"🎰 ПОБЕДА! +{bet}$ (Баланс: {u['money']}$)")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 ПРОИГРЫШ! -{bet}$ (Баланс: {u['money']}$)")

# --- 6. ПРОФИЛЬ И ТОП ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль — {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="✨ LVL", value=f"**{u['lvl']}**", inline=True)
    e.add_field(name="💰 Деньги", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    s = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ЛИДЕРЫ СЕРВЕРА:**\n"
    for i, (uid, info) in enumerate(s, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Топ пуст.")

# --- 7. МОДЕРАЦИЯ ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Удалено **{amount}** сообщений.", delete_after=3)

@bot.command()
async def help(ctx):
    e = discord.Embed(title="📜 КОМАНДЫ", color=0x5865f2)
    e.add_field(name="🎮 Игра", value="`!result K A D win/loss` (со скрином)\n`!profile`, `!top`", inline=False)
    e.add_field(name="💰 Экономика", value="`!work`, `!casino [ставка]`")
    await ctx.send(embed=e)

keep_alive()
bot.run(TOKEN)
