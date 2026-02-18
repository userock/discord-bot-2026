import discord
from discord.ext import commands, tasks
import os, random, datetime, time, json
from flask import Flask
from threading import Thread

# --- [ 1. СОХРАНЕНИЕ ДАННЫХ ] ---
DATA_FILE = "database.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_data()

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "losses": 0, "k": 0, "a": 0, "d": 0, "money": 1000, "last_work": 0}
        save_data(db)
    return db[uid]

# --- [ 2. SERVER ] ---
app = Flask('')
@app.route('/')
def home(): return "Evolution System: Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- [ 3. BOT CONFIG ] ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

RANKS = {"Bronze": 1000, "Silver": 1300, "Gold": 1600, "Platinum": 1900, "Diamond": 2200}

async def update_roles(member, elo):
    new_role_name = "Bronze"
    for role_name, threshold in RANKS.items():
        if elo >= threshold: new_role_name = role_name
    role = discord.utils.get(member.guild.roles, name=new_role_name)
    if role and role not in member.roles:
        to_remove = [r for r in member.roles if r.name in RANKS]
        await member.remove_roles(*to_remove)
        await member.add_roles(role)

# --- [ 4. КОМАНДА RESULT (ИСПРАВЛЕНА) ] ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, res: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **Ошибка!** Нужно прикрепить скриншот таблицы.")
    
    if not MOD_ID:
        return await ctx.send("❌ **Ошибка!** Не настроен `HUB_ID` в переменных Render.")

    m_chan = bot.get_channel(int(MOD_ID))
    if not m_chan:
        return await ctx.send(f"❌ **Ошибка!** Не могу найти канал с ID `{MOD_ID}`. Проверь права бота.")

    elo_ch = 25 if res.lower() == "win" else -20
    
    emb = discord.Embed(title="⚔️ ПРОВЕРКА МАТЧА", color=0x5865f2, timestamp=datetime.datetime.now())
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=res.upper(), inline=True)
    emb.add_field(name="📊 Статистика", value=f"`K: {k} | A: {a} | D: {d}`", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    # Важно: данные в футере разделены символом "|"
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_ch}|K:{k}|A:{a}|D:{d}")
    
    try:
        msg = await m_chan.send(embed=emb)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await ctx.message.add_reaction("📡")
        await ctx.send(f"📡 {ctx.author.mention}, твои статы отправлены в HUB на проверку!")
    except Exception as e:
        await ctx.send(f"❌ **Ошибка отправки:** `{e}`")

# --- [ 5. ОБРАБОТКА РЕАКЦИИ (ИСПРАВЛЕНА) ] ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    if str(reaction.message.channel.id) != str(MOD_ID): return
    if not reaction.message.embeds: return

    emb = reaction.message.embeds[0]
    if not emb.footer.text or "ID:" not in emb.footer.text: return

    # Парсим данные из футера
    try:
        data = dict(item.split(":") for item in emb.footer.text.split("|"))
        u_id = int(data['ID'])
        elo_val = int(data['ELO'])
    except Exception as e:
        print(f"Ошибка парсинга футера: {e}")
        return

    u = get_u(u_id)
    guild = reaction.message.guild
    member = guild.get_member(u_id)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo_val
        u['k'] += int(data['K']); u['a'] += int(data['A']); u['d'] += int(data['D'])
        if elo_val > 0: u['wins'] += 1
        else: u['losses'] += 1
        
        save_data(db)
        if member: await update_roles(member, u['elo'])
        
        await reaction.message.channel.send(f"✅ Результат <@{u_id}> подтверждён! Текущий ELO: **{u['elo']}**")
        await reaction.message.delete()

    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Результат <@{u_id}> отклонён модератором.")
        await reaction.message.delete()

# --- [ 6. ОСТАЛЬНЫЕ КОМАНДЫ ] ---
@bot.command()
async def help(ctx):
    e = discord.Embed(title="💠 EVOLUTION MENU", color=0x2b2d31)
    e.add_field(name="🎮 ИГРА", value="`!result K A D win/loss` + скрин\n`!profile` • Твоя стата", inline=False)
    e.add_field(name="💰 ЭКОНОМИКА", value="`!work` • Работа\n`!casino [ставка]`", inline=False)
    if ctx.author.guild_permissions.administrator:
        e.add_field(name="👑 АДМИН", value="`!set_elo [@user] [число]`\n`!clear [число]`", inline=False)
    await ctx.send(embed=e)

@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 ПРОФИЛЬ: {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="💰 Баланс", value=f"**{u['money']}$**", inline=True)
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    now = int(time.time())
    if now < u['last_work']:
        rem = u['last_work'] - now
        return await ctx.send(f"⏳ Отдохни еще {rem // 60}м {rem % 60}с")
    gain = random.randint(500, 1500)
    u['money'] += gain
    u['last_work'] = now + random.randint(300, 600)
    save_data(db)
    await ctx.send(f"✅ {ctx.author.mention}, заработано **{gain}$**")

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user.name} готов к работе!")
    stay_active.start()

@tasks.loop(minutes=2)
async def stay_active():
    await bot.change_presence(activity=discord.Streaming(name="!help | Evolution", url="https://twitch.tv/discord"))

keep_alive()
bot.run(TOKEN)
