import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict
from collections import deque

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import Database
from keyboards import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOGS_DIR / 'bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# ================== ХРАНИЛИЩЕ СЕССИЙ ==================
user_sessions: Dict[int, Dict] = {}  # telegram_id -> {user_id, nickname}

# ================== СИСТЕМА ОЧИСТКИ ==================
user_messages: Dict[int, deque] = {}
MAX_MSGS = 15

async def add_msg(uid, mid):
    if uid not in user_messages:
        user_messages[uid] = deque(maxlen=MAX_MSGS)
    user_messages[uid].append(mid)

async def del_msgs(cid, uid, keep=2):
    if uid not in user_messages:
        return
    to_del = list(user_messages[uid])[:-keep] if len(user_messages[uid]) > keep else []
    for mid in to_del:
        try:
            await bot.delete_message(cid, mid)
            if mid in user_messages[uid]:
                user_messages[uid].remove(mid)
        except:
            pass

async def send(cid, uid, text, kb=None, keep=2, **kwargs):
    await del_msgs(cid, uid, keep)
    msg = await bot.send_message(cid, text, reply_markup=kb, **kwargs)
    await add_msg(uid, msg.message_id)
    return msg

async def send_media(cid, uid, media, keep=2):
    await del_msgs(cid, uid, keep)
    msgs = await bot.send_media_group(cid, media)
    for m in msgs:
        await add_msg(uid, m.message_id)
    return msgs

async def clear_chat(cid, uid):
    if uid in user_messages:
        for mid in list(user_messages[uid]):
            try:
                await bot.delete_message(cid, mid)
            except:
                pass
        user_messages[uid].clear()

# ================== FSM ==================
class Register(StatesGroup):
    nick = State()
    pwd = State()
    confirm = State()

class Login(StatesGroup):
    nick = State()
    pwd = State()

class Comment(StatesGroup):
    game_id = State()
    text = State()

class AddGame(StatesGroup):
    platform = State()
    genre = State()
    file = State()
    title = State()
    desc = State()

class AddScreenshots(StatesGroup):
    game_id = State()
    screens = State()

class GenreManage(StatesGroup):
    name = State()
    display = State()
    desc = State()
    platform = State()
    price = State()
    new_val = State()

# ================== КОМАНДЫ ==================
@dp.message(Command("start"))
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    await clear_chat(msg.chat.id, msg.from_user.id)
    await send(msg.chat.id, msg.from_user.id,
               "🎮 <b>GameVault</b>\n\nВыбери платформу:", platforms_kb())

@dp.message(Command("stats"))
async def cmd_stats(msg: types.Message):
    if msg.from_user.id not in config.ADMIN_IDS:
        await send(msg.chat.id, msg.from_user.id, "❌ Нет прав")
        return
    s = db.get_stats()
    await send(msg.chat.id, msg.from_user.id,
               f"📊 Статистика:\n👥 Пользователей: {s['users']}\n🎮 Игр: {s['games']}\n🎨 Жанров: {s['genres']}\n📥 Скачиваний: {s['downloads']}")

@dp.message(Command("admin"))
async def cmd_admin(msg: types.Message):
    if msg.from_user.id not in config.ADMIN_IDS:
        await send(msg.chat.id, msg.from_user.id, "❌ Нет прав")
        return
    await send(msg.chat.id, msg.from_user.id, "🛠 Админ-панель:", admin_main_kb())

@dp.message(Command("addgame"))
async def cmd_addgame(msg: types.Message, state: FSMContext):
    if msg.from_user.id not in config.ADMIN_IDS:
        await send(msg.chat.id, msg.from_user.id, "❌ Нет прав")
        return
    await state.clear()
    await state.set_state(AddGame.platform)
    await send(msg.chat.id, msg.from_user.id, "Выбери платформу:", admin_platform_kb())

