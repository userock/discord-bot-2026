import discord
from discord.ext import commands, tasks
import os, json, random, datetime, time, re, asyncio, logging
import requests
from PIL import Image, ImageOps, ImageEnhance
import pytesseract
from io import BytesIO
from flask import Flask
from threading import Thread

# ==========================================
# [1] СИСТЕМА ЗРЕНИЯ (VISION CORE)
# ==========================================
# Указываем путь к установленному Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class VisionAI:
    @staticmethod
    async def process_image(url):
        try:
            # Загружаем картинку
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            
            # Улучшаем картинку для лучшего чтения (Ч/Б и контраст)
            img = img.convert('L') # В ч/б
            img = ImageOps.invert(img) # Инверсия, если фон темный
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2) # Увеличиваем контраст
            
            # Читаем текст (только цифры и символы KDA)
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(img, config=custom_config)
            
            # Ищем паттерны K/D/A (например 25/10/15)
            kda_match = re.findall(r'(\d+)[\s/|-]+(\d+)[\s/|-]+(\d+)', text)
            
            if kda_match:
                k, d, a = kda_match[0]
                return int(k), int(a), int(d) # Возвращаем K, A, D
            
            # Если не нашли цепочку, ищем просто первые 3 числа
            nums = re.findall(r'\d+', text)
            if len(nums) >= 3:
                return int(nums[0]), int(nums[1]), int(nums[2])
                
            return None
        except Exception as e:
            print(f"Vision Error: {e}")
            return None

# ==========================================
# [2] ЖИЗНЕОБЕСПЕЧЕНИЕ (KEEP ALIVE)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Evolution V80 Vision: ACTIVE"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# ==========================================
# [3] ГЛОБАЛЬНАЯ БАЗА ДАННЫХ
# ==========================================
class NeuralDB:
    def __init__(self, file="overlord_v80.json"):
        self.file = file
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            with open(self.file, "r", encoding="utf-8") as f: return json.load(f)
        return {"users": {}}

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user(self, uid):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "elo": 1000, "money": 5000, "lvl": 1, "xp": 0,
                "k": 0, "a": 0, "d": 0, "w": 0, "l": 0, "gpu": 0,
                "t_work": 0, "t_mine": 0
            }
            self.save()
        return self.data["users"][uid]

db = NeuralDB()

# ==========================================
# [4] КОНФИГУРАЦИЯ БОТА
# ==========================================
TOKEN = "ТВОЙ_ТОКЕН_ТУТ"
HUB_ID = "ID_КАНАЛА_HUB"
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

RANKS = {"Bronze": 0, "Silver": 1200, "Gold": 1600, "Platinum": 2100, "Diamond": 2700, "Immortal": 3500}

