"""
seed_demo.py — generates a couple of sample PDF books + cover images so the
store has content on first launch, with zero manual setup. Real deployments
should replace this with actual licensed book files uploaded via the Admin panel.
"""

import os
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import db

BASE = os.path.dirname(__file__)
BOOKS_DIR = os.path.join(BASE, "data", "books")
COVERS_DIR = os.path.join(BASE, "data", "covers")

SAMPLE_TEXT = """This is a sample chapter generated for demo purposes.

Once upon a time, in a small workshop lit by a single lamp, an inventor
sketched the outline of a machine nobody had asked for. It had no clear
purpose yet -- only a shape that felt right, gears that seemed to want to
turn in a particular direction.

Every page you turn in this sample book is here to prove one thing: that
the reader works. Page navigation, table of contents, search, highlights,
bookmarks, translation, and text-to-speech should all function against
this very paragraph.

Replace this file in the Admin panel with real, licensed content before
using this platform for anything beyond a demo or portfolio piece.
"""


def _make_cover(path, title, color):
    img = Image.new("RGB", (500, 720), color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
    words = title.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if len(test) > 14:
            lines.append(cur)
            cur = w
        else:
            cur = test
    lines.append(cur)
    y = 280
    for line in lines:
        draw.text((40, y), line, font=font, fill="white")
        y += 55
    img.save(path)


def _make_pdf(path, title, author, pages=8):
    doc = fitz.open()
    toc = []
    for i in range(pages):
        page = doc.new_page()
        if i == 0:
            page.insert_text((72, 200), title, fontsize=28, fontname="helv")
            page.insert_text((72, 250), f"by {author}", fontsize=16, fontname="helv")
            toc.append([1, "Title Page", i + 1])
        else:
            page.insert_text((72, 72), f"Chapter {i}", fontsize=20, fontname="helv")
            page.insert_textbox(fitz.Rect(72, 110, 520, 720), SAMPLE_TEXT, fontsize=12, fontname="helv")
            toc.append([1, f"Chapter {i}", i + 1])
    doc.set_toc(toc)
    doc.save(path)
    doc.close()


def _get_or_create_author(name, bio):
    existing = db.get_author_by_name(name)
    if existing:
        return existing["author_id"]
    return db.add_author(name, bio)


def seed_if_empty():
    os.makedirs(BOOKS_DIR, exist_ok=True)
    os.makedirs(COVERS_DIR, exist_ok=True)

    if db.list_books(status=None):
        return  # already seeded

    # Atomic guard: if two sessions race here on a cold start, only one
    # of them wins this lock — the other backs off instead of double-seeding.
    if not db.try_acquire_seed_lock():
        return

    demo_books = [
        ("The Clockwork Garden", "Amara Voss", "Sci-Fi", 0.0, "#6C5CE7"),
        ("Whispers of the Old Coast", "Daniel Reyes", "Fiction", 4.99, "#0EA5E9"),
        ("Atomic Focus", "Priya Nair", "Self-Help", 9.99, "#F59E0B"),
        ("The Founder's Ledger", "Marcus Chen", "Business", 12.5, "#10B981"),
        ("Quiet Verses", "Lila Moreau", "Poetry", 2.99, "#EC4899"),
        ("Signals from Nowhere", "Amara Voss", "Sci-Fi", 6.99, "#8B5CF6"),
    ]

    categories = {c["name"]: c["category_id"] for c in db.list_categories()}

    for title, author_name, cat_name, price, color in demo_books:
        author_id = _get_or_create_author(author_name, f"{author_name} is a demo author bio for sample purposes.")
        cat_id = categories.get(cat_name)
        safe = title.lower().replace(" ", "_").replace("'", "")
        pdf_path = os.path.join(BOOKS_DIR, f"{safe}.pdf")
        cover_path = os.path.join(COVERS_DIR, f"{safe}.png")
        _make_pdf(pdf_path, title, author_name)
        _make_cover(cover_path, title, color)
        db.add_book(title, author_id, cat_id, f"A demo sample book: {title}.", cover_path, pdf_path,
                    "PDF", "English", price, "2026-01-01")
