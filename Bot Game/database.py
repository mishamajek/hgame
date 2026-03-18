import sqlite3
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib

class Database:
    def __init__(self, db_path='games.db'):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _hash(self, pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()
    
    def init_db(self):
        with self.get_conn() as conn:
            c = conn.cursor()
            
            # Пользователи
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                nickname TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # Жанры
            c.execute('''CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                is_paid INTEGER DEFAULT 0,
                price_stars INTEGER DEFAULT 0,
                platform TEXT NOT NULL
            )''')
            
            # Покупки
            c.execute('''CREATE TABLE IF NOT EXISTS purchases (
                user_id INTEGER NOT NULL,
                genre_id INTEGER NOT NULL,
                expiry_date TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE,
                UNIQUE(user_id, genre_id)
            )''')
            
            # Игры
            c.execute('''CREATE TABLE IF NOT EXISTS games (
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
                FOREIGN KEY (genre_id) REFERENCES genres(id)
            )''')
            
            # Скриншоты
            c.execute('''CREATE TABLE IF NOT EXISTS screenshots (
                game_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )''')
            
            # Комментарии
            c.execute('''CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_nickname TEXT NOT NULL,
                text TEXT NOT NULL,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )''')
            
            # Индексы
            c.execute('CREATE INDEX IF NOT EXISTS idx_games_genre ON games(genre_id)')
            
            # Жанры - ТОЛЬКО ПО 4 ШТУКИ ДЛЯ КАЖДОЙ ПЛАТФОРМЫ
            genres_data = [
                # Windows
                (1, 'simulator', '🎮 Симулятор', 'Игры-симуляторы', 0, 0, 'windows'),
                (2, 'novel', '📖 Новелла', 'Визуальные новеллы', 0, 0, 'windows'),
                (3, 'rpg', '⚔️ RPG', 'Ролевые игры', 0, 0, 'windows'),
                (4, 'fighting', '👊 Файтинг', 'Файтинги', 0, 0, 'windows'),
                # Android
                (5, 'android_sim', '🎮 Симулятор', 'Симуляторы для Android', 0, 0, 'android'),
                (6, 'android_novel', '📖 Новелла', 'Новеллы для Android', 0, 0, 'android'),
                (7, 'android_rpg', '⚔️ RPG', 'RPG для Android', 0, 0, 'android'),
                (8, 'android_fight', '👊 Файтинг', 'Файтинги для Android', 0, 0, 'android')
            ]
            
            for id, name, display, desc, paid, price, platform in genres_data:
                c.execute('''INSERT OR IGNORE INTO genres 
                    (id, name, display_name, description, is_paid, price_stars, platform)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''', (id, name, display, desc, paid, price, platform))
            
            conn.commit()
    
    # === ПОЛЬЗОВАТЕЛИ ===
    def register(self, tg_id, nick, pwd):
        with self.get_conn() as conn:
            try:
                c = conn.cursor()
                c.execute('INSERT INTO users (telegram_id, nickname, password) VALUES (?, ?, ?)',
                         (tg_id, nick, self._hash(pwd)))
                conn.commit()
                return c.lastrowid
            except:
                return None
    
    def login(self, nick, pwd):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE nickname = ? AND password = ?',
                     (nick, self._hash(pwd)))
            row = c.fetchone()
            return dict(row) if row else None
    
    def get_user_by_telegram(self, tg_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE telegram_id = ?', (tg_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def get_user_by_id(self, user_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def link_telegram(self, user_id, tg_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET telegram_id = ? WHERE id = ?', (tg_id, user_id))
            conn.commit()
            return c.rowcount > 0
    
    # === ЖАНРЫ ===
    def get_genres(self, platform=None):
        with self.get_conn() as conn:
            c = conn.cursor()
            if platform:
                c.execute('SELECT * FROM genres WHERE platform = ? ORDER BY id', (platform,))
            else:
                c.execute('SELECT * FROM genres ORDER BY platform, id')
            return [dict(r) for r in c.fetchall()]
    
    def get_genre(self, genre_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM genres WHERE id = ?', (genre_id,))
            row = c.fetchone()
            return dict(row) if row else None
    
    def add_genre(self, name, display, desc, platform, paid=False, price=0):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO genres (name, display_name, description, platform, is_paid, price_stars)
                        VALUES (?, ?, ?, ?, ?, ?)''', (name, display, desc, platform, 1 if paid else 0, price))
            conn.commit()
            return c.lastrowid
    
    def update_genre(self, genre_id, **kwargs):
        with self.get_conn() as conn:
            c = conn.cursor()
            updates = []
            values = []
            for k, v in kwargs.items():
                if k in ['display_name', 'description', 'is_paid', 'price_stars']:
                    updates.append(f"{k} = ?")
                    values.append(v)
            if not updates:
                return False
            values.append(genre_id)
            c.execute(f'UPDATE genres SET {", ".join(updates)} WHERE id = ?', values)
            conn.commit()
            return c.rowcount > 0
    
    def delete_genre(self, genre_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM genres WHERE id = ?', (genre_id,))
            conn.commit()
            return c.rowcount > 0
    
    # === ПЛАТНЫЙ ДОСТУП ===
    def purchase_access(self, user_id, genre_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            expiry = (datetime.now() + timedelta(days=30)).isoformat()
            c.execute('''INSERT OR REPLACE INTO purchases (user_id, genre_id, expiry_date)
                        VALUES (?, ?, ?)''', (user_id, genre_id, expiry))
            conn.commit()
            return True
    
    def check_access(self, user_id, genre_id):
        if not user_id:
            return False
        genre = self.get_genre(genre_id)
        if not genre or not genre['is_paid']:
            return True
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('''SELECT * FROM purchases WHERE user_id = ? AND genre_id = ? 
                        AND expiry_date > CURRENT_TIMESTAMP''', (user_id, genre_id))
            return c.fetchone() is not None
    
    def get_purchases(self, user_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('''SELECT g.*, p.expiry_date FROM genres g
                        JOIN purchases p ON g.id = p.genre_id
                        WHERE p.user_id = ? AND p.expiry_date > CURRENT_TIMESTAMP''', (user_id,))
            return [dict(r) for r in c.fetchall()]
    
    # === ИГРЫ ===
    def get_games(self, genre_id, page=1, per_page=5):
        offset = (page - 1) * per_page
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) as total FROM games WHERE genre_id = ?', (genre_id,))
            total = c.fetchone()['total']
            pages = max(1, (total + per_page - 1) // per_page if total > 0 else 1)
            
            c.execute('''SELECT id, title, file_size, download_count FROM games 
                        WHERE genre_id = ? ORDER BY title LIMIT ? OFFSET ?''',
                     (genre_id, per_page, offset))
            games = [dict(r) for r in c.fetchall()]
            return games, page, pages
    
    def add_game(self, title, desc, filename, file_id, size, genre_id, channel_id, msg_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO games (title, description, file_name, file_id, file_size,
                        genre_id, channel_id, message_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (title, desc, filename, file_id, size, genre_id, channel_id, msg_id))
            conn.commit()
            return c.lastrowid
    
    def get_game(self, game_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('''SELECT g.*, gr.display_name as genre_name, gr.is_paid, gr.price_stars
                        FROM games g JOIN genres gr ON g.genre_id = gr.id
                        WHERE g.id = ?''', (game_id,))
            game = c.fetchone()
            if not game:
                return None
            result = dict(game)
            c.execute('SELECT file_id FROM screenshots WHERE game_id = ?', (game_id,))
            result['screenshots'] = [dict(r) for r in c.fetchall()]
            return result
    
    def inc_downloads(self, game_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE games SET download_count = download_count + 1 WHERE id = ?', (game_id,))
            conn.commit()
    
    def game_exists(self, file_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM games WHERE file_id = ?', (file_id,))
            return c.fetchone() is not None
    
    # === СКРИНШОТЫ ===
    def add_screenshot(self, game_id, file_id):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('INSERT INTO screenshots (game_id, file_id) VALUES (?, ?)', (game_id, file_id))
            conn.commit()
    
    # === КОММЕНТАРИИ ===
    def add_comment(self, game_id, user_id, nickname, text):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO comments (game_id, user_id, user_nickname, text)
                        VALUES (?, ?, ?, ?)''', (game_id, user_id, nickname, text))
            conn.commit()
            return c.lastrowid
    
    def get_comments(self, game_id, page=1, per_page=5):
        offset = (page - 1) * per_page
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) as total FROM comments WHERE game_id = ?', (game_id,))
            total = c.fetchone()['total']
            pages = max(1, (total + per_page - 1) // per_page if total > 0 else 1)
            
            c.execute('''SELECT * FROM comments WHERE game_id = ? 
                        ORDER BY created_date DESC LIMIT ? OFFSET ?''',
                     (game_id, per_page, offset))
            return [dict(r) for r in c.fetchall()], page, pages
    
    # === СТАТИСТИКА ===
    def get_stats(self):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM games'); games = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM users'); users = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM genres'); genres = c.fetchone()[0]
            c.execute('SELECT SUM(download_count) FROM games'); dl = c.fetchone()[0] or 0
            return {'games': games, 'users': users, 'genres': genres, 'downloads': dl}