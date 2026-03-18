import sqlite3

conn = sqlite3.connect('games.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Получаем все жанры
cursor.execute("SELECT id, display_name, platform FROM genres ORDER BY platform, id")
genres = cursor.fetchall()

print("\n📋 ДОСТУПНЫЕ ЖАНРЫ:")
print("-" * 40)
for g in genres:
    print(f"  ID {g['id']}: {g['display_name']} | {g['platform']}")
print("-" * 40)

# Получаем все игры, которые сейчас в симуляторе (ID 1)
cursor.execute("SELECT id, title, file_name FROM games WHERE genre_id = 1")
games = cursor.fetchall()

print(f"\n🎮 Найдено игр в жанре 'Симулятор': {len(games)}")
print("\n" + "="*60)

for idx, game in enumerate(games, 1):
    print(f"\n[{idx}/{len(games)}] ИГРА:")
    print(f"   ID: {game['id']}")
    print(f"   Название: {game['title']}")
    print(f"   Файл: {game['file_name']}")
    print()
    
    print("   Выберите жанр (введите ID):")
    for g in genres:
        print(f"     {g['id']} - {g['display_name']}")
    
    while True:
        try:
            choice = input("\n   Ваш выбор (ID жанра или 's' пропустить, 'q' выйти): ").strip()
            
            if choice.lower() == 'q':
                conn.commit()
                print("\n💾 Изменения сохранены!")
                conn.close()
                exit()
            
            if choice.lower() == 's':
                print("   ⏭️ Пропущено")
                break
            
            genre_id = int(choice)
            
            # Проверяем существование жанра
            cursor.execute("SELECT id FROM genres WHERE id = ?", (genre_id,))
            if cursor.fetchone():
                cursor.execute("UPDATE games SET genre_id = ? WHERE id = ?", (genre_id, game['id']))
                conn.commit()
                print(f"   ✅ Игра перенесена в жанр ID {genre_id}")
                break
            else:
                print("   ❌ Неверный ID жанра")
        except ValueError:
            print("   ❌ Введите число")
    
    print("-"*40)

conn.commit()
print("\n🎉 Все игры обработаны!")
conn.close()