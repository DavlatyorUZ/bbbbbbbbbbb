import asyncio
import os
import re
import shutil
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName
from groq import Groq
from dotenv import load_dotenv
import urllib.request
import yt_dlp
from PIL import Image, ImageDraw, ImageFont

# ╔════════════════════════════════════════════╗
# ║   🤖 DavlatyorUZ UserBot v8.0 (MUKAMMAL)     ║
# ║   VIDEO DOWNLOAD + All Features           ║
# ╚════════════════════════════════════════════╝

# .env faylini yuklash
load_dotenv()

def get_env_int(name, default=0):
    """Environment'dan son qiymatni xavfsiz olish"""
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        print(f"⚠️ {name} noto'g'ri qiymatga ega: {value!r}. Default ishlatildi: {default}")
        return default

# API kalitlar
API_ID = get_env_int('API_ID', 0)
API_HASH = os.getenv('API_HASH', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
YOUR_USER_ID = get_env_int('YOUR_USER_ID', 0)
HELP_GIF_URL = os.getenv('HELP_GIF_URL', '')

# Tekshirish
if API_ID == 0 or not API_HASH or not GROQ_API_KEY:
    print("❌ Xatolik: .env faylida API kalitlar topilmadi!")
    print("\n📝 Iltimos, .env faylini quyidagicha yarating:")
    print("API_ID=sizning_api_id")
    print("API_HASH=sizning_api_hash")
    print("GROQ_API_KEY=sizning_groq_api_key")
    print("YOUR_USER_ID=sizning_telegram_id")
    print("HELP_GIF_URL=gif_url (ixtiyoriy)")
    exit(1)

if YOUR_USER_ID == 0:
    print("❌ Xatolik: YOUR_USER_ID topilmadi!")
    exit(1)

# Groq client
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq AI muvaffaqiyatli ulandi!")
except Exception as e:
    print(f"❌ Groq ulanish xatosi: {e}")
    exit(1)

# Userbot client
client = TelegramClient('userbot_session', API_ID, API_HASH)

# ╔════════════════════════════════════════════╗
# ║            GLOBAL VARIABLES                ║
# ╚════════════════════════════════════════════╝

# PER-CHAT AI CONTROL
chat_ai_settings = {}

# BANDMAN SETTINGS
bandman_settings = {YOUR_USER_ID: {"enabled": True, "message": None}}
DEFAULT_BANDMAN_MESSAGE = "🔴 **Hozir bandman!**\n\n📝 Xabaringizni o'qidim, lekin hozir javob bera olmayman.\n⏰ Keyinroq albatta javob beraman!\n\n💫 Tez orada bog'lanamiz! 🤝"

# MEDIA FOLDERS
saved_media_folder = "saved_media"
temp_folder = "temp_files"
downloaded_videos_folder = "downloaded_videos"

for folder in [saved_media_folder, temp_folder, downloaded_videos_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# EDIT TRACKING
message_history = {}

# CHAT HISTORIES
chat_histories = {}

# AI STATUS
ai_enabled = False
current_chat_id = None
current_model = "llama-3.3-70b-versatile"

# USER LAST MESSAGE
user_last_message = {}

# SAVED MEDIA TRACKING
saved_message_ids = set()

# REPLY MEDIA TRACKING
reply_media_cache = {}

# PERFORMANCE / RELIABILITY LIMITS
AI_RESPONSE_TIMEOUT_SECONDS = 45
BANDMAN_COOLDOWN_SECONDS = 60
MAX_MESSAGE_HISTORY_ITEMS = 5000
MAX_USER_LAST_MESSAGE_TRACK = 2000
STICKER_EMOJI_DEFAULT = "😀"
STICKER_BOT_USERNAME = "Stickers"
ANIMATION_DEFAULT_EFFECT = "wave"
ANIMATION_MAX_TEXT_LENGTH = 120
ANIMATION_DEFAULT_INTERVAL = 0.45
ANIMATION_DEFAULT_LOOPS = 2
LOVE_FRAME_INTERVAL = 0.7
STICKER_BRAND_TEXT = "@DavlatyorUz"
BOT_STARTED_AT = datetime.now()
STICKER_FONT_CANDIDATES = [
    "SegoeUI.ttf",
    "seguiemj.ttf",
    "arial.ttf",
    "calibri.ttf",
    "verdana.ttf",
    "DejaVuSans-Bold.ttf",
    "DejaVuSans.ttf",
]

# AVAILABLE MODELS
AVAILABLE_MODELS = {
    "1": {"name": "llama-3.3-70b-versatile", "desc": "Eng kuchli, tavsiya etiladi"},
    "2": {"name": "llama-3.1-8b-instant", "desc": "Tez va samarali"},
    "3": {"name": "gemma2-9b-it", "desc": "Yaxshi muvozanat"}
}

# EMOJI DICTIONARY
EMOJI = {
    "success": "✅",
    "user": "👤",
    "error": "❌",
    "info": "📌",
    "warning": "⚠️",
    "ai": "🤖",
    "chat": "💬",
    "group": "👥",
    "private": "🔒",
    "stats": "📊",
    "settings": "⚙️",
    "time": "⏰",
    "star": "⭐",
    "fire": "🔥",
    "crown": "👑",
    "lock": "🔒",
    "save": "💾",
    "edit": "✏️",
    "reply": "↩️",
    "download": "📥",
    "upload": "📤",
    "heart": "❤️",
    "rocket": "🚀",
    "gear": "⚙️",
    "folder": "📁",
    "file": "📄",
    "video": "🎬",
    "image": "🖼️",
    "music": "🎵",
    "document": "📑",
    "loading": "⏳",
    "check": "✔️"
}

# ╔════════════════════════════════════════════╗
# ║        UTILITY FUNCTIONS                   ║
# ╚════════════════════════════════════════════╝

def is_owner(event):
    """Faqat bot egasini tekshirish"""
    return event.sender_id == YOUR_USER_ID

def get_ai_response(user_message, user_id, user_name):
    """Groq AI orqali javob olish"""
    try:
        if user_id not in chat_histories:
            chat_histories[user_id] = []
            chat_histories[user_id].append({
                "role": "system",
                "content": f"Siz {user_name} bilan suhbatlashayotgan AI assistentsiz. O'zbek tilida, do'stona va yordamchi tarzda javob bering."
            })
        
        chat_histories[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        if len(chat_histories[user_id]) > 20:
            chat_histories[user_id] = [chat_histories[user_id][0]] + chat_histories[user_id][-19:]
        
        completion = groq_client.chat.completions.create(
            model=current_model,
            messages=chat_histories[user_id],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False
        )
        
        ai_response = completion.choices[0].message.content
        
        chat_histories[user_id].append({
            "role": "assistant",
            "content": ai_response
        })
        
        return ai_response
        
    except Exception as e:
        error_msg = str(e)
        if "decommissioned" in error_msg:
            return f"❌ **Model eskirgan!**\n\n📝 Iltimos, `.models` komandasi bilan yangi model tanlang!"
        return f"❌ **Xatolik:** `{error_msg}`"

async def download_gif(url, filename="temp.gif"):
    """GIF faylni URL'dan yuklash"""
    try:
        temp_path = os.path.join(temp_folder, filename)
        await asyncio.to_thread(urllib.request.urlretrieve, url, temp_path)
        return temp_path
    except Exception as e:
        print(f"❌ GIF yuklash xatosi: {e}")
        return None

def get_file_info(file_path):
    """Fayl haqida ma'lumot olish"""
    try:
        size = os.path.getsize(file_path)
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.2f} KB"
        else:
            size_str = f"{size / (1024 * 1024):.2f} MB"
        return size_str
    except OSError:
        return "Noma'lum"

def cleanup_temp():
    """Vaqtinchalik fayllarni tozalash"""
    try:
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
            os.makedirs(temp_folder)
    except OSError as e:
        print(f"⚠️ Temp fayllarni tozalashda xatolik: {e}")

def download_video_sync(url):
    """Video yuklashni alohida threadda bajarish"""
    ydl_opts = {
        'format': 'best[height<=720]/best',
        'outtmpl': os.path.join(downloaded_videos_folder, '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_path = ydl.prepare_filename(info)
        video_title = info.get('title', 'Video')
        video_duration = info.get('duration', 0)
    return video_path, video_title, video_duration

def shrink_dict_if_needed(data, max_items):
    """Dictionary hajmi oshib ketmasligi uchun eng eski elementlarni o'chirish"""
    while len(data) > max_items:
        oldest_key = next(iter(data))
        data.pop(oldest_key, None)

async def generate_ai_response_async(user_message, user_id, user_name):
    """AI javobni timeout bilan olish"""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(get_ai_response, user_message, user_id, user_name),
            timeout=AI_RESPONSE_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return (
            f"{EMOJI['warning']} **AI javob kechikdi**\n\n"
            f"Server band bo'lishi mumkin. Iltimos, qayta urinib ko'ring."
        )

def build_animation_frames(effect, text):
    """Effekt bo'yicha frame ro'yxatini yaratish"""
    effect = (effect or ANIMATION_DEFAULT_EFFECT).lower()
    clean_text = (text or "").strip()
    if not clean_text:
        clean_text = "Salom"
    clean_text = clean_text[:ANIMATION_MAX_TEXT_LENGTH]

    if effect == "type":
        frames = [clean_text[:i] + "▌" for i in range(1, len(clean_text) + 1)]
        frames.append(clean_text)
        return frames

    if effect == "blink":
        return [clean_text, " ", clean_text, " "]

    if effect == "loading":
        dots = ["", ".", "..", "..."]
        return [f"{clean_text}{d}" for d in dots]

    # default: wave
    wave_chars = ["◜", "◠", "◝", "◞", "◡", "◟"]
    return [f"{wave_chars[i % len(wave_chars)]} {clean_text} {wave_chars[(i + 3) % len(wave_chars)]}" for i in range(12)]

async def run_text_animation(target_message, effect, text, interval=ANIMATION_DEFAULT_INTERVAL, loops=ANIMATION_DEFAULT_LOOPS):
    """Xabarni ketma-ket edit qilib animatsiya ko'rsatish"""
    frames = build_animation_frames(effect, text)
    for _ in range(max(1, loops)):
        for frame in frames:
            await target_message.edit(frame)
            await asyncio.sleep(interval)

def get_love_frames():
    """Love animatsiyasi uchun maxsus frame'lar"""
    return [
        """❤️❤️❤️❤️❤️❤️❤️❤️❤️
🧡🧡🧡🧡🧡🧡🧡🧡🧡
💛💛💛💛💛💛💛💛💛
💚💚💚💚💚💚💚💚💚
💙💙💙💙💙💙💙💙💙
💜💜💜💜💜💜💜💜💜""",
        """💝💝💝💝💝💝💝💝💝
💖💖💖💖💖💖💖💖💖
💗💗💗💗💗💗💗💗💗
💓💓💓💓💓💓💓💓💓
💞💞💞💞💞💞💞💞💞
💕💕💕💕💕💕💕💕💕""",
        """❤❤❤❤❤❤❤❤
❤❤❤❤❤❤❤❤
❤❤ 𝙸 𝚕𝚘𝚟𝚎 𝚢𝚘𝚞 ❤❤
❤❤❤❤❤❤❤❤
❤❤❤❤❤❤❤❤""",
        """♡♡♡♡♡♡♡♡♡♡♡♡♡♡♡
♡┏┓┈╭━━╮┓┏┓━━┓♡
♡┃┃┉┃╭╮┃┃┃┃┏━┛♡
♡┃┃┈┃┃┃┃┃┃┃┗━┓♡
♡┃┃┉┃┃┃┃┃┃┃┏━┛♡
♡┃┗━┓╰╯┃╰╯┃┗━┓♡
♡┗━━┛━━╯━━╯━━┛♡
♡♡♡♡♡♡♡♡♡♡♡♡♡♡♡""",
        "💘 𝐈 𝐋𝐎𝐕𝐄 𝐘𝐎𝐔 💘"
    ]

def get_sticker_pack_name():
    """Sticker pack short name"""
    return f"davlatyoruz_{YOUR_USER_ID}_by_userbot"

def get_sticker_pack_title():
    """Sticker pack title"""
    return "DavlatyorUZ Personal Pack"

def add_brand_watermark(canvas, brand_text=STICKER_BRAND_TEXT):
    """Sticker pastki qismiga brend yozuvini qo'shish"""
    draw = ImageDraw.Draw(canvas)

    def load_brand_font():
        for candidate in STICKER_FONT_CANDIDATES:
            try:
                return ImageFont.truetype(candidate, 24)
            except OSError:
                continue
        return ImageFont.load_default()

    brand_font = load_brand_font()
    text = (brand_text or "").strip()
    if not text:
        return

    bbox = draw.textbbox((0, 0), text, font=brand_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = max(8, (512 - text_width) // 2)
    y = 512 - text_height - 12

    # O'qilishi uchun yarim-shaffof panel
    panel_padding_x = 14
    panel_padding_y = 6
    panel = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle(
        [
            x - panel_padding_x,
            y - panel_padding_y,
            x + text_width + panel_padding_x,
            y + text_height + panel_padding_y,
        ],
        radius=14,
        fill=(0, 0, 0, 110),
    )
    canvas.alpha_composite(panel)

    draw = ImageDraw.Draw(canvas)
    draw.text((x + 1, y + 1), text, font=brand_font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=brand_font, fill=(255, 255, 255, 245))

def prepare_sticker_from_image(input_path, output_path):
    """Rasmni Telegram static sticker formatiga o'tkazish"""
    image = Image.open(input_path).convert("RGBA")
    width, height = image.size
    if width == 0 or height == 0:
        raise ValueError("Rasm o'lchami noto'g'ri.")

    # Kichik rasmlar ham sticker ichida katta ko'rinishi uchun upscale/downscale qilamiz
    scale = 512 / max(width, height)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    image = image.resize(new_size, Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    x = (512 - image.width) // 2
    y = (512 - image.height) // 2
    canvas.paste(image, (x, y), image)
    add_brand_watermark(canvas)
    canvas.save(output_path, "WEBP")
    return output_path

def prepare_sticker_from_text(text, output_path):
    """Matndan premium static sticker yaratish (animated-style dizayn)"""
    text = (text or "").strip()
    if not text:
        text = "Sticker"
    text = text[:250]

    canvas = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)
    # "Animated look" uchun gradient + harakat chiziqlari beriladi (static sticker)
    seed = sum(ord(ch) for ch in text)
    palette = [
        ((66, 133, 244), (52, 168, 83)),
        ((171, 71, 188), (66, 133, 244)),
        ((255, 112, 67), (236, 64, 122)),
        ((0, 172, 193), (29, 233, 182)),
    ]
    c1, c2 = palette[seed % len(palette)]
    bg = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    for y in range(512):
        t = y / 511
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        bg_draw.line([(0, y), (512, y)], fill=(r, g, b, 235), width=1)

    motion_overlay = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    motion_draw = ImageDraw.Draw(motion_overlay)
    for idx in range(6):
        x_offset = (seed + idx * 73) % 512
        motion_draw.line(
            [(x_offset - 140, 0), (x_offset + 120, 512)],
            fill=(255, 255, 255, 35),
            width=10
        )

    canvas.alpha_composite(bg)
    canvas.alpha_composite(motion_overlay)

    def load_font(size):
        for candidate in STICKER_FONT_CANDIDATES:
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def wrap_for_font(input_text, font_obj, max_width):
        lines = []
        current = ""
        for word in input_text.split():
            candidate = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), candidate, font=font_obj)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    chosen_font = load_font(70)
    wrapped = wrap_for_font(text, chosen_font, 460)
    for size in [72, 66, 60, 54, 48, 42, 36]:
        trial_font = load_font(size)
        trial_lines = wrap_for_font(text, trial_font, 460)[:8]
        line_height = int(size * 1.15)
        total_height = len(trial_lines) * line_height
        if total_height <= 420:
            chosen_font = trial_font
            wrapped = trial_lines
            break

    sample_box = draw.textbbox((0, 0), "Ag", font=chosen_font)
    line_height = max(28, int((sample_box[3] - sample_box[1]) * 1.25))
    total_height = len(wrapped) * line_height
    current_y = (512 - total_height) // 2
    for ln in wrapped:
        bbox = draw.textbbox((0, 0), ln, font=chosen_font)
        width = bbox[2] - bbox[0]
        x = (512 - width) // 2
        # Shadow
        draw.text(
            (x + 4, current_y + 4),
            ln,
            fill=(0, 0, 0, 120),
            font=chosen_font,
            stroke_width=0
        )
        draw.text(
            (x, current_y),
            ln,
            fill=(255, 255, 255, 255),
            font=chosen_font,
            stroke_width=4,
            stroke_fill=(0, 0, 0, 255)
        )
        current_y += line_height

    add_brand_watermark(canvas)
    canvas.save(output_path, "WEBP")
    return output_path

def format_uptime():
    """Bot uptime ni chiroyli formatlash"""
    delta: timedelta = datetime.now() - BOT_STARTED_AT
    total_seconds = int(delta.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

async def sticker_pack_exists(pack_name):
    """Sticker pack mavjudligini tekshirish"""
    try:
        await client(GetStickerSetRequest(
            stickerset=InputStickerSetShortName(pack_name),
            hash=0
        ))
        return True
    except Exception:
        return False

async def get_sticker_pack_count(pack_name):
    """Sticker pack ichidagi stickerlar sonini olish"""
    try:
        sticker_set = await client(GetStickerSetRequest(
            stickerset=InputStickerSetShortName(pack_name),
            hash=0
        ))
        return len(sticker_set.documents or [])
    except Exception:
        return -1

async def send_and_read(conv, message=None, file_path=None):
    """@Stickers botga xabar/fayl yuborib javobni kichik harfda qaytarish"""
    if message is not None:
        await conv.send_message(message)
    elif file_path is not None:
        await conv.send_file(file_path)
    response = await conv.get_response()
    return (response.raw_text or "").lower()

def response_has_error(text):
    """Bot javobidagi xatolik indikatorlari"""
    return any(token in text for token in [
        "sorry",
        "invalid",
        "error",
        "failed",
        "can't",
        "cannot",
        "too many",
        "bad request",
        "wrong",
    ])

def response_indicates_success(text):
    """@Stickers muvaffaqiyat signalini tekshirish"""
    if not text:
        return False
    return any(token in text for token in [
        "done",
        "added",
        "sticker set",
        "published",
        "pack",
        "kaboom",
        "awesome",
    ])

async def verify_sticker_added(pack_name, before_count, retries=4, delay=1.4):
    """Sticker soni o'sganini bir necha marta tekshirish"""
    latest_count = -1
    for _ in range(retries):
        await asyncio.sleep(delay)
        latest_count = await get_sticker_pack_count(pack_name)
        if latest_count > before_count:
            return True, latest_count
    return False, latest_count

async def create_sticker_pack_via_bot(sticker_path, emoji, pack_title, pack_name):
    """@Stickers bot orqali yangi pack yaratish"""
    async with client.conversation(STICKER_BOT_USERNAME, timeout=120) as conv:
        try:
            await send_and_read(conv, message="/cancel")
        except Exception:
            pass

        first = await send_and_read(conv, message="/newpack")
        if response_has_error(first):
            raise RuntimeError(f"@Stickers /newpack xatosi: {first[:180]}")

        if "animated" in first and "video" in first:
            step = await send_and_read(conv, message="Static")
            if response_has_error(step):
                raise RuntimeError(f"Sticker turini tanlash xatosi: {step[:180]}")

        title_resp = await send_and_read(conv, message=pack_title)
        if response_has_error(title_resp):
            raise RuntimeError(f"Pack nomini yuborishda xatolik: {title_resp[:180]}")

        sticker_resp = await send_and_read(conv, file_path=sticker_path)
        if response_has_error(sticker_resp):
            raise RuntimeError(f"Sticker fayl qabul qilinmadi: {sticker_resp[:180]}")

        emoji_resp = await send_and_read(conv, message=emoji)
        if response_has_error(emoji_resp):
            raise RuntimeError(f"Emoji yuborishda xatolik: {emoji_resp[:180]}")

        publish_resp = await send_and_read(conv, message="/publish")
        if response_has_error(publish_resp):
            raise RuntimeError(f"/publish xatosi: {publish_resp[:180]}")

        shortname_prompt = publish_resp
        if "short name" not in shortname_prompt and "address" not in shortname_prompt:
            skip_resp = await send_and_read(conv, message="/skip")
            if response_has_error(skip_resp):
                raise RuntimeError(f"/skip xatosi: {skip_resp[:180]}")
            shortname_prompt = skip_resp

        final = await send_and_read(conv, message=pack_name)
        if response_has_error(final):
            raise RuntimeError(f"Pack username berishda xatolik: {final[:180]}")
        return final

async def add_sticker_to_pack_via_bot(sticker_path, emoji, pack_name):
    """@Stickers bot orqali mavjud packga sticker qo'shish"""
    async with client.conversation(STICKER_BOT_USERNAME, timeout=120) as conv:
        try:
            await send_and_read(conv, message="/cancel")
        except Exception:
            pass

        first = await send_and_read(conv, message="/addsticker")
        if response_has_error(first):
            raise RuntimeError(f"@Stickers /addsticker xatosi: {first[:180]}")

        pack_resp = await send_and_read(conv, message=pack_name)
        if response_has_error(pack_resp):
            raise RuntimeError(f"Pack tanlashda xatolik: {pack_resp[:180]}")

        if "animated" in pack_resp and "video" in pack_resp:
            type_resp = await send_and_read(conv, message="Static")
            if response_has_error(type_resp):
                raise RuntimeError(f"Sticker turini tanlash xatosi: {type_resp[:180]}")

        sticker_resp = await send_and_read(conv, file_path=sticker_path)
        if response_has_error(sticker_resp):
            raise RuntimeError(f"Sticker fayl qabul qilinmadi: {sticker_resp[:180]}")

        emoji_resp = await send_and_read(conv, message=emoji)
        if response_has_error(emoji_resp):
            raise RuntimeError(f"Emoji yuborishda xatolik: {emoji_resp[:180]}")

        done_resp = await send_and_read(conv, message="/done")
        if response_has_error(done_resp):
            raise RuntimeError(f"/done yakunlash xatosi: {done_resp[:180]}")
        return done_resp

def is_valid_url(url):
    """URL ni tekshirish"""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

# ╔════════════════════════════════════════════╗
# ║     VIDEO DOWNLOAD COMMAND (.DOWN)        ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.down\s+(.+)'))
async def download_video(event):
    """Video link orqali video yuklab olish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    url = event.pattern_match.group(1).strip()
    
    # URL tekshiruvi
    if not is_valid_url(url):
        await event.reply(
            f"{EMOJI['error']} **XATOLIK**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Noto'g'ri URL!\n\n"
            f"Masalan: `.down https://www.youtube.com/watch?v=...`"
        )
        await event.delete()
        return
    
    # Yuklash ishlamadimi bilish
    loading_msg = await event.reply(
        f"{EMOJI['loading']} **VIDEO YUKLANMOQDA...**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Biroz kuting, video yuklanmokda..."
    )
    
    try:
        # Event loopni bloklamaslik uchun yuklash alohida threadda bajariladi
        video_path, video_title, video_duration = await asyncio.to_thread(download_video_sync, url)
        
        # Vaqtni formatlash
        minutes = video_duration // 60
        seconds = video_duration % 60
        duration_str = f"{minutes}:{seconds:02d}"
        
        file_info = get_file_info(video_path)
        
        # Video bilan tashlash
        await loading_msg.edit(
            f"{EMOJI['upload']} **VIDEO TASHLANYAPDI...**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await client.send_file(
            event.chat_id,
            video_path,
            caption=f"""
{EMOJI['video']} **VIDEO SAQLANDI VA TASHLANDI**
━━━━━━━━━━━━━━━━━━━━━━━━━
📺 **Sarlavha:** {video_title}
⏱️ **Davomiyligi:** {duration_str}
📏 **Hajmi:** {file_info}
🔗 **Manba:** `{url}`
⏰ **Vaqti:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
        )
        
        # Yuklash xabari va .down xabarin o'chirish
        await loading_msg.delete()
        await event.delete()
        
        print(f"✅ VIDEO YUKLANDI: {video_title}")
        
        # Vaqtinchalik faylni o'chirish (ixtiyoriy)
        # os.remove(video_path)
        
    except Exception as e:
        print(f"❌ Video yuklash xatosi: {e}")
        error_str = str(e)[:200]
        await loading_msg.edit(
            f"{EMOJI['error']} **YUKLAB OLISHDA XATOLIK**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"`{error_str}`\n\n"
            f"💡 Tekshiring:\n"
            f"• URL to'g'rimi?\n"
            f"• Video mavjudmi?\n"
            f"• Internet tezligini tekshiring"
        )

# ╔════════════════════════════════════════════╗
# ║        BANDMAN MANAGEMENT COMMANDS         ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.bandman(?:\s+(on|off))?(?:\s+(.+))?'))
async def manage_bandman(event):
    """Bandman rejimini boshqarish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    global bandman_settings
    user_id = YOUR_USER_ID
    
    action = event.pattern_match.group(1)
    custom_msg = event.pattern_match.group(2)
    
    if action == "off":
        bandman_settings[user_id]["enabled"] = False
        await event.reply(
            f"{EMOJI['success']} **BANDMAN O'CHIRILDI!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ Avtomatik javoblar berilmaydi\n"
            f"⏰ Status: O'chirilgan"
        )
    elif action == "on" or action is None:
        bandman_settings[user_id]["enabled"] = True
        if custom_msg:
            bandman_settings[user_id]["message"] = f"🔴 **Hozir bandman!**\n\n{custom_msg}\n\n💫 Tez orada bog'lanamiz! 🤝"
            await event.reply(
                f"{EMOJI['success']} **BANDMAN YOQILDI!**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 Shaxsiy xabar o'rnatildi\n"
                f"⏰ Status: Yoqilgan"
            )
        else:
            bandman_settings[user_id]["message"] = None
            await event.reply(
                f"{EMOJI['success']} **BANDMAN YOQILDI!**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 Standart xabar ishlatilmoqda\n"
                f"⏰ Status: Yoqilgan"
            )
    
    await event.delete()

# ╔════════════════════════════════════════════╗
# ║      CHAT AI CONTROL COMMANDS              ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.chatai(?:\s+(on|off))?'))
async def manage_chat_ai(event):
    """Bitta chat uchun AI boshqaruvi"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    chat_id = event.chat_id
    action = event.pattern_match.group(1)
    
    if chat_id not in chat_ai_settings:
        chat_ai_settings[chat_id] = {"enabled": True, "model": current_model}
    
    if action == "off":
        chat_ai_settings[chat_id]["enabled"] = False
        chat_info = "Bu chatda"
        try:
            entity = await event.get_chat()
            if hasattr(entity, 'title') and entity.title:
                chat_info = f"'{entity.title}' chatda"
        except Exception:
            pass
        
        await event.reply(
            f"{EMOJI['ai']} **AI O'CHIRILDI**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ {chat_info} AI o'chirildi\n"
            f"📍 Javoblar berilmaydi"
        )
    else:
        chat_ai_settings[chat_id]["enabled"] = True
        chat_info = "Bu chatda"
        try:
            entity = await event.get_chat()
            if hasattr(entity, 'title') and entity.title:
                chat_info = f"'{entity.title}' chatda"
        except Exception:
            pass
        
        await event.reply(
            f"{EMOJI['ai']} **AI YOQILDI**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ {chat_info} AI yoqildi\n"
            f"📍 Javoblar berila boshladi"
        )
    
    await event.delete()

# ╔════════════════════════════════════════════╗
# ║     MEDIA SAVE (.SAVE) COMMANDS            ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.save'))
async def save_replied_media(event):
    """Reply qilgan media faylni saqlash"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    try:
        reply_to_msg = await event.get_reply_message()
        
        if not reply_to_msg:
            await event.reply(
                f"{EMOJI['error']} **XATOLIK**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Rasm/videoga reply qilib `.save` yozing!"
            )
            await event.delete()
            return
        
        if not reply_to_msg.media:
            await event.reply(
                f"{EMOJI['error']} **XATOLIK**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Bu xabar media emas!"
            )
            await event.delete()
            return
        
        file_path = await reply_to_msg.download_media(file=saved_media_folder)
        
        try:
            sender = await reply_to_msg.get_sender()
            user_name = sender.username or sender.first_name or str(sender.id)
        except Exception:
            user_name = "Noma'lum"
        
        file_info = get_file_info(file_path)
        file_name = os.path.basename(file_path)
        
        await client.send_file(
            YOUR_USER_ID,
            file_path,
            caption=f"""
{EMOJI['save']} **MEDIA SAQLANDI (.SAVE)**
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 **Manba:** {user_name}
📁 **Fayl nomi:** `{file_name}`
📏 **Hajmi:** `{file_info}`
⏰ **Vaqti:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔗 **ID:** `{reply_to_msg.id}`
            """
        )
        
        await event.delete()
        
        print(f"✅ .SAVE SAQLANDI: {user_name} dan {file_name}")
        
    except Exception as e:
        print(f"❌ .save xatosi: {e}")
        await event.reply(f"{EMOJI['error']} **XATOLIK:** `{e}`")
        await event.delete()

# ╔════════════════════════════════════════════╗
# ║     AUTO MEDIA SAVE (.AUTOSAVE)           ║
# ╚════════════════════════════════════════════╝

auto_save_enabled = False
auto_save_chat_id = None

@client.on(events.NewMessage(pattern=r'\.autosave\s+(on|off)'))
async def manage_autosave(event):
    """Auto-save rejimini boshqarish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    global auto_save_enabled, auto_save_chat_id
    
    action = event.pattern_match.group(1)
    
    if action == "on":
        auto_save_enabled = True
        auto_save_chat_id = event.chat_id
        saved_message_ids.clear()
        
        chat_name = "Private Chat"
        try:
            entity = await event.get_chat()
            if hasattr(entity, 'title') and entity.title:
                chat_name = entity.title
            elif hasattr(entity, 'first_name'):
                chat_name = entity.first_name
        except Exception:
            pass
        
        await event.reply(
            f"{EMOJI['save']} **AUTO-SAVE YOQILDI!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 **Chat:** {chat_name}\n"
            f"📍 **Chat ID:** `{event.chat_id}`\n\n"
            f"✅ Faqat bu chatdan media saqlana boshladi!\n"
            f"🔴 Boshqa chatlardan SAQLANMAYDI\n\n"
            f"⏹️ O'chirish: `.autosave off`"
        )
    else:
        auto_save_enabled = False
        auto_save_chat_id = None
        
        await event.reply(
            f"{EMOJI['save']} **AUTO-SAVE O'CHIRILDI!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ Media fayllar avtomatik saqlanmaydi.\n\n"
            f"✅ Yoqish: `.autosave on`\n"
            f"📌 Bitta fayl: `.save`"
        )
    
    await event.delete()

@client.on(events.NewMessage)
async def auto_save_media(event):
    """Avtomatik media saqlash"""
    global auto_save_enabled, auto_save_chat_id, saved_message_ids
    
    if event.out:
        return
    
    if not auto_save_enabled:
        return
    
    if event.chat_id != auto_save_chat_id:
        return
    
    if not event.media:
        return
    
    if event.id in saved_message_ids:
        return
    
    try:
        sender = await event.get_sender()
        user_name = sender.username or sender.first_name or str(sender.id)
        
        file_path = await event.download_media(file=saved_media_folder)
        saved_message_ids.add(event.id)
        
        file_info = get_file_info(file_path)
        file_name = os.path.basename(file_path)
        
        await client.send_file(
            YOUR_USER_ID,
            file_path,
            caption=f"""
{EMOJI['save']} **MEDIA AUTO-SAQLANDI**
━━━━━━━━━━━━━━━━━━━━━━━━━
👤 **Manba:** {user_name}
📁 **Fayl nomi:** `{file_name}`
📏 **Hajmi:** `{file_info}`
⏰ **Vaqti:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
        )
        
        print(f"✅ AUTO-SAVE: {user_name} dan {file_name}")
        
    except Exception as e:
        print(f"❌ Auto-save xatosi: {e}")

# ╔════════════════════════════════════════════╗
# ║           AI CONTROL COMMANDS              ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.onai'))
async def enable_ai(event):
    """AI rejimini yoqish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    global ai_enabled, current_chat_id
    ai_enabled = True
    current_chat_id = event.chat_id
    chat_histories.clear()
    
    chat_name = "Bu chat"
    try:
        entity = await event.get_chat()
        if hasattr(entity, 'title') and entity.title:
            chat_name = f"'{entity.title}'"
    except Exception as e:
        print(f"⚠️ Chat nomini olishda xatolik: {e}")
    
    await event.reply(
        f"{EMOJI['ai']} **AI AVTO-JAVOB REJIMI**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Holat: **Yoqilgan**\n"
        f"📍 Chat: {chat_name}\n\n"
        f"📌 **Ishlash tartibi:**\n"
        f"• {EMOJI['private']} **Private chat** → Har qanday xabarga javob\n"
        f"• {EMOJI['group']} **Guruhlar** → Faqat reply qilganlarga\n\n"
        f"🔹 **Model:** `{current_model}`\n\n"
        f"📝 `.offai` - O'chirish\n"
        f"📊 `.stats` - Statistika"
    )
    await event.delete()

@client.on(events.NewMessage(pattern=r'\.offai'))
async def disable_ai(event):
    """AI rejimini o'chirish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    global ai_enabled
    ai_enabled = False
    
    await event.reply(
        f"{EMOJI['ai']} **AI AVTO-JAVOB REJIMI**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴 Holat: **O'chirilgan**\n\n"
        f"✅ Qayta yoqish uchun `.onai` yozing"
    )
    await event.delete()

# ╔════════════════════════════════════════════╗
# ║        MODEL MANAGEMENT COMMANDS           ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.models'))
async def list_models(event):
    """Barcha mavjud modellarni ko'rsatish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    models_text = f"""
{EMOJI['settings']} **MAVJUD MODELLAR**
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    for key, model in AVAILABLE_MODELS.items():
        marker = "✅" if model["name"] == current_model else "📌"
        models_text += f"\n{marker} `.model {key}` **{model['name']}**\n   └ {model['desc']}\n"
    
    models_text += f"\n{EMOJI['info']} Masalan: `.model 1` - Modelni tanlang"
    await event.reply(models_text)
    await event.delete()

@client.on(events.NewMessage(pattern=r'\.model\s+(\d+)'))
async def change_model(event):
    """AI modelini o'zgaritirish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    global current_model, chat_histories
    
    model_number = event.pattern_match.group(1)
    
    if model_number in AVAILABLE_MODELS:
        old_model = current_model
        current_model = AVAILABLE_MODELS[model_number]["name"]
        chat_histories.clear()
        
        await event.reply(
            f"{EMOJI['success']} **MODEL O'ZGARTIRILDI**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 Eski: `{old_model}`\n"
            f"📥 Yangi: `{current_model}`\n\n"
            f"💡 {AVAILABLE_MODELS[model_number]['desc']}\n"
            f"🔄 Tarix tozalandi"
        )
        await event.delete()
    else:
        await event.reply(
            f"{EMOJI['error']} **XATOLIK**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Noto'g'ri raqam!\n\n`.models` bilan ko'ring"
        )
        await event.delete()

# ╔════════════════════════════════════════════╗
# ║        STATISTICS & INFO COMMANDS          ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.stats'))
async def ai_stats(event):
    """Statistika ko'rsatish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    global ai_enabled, chat_histories, current_model, auto_save_enabled, bandman_settings, auto_save_chat_id
    
    status = "✅ Yoqilgan" if ai_enabled else "❌ O'chirilgan"
    bandman_status = "✅ Yoqilgan" if bandman_settings.get(YOUR_USER_ID, {}).get("enabled", True) else "❌ O'chirilgan"
    autosave_status = "✅ Yoqilgan" if auto_save_enabled else "❌ O'chirilgan"
    autosave_chat_info = f"Chat ID: `{auto_save_chat_id}`" if auto_save_chat_id else "Inactive"
    active_users = len(chat_histories)
    
    # Saqlangan media soni
    saved_media_count = 0
    try:
        saved_media_count = len([f for f in os.listdir(saved_media_folder) if os.path.isfile(os.path.join(saved_media_folder, f))])
    except OSError as e:
        print(f"⚠️ Saqlangan media statistikasi xatosi: {e}")
    
    # Yuklangan video soni
    downloaded_videos_count = 0
    try:
        downloaded_videos_count = len([f for f in os.listdir(downloaded_videos_folder) if os.path.isfile(os.path.join(downloaded_videos_folder, f))])
    except OSError as e:
        print(f"⚠️ Video statistikasini olishda xatolik: {e}")
    
    stats_text = f"""
{EMOJI['stats']} **STATISTIKA**
━━━━━━━━━━━━━━━━━━━━━━━━━
{EMOJI['ai']} AI Holati: {status}
{EMOJI['time']} Bandman: {bandman_status}
{EMOJI['save']} Auto-save: {autosave_status}
   └ {autosave_chat_info}
{EMOJI['chat']} Faol foydalanuvchilar: `{active_users}`
{EMOJI['folder']} Saqlangan media: `{saved_media_count}`
{EMOJI['video']} Yuklangan videolar: `{downloaded_videos_count}`
{EMOJI['settings']} Model: `{current_model}`
{EMOJI['user']} User ID: `{YOUR_USER_ID}`
    """
    await event.reply(stats_text)
    await event.delete()

# ╔════════════════════════════════════════════╗
# ║           HELP COMMAND (GIF)               ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.animate(?:\s+([a-zA-Z]+))?(?:\s+(.+))?'))
async def animate_text_command(event):
    """Animatsion matn effekti"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return

    effect = (event.pattern_match.group(1) or ANIMATION_DEFAULT_EFFECT).lower()
    text = event.pattern_match.group(2)

    if not text:
        reply_msg = await event.get_reply_message()
        if reply_msg and reply_msg.raw_text:
            text = reply_msg.raw_text

    if not text:
        await event.reply(
            f"{EMOJI['error']} **XATOLIK**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Foydalanish:\n"
            f"`.animate wave Salom`\n"
            f"`.animate type Matn`\n"
            f"`.animate blink Assalomu alaykum`\n"
            f"`.animate loading Yuklanmoqda`\n\n"
            f"Yoki matnga reply qilib: `.animate wave`"
        )
        await event.delete()
        return

    allowed_effects = {"wave", "type", "blink", "loading"}
    if effect not in allowed_effects:
        effect = ANIMATION_DEFAULT_EFFECT

    anim_msg = await event.reply(f"⏳ `{text[:ANIMATION_MAX_TEXT_LENGTH]}`")
    try:
        await run_text_animation(anim_msg, effect, text)
        await anim_msg.edit(f"✨ {text[:ANIMATION_MAX_TEXT_LENGTH]}")
    except Exception as e:
        await anim_msg.edit(f"{EMOJI['error']} Animatsiya xatosi: `{str(e)[:120]}`")
    finally:
        await event.delete()

@client.on(events.NewMessage(pattern=r'\.love'))
async def love_animation_command(event):
    """Maxsus love animatsiyasi"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return

    frames = get_love_frames()
    anim_msg = await event.reply("💖 Love animatsiya boshlanmoqda...")
    try:
        for frame in frames:
            await anim_msg.edit(frame)
            await asyncio.sleep(LOVE_FRAME_INTERVAL)
    except Exception as e:
        await anim_msg.edit(f"{EMOJI['error']} Love animatsiya xatosi: `{str(e)[:120]}`")
    finally:
        await event.delete()

@client.on(events.NewMessage(pattern=r'\.ping'))
async def ping_command(event):
    """Bot javob tezligini ko'rsatish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return

    started = datetime.now()
    pong_msg = await event.reply("🏓 Pinging...")
    latency_ms = int((datetime.now() - started).total_seconds() * 1000)
    await pong_msg.edit(
        f"🏓 **PONG**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Kechikish: `{latency_ms} ms`\n"
        f"⏱ Uptime: `{format_uptime()}`"
    )
    await event.delete()

@client.on(events.NewMessage(pattern=r'\.uptime'))
async def uptime_command(event):
    """Bot ishlash vaqtini ko'rsatish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return

    await event.reply(
        f"⏱ **BOT UPTIME**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 Ishlash vaqti: `{format_uptime()}`\n"
        f"🚀 Boshlanish: `{BOT_STARTED_AT.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    await event.delete()

@client.on(events.NewMessage(pattern=r'\.packinfo'))
async def sticker_pack_info_command(event):
    """Sticker pack holatini ko'rsatish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return

    pack_name = get_sticker_pack_name()
    count = await get_sticker_pack_count(pack_name)
    if count < 0:
        await event.reply(
            f"{EMOJI['warning']} **PACK TOPILMADI YOKI O'QILMADI**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Pack: `{pack_name}`\n"
            f"💡 Avval `.sticer` ishlatib pack yarating."
        )
    else:
        await event.reply(
            f"{EMOJI['success']} **STICKER PACK INFO**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Pack: `{pack_name}`\n"
            f"🏷 Brand: `{STICKER_BRAND_TEXT}`\n"
            f"🧩 Stickerlar soni: `{count}`\n"
            f"🔗 https://t.me/addstickers/{pack_name}"
        )
    await event.delete()

@client.on(events.NewMessage(pattern=r'\.help'))
async def help_command(event):
    """GIF bilan yordam habarini yuborish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    help_text = f"""
{EMOJI['crown']} **DavlatyorUZ UserBot v8.0 (MUKAMMAL)**
━━━━━━━━━━━━━━━━━━━━


{EMOJI['ai']} **AI AVTO-JAVOB**
├─ `.onai` - Yoqish
├─ `.offai` - O'chirish
└─ `.chatai on/off` - Chat uchun alohida

{EMOJI['time']} **BANDMAN REJIMI**
├─ `.bandman on` - Yoqish
├─ `.bandman off` - O'chirish
└─ `.bandman on [xabar]` - Shaxsiy xabar

{EMOJI['save']} **MEDIA SAQLASH**
├─ `.save` - Reply qilgan media saqlash
├─ `.autosave on` - Avtomatik saqlash
└─ `.autosave off` - O'chirish

{EMOJI['download']} **VIDEO YUKLAB OLISH (YANGI!)**
└─ `.down <URL>` - Video linkini yuklab olish
   Masalan: `.down https://www.youtube.com/watch?v=...`
   
   ✅ YouTube, Instagram, TikTok va boshqa saytlar
   ✅ 720p yoki eng yaxshi sifat
   ✅ Avtomatik tashlash

{EMOJI['image']} **STICKER YARATISH (YANGI!)**
└─ Reply + `.sticer` - 1 ta sticker yaratadi
   Ixtiyoriy: `.sticer 😎` (emoji bilan)
   Avtomatik sizning pack'ingizga qo'shadi
   Sticker tagida brand: `{STICKER_BRAND_TEXT}`

{EMOJI['rocket']} **ANIMATSION MATN (YANGI!)**
├─ `.animate wave Salom` - Wave effekt
├─ `.animate type Matn` - Typewriter effekt
├─ `.animate blink Matn` - Blink effekt
└─ `.animate loading Yuklanmoqda` - Loading effekt

{EMOJI['heart']} **LOVE ANIMATSIYA (YANGI!)**
└─ `.love` - Maxsus yurakli love animatsiya

{EMOJI['stats']} **MONITORING (YANGI!)**
├─ `.ping` - Tezlik/latency
├─ `.uptime` - Ishlash vaqti
└─ `.packinfo` - Sticker pack holati

{EMOJI['settings']} **MODEL BOSHQARUVI**
├─ `.models` - Barcha modellar
├─ `.model 1` - Model tanlash
└─ `.stats` - Statistika

{EMOJI['edit']} **EDIT TRACKING**
└─ Xabar tahrirlansa asl matn ko'rinadi

{EMOJI['lock']} **FAQAT SIZ ISHLATA OLASIZ!**
━━━━━━━━━━━━━━━━━━━━━
⚡ Version 8.0 | 🚀 Fully Featured
    """
    
    try:
        if HELP_GIF_URL:
            gif_path = await download_gif(HELP_GIF_URL, "help.gif")
            if gif_path:
                await client.send_file(
                    event.chat_id,
                    gif_path,
                    caption=help_text,
                    supports_streaming=True
                )
                await event.delete()
                return
    except Exception as e:
        print(f"GIF yuborish xatosi: {e}")
    
    await event.reply(help_text)
    await event.delete()

# ╔════════════════════════════════════════════╗
# ║        STICKER MAKER (.STICER)            ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.sticer(?:\s+(.+))?'))
async def make_sticker(event):
    """Reply qilingan xabardan sticker yaratish va packga qo'shish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg:
        await event.reply(
            f"{EMOJI['error']} **XATOLIK**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Rasm yoki matnga reply qilib `.sticer` yozing."
        )
        await event.delete()
        return

    emoji = (event.pattern_match.group(1) or STICKER_EMOJI_DEFAULT).strip()
    if len(emoji) > 10:
        emoji = STICKER_EMOJI_DEFAULT

    status_msg = await event.reply(
        f"{EMOJI['loading']} **STICKER TAYYORLANMOQDA...**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Iltimos, kuting."
    )

    input_path = None
    sticker_path = os.path.join(temp_folder, f"sticker_{event.id}.webp")
    pack_name = get_sticker_pack_name()
    pack_title = get_sticker_pack_title()

    try:
        if reply_msg.media:
            input_path = await reply_msg.download_media(file=temp_folder)
            if not input_path:
                raise RuntimeError("Media yuklab olinmadi.")
            await asyncio.to_thread(prepare_sticker_from_image, input_path, sticker_path)
        elif reply_msg.raw_text:
            await asyncio.to_thread(prepare_sticker_from_text, reply_msg.raw_text, sticker_path)
        else:
            raise RuntimeError("Reply xabarida media yoki matn topilmadi.")

        exists = await sticker_pack_exists(pack_name)
        before_count = await get_sticker_pack_count(pack_name) if exists else 0

        if not exists:
            await status_msg.edit(
                f"{EMOJI['info']} **YANGI STICKER PACK YARATILMOQDA...**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Pack: `{pack_name}`"
            )
            bot_result = await create_sticker_pack_via_bot(sticker_path, emoji, pack_title, pack_name)
        else:
            await status_msg.edit(
                f"{EMOJI['info']} **STICKER PACKGA QO'SHILMOQDA...**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Pack: `{pack_name}`"
            )
            bot_result = await add_sticker_to_pack_via_bot(sticker_path, emoji, pack_name)

        # Real verifikatsiya: sticker soni oshganini qayta-qayta tekshiramiz
        added, after_count = await verify_sticker_added(pack_name, before_count)
        if not added:
            # Ba'zan Telegram API count ni kechikib yangilaydi; bot success bergan bo'lsa xatoni yumshatamiz
            if response_indicates_success(bot_result):
                await status_msg.edit(
                    f"{EMOJI['warning']} **STICKER QO'SHILGAN BO'LISHI MUMKIN**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"😊 Emoji: {emoji}\n"
                    f"📦 Pack: `{pack_name}`\n"
                    f"📊 Tekshiruv: `{before_count}` → `{after_count}`\n"
                    f"🔗 https://t.me/addstickers/{pack_name}\n\n"
                    f"ℹ️ @Stickers javobi muvaffaqiyatli bo'ldi, ammo count darhol yangilanmadi."
                )
                await event.delete()
                return

            raise RuntimeError(
                "Sticker packga qo'shilmadi. @Stickers oqimida yakun bo'lmagan yoki pack nomi mos emas."
            )

        await status_msg.edit(
            f"{EMOJI['success']} **STICKER MUVAFFAQIYATLI QO'SHILDI**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"😊 Emoji: {emoji}\n"
            f"📦 Pack: `{pack_name}`\n"
            f"📊 Soni: `{before_count}` → `{after_count}`\n"
            f"🔗 https://t.me/addstickers/{pack_name}\n\n"
            f"ℹ️ Har `.sticer` komandasida 1 ta sticker qo'shiladi."
        )
        await event.delete()

    except Exception as e:
        await status_msg.edit(
            f"{EMOJI['error']} **STICKER YARATISHDA XATOLIK**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"`{str(e)[:300]}`\n\n"
            f"💡 Ehtimoliy sabab:\n"
            f"• @Stickers bilan muloqot yakunlanmagan bo'lishi mumkin\n"
            f"• Pack private/nomi noto'g'ri bo'lishi mumkin\n"
            f"• Telegram API count yangilanishi kechikkan bo'lishi mumkin"
        )
        await event.delete()
    finally:
        try:
            if input_path and os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(sticker_path):
                os.remove(sticker_path)
        except OSError:
            pass

# ╔════════════════════════════════════════════╗
# ║        UTILITY & SYSTEM COMMANDS           ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage(pattern=r'\.reset'))
async def reset_all(event):
    """Barcha sozlamalarni reset qilish"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    global ai_enabled, current_chat_id, chat_histories, auto_save_enabled, auto_save_chat_id
    ai_enabled = False
    current_chat_id = None
    chat_histories.clear()
    auto_save_enabled = False
    auto_save_chat_id = None
    
    await event.reply(
        f"{EMOJI['success']} **TO'LIQ RESET**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ AI rejimi: O'chirilgan\n"
        f"✅ Auto-save: O'chirilgan\n"
        f"✅ Tarix: Tozalangan\n"
        f"✅ Chat settings: Reset\n\n"
        f"💡 Qayta boshlash uchun `.onai` yozing"
    )
    await event.delete()

@client.on(events.NewMessage(pattern=r'\.cleanup'))
async def cleanup_command(event):
    """Vaqtinchalik fayllarni tozalash"""
    if not is_owner(event):
        await event.reply(f"{EMOJI['lock']} **Bu komandani faqat bot egasi ishlata oladi!**")
        await event.delete()
        return
    
    try:
        cleanup_temp()
        await event.reply(
            f"{EMOJI['success']} **TOZALANDI!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Vaqtinchalik fayllar o'chirildi"
        )
    except Exception as e:
        await event.reply(f"{EMOJI['error']} **XATOLIK:** `{e}`")
    
    await event.delete()

# ╔════════════════════════════════════════════╗
# ║      EDIT TRACKING FUNCTIONALITY           ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage)
async def store_message_history(event):
    """Xabar tarixini saqlash"""
    if event.out:
        return
    
    try:
        if event.raw_text or event.media:
            message_history[event.id] = {
                "original_text": event.raw_text,
                "user": event.sender_id,
                "timestamp": datetime.now(),
                "has_media": event.media is not None
            }
            shrink_dict_if_needed(message_history, MAX_MESSAGE_HISTORY_ITEMS)
    except Exception:
        pass

@client.on(events.MessageEdited)
async def track_message_edit(event):
    """Xabar tahrirlangani kuzatish"""
    if not event.is_private:
        return
    
    try:
        msg_id = event.message.id
        
        if msg_id not in message_history:
            return
        
        original_data = message_history[msg_id]
        original_text = original_data["original_text"]
        edited_text = event.raw_text
        sender_id = original_data["user"]
        
        if original_text == edited_text:
            return
        
        try:
            sender = await client.get_entity(sender_id)
            user_name = sender.first_name if hasattr(sender, 'first_name') else str(sender_id)
        except Exception:
            user_name = f"Foydalanuvchi ({sender_id})"
        
        await event.reply(
            f"{EMOJI['edit']} **XABAR TAHRIRLANDI**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **Nomi:** {user_name}\n\n"
            f"📝 **Asl matn:**\n`{original_text}`\n\n"
            f"✏️ **Yangi matn:**\n`{edited_text}`"
        )
        
        message_history[msg_id]["original_text"] = edited_text
        
    except Exception as e:
        print(f"Edit tracking xatosi: {e}")

# ╔════════════════════════════════════════════╗
# ║      BANDMAN AUTO-REPLY FUNCTIONALITY      ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage)
async def bandman_auto_reply(event):
    """Bandman avtomatik javob"""
    global bandman_settings, user_last_message
    
    if event.out:
        return
    
    if event.raw_text and event.raw_text.startswith('.'):
        return
    
    user_id = event.sender_id
    bandman_enabled = bandman_settings.get(YOUR_USER_ID, {}).get("enabled", True)
    
    if not bandman_enabled:
        return
    
    if event.is_private and not ai_enabled:
        shrink_dict_if_needed(user_last_message, MAX_USER_LAST_MESSAGE_TRACK)

        if user_id in user_last_message:
            time_diff = datetime.now() - user_last_message[user_id]
            if time_diff.total_seconds() < BANDMAN_COOLDOWN_SECONDS:
                return
        
        user_last_message[user_id] = datetime.now()
        
        custom_msg = bandman_settings.get(YOUR_USER_ID, {}).get("message")
        bandman_message = custom_msg if custom_msg else DEFAULT_BANDMAN_MESSAGE
        
        await event.reply(f"{bandman_message}")
        print(f"✅ Bandman javob yuborildi: {user_id}")

# ╔════════════════════════════════════════════╗
# ║       AI AUTO-REPLY FUNCTIONALITY          ║
# ╚════════════════════════════════════════════╝

@client.on(events.NewMessage)
async def auto_reply(event):
    """AI avtomatik javob"""
    global ai_enabled, current_chat_id, chat_ai_settings
    
    if event.out:
        return
    
    if event.raw_text and event.raw_text.startswith('.'):
        return
    
    if not ai_enabled:
        return
    
    chat_id = event.chat_id
    
    if chat_id not in chat_ai_settings:
        chat_ai_settings[chat_id] = {"enabled": True, "model": current_model}
    
    if not chat_ai_settings[chat_id]["enabled"]:
        return
    
    if event.chat_id != current_chat_id:
        return
    
    try:
        sender = await event.get_sender()
        if sender:
            user_name = sender.first_name or sender.username or "Foydalanuvchi"
            user_id = sender.id
        else:
            user_name = "Foydalanuvchi"
            user_id = event.sender_id
    except Exception:
        user_name = "Foydalanuvchi"
        user_id = event.sender_id
    
    # PRIVATE CHAT
    if event.is_private:
        user_message = event.raw_text
        if user_message and len(user_message) > 0:
            try:
                reply_msg = await event.reply(f"{EMOJI['ai']} **AI javob yozmoqda...**")
                
                ai_response = await generate_ai_response_async(user_message, user_id, user_name)
                await reply_msg.edit(
                    f"{EMOJI['ai']} **AI JAVOB**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{ai_response}\n\n"
                    f"{EMOJI['chat']} {user_name} → {EMOJI['ai']} AI"
                )
                print(f"✅ Private - {user_name}: {user_message[:50]}...")
            except Exception as e:
                try:
                    await reply_msg.edit(f"{EMOJI['error']} **XATOLIK**\n\n`{str(e)}`")
                except Exception:
                    pass
    
    # GURUHLAR (faqat reply)
    elif event.is_reply:
        try:
            reply_to_msg = await event.get_reply_message()
            if reply_to_msg and reply_to_msg.out:
                user_message = event.raw_text
                if user_message and len(user_message) > 0:
                    try:
                        reply_msg = await event.reply(f"{EMOJI['ai']} *AI javob yozmoqda...*")
                        
                        ai_response = await generate_ai_response_async(user_message, user_id, user_name)
                        await reply_msg.edit(
                            f"{EMOJI['group']} **GURUH JAVOBI**\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"{ai_response}\n\n"
                            f"{EMOJI['chat']} **{user_name}** ga javob"
                        )
                        print(f"✅ Guruh (reply) - {user_name}: {user_message[:50]}...")
                    except Exception as e:
                        try:
                            await reply_msg.edit(f"{EMOJI['error']} **XATOLIK**\n\n`{str(e)}`")
                        except Exception:
                            pass
        except Exception as e:
            print(f"Reply xatolik: {e}")

# ╔════════════════════════════════════════════╗
# ║           STARTUP FUNCTION                 ║
# ╚════════════════════════════════════════════╝

async def main():
    """Userbotni ishga tushirish"""
    print("""
╔══════════════════════════════════════════════════════╗
║     🤖 DavlatyorUZ UserBot v8.0 (MUKAMMAL VERSIYA)     ║
╠══════════════════════════════════════════════════════╣
║  ✅ AI Auto-reply (Private + Groups)               ║
║  ✅ Per-chat AI control                            ║
║  ✅ Bandman rejimi (DEFAULT ON)                    ║
║  ✅ Media Save (.save komandasi)                   ║
║  ✅ Auto-save media (bitta chatdan)                ║
║  ✅ Edit tracking (tahrirlash kuzatish)            ║
║  ✅ .help komandasi GIF bilan                      ║
║  ✅ Video Download (.down komandasi)      ⭐ YANGI ║
║  ✅ Statistika va boshqa xususiyatlar              ║
╚══════════════════════════════════════════════════════╝
    """)
    
    print("🚀 Userbot ishga tushmoqda...")
    try:
        await client.start()
        print("✅ Userbot muvaffaqiyatli ishga tushdi!")
        print(f"👤 Bot egasi ID: {YOUR_USER_ID}")
        print(f"🤖 Joriy AI model: {current_model}")
        print(f"🎬 .help GIF URL: {'✅ O\'rnatilgan' if HELP_GIF_URL else '❌ O\'rnatilmagan (ixtiyoriy)'}")
        
        print("\n" + "="*60)
        print("📝 ASOSIY KOMANDALAR:")
        print("="*60)
        print("   🤖 AI REJIMI:")
        print("      • .onai - AI yoqish")
        print("      • .offai - AI o'chirish")
        print("      • .chatai on/off - Chat uchun alohida")
        print("\n   💾 MEDIA SAQLASH:")
        print("      • .save - Reply qilgan media saqlash")
        print("      • .autosave on/off - Avtomatik saqlash")
        print("\n   📥 VIDEO YUKLASH (YANGI!):")
        print("      • .down <URL> - Video linki orqali yuklab olish")
        print("      • Masalan: .down https://www.youtube.com/watch?v=...")
        print("      • Qollash: YouTube, Instagram, TikTok va boshqa")
        print("\n   🖼️ STICKER YARATISH (YANGI!):")
        print("      • Reply + .sticer - 1 ta sticker yaratish")
        print("      • .sticer 😎 - Emoji bilan sticker")
        print("      • Sticker avtomatik packga qo'shiladi")
        print(f"      • Brand watermark: {STICKER_BRAND_TEXT}")
        print("\n   ✨ ANIMATSIYA (YANGI!):")
        print("      • .animate wave Salom - Wave effekt")
        print("      • .animate type Matn - Typewriter")
        print("      • .animate blink Matn - Blink")
        print("      • .animate loading Yuklanmoqda - Loading")
        print("      • .love - Maxsus love animatsiyasi")
        print("\n   📊 MONITORING:")
        print("      • .ping - Bot latency")
        print("      • .uptime - Ishlash vaqti")
        print("      • .packinfo - Sticker pack holati")
        print("\n   ⏰ BANDMAN REJIMI:")
        print("      • .bandman on/off - Bandman yoqish/o'chirish")
        print("      • .bandman on [xabar] - Shaxsiy xabar")
        print("\n   ⚙️ BOSHQA:")
        print("      • .models - Barcha modellar")
        print("      • .model 1 - Model tanlash")
        print("      • .stats - Statistika")
        print("      • .help - Yordam (GIF bilan)")
        print("      • .reset - To'liq reset")
        print("      • .cleanup - Temp fayllarni tozalash")
        print("="*60 + "\n")
        
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Xatolik: {e}")

if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n🛑 Userbot to'xtatildi")
        cleanup_temp()
    except Exception as e:
        print(f"❌ Xatolik: {e}")
