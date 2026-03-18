import sqlite3

# Подключаемся к существующей базе
conn = sqlite3.connect('games.db')
cursor = conn.cursor()

try:
    # Проверяем, есть ли колонка genre_id в таблице games
    cursor.execute("PRAGMA table_info(games)")
    columns = cursor.fetchall()
    has_genre_id = any(col[1] == 'genre_id' for col in columns)
    
    if has_genre_id:
        print("✅ Колонка genre_id уже существует")
    else:
        print("🔄 Добавляем колонку genre_id...")
        # Добавляем колонку genre_id
        cursor.execute("ALTER TABLE games ADD COLUMN genre_id INTEGER DEFAULT 1")
        print("✅ Колонка добавлена")
    
    # Пробуем создать индекс
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_genre ON games(genre_id)")
        print("✅ Индекс создан")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Ошибка при создании индекса: {e}")
    
    conn.commit()
    print("🎉 База данных успешно обновлена!")

except Exception as e:
    print(f"❌ Ошибка: {e}")
finally:
    conn.close()