"""
db.py
SQLite data layer for the E-Book Platform.
Schema follows the spec: Users, Books, Authors, Categories, Library,
Wishlist, Purchases, Reviews, Bookmarks, Notifications (+ Highlights, Settings).

NOTE ON PERSISTENCE:
Streamlit Community Cloud gives each app an ephemeral filesystem — the
SQLite file and any uploaded book files are wiped on reboot / redeploy.
That's fine for a demo. For production, swap this module's connection
for Postgres (e.g. Supabase/Neon) and point file storage at S3 / GCS.
Every function below is isolated so that swap only touches this file.
"""

import sqlite3
import hashlib
import uuid
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ebook_platform.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password TEXT NOT NULL,
        profile_image TEXT,
        is_admin INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS authors (
        author_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        biography TEXT,
        profile_image TEXT
    );

    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        image TEXT
    );

    CREATE TABLE IF NOT EXISTS books (
        book_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author_id INTEGER,
        category_id INTEGER,
        description TEXT,
        cover_image TEXT,
        file_url TEXT,
        format TEXT,
        language TEXT,
        price REAL DEFAULT 0,
        publication_date TEXT,
        status TEXT DEFAULT 'published',
        downloads INTEGER DEFAULT 0,
        FOREIGN KEY (author_id) REFERENCES authors(author_id),
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
    );

    CREATE TABLE IF NOT EXISTS library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_id INTEGER,
        progress REAL DEFAULT 0,
        last_page INTEGER DEFAULT 0,
        total_pages INTEGER DEFAULT 0,
        status TEXT DEFAULT 'reading',
        last_opened TEXT,
        UNIQUE(user_id, book_id)
    );

    CREATE TABLE IF NOT EXISTS wishlist (
        user_id INTEGER,
        book_id INTEGER,
        added_at TEXT,
        PRIMARY KEY (user_id, book_id)
    );

    CREATE TABLE IF NOT EXISTS purchases (
        purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE,
        user_id INTEGER,
        book_id INTEGER,
        amount REAL,
        payment_status TEXT,
        purchase_date TEXT
    );

    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_id INTEGER,
        rating INTEGER,
        review TEXT,
        likes INTEGER DEFAULT 0,
        reported INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS review_likes (
        user_id INTEGER,
        review_id INTEGER,
        PRIMARY KEY (user_id, review_id)
    );

    CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_id INTEGER,
        page INTEGER,
        note TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS highlights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        book_id INTEGER,
        page INTEGER,
        text TEXT,
        color TEXT,
        note TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        message TEXT,
        type TEXT,
        status TEXT DEFAULT 'unread',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS reader_settings (
        user_id INTEGER PRIMARY KEY,
        font_size INTEGER DEFAULT 18,
        font_family TEXT DEFAULT 'Serif',
        line_spacing REAL DEFAULT 1.5,
        alignment TEXT DEFAULT 'left',
        theme TEXT DEFAULT 'Light',
        brightness INTEGER DEFAULT 100
    );

    CREATE TABLE IF NOT EXISTS seed_lock (
        id INTEGER PRIMARY KEY
    );
    """)
    conn.commit()

    # Seed an admin account + demo categories if empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (name, email, phone, password, is_admin, created_at) VALUES (?,?,?,?,?,?)",
            ("Admin", "admin@bookstore.com", "0000000000", hash_password("admin123"), 1, now()),
        )
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        for cat in ["Fiction", "Non-Fiction", "Sci-Fi", "Self-Help", "Business", "Poetry"]:
            c.execute("INSERT INTO categories (name) VALUES (?)", (cat,))
    conn.commit()
    conn.close()


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ---------- SEEDING / RESET GUARDS ----------
def try_acquire_seed_lock():
    """
    Atomic guard so concurrent sessions on first load can't both seed demo
    data. SQLite serializes writes across connections/processes, so only one
    caller's INSERT can win a primary-key collision on id=1 — the rest get
    an IntegrityError and back off. Returns True only for the winner.
    """
    conn = get_conn()
    try:
        conn.execute("INSERT INTO seed_lock (id) VALUES (1)")
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_author_by_name(name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM authors WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def factory_reset_catalog():
    """
    Wipes all catalog/activity data (books, authors, purchases, library,
    wishlist, reviews, bookmarks, highlights, notifications, seed lock) but
    keeps user accounts and categories, then lets seed_demo repopulate
    cleanly. Used by the admin 'danger zone' to recover from duplicated /
    inconsistent demo data without redeploying.
    """
    conn = get_conn()
    for table in ["books", "authors", "purchases", "library", "wishlist",
                  "reviews", "review_likes", "bookmarks", "highlights",
                  "notifications", "seed_lock"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


# ---------- USERS ----------
def create_user(name, email, phone, password):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (name, email, phone, password, created_at) VALUES (?,?,?,?,?)",
            (name, email, phone, hash_password(password), now()),
        )
        conn.commit()
        push_notification(get_user_by_email(email)["user_id"], "Welcome!",
                           f"Hi {name}, welcome to the bookstore.", "system")
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "Email already registered."
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_login(email, password):
    user = get_user_by_email(email)
    if user and user["password"] == hash_password(password):
        return user
    return None


def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_profile_image(user_id, path):
    conn = get_conn()
    conn.execute("UPDATE users SET profile_image=? WHERE user_id=?", (path, user_id))
    conn.commit()
    conn.close()


# ---------- AUTHORS / CATEGORIES ----------
def add_author(name, bio="", image=None):
    conn = get_conn()
    cur = conn.execute("INSERT INTO authors (name, biography, profile_image) VALUES (?,?,?)", (name, bio, image))
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def list_authors():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM authors ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name, image=None):
    conn = get_conn()
    conn.execute("INSERT INTO categories (name, image) VALUES (?,?)", (name, image))
    conn.commit()
    conn.close()


def list_categories():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- BOOKS ----------
def add_book(title, author_id, category_id, description, cover_image, file_url,
             fmt, language, price, pub_date, status="published"):
    conn = get_conn()
    cur = conn.execute("""INSERT INTO books
        (title, author_id, category_id, description, cover_image, file_url, format, language, price, publication_date, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (title, author_id, category_id, description, cover_image, file_url, fmt, language, price, pub_date, status))
    conn.commit()
    bid = cur.lastrowid
    conn.close()
    # notify all users of new release
    broadcast_notification("New release!", f"'{title}' just landed in the store.", "new_release")
    return bid


