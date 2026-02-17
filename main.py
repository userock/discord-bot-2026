import discord
from discord.ext import commands
import os, requests, random, re
from flask import Flask
from threading import Thread

# --- 1. СЕРВЕР ДЛЯ ПОДДЕРЖКИ РАБОТЫ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution System: KDA Edition Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ПЕРЕМЕННЫХ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") # Канал куда летят логи со статистикой
OCR_KEY = os.getenv("OCR_API_KEY")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # База данных (в оперативной памяти)
BAD_WORDS = ["хуй", "пидор", "сука"] # Добавь свои банворды

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "money": 500, "xp": 0, "lvl": 1, "kills": 0, "deaths": 0}
    return db[uid]

# --- 3. ФИЛЬТР МАТА И СИСТЕМА УРОВНЕЙ ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    if any(w in msg.content.lower() for w in BAD_WORDS):
        await msg.delete()
        return await msg.channel.send(f"🚫 {msg.author.mention}, не матерись!", delete_after=5)

    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 12)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        await msg.channel.send(f"🆙 {msg.author.mention} поднял уровень до **{u['lvl']}**!")
    await bot.process_commands(msg)

# --- 4. ГЛАВНАЯ КОМАНДА: СКАНЕР K/D/A И РЕЗУЛЬТАТА ---
@bot.command()
async def result(ctx):
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот таблицы результатов!")

    wait = await ctx.send("👁️ **ИИ анализирует твою статистику...**")
    img_url = ctx.message.attachments[0].url

    try:
        # Запрос к OCR.space
        r = requests.get(f"https://api.ocr.space/parse/imageurl?apikey={OCR_KEY}&url={img_url}&language=eng&isTable=true").json()
        
        text = ""
        if r.get("ParsedResults"):
            text = r["ParsedResults"][0]["ParsedText"]
        
        # Ищем статистику (3 числа подряд: Убийства Помощь Смерти)
        # На твоем скрине это выглядит как "19 2 7"
        stats = re.findall(r'(\d+)\s+(\d+)\s+(\d+)', text)
        
        k, a, d = (0, 0, 0)
        kda_str = "Статистика не распознана"
        
        if stats:
            k, a, d = stats[0] # Берем первую найденную строку цифр
            kda_str = f"⚔️ Убийства: **{k}** | 🤝 Помощь: **{a}** | 💀 Смерти: **{d}**"

        # Проверка на победу (ищем ключевые слова)
        is_win = any(w in text.lower() for w in ["victory", "win", "победа", "winner"])
        elo_change = 25 if is_win else -20
        verdict = "ПОБЕДА ✅" if is_win else "ПОРАЖЕНИЕ/НЕЯСНО ⚠️"

        # Отправка в HUB (канал модерации)
        m_chan = bot.get_channel(int(MOD_ID))
        emb = discord.Embed(title="📊 ДЕТАЛЬНЫЙ ОТЧЕТ МАТЧА", color=0x00ff00 if is_win else 0xff0000)
        emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=False)
        emb.add_field(name="📈 Статистика (K/D/A)", value=kda_str, inline=False)
        emb.add_field(name="🤖 Вердикт ИИ", value=f"**{verdict}**\nРекомендуемое ELO: `{elo_change}`", inline=False)
        emb.set_image(url=img_url)
        # Прячем данные для кнопок в футер
        emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|D:{d}")

        msg = await m_chan.send(embed=emb)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        await wait.edit(content=f"📡 Статистика отправлена админам! ({kda_str})")

    except Exception as e:
        print(e)
        await wait.edit(content="❌ Ошибка чтения скрина. Убедись, что таблица видна четко.")

# --- 5. КОМАНДЫ ПРОФИЛЯ И ЭКОНОМИКИ ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль {m.name}", color=0x7289da)
    e.add_field(name="📈 ELO", value=f"`{u['elo']}`")
    e.add_field(name="⚔️ Всего убийств", value=f"`{u['kills']}`")
    e.add_field(name="✨ Уровень", value=f"`{u['lvl']}`")
    e.add_field(name="💰 Монеты", value=f"`{u['money']}`")
    await ctx.send(embed=e)

@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id); earn = random.randint(50, 200); u['money'] += earn
    await ctx.send(f"🔨 Ты отработал смену и получил **{earn}** монет!")

@bot.command()
async def top(ctx):
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП-10 ИГРОКОВ:**\n"
    for i, (uid, info) in enumerate(items, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Список пуст")

# --- 6. ЛОГИКА КНОПОК В АДМИНКЕ ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    # Достаем данные: ID:123|ELO:25|K:10|D:5
    data = dict(item.split(":") for item in emb.footer.text.split("|"))
    
    pid = data['ID']
    elo = int(data['ELO'])
    k = int(data['K'])
    d = int(data['D'])

    if str(reaction.emoji) == "✅":
        u = get_u(pid)
        u['elo'] += elo
        u['kills'] += k
        u['deaths'] += d
        u['wins'] += 1 if elo > 0 else 0
        await reaction.message.channel.send(f"✅ Статистика игрока <@{pid}> обновлена!")
    
    await reaction.message.delete()

# --- 7. ВСЕ ОСТАЛЬНЫЕ КОМАНДЫ (ДЛЯ КОЛИЧЕСТВА) ---
@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Пинг: `{round(bot.latency*1000)}ms`")

@bot.command()
async def coin(ctx): await ctx.send(f"🎲 Выпало: {random.choice(['Орел', 'Решка'])}")

@bot.command()
async def help(ctx):
    await ctx.send("📜 **Команды:** `!result` (скрин), `!profile`, `!top`, `!work`, `!ping`, `!coin`, `!clear` (админ)")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, a: int): await ctx.channel.purge(limit=a+1)

keep_alive()
bot.run(TOKEN)