@dp.message(Command("addscreenshots"))
async def cmd_addscreens(msg: types.Message, state: FSMContext):
    if msg.from_user.id not in config.ADMIN_IDS:
        await send(msg.chat.id, msg.from_user.id, "❌ Нет прав")
        return
    try:
        game_id = int(msg.text.split()[1])
        game = db.get_game(game_id)
        if game:
            await state.update_data(game_id=game_id, screens=[])
            await state.set_state(AddScreenshots.screens)
            await send(msg.chat.id, msg.from_user.id,
                      f"🖼️ Отправь фото для '{game['title']}' (до 5). /done для завершения")
            return
    except:
        pass
    await send(msg.chat.id, msg.from_user.id, "❌ Использование: /addscreenshots [ID]")

# ================== ПРОФИЛЬ ==================
@dp.callback_query(F.data == "profile")
async def profile_cb(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    uid = cb.from_user.id
    session = user_sessions.get(uid)
    
    if session:
        user = db.get_user_by_id(session['user_id'])
        if user:
            purchases = db.get_purchases(session['user_id'])
            text = f"👤 <b>{user['nickname']}</b>\n📅 {user['registered_date'][:10]}\n\n🎯 Подписки:\n"
            if purchases:
                for p in purchases:
                    text += f"• {p['display_name']} до {p['expiry_date'][:10]}\n"
            else:
                text += "• Нет активных подписок"
            await send(cb.message.chat.id, uid, text, profile_kb())
            return
    
    await send(cb.message.chat.id, uid, "👤 Авторизация:", login_kb())

@dp.callback_query(F.data == "login")
async def login_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(Login.nick)
    await send(cb.message.chat.id, cb.from_user.id, "🔑 Введите никнейм:", cancel_kb())

@dp.message(Login.nick)
async def login_nick(msg: types.Message, state: FSMContext):
    await state.update_data(nick=msg.text.strip())
    await state.set_state(Login.pwd)
    await send(msg.chat.id, msg.from_user.id, "🔑 Введите пароль:", cancel_kb())

@dp.message(Login.pwd)
async def login_pwd(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    user = db.login(data['nick'], msg.text.strip())
    if user:
        user_sessions[msg.from_user.id] = {'user_id': user['id'], 'nickname': user['nickname']}
        if not user.get('telegram_id'):
            db.link_telegram(user['id'], msg.from_user.id)
        await state.clear()
        await send(msg.chat.id, msg.from_user.id, f"✅ Привет, {user['nickname']}!")
        await profile_cb(None, state)
    else:
        await send(msg.chat.id, msg.from_user.id, "❌ Неверный ник или пароль")

@dp.callback_query(F.data == "register")
async def register_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(Register.nick)
    await send(cb.message.chat.id, cb.from_user.id, "📝 Придумайте никнейм (буквы и цифры):", cancel_kb())

@dp.message(Register.nick)
async def reg_nick(msg: types.Message, state: FSMContext):
    nick = msg.text.strip()
    if not nick.isalnum():
        await send(msg.chat.id, msg.from_user.id, "❌ Только буквы и цифры")
        return
    if db.get_user_by_telegram(msg.from_user.id):
        await send(msg.chat.id, msg.from_user.id, "❌ Вы уже зарегистрированы")
        return
    await state.update_data(nick=nick)
    await state.set_state(Register.pwd)
    await send(msg.chat.id, msg.from_user.id, "🔐 Придумайте пароль (мин 4 символа):", cancel_kb())

@dp.message(Register.pwd)
async def reg_pwd(msg: types.Message, state: FSMContext):
    pwd = msg.text.strip()
    if len(pwd) < 4:
        await send(msg.chat.id, msg.from_user.id, "❌ Минимум 4 символа")
        return
    await state.update_data(pwd=pwd)
    await state.set_state(Register.confirm)
    await send(msg.chat.id, msg.from_user.id, "🔐 Повторите пароль:", cancel_kb())

@dp.message(Register.confirm)
async def reg_confirm(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    if data['pwd'] != msg.text.strip():
        await send(msg.chat.id, msg.from_user.id, "❌ Пароли не совпадают")
        await state.clear()
        return
    uid = db.register(msg.from_user.id, data['nick'], data['pwd'])
    if uid:
        user_sessions[msg.from_user.id] = {'user_id': uid, 'nickname': data['nick']}
        await state.clear()
        await send(msg.chat.id, msg.from_user.id, f"✅ Добро пожаловать, {data['nick']}!")
        await profile_cb(None, state)
    else:
        await send(msg.chat.id, msg.from_user.id, "❌ Ошибка регистрации")

@dp.callback_query(F.data == "my_subscriptions")
async def subs_cb(cb: types.CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    session = user_sessions.get(uid)
    if not session:
        await send(cb.message.chat.id, uid, "❌ Войдите в систему")
        return
    purchases = db.get_purchases(session['user_id'])
    text = "📊 Ваши подписки:\n\n"
    if purchases:
        for p in purchases:
            text += f"• {p['display_name']} до {p['expiry_date'][:10]}\n"
    else:
        text += "Нет активных подписок"
    await send(cb.message.chat.id, uid, text, profile_kb())

@dp.callback_query(F.data == "cancel")
async def cancel_cb(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await send(cb.message.chat.id, cb.from_user.id, "❌ Отменено", platforms_kb())

@dp.callback_query(F.data == "ignore")
async def ignore_cb(cb: types.CallbackQuery):
    await cb.answer()

# ================== НАВИГАЦИЯ ==================
@dp.callback_query(F.data == "back_platforms")
async def back_platforms(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await send(cb.message.chat.id, cb.from_user.id, "Выбери платформу:", platforms_kb())

@dp.callback_query(F.data.startswith("platform_"))
async def platform_cb(cb: types.CallbackQuery, state: FSMContext):
    platform = cb.data.replace("platform_", "")
    await cb.answer()
    await state.clear()
    genres = db.get_genres(platform)
    await send(cb.message.chat.id, cb.from_user.id,
              f"{config.PLATFORMS[platform]['display']}\n\nВыбери жанр:",
              genres_kb(platform, genres))

@dp.callback_query(F.data.startswith("genre_"))
async def genre_cb(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    genre_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1
    
    await cb.answer()
    await state.clear()
    
    genre = db.get_genre(genre_id)
    if not genre:
        await send(cb.message.chat.id, cb.from_user.id, "❌ Жанр не найден")
        return
    
    session = user_sessions.get(cb.from_user.id)
    has_access = db.check_access(session['user_id'] if session else None, genre_id)
    
    if genre['is_paid'] and not has_access:
        text = (f"💎 <b>{genre['display_name']}</b>\n\n"
                f"{genre['description']}\n\n"
                f"Цена: {genre['price_stars']} ⭐ за 30 дней")
        kb = InlineKeyboardBuilder()
        kb.button(text=f"💫 Купить за {genre['price_stars']} ⭐", callback_data=f"buy_{genre_id}")
        kb.button(text="📋 Посмотреть игры", callback_data=f"preview_{genre_id}_1")
        kb.button(text="◀️ Назад", callback_data=f"back_genres_{genre_id}")
        kb.adjust(1)
        await send(cb.message.chat.id, cb.from_user.id, text, kb.as_markup())
        return
    
    games, cur_page, pages = db.get_games(genre_id, page)
    if not games:
        await send(cb.message.chat.id, cb.from_user.id, "😕 Игр пока нет",
                  genres_kb(genre['platform'], db.get_genres(genre['platform'])))
        return
    
    await send(cb.message.chat.id, cb.from_user.id,
              f"{genre['display_name']} ({len(games)} игр)",
              games_kb(games, genre_id, cur_page, pages))

@dp.callback_query(F.data.startswith("preview_"))
async def preview_cb(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    genre_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1
    
    await cb.answer()
    
    genre = db.get_genre(genre_id)
    games, cur_page, pages = db.get_games(genre_id, page)
    
    if games:
        await send(cb.message.chat.id, cb.from_user.id,
                  f"💎 {genre['display_name']} (предпросмотр)",
                  games_kb(games, genre_id, cur_page, pages))

@dp.callback_query(F.data.startswith("back_genres_"))
async def back_genres_cb(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("back_genres_", ""))
    genre = db.get_genre(genre_id)
    await cb.answer()
    await state.clear()
    if genre:
        genres = db.get_genres(genre['platform'])
        await send(cb.message.chat.id, cb.from_user.id,
                  f"{config.PLATFORMS[genre['platform']]['display']}\n\nВыбери жанр:",
                  genres_kb(genre['platform'], genres))

@dp.callback_query(F.data.startswith("back_games_"))
async def back_games_cb(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    genre_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 1
    
    await cb.answer()
    await state.clear()
    
    genre = db.get_genre(genre_id)
    games, cur_page, pages = db.get_games(genre_id, page)
    
    if games:
        await send(cb.message.chat.id, cb.from_user.id, genre['display_name'],
                  games_kb(games, genre_id, cur_page, pages))

# ================== ПОКУПКИ ==================
@dp.callback_query(F.data.startswith("buy_"))
async def buy_cb(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("buy_", ""))
    genre = db.get_genre(genre_id)
    await cb.answer()
    
    session = user_sessions.get(cb.from_user.id)
    if not session:
        await send(cb.message.chat.id, cb.from_user.id, "❌ Войдите в систему", login_kb())
        return
    
    await bot.send_invoice(
        chat_id=cb.message.chat.id,
        title=f"💎 {genre['display_name']}",
        description="30 дней доступа ко всем играм жанра",
        payload=f"pay_{genre_id}",
        provider_token="",
        currency="XTR",
        prices=[types.LabeledPrice(label=genre['display_name'], amount=genre['price_stars'])],
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=f"💫 Оплатить {genre['price_stars']} ⭐", pay=True)],
            [types.InlineKeyboardButton(text="◀️ Отмена", callback_data=f"genre_{genre_id}_1")]
        ])
    )

@dp.pre_checkout_query()
async def pre_checkout(q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def payment_success(msg: types.Message):
    payload = msg.successful_payment.invoice_payload
    if payload.startswith("pay_"):
        genre_id = int(payload.replace("pay_", ""))
        session = user_sessions.get(msg.from_user.id)
        if session:
            db.purchase_access(session['user_id'], genre_id)
            genre = db.get_genre(genre_id)
            await send(msg.chat.id, msg.from_user.id,
                      f"✅ Доступ к '{genre['display_name']}' открыт на 30 дней!")

# ================== ИГРЫ ==================
@dp.callback_query(F.data.startswith("game_"))
async def game_cb(cb: types.CallbackQuery, state: FSMContext):
    game_id = int(cb.data.replace("game_", ""))
    game = db.get_game(game_id)
    
    await cb.answer()
    await state.clear()
    
    if not game:
        await send(cb.message.chat.id, cb.from_user.id, "❌ Игра не найдена")
        return
    
    size = game['file_size'] / (1024 * 1024)
    text = (f"🎮 <b>{game['title']}</b>\n\n"
            f"{game['description']}\n\n"
            f"💾 Размер: {size:.1f} МБ\n"
            f"📥 Скачиваний: {game['download_count']}")
    
    session = user_sessions.get(cb.from_user.id)
    can_download = db.check_access(session['user_id'] if session else None, game['genre_id'])
    
    if game['is_paid'] and not can_download:
        text += f"\n\n⚠️ Платный жанр! Цена: {game['price_stars']} ⭐"
    
    if game['screenshots']:
        media = []
        for i, s in enumerate(game['screenshots']):
            if i == 0:
                media.append(types.InputMediaPhoto(media=s['file_id'], caption=text, parse_mode=ParseMode.HTML))
            else:
                media.append(types.InputMediaPhoto(media=s['file_id']))
        await send_media(cb.message.chat.id, cb.from_user.id, media)
        await send(cb.message.chat.id, cb.from_user.id, "Выбери действие:",
                  game_actions_kb(game_id, game['genre_id'], can_download, session is not None))
    else:
        await send(cb.message.chat.id, cb.from_user.id, text,
                  game_actions_kb(game_id, game['genre_id'], can_download, session is not None))

@dp.callback_query(F.data.startswith("download_"))
async def download_cb(cb: types.CallbackQuery, state: FSMContext):
    game_id = int(cb.data.replace("download_", ""))
    game = db.get_game(game_id)
    
    await cb.answer()
    await state.clear()
    
    if not game:
        await send(cb.message.chat.id, cb.from_user.id, "❌ Игра не найдена")
        return
    
    session = user_sessions.get(cb.from_user.id)
    can_download = db.check_access(session['user_id'] if session else None, game['genre_id'])
    
    if game['is_paid'] and not can_download:
        genre = db.get_genre(game['genre_id'])
        kb = InlineKeyboardBuilder()
        kb.button(text=f"💫 Купить за {genre['price_stars']} ⭐", callback_data=f"buy_{game['genre_id']}")
        kb.button(text="◀️ Назад", callback_data=f"game_{game_id}")
        kb.adjust(1)
        await send(cb.message.chat.id, cb.from_user.id,
                  f"❌ Нет доступа! Купите жанр '{genre['display_name']}'", kb.as_markup())
        return
    
    wait = await send(cb.message.chat.id, cb.from_user.id, "⏳ Отправляю файл...")
    try:
        db.inc_downloads(game_id)
        file = await bot.send_document(cb.message.chat.id, game['file_id'],
                                       caption=f"🎮 {game['title']}\n\nПриятной игры!")
        await add_msg(cb.from_user.id, file.message_id)
        if wait:
            await bot.delete_message(cb.message.chat.id, wait.message_id)
    except Exception as e:
        logger.error(f"Download error: {e}")
        await send(cb.message.chat.id, cb.from_user.id, "❌ Ошибка при отправке")

@dp.callback_query(F.data == "no_access")
async def no_access(cb: types.CallbackQuery):
    await cb.answer("❌ Нет доступа! Купите подписку на жанр.", show_alert=True)

# ================== КОММЕНТАРИИ ==================
@dp.callback_query(F.data.startswith("comments_"))
async def comments_cb(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split("_")
    game_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1
    
    await cb.answer()
    
    comments, cur_page, pages = db.get_comments(game_id, page)
    game = db.get_game(game_id)
    
    if not game:
        await send(cb.message.chat.id, cb.from_user.id, "❌ Игра не найдена")
        return
    
    text = f"💬 Комментарии к '{game['title']}'\n\n"
    if not comments:
        text += "Пока нет комментариев"
    else:
        for c in comments:
            text += f"👤 <b>{c['user_nickname']}</b> [{c['created_date'][:16]}]\n{c['text']}\n──────────────────\n"
    
    session = user_sessions.get(cb.from_user.id)
    await send(cb.message.chat.id, cb.from_user.id, text,
              comments_kb(game_id, cur_page, pages, session is not None))

@dp.callback_query(F.data.startswith("write_comment_"))
async def write_comment_start(cb: types.CallbackQuery, state: FSMContext):
    game_id = int(cb.data.replace("write_comment_", ""))
    await cb.answer()
    
    session = user_sessions.get(cb.from_user.id)
    if not session:
        await send(cb.message.chat.id, cb.from_user.id, "❌ Войдите в систему", login_kb())
        return
    
    await state.update_data(game_id=game_id)
    await state.set_state(Comment.text)
    await send(cb.message.chat.id, cb.from_user.id, "✏️ Введите комментарий:", cancel_kb())

@dp.message(Comment.text)
async def write_comment_text(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    session = user_sessions.get(msg.from_user.id)
    
    if not session:
        await send(msg.chat.id, msg.from_user.id, "❌ Сессия истекла")
        await state.clear()
        return
    
    db.add_comment(data['game_id'], session['user_id'], session['nickname'], msg.text.strip())
    await state.clear()
    await send(msg.chat.id, msg.from_user.id, "✅ Комментарий добавлен!")

# ================== ДОБАВЛЕНИЕ ИГР ==================
@dp.callback_query(AddGame.platform, F.data.startswith("admin_platform_"))
async def addgame_platform(cb: types.CallbackQuery, state: FSMContext):
    platform = cb.data.replace("admin_platform_", "")
    await state.update_data(platform=platform)
    
    genres = db.get_genres(platform)
    kb = InlineKeyboardBuilder()
    for g in genres:
        kb.button(text=g['display_name'], callback_data=f"addgame_genre_{g['id']}")
    kb.button(text="◀️ Назад", callback_data="cancel_add_game")
    kb.adjust(1)
    
    await cb.answer()
    await state.set_state(AddGame.genre)
    await send(cb.message.chat.id, cb.from_user.id, "Выбери жанр:", kb.as_markup())

@dp.callback_query(AddGame.genre, F.data.startswith("addgame_genre_"))
async def addgame_genre(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("addgame_genre_", ""))
    await state.update_data(genre_id=genre_id)
    await cb.answer()
    await state.set_state(AddGame.file)
    await send(cb.message.chat.id, cb.from_user.id, "📤 Отправь файл игры:")

@dp.callback_query(F.data == "cancel_add_game")
async def cancel_addgame(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await send(cb.message.chat.id, cb.from_user.id, "❌ Отменено")

@dp.message(AddGame.file, F.document)
async def addgame_file(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    doc = msg.document
    
    if db.game_exists(doc.file_id):
        await send(msg.chat.id, msg.from_user.id, "❌ Файл уже есть")
        await state.clear()
        return
    
    genre = db.get_genre(data['genre_id'])
    channel = config.PLATFORMS[genre['platform']]["channel_id"]
    
    wait = await send(msg.chat.id, msg.from_user.id, "⏳ Загружаю в хранилище...")
    
    try:
        sent = await bot.send_document(channel, doc.file_id, caption=f"📁 {doc.file_name}")
        await state.update_data(
            file_id=sent.document.file_id,
            file_name=doc.file_name,
            file_size=doc.file_size,
            msg_id=sent.message_id,
            channel_id=channel
        )
        if wait:
            await bot.delete_message(msg.chat.id, wait.message_id)
        await state.set_state(AddGame.title)
        await send(msg.chat.id, msg.from_user.id,
                  "📝 Введи название (или /skip для имени файла):")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        await send(msg.chat.id, msg.from_user.id, "❌ Ошибка загрузки")
        await state.clear()

@dp.message(AddGame.file)
async def addgame_file_invalid(msg: types.Message, state: FSMContext):
    await send(msg.chat.id, msg.from_user.id, "❌ Отправь файл")

@dp.message(AddGame.title)
async def addgame_title(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    if msg.text and msg.text != "/skip":
        title = msg.text
    else:
        title = Path(data['file_name']).stem
    await state.update_data(title=title)
    await state.set_state(AddGame.desc)
    await send(msg.chat.id, msg.from_user.id, "📝 Введи описание:")

@dp.message(AddGame.desc)
async def addgame_desc(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    game_id = db.add_game(
        data['title'], msg.text, data['file_name'], data['file_id'],
        data['file_size'], data['genre_id'], data['channel_id'], data['msg_id']
    )
    genre = db.get_genre(data['genre_id'])
    await state.clear()
    await send(msg.chat.id, msg.from_user.id,
              f"✅ Игра добавлена! ID: {game_id}\n/addscreenshots {game_id}")

# ================== ДОБАВЛЕНИЕ СКРИНШОТОВ ==================
@dp.message(AddScreenshots.screens, F.photo)
async def add_screenshot(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    screens = data.get('screens', [])
    
    if len(screens) >= 5:
        await send(msg.chat.id, msg.from_user.id, "❌ Максимум 5 скриншотов")
        return
    
    screens.append(msg.photo[-1].file_id)
    await state.update_data(screens=screens)
    await send(msg.chat.id, msg.from_user.id, f"✅ Добавлено ({len(screens)}/5)")

@dp.message(AddScreenshots.screens, F.text == "/done")
async def screenshots_done(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    for s in data.get('screens', []):
        db.add_screenshot(data['game_id'], s)
    await state.clear()
    await send(msg.chat.id, msg.from_user.id, "✅ Скриншоты сохранены!")

@dp.message(AddScreenshots.screens)
async def screenshots_invalid(msg: types.Message, state: FSMContext):
    await send(msg.chat.id, msg.from_user.id, "❌ Отправь фото или /done")

# ================== УПРАВЛЕНИЕ ЖАНРАМИ ==================
@dp.callback_query(F.data == "admin_genres")
async def admin_genres(cb: types.CallbackQuery):
    await cb.answer()
    genres = db.get_genres()
    await send(cb.message.chat.id, cb.from_user.id, "🎮 Управление жанрами:", admin_genres_kb(genres))

@dp.callback_query(F.data == "add_genre")
async def add_genre_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(GenreManage.name)
    await send(cb.message.chat.id, cb.from_user.id,
              "➕ Введите название (латиница, например 'rpg'):", cancel_kb())

@dp.message(GenreManage.name)
async def add_genre_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(GenreManage.display)
    await send(msg.chat.id, msg.from_user.id, "➕ Введите отображаемое название (с эмодзи):")

@dp.message(GenreManage.display)
async def add_genre_display(msg: types.Message, state: FSMContext):
    await state.update_data(display=msg.text.strip())
    await state.set_state(GenreManage.desc)
    await send(msg.chat.id, msg.from_user.id, "➕ Введите описание:")

@dp.message(GenreManage.desc)
async def add_genre_desc(msg: types.Message, state: FSMContext):
    await state.update_data(desc=msg.text.strip())
    await state.set_state(GenreManage.platform)
    await send(msg.chat.id, msg.from_user.id, "➕ Выбери платформу:", admin_platform_kb())

@dp.callback_query(GenreManage.platform, F.data.startswith("admin_platform_"))
async def add_genre_platform(cb: types.CallbackQuery, state: FSMContext):
    platform = cb.data.replace("admin_platform_", "")
    await state.update_data(platform=platform)
    await cb.answer()
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Платный", callback_data="genre_paid_yes")
    kb.button(text="❌ Бесплатный", callback_data="genre_paid_no")
    kb.adjust(1)
    
    await state.set_state(GenreManage.price)
    await send(cb.message.chat.id, cb.from_user.id, "➕ Жанр будет платным?", kb.as_markup())

@dp.callback_query(GenreManage.price, F.data == "genre_paid_yes")
async def add_genre_paid_yes(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(paid=True)
    await cb.answer()
    await state.set_state(GenreManage.price)
    await send(cb.message.chat.id, cb.from_user.id, "💰 Введите цену в Stars:")

@dp.callback_query(GenreManage.price, F.data == "genre_paid_no")
async def add_genre_paid_no(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db.add_genre(data['name'], data['display'], data['desc'], data['platform'], False, 0)
    await cb.answer()
    await state.clear()
    await send(cb.message.chat.id, cb.from_user.id, "✅ Бесплатный жанр добавлен!")

@dp.message(GenreManage.price)
async def add_genre_price(msg: types.Message, state: FSMContext):
    try:
        price = int(msg.text.strip())
        if price <= 0:
            raise ValueError
    except:
        await send(msg.chat.id, msg.from_user.id, "❌ Введите положительное число")
        return
    
    data = await state.get_data()
    db.add_genre(data['name'], data['display'], data['desc'], data['platform'], True, price)
    await state.clear()
    await send(msg.chat.id, msg.from_user.id, f"✅ Платный жанр добавлен за {price} ⭐!")

@dp.callback_query(F.data.startswith("edit_genre_"))
async def edit_genre(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("edit_genre_", ""))
    genre = db.get_genre(genre_id)
    await cb.answer()
    
    text = (f"✏️ <b>{genre['display_name']}</b>\n"
            f"Платформа: {config.PLATFORMS[genre['platform']]['display']}\n"
            f"Платный: {'✅' if genre['is_paid'] else '❌'}\n"
            f"Цена: {genre['price_stars']} ⭐\n"
            f"Описание: {genre['description']}")
    
    await send(cb.message.chat.id, cb.from_user.id, text, edit_genre_kb(genre_id))

@dp.callback_query(F.data.startswith("genre_edit_name_"))
async def edit_genre_name(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("genre_edit_name_", ""))
    await state.update_data(genre_id=genre_id, field='name')
    await cb.answer()
    await state.set_state(GenreManage.new_val)
    await send(cb.message.chat.id, cb.from_user.id, "✏️ Новое название:", cancel_kb())

@dp.callback_query(F.data.startswith("genre_edit_desc_"))
async def edit_genre_desc(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("genre_edit_desc_", ""))
    await state.update_data(genre_id=genre_id, field='desc')
    await cb.answer()
    await state.set_state(GenreManage.new_val)
    await send(cb.message.chat.id, cb.from_user.id, "✏️ Новое описание:", cancel_kb())

@dp.callback_query(F.data.startswith("genre_edit_price_"))
async def edit_genre_price(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("genre_edit_price_", ""))
    await state.update_data(genre_id=genre_id, field='price')
    await cb.answer()
    await state.set_state(GenreManage.new_val)
    await send(cb.message.chat.id, cb.from_user.id, "💰 Новая цена:", cancel_kb())

@dp.message(GenreManage.new_val)
async def update_genre(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    val = msg.text.strip()
    
    if data['field'] == 'name':
        db.update_genre(data['genre_id'], display_name=val)
        await send(msg.chat.id, msg.from_user.id, f"✅ Название обновлено: {val}")
    elif data['field'] == 'desc':
        db.update_genre(data['genre_id'], description=val)
        await send(msg.chat.id, msg.from_user.id, "✅ Описание обновлено")
    elif data['field'] == 'price':
        try:
            price = int(val)
            if price <= 0:
                raise ValueError
            db.update_genre(data['genre_id'], price_stars=price, is_paid=True)
            await send(msg.chat.id, msg.from_user.id, f"✅ Цена обновлена: {price} ⭐")
        except:
            await send(msg.chat.id, msg.from_user.id, "❌ Введите число")
            return
    await state.clear()

@dp.callback_query(F.data.startswith("genre_toggle_"))
async def toggle_genre_paid(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("genre_toggle_", ""))
    genre = db.get_genre(genre_id)
    
    if genre['is_paid']:
        db.update_genre(genre_id, is_paid=False, price_stars=0)
        await cb.answer("✅ Жанр стал бесплатным")
        await send(cb.message.chat.id, cb.from_user.id, f"✅ Жанр '{genre['display_name']}' теперь бесплатный!")
    else:
        await state.update_data(genre_id=genre_id)
        await cb.answer()
        await state.set_state(GenreManage.new_val)
        await send(cb.message.chat.id, cb.from_user.id, "💰 Введите цену:", cancel_kb())

@dp.callback_query(F.data.startswith("genre_delete_"))
async def delete_genre_confirm(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("genre_delete_", ""))
    genre = db.get_genre(genre_id)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"genre_delete_final_{genre_id}")
    kb.button(text="❌ Отмена", callback_data=f"edit_genre_{genre_id}")
    kb.adjust(1)
    
    await cb.answer()
    await send(cb.message.chat.id, cb.from_user.id,
              f"⚠️ Удалить '{genre['display_name']}'? Все игры удалятся!", kb.as_markup())

@dp.callback_query(F.data.startswith("genre_delete_final_"))
async def delete_genre_final(cb: types.CallbackQuery, state: FSMContext):
    genre_id = int(cb.data.replace("genre_delete_final_", ""))
    genre = db.get_genre(genre_id)
    
    if db.delete_genre(genre_id):
        await cb.answer("✅ Удалено")
        await send(cb.message.chat.id, cb.from_user.id, f"✅ Жанр '{genre['display_name']}' удален")
    else:
        await cb.answer("❌ Ошибка")

@dp.callback_query(F.data == "admin_back")
async def admin_back(cb: types.CallbackQuery):
    await cb.answer()
    await send(cb.message.chat.id, cb.from_user.id, "🛠 Админ-панель:", admin_main_kb())

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_cb(cb: types.CallbackQuery):
    await cb.answer()
    await cmd_stats(cb.message)

# ================== ЗАПУСК ==================
async def main():
    logger.info("🚀 GameVault запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())