# ==========================================
# [5] КОМАНДА RESULT С АВТО-СКАНЕРОМ
# ==========================================
@bot.command()
async def result(ctx, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **ОШИБКА:** Сначала прикрепи скриншот!")

    status = status.lower()
    loading_msg = await ctx.send("🔍 **NEURAL VISION:** Сканирую скриншот на наличие KDA...")
    
    # Запуск ИИ-зрения
    img_url = ctx.message.attachments[0].url
    stats = await VisionAI.process_image(img_url)

    if not stats:
        await loading_msg.delete()
        return await ctx.send("❌ **VISION ERROR:** Не удалось четко распознать KDA. Введи вручную или попробуй другой скрин.")

    k, a, d = stats
    await loading_msg.delete()

    # Расчет ELO
    is_win = status in ["win", "победа", "w"]
    elo_delta = 25 if is_win else -20
    
    emb = discord.Embed(title="🤖 РЕЗУЛЬТАТ СКАНИРОВАНИЯ", color=0x3498db)
    emb.add_field(name="Обнаруженные статы", value=f"**K:** {k} | **A:** {a} | **D:** {d}", inline=False)
    emb.add_field(name="Исход", value=status.upper(), inline=True)
    emb.add_field(name="Изменение ELO", value=f"{elo_delta}", inline=True)
    emb.set_image(url=img_url)
    emb.set_footer(text="Подтверди данные: ✅ (Верно) | ❌ (Ошибка ИИ)")

    confirm_msg = await ctx.send(embed=emb)
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        
        if str(reaction.emoji) == "✅":
            hub_chan = bot.get_channel(int(HUB_ID))
            if hub_chan:
                emb.title = "🛰️ ОТЧЕТ ПРОВЕРЕН ИИ"
                emb.set_footer(text=f"PAYLOAD:{ctx.author.id}|{elo_delta}|{k}|{a}|{d}")
                final = await hub_chan.send(embed=emb)
                await final.add_reaction("🆗")
                await ctx.send("✅ **AI:** Отчет отправлен на финальную модерацию в HUB.")
            else:
                await ctx.send("❌ Ошибка: HUB_ID не найден.")
        else:
            await ctx.send("❌ **AI:** Понял, отменяю. Попробуй сделать более четкий скриншот.")
            
    except asyncio.TimeoutError:
        await ctx.send("⏳ Время вышло.")

# ==========================================
# [6] ОБРАБОТКА HUB (ПРИНЯТИЕ АДМИНОМ)
# ==========================================
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != str(HUB_ID): return
    if not user.guild_permissions.manage_messages: return

    if str(reaction.emoji) == "🆗":
        emb = reaction.message.embeds[0]
        try:
            raw = emb.footer.text.split("PAYLOAD:")[1].split("|")
            uid, elo_add, k, a, d = int(raw[0]), int(raw[1]), int(raw[2]), int(raw[3]), int(raw[4])
            
            u = db.get_user(uid)
            u['elo'] += elo_add
            u['k'] += k; u['a'] += a; u['d'] += d
            if elo_add > 0: u['w'] += 1
            else: u['l'] += 1
            db.save()
            
            await reaction.message.channel.send(f"🏆 **МАТЧ ЗАЧИСЛЕН:** <@{uid}>. Рейтинг: {u['elo']}")
            await reaction.message.delete()
        except: pass

# ==========================================
# [7] ИИ ПРОФИЛЬ И ЭКОНОМИКА
# ==========================================
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author
    u = db.get_user(m.id)
    
    rank = "Bronze"
    for r, v in RANKS.items():
        if u['elo'] >= v: rank = r

    emb = discord.Embed(title=f"👤 DOSSIER: {m.name}", color=0x00ffff)
    emb.add_field(name="🏆 RANK", value=f"`{rank}` ({u['elo']})", inline=True)
    emb.add_field(name="💳 WALLET", value=f"`{u['money']}$`", inline=True)
    emb.add_field(name="⚔️ STATS", value=f"KDA: `{u['k']}/{u['a']}/{u['d']}`\nWinrate: `{u['w']}W/{u['l']}L`", inline=False)
    
    # AI Анализ (как у меня)
    kda_val = (u['k']+u['a'])/u['d'] if u['d']>0 else u['k']
    analysis = "Анализ: Твоя стратегия эффективна." if kda_val > 2 else "Анализ: Требуется калибровка точности."
    emb.add_field(name="🤖 AI ANALYTICS", value=f"_{analysis}_")
    
    await ctx.send(embed=emb)

@bot.command()
async def work(ctx):
    u = db.get_user(ctx.author.id)
    if time.time() < u['t_work']: return await ctx.send("⏳ Рано.")
    gain = random.randint(1000, 3000)
    u['money'] += gain
    u['t_work'] = time.time() + 600
    db.save()
    await ctx.send(f"💰 Заработано **{gain}$**")

@bot.command()
async def help(ctx):
    emb = discord.Embed(title="🌌 EVOLUTION V80 HELP", color=0x2b2d31)
    emb.add_field(name="⚔️ МАТЧИ", value="`!result` (кидай скрин)")
    emb.add_field(name="📊 ИНФО", value="`!profile`, `!top`")
    emb.add_field(name="💰 ДЕНЬГИ", value="`!work`, `!mine`, `!shop`")
    await ctx.send(embed=emb)

# ==========================================
# [8] ЗАПУСК
# ==========================================
@bot.event
async def on_ready():
    print(f"--- Evolution Overlord V80: Neural Vision Online ---")
    keep_alive()

bot.run(TOKEN)