def list_books(search=None, category_id=None, status="published"):
    conn = get_conn()
    q = """SELECT b.*, a.name as author_name, c.name as category_name
           FROM books b LEFT JOIN authors a ON b.author_id=a.author_id
           LEFT JOIN categories c ON b.category_id=c.category_id WHERE 1=1"""
    params = []
    if status:
        q += " AND b.status=?"
        params.append(status)
    if search:
        q += " AND (b.title LIKE ? OR a.name LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if category_id:
        q += " AND b.category_id=?"
        params.append(category_id)
    q += " ORDER BY b.book_id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_book(book_id):
    conn = get_conn()
    row = conn.execute("""SELECT b.*, a.name as author_name, c.name as category_name
                           FROM books b LEFT JOIN authors a ON b.author_id=a.author_id
                           LEFT JOIN categories c ON b.category_id=c.category_id
                           WHERE b.book_id=?""", (book_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def increment_downloads(book_id):
    conn = get_conn()
    conn.execute("UPDATE books SET downloads = downloads + 1 WHERE book_id=?", (book_id,))
    conn.commit()
    conn.close()


def delete_book(book_id):
    conn = get_conn()
    conn.execute("DELETE FROM books WHERE book_id=?", (book_id,))
    conn.commit()
    conn.close()


# ---------- LIBRARY / PROGRESS ----------
def add_to_library(user_id, book_id, total_pages=0):
    conn = get_conn()
    conn.execute("""INSERT INTO library (user_id, book_id, progress, last_page, total_pages, status, last_opened)
                     VALUES (?,?,0,0,?,'reading',?)
                     ON CONFLICT(user_id, book_id) DO UPDATE SET total_pages=excluded.total_pages""",
                 (user_id, book_id, total_pages, now()))
    conn.commit()
    conn.close()


def update_progress(user_id, book_id, last_page, total_pages):
    progress = round((last_page / total_pages) * 100, 1) if total_pages else 0
    status = "completed" if progress >= 99.5 else "reading"
    conn = get_conn()
    conn.execute("""INSERT INTO library (user_id, book_id, progress, last_page, total_pages, status, last_opened)
                     VALUES (?,?,?,?,?,?,?)
                     ON CONFLICT(user_id, book_id) DO UPDATE SET
                        progress=excluded.progress, last_page=excluded.last_page,
                        total_pages=excluded.total_pages, status=excluded.status, last_opened=excluded.last_opened""",
                 (user_id, book_id, progress, last_page, total_pages, status, now()))
    conn.commit()
    conn.close()


def get_library_entry(user_id, book_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM library WHERE user_id=? AND book_id=?", (user_id, book_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_library(user_id):
    conn = get_conn()
    rows = conn.execute("""SELECT l.*, b.title, b.cover_image, b.format, a.name as author_name
                            FROM library l JOIN books b ON l.book_id=b.book_id
                            LEFT JOIN authors a ON b.author_id=a.author_id
                            WHERE l.user_id=? ORDER BY l.last_opened DESC""", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def owns_book(user_id, book_id):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM purchases WHERE user_id=? AND book_id=? AND payment_status='Success'",
                        (user_id, book_id)).fetchone()
    conn.close()
    return row is not None


# ---------- WISHLIST ----------
def toggle_wishlist(user_id, book_id):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM wishlist WHERE user_id=? AND book_id=?", (user_id, book_id)).fetchone()
    if row:
        conn.execute("DELETE FROM wishlist WHERE user_id=? AND book_id=?", (user_id, book_id))
        added = False
    else:
        conn.execute("INSERT INTO wishlist (user_id, book_id, added_at) VALUES (?,?,?)", (user_id, book_id, now()))
        added = True
    conn.commit()
    conn.close()
    return added


def is_wishlisted(user_id, book_id):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM wishlist WHERE user_id=? AND book_id=?", (user_id, book_id)).fetchone()
    conn.close()
    return row is not None


def get_wishlist(user_id):
    conn = get_conn()
    rows = conn.execute("""SELECT w.*, b.title, b.cover_image, b.price, a.name as author_name
                            FROM wishlist w JOIN books b ON w.book_id=b.book_id
                            LEFT JOIN authors a ON b.author_id=a.author_id
                            WHERE w.user_id=?""", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- PURCHASES ----------
def make_purchase(user_id, book_id, amount):
    txn_id = "TXN-" + uuid.uuid4().hex[:12].upper()
    conn = get_conn()
    conn.execute("""INSERT INTO purchases (transaction_id, user_id, book_id, amount, payment_status, purchase_date)
                     VALUES (?,?,?,?,?,?)""", (txn_id, user_id, book_id, amount, "Success", now()))
    conn.commit()
    conn.close()
    book = get_book(book_id)
    push_notification(user_id, "Purchase confirmed",
                       f"You bought '{book['title']}' for ${amount:.2f}. Txn: {txn_id}", "purchase")
    add_to_library(user_id, book_id)
    return txn_id


def get_purchases(user_id):
    conn = get_conn()
    rows = conn.execute("""SELECT p.*, b.title, b.cover_image, b.format
                            FROM purchases p JOIN books b ON p.book_id=b.book_id
                            WHERE p.user_id=? ORDER BY p.purchase_date DESC""", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def all_purchases():
    conn = get_conn()
    rows = conn.execute("""SELECT p.*, b.title, u.name as user_name
                            FROM purchases p JOIN books b ON p.book_id=b.book_id
                            JOIN users u ON p.user_id=u.user_id
                            ORDER BY p.purchase_date DESC""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- REVIEWS ----------
def add_review(user_id, book_id, rating, text):
    conn = get_conn()
    existing = conn.execute("SELECT review_id FROM reviews WHERE user_id=? AND book_id=?",
                             (user_id, book_id)).fetchone()
    if existing:
        conn.execute("UPDATE reviews SET rating=?, review=?, created_at=? WHERE review_id=?",
                     (rating, text, now(), existing["review_id"]))
    else:
        conn.execute("INSERT INTO reviews (user_id, book_id, rating, review, created_at) VALUES (?,?,?,?,?)",
                     (user_id, book_id, rating, text, now()))
    conn.commit()
    conn.close()


def delete_review(review_id):
    conn = get_conn()
    conn.execute("DELETE FROM reviews WHERE review_id=?", (review_id,))
    conn.commit()
    conn.close()


def get_reviews(book_id):
    conn = get_conn()
    rows = conn.execute("""SELECT r.*, u.name as user_name FROM reviews r
                            JOIN users u ON r.user_id=u.user_id
                            WHERE r.book_id=? ORDER BY r.likes DESC, r.created_at DESC""", (book_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def like_review(user_id, review_id):
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM review_likes WHERE user_id=? AND review_id=?", (user_id, review_id)).fetchone()
    if row:
        conn.close()
        return False
    conn.execute("INSERT INTO review_likes (user_id, review_id) VALUES (?,?)", (user_id, review_id))
    conn.execute("UPDATE reviews SET likes = likes + 1 WHERE review_id=?", (review_id,))
    conn.commit()
    conn.close()
    return True


def report_review(review_id):
    conn = get_conn()
    conn.execute("UPDATE reviews SET reported = reported + 1 WHERE review_id=?", (review_id,))
    conn.commit()
    conn.close()


def book_rating_summary(book_id):
    conn = get_conn()
    row = conn.execute("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE book_id=?",
                        (book_id,)).fetchone()
    conn.close()
    return (round(row["avg"], 1) if row["avg"] else 0), row["cnt"]


# ---------- BOOKMARKS ----------
def add_bookmark(user_id, book_id, page, note=""):
    conn = get_conn()
    conn.execute("INSERT INTO bookmarks (user_id, book_id, page, note, created_at) VALUES (?,?,?,?,?)",
                 (user_id, book_id, page, note, now()))
    conn.commit()
    conn.close()


def get_bookmarks(user_id, book_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bookmarks WHERE user_id=? AND book_id=? ORDER BY page",
                         (user_id, book_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_bookmark(bookmark_id):
    conn = get_conn()
    conn.execute("DELETE FROM bookmarks WHERE id=?", (bookmark_id,))
    conn.commit()
    conn.close()


# ---------- HIGHLIGHTS / NOTES ----------
def add_highlight(user_id, book_id, page, text, color="#FFF176", note=""):
    conn = get_conn()
    conn.execute("""INSERT INTO highlights (user_id, book_id, page, text, color, note, created_at)
                     VALUES (?,?,?,?,?,?,?)""", (user_id, book_id, page, text, color, note, now()))
    conn.commit()
    conn.close()


def get_highlights(user_id, book_id, page=None):
    conn = get_conn()
    if page is not None:
        rows = conn.execute("SELECT * FROM highlights WHERE user_id=? AND book_id=? AND page=? ORDER BY id",
                             (user_id, book_id, page)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM highlights WHERE user_id=? AND book_id=? ORDER BY page",
                             (user_id, book_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_highlight(highlight_id):
    conn = get_conn()
    conn.execute("DELETE FROM highlights WHERE id=?", (highlight_id,))
    conn.commit()
    conn.close()


# ---------- NOTIFICATIONS ----------
def push_notification(user_id, title, message, ntype="system"):
    conn = get_conn()
    conn.execute("""INSERT INTO notifications (user_id, title, message, type, status, created_at)
                     VALUES (?,?,?,?,'unread',?)""", (user_id, title, message, ntype, now()))
    conn.commit()
    conn.close()


def broadcast_notification(title, message, ntype="system"):
    conn = get_conn()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    for u in users:
        conn.execute("""INSERT INTO notifications (user_id, title, message, type, status, created_at)
                         VALUES (?,?,?,?,'unread',?)""", (u["user_id"], title, message, ntype, now()))
    conn.commit()
    conn.close()


def get_notifications(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_notification_read(notification_id):
    conn = get_conn()
    conn.execute("UPDATE notifications SET status='read' WHERE notification_id=?", (notification_id,))
    conn.commit()
    conn.close()


def unread_count(user_id):
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND status='unread'",
                        (user_id,)).fetchone()
    conn.close()
    return row["c"]


# ---------- READER SETTINGS ----------
def get_reader_settings(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM reader_settings WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        conn.execute("INSERT INTO reader_settings (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = conn.execute("SELECT * FROM reader_settings WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row)


def save_reader_settings(user_id, **kwargs):
    if not kwargs:
        return
    conn = get_conn()
    get_reader_settings(user_id)  # ensure row exists
    cols = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE reader_settings SET {cols} WHERE user_id=?", (*kwargs.values(), user_id))
    conn.commit()
    conn.close()


# ---------- ADMIN DASHBOARD STATS ----------
def dashboard_stats():
    conn = get_conn()
    c = conn.cursor()
    stats = {}
    stats["total_users"] = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    stats["total_books"] = c.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    stats["total_authors"] = c.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
    stats["total_sales"] = c.execute("SELECT COUNT(*) FROM purchases WHERE payment_status='Success'").fetchone()[0]
    stats["revenue"] = c.execute("SELECT COALESCE(SUM(amount),0) FROM purchases WHERE payment_status='Success'").fetchone()[0]
    stats["active_users"] = c.execute(
        "SELECT COUNT(DISTINCT user_id) FROM library WHERE last_opened >= date('now','-7 day')").fetchone()[0]
    stats["downloads"] = c.execute("SELECT COALESCE(SUM(downloads),0) FROM books").fetchone()[0]
    conn.close()
    return stats


def most_popular_books(limit=5):
    conn = get_conn()
    rows = conn.execute("""SELECT b.title, COUNT(p.purchase_id) as sales
                            FROM books b LEFT JOIN purchases p ON b.book_id=p.book_id
                            GROUP BY b.book_id ORDER BY sales DESC LIMIT ?""", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def recent_purchases(limit=10):
    conn = get_conn()
    rows = conn.execute("""SELECT p.*, b.title, u.name as user_name FROM purchases p
                            JOIN books b ON p.book_id=b.book_id JOIN users u ON p.user_id=u.user_id
                            ORDER BY p.purchase_date DESC LIMIT ?""", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def sales_over_time():
    conn = get_conn()
    rows = conn.execute("""SELECT date(purchase_date) as day, SUM(amount) as total
                            FROM purchases WHERE payment_status='Success'
                            GROUP BY day ORDER BY day""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def all_users():
    conn = get_conn()
    rows = conn.execute("SELECT user_id, name, email, phone, is_admin, created_at FROM users ORDER BY user_id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
