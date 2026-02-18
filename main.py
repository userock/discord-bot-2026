import discord
from discord.ext import commands, tasks
import os, random, datetime
from flask import Flask
from threading import Thread

# --- 1. ВЕЧНЫЙ ДВИГАТЕЛЬ (ЧТОБЫ НЕ ЗАСЫПАЛ) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System: Status Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # База данных в оперативной памяти

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, "k": 0, "a": 0, "d": 0, 
            "money": 1000, "xp": 0, "lvl": 1, "inv": []
        }
    return db[uid]

# --- 3. ЦИКЛ АКТИВНОСТИ ---
@tasks.loop(minutes=2)
async def stay_active():
    # Бот будет имитировать стрим, это лучше всего держит его в сети
    await bot.change_presence(activity=discord.Streaming(name="EVOLUTION HUB", url="https://twitch.tv/discord"))

# --- 4. КРАСИВЕЙШЕЕ МЕНЮ HELP (EMBED) ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="✨ ЦЕНТР УПРАВЛЕНИЯ EVOLUTION",
        description="Добро пожаловать! Здесь список всех доступных модулей системы.",
        color=0x00aaff,
        timestamp=datetime.datetime.now()
    )
    
    embed.add_field(
        name="🎮 ГЕЙМИНГ & РЕЙТИНГ",
        value="`!result K A D win/loss` — Отправить отчет\n`!profile` — Твоя статистика\n`!top` — Список лучших",
        inline=False
    )
    
    embed.add_field(
        name="💰 ЭКОНОМИКА & ФАН",
        value="`!work` — Заработать кэш\n`!casino [ставка]` — Рискнуть всем\n`!shop` — Магазин предметов",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ АДМИНИСТРИРОВАНИЕ",
        value="`!clear [число]` — Очистить чат\n`!add_money [@user] [кол-во]` — Выдать валюту",
        inline=False
    )
    
    embed.set_footer(text="Система работает 24/7", icon_url=bot.user.display_avatar.url)
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    await ctx.send(embed=embed)

# --- 5. СИСТЕМА ПРОВЕРКИ РЕЗУЛЬТАТОВ ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **Ошибка!** Прикрепи скриншот таблицы!")
    
    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan: return await ctx.send("❌ **Ошибка!** Настрой HUB_ID в Render!")

    emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА НА ПОВЕРКУ", color=0xff8800)
    emb.add_field(name="Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="Результат", value=status.upper(), inline=True)
    emb.add_field(name="Стата K/A/D", value=f"**{k} / {a} / {d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send("📡 **Данные отправлены!** Ожидайте подтверждения в HUB.")

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
        await reaction.message.channel.send(f"✅ **Одобрено!** Статистика <@{data['ID']}> обновлена.")
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ **Отклонено!** Заявка <@{data['ID']}> аннулирована.")
    await reaction.message.delete()

# --- 6. ЭКОНОМИКА ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    gain = random.randint(300, 1000)
    u['money'] += gain
    await ctx.send(f"💰 **{ctx.author.name}**, ты славно потрудился и получил **{gain}$**!")

@bot.command()
async def casino(ctx, bet: int):
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ У тебя нет столько денег!")
    if random.random() > 0.5:
        u['money'] += bet
        await ctx.send(f"🎰 **ПОБЕДА!** Ты выиграл **{bet}$**! (Баланс: {u['money']}$)")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 **ПРОИГРЫШ!** Ты слил **{bet}$**. (Баланс: {u['money']}$)")

# --- 7. ПРОФИЛЬ ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"📊 ДОСЬЕ: {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="✨ Уровень", value=f"**{u['lvl']}**", inline=True)
    e.add_field(name="💰 Кошелек", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ Суммарно K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

# --- 8. АДМИНКА ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Очищено **{amount}** сообщений.", delete_after=3)

@bot.event
async def on_ready():
    print(f"✅ СИСТЕМА ЗАПУЩЕНА ПОД ИМЕНЕМ {bot.user.name}")
    stay_active.start()

keep_alive()
bot.run(TOKEN)
