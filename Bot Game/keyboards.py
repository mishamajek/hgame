from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PLATFORMS

def platforms_kb():
    builder = InlineKeyboardBuilder()
    for key, data in PLATFORMS.items():
        builder.button(text=data["display"], callback_data=f"platform_{key}")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()

def genres_kb(platform, genres):
    builder = InlineKeyboardBuilder()
    for g in genres:
        if g['platform'] == platform:
            text = g['display_name']
            if g['is_paid']:
                text += f" 💎 {g['price_stars']} ⭐"
            builder.button(text=text, callback_data=f"genre_{g['id']}_1")
    builder.button(text="◀️ Назад", callback_data="back_platforms")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.adjust(2)
    return builder.as_markup()

def games_kb(games, genre_id, page, pages):
    builder = InlineKeyboardBuilder()
    for g in games:
        size = g['file_size'] / (1024 * 1024)
        builder.button(text=f"{g['title']} ({size:.1f} МБ)", callback_data=f"game_{g['id']}")
    
    # Строка пагинации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"genre_{genre_id}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{pages}", callback_data="ignore"))
    if page < pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"genre_{genre_id}_{page+1}"))
    
    builder.row(*nav_buttons)
    builder.button(text="◀️ К жанрам", callback_data=f"back_genres_{genre_id}")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()

def game_actions_kb(game_id, genre_id, can_download=False, logged_in=False):
    builder = InlineKeyboardBuilder()
    if can_download:
        builder.button(text="📥 Скачать", callback_data=f"download_{game_id}")
    else:
        builder.button(text="🔒 Нет доступа", callback_data="no_access")
    builder.button(text="💬 Комментарии", callback_data=f"comments_{game_id}_1")
    if logged_in:
        builder.button(text="✏️ Комментировать", callback_data=f"write_comment_{game_id}")
    builder.button(text="◀️ Назад", callback_data=f"back_games_{genre_id}_1")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()

def comments_kb(game_id, page, pages, logged_in=False):
    builder = InlineKeyboardBuilder()
    
    # Строка пагинации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"comments_{game_id}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{pages}", callback_data="ignore"))
    if page < pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"comments_{game_id}_{page+1}"))
    
    builder.row(*nav_buttons)
    
    if logged_in:
        builder.button(text="✏️ Написать", callback_data=f"write_comment_{game_id}")
    builder.button(text="◀️ К игре", callback_data=f"game_{game_id}")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.adjust(1)
    return builder.as_markup()

def profile_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Подписки", callback_data="my_subscriptions")
    builder.button(text="◀️ На главную", callback_data="back_platforms")
    builder.adjust(1)
    return builder.as_markup()

def login_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔑 Войти", callback_data="login")
    builder.button(text="📝 Регистрация", callback_data="register")
    builder.button(text="◀️ Назад", callback_data="back_platforms")
    builder.adjust(1)
    return builder.as_markup()

def cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()

def admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Управление жанрами", callback_data="admin_genres")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="➕ Добавить игру", callback_data="admin_add_game")
    builder.button(text="◀️ Выход", callback_data="back_platforms")
    builder.adjust(1)
    return builder.as_markup()

def admin_platform_kb():
    builder = InlineKeyboardBuilder()
    for key, data in PLATFORMS.items():
        builder.button(text=data["display"], callback_data=f"admin_platform_{key}")
    builder.button(text="❌ Отмена", callback_data="cancel_add_game")
    builder.adjust(1)
    return builder.as_markup()

def admin_genres_kb(genres):
    builder = InlineKeyboardBuilder()
    for g in genres:
        text = f"{g['display_name']}"
        if g['is_paid']:
            text += f" 💎 {g['price_stars']}⭐"
        builder.button(text=text, callback_data=f"edit_genre_{g['id']}")
    builder.button(text="➕ Добавить жанр", callback_data="add_genre")
    builder.button(text="◀️ Назад", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()

def edit_genre_kb(genre_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Название", callback_data=f"genre_edit_name_{genre_id}")
    builder.button(text="📋 Описание", callback_data=f"genre_edit_desc_{genre_id}")
    builder.button(text="💰 Цена", callback_data=f"genre_edit_price_{genre_id}")
    builder.button(text="💎 Платный/бесплатный", callback_data=f"genre_toggle_{genre_id}")
    builder.button(text="❌ Удалить", callback_data=f"genre_delete_{genre_id}")
    builder.button(text="◀️ Назад", callback_data="admin_genres")
    builder.adjust(1)
    return builder.as_markup()