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
# Привязываем "мозг" распознавания по твоему пути
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class VisionAI:
    @staticmethod
    async def process_image(url):
        try:
            # Загружаем изображение по ссылке
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            
            # Предварительная обработка для ИИ (улучшаем читаемость)
            img = img.convert('L')  # Перевод в градации серого
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.5)  # Задираем контраст для четкости цифр
            
            # Чтение текста через Tesseract
            # Конфиг --psm 6 говорит ИИ искать блоки текста, подходящие под таблицу
            text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
            
            # Ищем паттерны KDA (цифра/цифра/цифра)
            kda_match = re.findall(r'(\d+)[\s/|-]+(\d+)[\s/|-]+(\d+)', text)
            
            if kda_match:
                # Возвращаем Киллы, Ассисты, Смерти
                k, d, a = kda_match[0] 
                return int(k), int(a), int(d)
            
            # Запасной вариант: просто ищем любые последовательности цифр
            nums = re.findall(r'\d+', text)
            if len(nums) >= 3:
                return int(nums[0]), int(nums[1]), int(nums[2])
                
            return None
        except Exception as e:
            print(f"[!] Vision System Error: {e}")
            return None

# ==========================================
# [2] ЖИЗНЕОБЕСПЕЧЕНИЕ (KEEP ALIVE)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Evolution V80 Vision: SYSTEM ONLINE"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# ==========================================
# [3] БАЗА ДАННЫХ (JSON ENGINE)
# ==========================================
class NeuralDB:
    def __init__(self, file="overlord_v80_data.json"):
        self.file = file
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r", encoding="utf-8") as f: return json.load(f)
            except: return {"users": {}}
        return {"users": {}}

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user(self, uid):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "elo": 1000, "money": 5000, "lvl": 1, "xp": 0,
                "k": 0, "a": 0, "d": 0, "w": 0, "l": 0,
                "t_work": 0, "gpu": 0
            }
            self.save()
        return self.data["users"][uid]

db = NeuralDB()

# ==========================================
# [4] КОНФИГУРАЦИЯ
# ==========================================
TOKEN = "ТВОЙ_ТОКЕН_ЗДЕСЬ"
HUB_ID = "ID_КАНАЛА_ХАБА_ЗДЕСЬ"
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

RANKS = {"Bronze": 0, "Silver": 1200, "Gold": 1600, "Platinum": 2100, "Diamond": 2700, "Immortal": 3500}

