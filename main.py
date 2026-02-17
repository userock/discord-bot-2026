import discord
from discord.ext import commands
import os, random
from flask import Flask
from threading import Thread

# --- 1. ХОСТИНГ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution System: Manual Mode Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # Твоя база данных (сохраняется пока бот включен)

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "money": 500, "k": 0, "d": 0, "lvl": 1, "xp": 0}
    return db[uid]

# --- 3. СИСТЕМА УРОВНЕЙ И МАТ-ФИЛЬТР ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Простой фильтр мата
    bad_words = ["хуй", "сука", "пидор"]
    if any(w in msg.content.lower() for w in bad_words):
        await msg.delete()
        return await msg.channel.send(f"🚫 {msg.author.mention}, не матерись!", delete_after=5)

    # Опыт за общение
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 15)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        await msg.channel.send(f"🆙 {msg.author.mention} поднял уровень до **{u['lvl']}**!")
    
    await bot.process_commands(msg)

# --- 4. КОМАНДА РЕЗУЛЬТАТА (БЕЗ КЛЮЧЕЙ) ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """Использование: !result [убийства] [помощь] [смерти] [win/loss] + СКРИН"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Ты забыл прикрепить скриншот таблицы!")

    # Настройка наград (25 за победу, -20 за поражение)
    elo_val = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan:
        return await ctx.send("❌ Ошибка: Проверь HUB_ID в настройках Render!")

    # Отправка админу в HUB
    emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА НА ПРОВЕРКУ", color=0x7289da)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=status.upper(), inline=True)
    emb.add_field(name="📊 Стата", value=f"Убийства: **{k}** | Помощь: **{a}** | Смерти: **{d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    # Прячем данные для кнопок в футер
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_val}|K:{k}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 **Данные отправлены!** Ожидай проверки админом.")

# --- 5. ЛОГИКА АДМИН-КНОПОК ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return 
    
    emb = reaction.message.embeds[0]
    # Достаем инфу: ID:123|ELO:25|K:10|D:5
    try:
        data = dict(item.split(":") for item in emb.footer.text.split("|"))
    except: return

    if str(reaction.emoji) == "✅":
        u = get_u(data['ID'])
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K'])
        u['d'] += int(data['D'])
        u['wins'] += 1 if int(data['ELO']) > 0 else 0
        await reaction.message.channel.send(f"✅ Статистика игрока <@{data['ID']}> подтверждена!")
    
    await reaction.message.delete()

# --- 6. КОМАНДЫ ПРОФИЛЯ И ЭКОНОМИКИ ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"`{u['elo']}`")
    e.add_field(name="⚔️ Убийства", value=f"`{u['k']}`")
    e.add_field(name="💀 Смерти", value=f"`{u['d']}`")
    e.add_field(name="🏆 Победы", value=f"`{u['wins']}`")
    e.add_field(name="✨ Уровень", value=f"`{u['lvl']}`")
    e.add_field(name="💰 Монеты", value=f"`{u['money']}`")
    await ctx.send(embed=e)

@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id); earn = random.randint(100, 300); u['money'] += earn
    await ctx.send(f"🔨 Ты отработал смену и получил **{earn}** монет!")

@bot.command()
async def top(ctx):
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП-10 ИГРОКОВ:**\n"
    for i, (uid, info) in enumerate(items, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Список пуст")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Пинг: `{round(bot.latency*1000)}ms`")

@bot.command()
async def help(ctx):
    await ctx.send("📜 **Команды:**\n`!result 19 2 7 win` (+скрин)\n`!profile` - твоя стата\n`!work` - заработок\n`!top` - лидеры")

keep_alive()
bot.run(TOKEN)
