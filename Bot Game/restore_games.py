import sqlite3

# Подключаемся к базе
conn = sqlite3.connect('games.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("🔍 Анализ базы данных...")

# Получаем все жанры
cursor.execute("SELECT id, name, display_name, platform FROM genres")
genres = cursor.fetchall()
print(f"\n📋 Доступные жанры:")
for g in genres:
    print(f"  ID: {g['id']} | {g['display_name']} | {g['platform']}")

# Получаем все игры с их текущим genre_id
cursor.execute("SELECT id, title, genre_id, file_name FROM games")
games = cursor.fetchall()
print(f"\n🎮 Найдено игр: {len(games)}")

# Проверяем, есть ли игры с genre_id = NULL или 0
cursor.execute("SELECT COUNT(*) FROM games WHERE genre_id IS NULL OR genre_id = 0")
invalid = cursor.fetchone()[0]
print(f"⚠️ Игр без жанра: {invalid}")

if invalid > 0:
    print("\n🔄 Восстанавливаем связи...")
    
    # Для каждой игры без жанра пытаемся определить жанр из названия
    cursor.execute("SELECT * FROM games WHERE genre_id IS NULL OR genre_id = 0")
    games_to_fix = cursor.fetchall()
    
    fixed = 0
    for game in games_to_fix:
        # Пытаемся определить жанр по названию файла или другим признакам
        # По умолчанию ставим первый попавшийся жанр для этой платформы
        file_name = game['file_name'].lower()
        
        # Простой алгоритм: ищем ключевые слова в названии
        genre_id = 1  # По умолчанию
        
        for genre in genres:
            if genre['name'].lower() in file_name:
                genre_id = genre['id']
                break
        
        cursor.execute("UPDATE games SET genre_id = ? WHERE id = ?", (genre_id, game['id']))
        fixed += 1
        print(f"  Игра '{game['title']}' -> жанр ID {genre_id}")
    
    conn.commit()
    print(f"\n✅ Восстановлено {fixed} игр!")

# Показываем итог
print("\n📊 Итоговое распределение игр по жанрам:")
cursor.execute("""
    SELECT g.display_name, COUNT(*) as count 
    FROM games 
    JOIN genres g ON games.genre_id = g.id 
    GROUP BY games.genre_id
""")
stats = cursor.fetchall()
for stat in stats:
    print(f"  {stat['display_name']}: {stat['count']} игр")

conn.close()
print("\n🎉 Готово! Теперь можно запускать бота.")