# ==========================================
# [5] КОМАНДА !RESULT С АВТО-ЗРЕНИЕМ
# ==========================================
@bot.command()
async def result(ctx, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **ОШИБКА:** Сначала прикрепи скриншот с таблицей счета!")

    status = status.lower()
    msg_status = await ctx.send("🌀 **ИИ-АНАЛИЗ:** Считываю данные со скриншота...")
    
    # Запуск обработки изображения
    img_url = ctx.message.attachments[0].url
    stats = await VisionAI.process_image(img_url)

    if not stats:
        await msg_status.delete()
        return await ctx.send("❌ **ИИ-ОШИБКА:** Не удалось распознать KDA. Попробуй более четкий скриншот или введи вручную.")

    k, a, d = stats
    await msg_status.delete()

    # Расчет ELO (Победа +25, Поражение -20)
    is_win = status in ["win", "победа", "w"]
    elo_delta = 25 if is_win else -20
    
    emb = discord.Embed(title="🤖 ИИ РАСПОЗНАЛ МАТЧ", color=0x3498db)
    emb.add_field(name="Обнаружен KDA", value=f"**K:** {k} | **A:** {a} | **D:** {d}", inline=False)
    emb.add_field(name="Результат", value=status.upper(), inline=True)
    emb.add_field(name="Прогноз ELO", value=f"{'+' if elo_delta > 0 else ''}{elo_delta}", inline=True)
    emb.set_image(url=img_url)
    emb.set_footer(text=f"PAYLOAD:{ctx.author.id}|{elo_delta}|{k}|{a}|{d}")

    confirm = await ctx.send(content="**Проверь данные ниже:**", embed=emb)
    await confirm.add_reaction("✅")
    await confirm.add_reaction("❌")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        
        if str(reaction.emoji) == "✅":
            hub_chan = bot.get_channel(int(HUB_ID))
            if hub_chan:
                await hub_chan.send(content=f"📡 **НОВЫЙ ОТЧЕТ ОТ {ctx.author}:**", embed=emb)
                await ctx.send("✅ **ГОТОВО:** Данные подтверждены и отправлены в HUB.")
            else:
                await ctx.send("❌ **ОШИБКА:** Канал HUB не найден. Проверь HUB_ID в коде.")
        else:
            await ctx.send("❌ **ОТМЕНА:** ИИ ошибся. Попробуй загрузить другой скриншот.")
            
    except asyncio.TimeoutError:
        await ctx.send("⏳ Время подтверждения вышло.")

# ==========================================
# [6] ОБРАБОТКА ХАБА (ОДОБРЕНИЕ АДМИНОМ)
# ==========================================
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != str(HUB_ID): return
    # Только админы могут подтверждать в Хабе
    if not user.guild_permissions.manage_messages: return

    if str(reaction.emoji) == "✅":
        if not reaction.message.embeds: return
        emb = reaction.message.embeds[0]
        
        try:
            # Вытаскиваем данные из скрытого Payload в футере
            data = emb.footer.text.split("PAYLOAD:")[1].split("|")
            uid, elo_add, k, a, d = int(data[0]), int(data[1]), int(data[2]), int(data[3]), int(data[4])
            
            u = db.get_user(uid)
            u['elo'] += elo_add
            u['k'] += k; u['a'] += a; u['d'] += d
            if elo_add > 0: u['w'] += 1
            else: u['l'] += 1
            db.save()
            
            await reaction.message.channel.send(f"🏆 **МАТЧ ЗАЧИСЛЕН:** Игрок <@{uid}> обновлен. ELO: **{u['elo']}**")
            await reaction.message.delete()
        except Exception as e:
            print(f"Error in Hub confirmation: {e}")

# ==========================================
# [7] ИИ-ПРОФИЛЬ И ЭКОНОМИКА
# ==========================================
@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    u = db.get_user(member.id)
    
    # Определение ранга
    current_rank = "Bronze"
    for r, v in RANKS.items():
        if u['elo'] >= v: current_rank = r

    emb = discord.Embed(title=f"📁 ПРОФИЛЬ: {member.name.upper()}", color=0x00d9ff)
    emb.set_thumbnail(url=member.display_avatar.url)
    emb.add_field(name="🏆 РАНГ", value=f"`{current_rank}` | ELO: **{u['elo']}**", inline=True)
    emb.add_field(name="💳 БАЛАНС", value=f"`{u['money']}$`", inline=True)
    emb.add_field(name="📊 БОЕВАЯ СТАТИСТИКА", value=f"```fix\nK/A/D: {u['k']}/{u['a']}/{u['d']}\nWinrate: {u['w']}W - {u['l']}L\n```", inline=False)
    
    # ИИ Аналитика стиля игры
    kda_ratio = (u['k'] + u['a']) / u['d'] if u['d'] > 0 else u['k']
    style = "Агрессивный доминатор" if kda_ratio > 2.5 else "Стабильный тактик"
    emb.add_field(name="🤖 ИИ-АНАЛИЗ", value=f"Стиль: **{style}**\nСовет: _Тренируй точность для перехода в следующий ранг._", inline=False)
    
    await ctx.send(embed=emb)

@bot.command()
async def work(ctx):
    u = db.get_user(ctx.author.id)
    if time.time() < u['t_work']:
        rem = int(u['t_work'] - time.time())
        return await ctx.send(f"⏳ Ты устал. Отдохни еще {rem//60} мин.")
    
    reward = random.randint(1000, 3500)
    u['money'] += reward
    u['t_work'] = time.time() + 900 # КД 15 минут
    db.save()
    await ctx.send(f"💰 **РАБОТА:** Ты выполнил заказ и получил **{reward}$**")

# ==========================================
# [8] ЗАПУСК
# ==========================================
@bot.event
async def on_ready():
    print(f"--- Evolution Overlord V80: Neural Vision Online ---")
    print(f"Logged in as: {bot.user}")
    keep_alive()

bot.run(TOKEN)
