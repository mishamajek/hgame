import sqlite3
import os

print("⚠️ ВНИМАНИЕ: Это удалит существующую базу данных games.db")
answer = input("Продолжить? (да/нет): ")

if answer.lower() != 'да':
    print("❌ Операция отменена")
    exit()

# Удаляем старую базу если есть
if os.path.exists('games.db'):
    os.remove('games.db')
    print("✅ Старая база удалена")

# Создаем новую базу
conn = sqlite3.connect('games.db')
cursor = conn.cursor()

# Таблица пользователей
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        nickname TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
''')

# Таблица жанров (ТОЛЬКО НУЖНЫЕ)
cursor.execute('''
    CREATE TABLE genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        display_name TEXT NOT NULL,
        description TEXT,
        is_paid BOOLEAN DEFAULT 0,
        price_stars INTEGER DEFAULT 0,
        platform TEXT NOT NULL,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Таблица покупок жанров
cursor.execute('''
    CREATE TABLE genre_purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        genre_id INTEGER NOT NULL,
        purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expiry_date TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE,
        UNIQUE(user_id, genre_id)
    )
''')

# Таблица игр
cursor.execute('''
    CREATE TABLE games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        file_name TEXT NOT NULL,
        file_id TEXT NOT NULL UNIQUE,
        file_size INTEGER,
        genre_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        download_count INTEGER DEFAULT 0,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY (genre_id) REFERENCES genres(id)
    )
''')

# Таблица скриншотов
cursor.execute('''
    CREATE TABLE game_screenshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER NOT NULL,
        file_id TEXT NOT NULL,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
    )
''')

# Таблица комментариев
cursor.execute('''
    CREATE TABLE comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        user_nickname TEXT NOT NULL,
        text TEXT NOT NULL,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
''')

# Создаем индексы
cursor.execute('CREATE INDEX idx_games_genre ON games(genre_id)')
cursor.execute('CREATE INDEX idx_comments_game ON comments(game_id)')
cursor.execute('CREATE INDEX idx_purchases_user ON genre_purchases(user_id)')

# ========== ДОБАВЛЯЕМ ТОЛЬКО НУЖНЫЕ ЖАНРЫ ==========
print("\n📋 Добавляем жанры:")

# Windows жанры
windows_genres = [
    ('simulator', '🎮 Симулятор', 'Игры-симуляторы', 'windows', 0, 0),
    ('novel', '📖 Новелла', 'Визуальные новеллы', 'windows', 0, 0),
    ('rpg', '⚔️ RPG', 'Ролевые игры', 'windows', 0, 0),
    ('fighting', '👊 Файтинг', 'Файтинги', 'windows', 0, 0),
]

for name, display, desc, platform, is_paid, price in windows_genres:
    cursor.execute('''
        INSERT INTO genres (name, display_name, description, platform, is_paid, price_stars)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, display, desc, platform, is_paid, price))
    print(f"  ✅ {display} (Windows)")

# Android жанры (те же названия, но для Android)
android_genres = [
    ('android_simulator', '🎮 Симулятор', 'Симуляторы для Android', 'android', 0, 0),
    ('android_novel', '📖 Новелла', 'Визуальные новеллы для Android', 'android', 0, 0),
    ('android_rpg', '⚔️ RPG', 'Ролевые игры для Android', 'android', 0, 0),
    ('android_fighting', '👊 Файтинг', 'Файтинги для Android', 'android', 0, 0),
]

for name, display, desc, platform, is_paid, price in android_genres:
    cursor.execute('''
        INSERT INTO genres (name, display_name, description, platform, is_paid, price_stars)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, display, desc, platform, is_paid, price))
    print(f"  ✅ {display} (Android)")

conn.commit()

# Показываем результат
cursor.execute("SELECT id, display_name, platform FROM genres ORDER BY platform, id")
genres = cursor.fetchall()

print("\n📊 Итоговый список жанров:")
print("-" * 40)
for g in genres:
    print(f"  ID {g[0]}: {g[1]} | {g[2]}")
print("-" * 40)

conn.close()
print("\n🎉 Новая база данных создана!")
print("\nТеперь вы можете добавлять игры заново через админ-панель.")
print("ID жанров для справки:")
print("  Windows:")
print("    1 - 🎮 Симулятор")
print("    2 - 📖 Новелла")
print("    3 - ⚔️ RPG")
print("    4 - 👊 Файтинг")
print("  Android:")
print("    5 - 🎮 Симулятор")
print("    6 - 📖 Новелла")
print("    7 - ⚔️ RPG")
print("    8 - 👊 Файтинг")