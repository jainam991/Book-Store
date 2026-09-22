"""
utils.py
Book parsing (PDF via PyMuPDF, EPUB via ebooklib) + TTS / translation / dictionary helpers.
Every external-service call is wrapped in try/except so the app never crashes
if the platform has no internet access at runtime.
"""

import io
import os
import base64
import streamlit as st

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
except ImportError:
    ebooklib = None


# ---------------- PDF ----------------
@st.cache_resource(show_spinner=False)
def load_pdf(file_path):
    return fitz.open(file_path)


def pdf_page_count(file_path):
    doc = load_pdf(file_path)
    return doc.page_count


def pdf_render_page(file_path, page_num, zoom=1.6):
    """Return PNG bytes of a rendered PDF page (0-indexed)."""
    doc = load_pdf(file_path)
    page = doc.load_page(page_num)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")


def pdf_page_text(file_path, page_num):
    doc = load_pdf(file_path)
    return doc.load_page(page_num).get_text()


def pdf_toc(file_path):
    doc = load_pdf(file_path)
    toc = doc.get_toc()  # [[level, title, page], ...]
    return toc


def pdf_search(file_path, query):
    """Search whole PDF, return list of (page_num, snippet)."""
    doc = load_pdf(file_path)
    results = []
    for i in range(doc.page_count):
        text = doc.load_page(i).get_text()
        idx = text.lower().find(query.lower())
        if idx != -1:
            start = max(0, idx - 40)
            end = min(len(text), idx + len(query) + 40)
            snippet = text[start:end].replace("\n", " ")
            results.append((i, f"...{snippet}..."))
    return results


# ---------------- EPUB ----------------
@st.cache_resource(show_spinner=False)
def load_epub(file_path):
    return epub.read_epub(file_path)


def epub_chapters(file_path):
    """Return list of dicts: {id, title, html} in reading order (acts as 'pages')."""
    book = load_epub(file_path)
    chapters = []
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    for i, item in enumerate(items):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        title_tag = soup.find(["h1", "h2", "h3", "title"])
        title = title_tag.get_text(strip=True) if title_tag else f"Section {i+1}"
        text = soup.get_text("\n", strip=True)
        if not text.strip():
            continue
        chapters.append({"id": item.get_id(), "title": title, "html": str(soup), "text": text})
    return chapters


def epub_toc(file_path):
    book = load_epub(file_path)
    toc_list = []

    def walk(items):
        for it in items:
            if isinstance(it, tuple):
                section, children = it
                toc_list.append(getattr(section, "title", str(section)))
                walk(children)
            else:
                toc_list.append(getattr(it, "title", str(it)))

    walk(book.toc)
    return toc_list


def epub_search(file_path, query):
    chapters = epub_chapters(file_path)
    results = []
    for i, ch in enumerate(chapters):
        idx = ch["text"].lower().find(query.lower())
        if idx != -1:
            start = max(0, idx - 40)
            end = min(len(ch["text"]), idx + len(query) + 40)
            snippet = ch["text"][start:end].replace("\n", " ")
            results.append((i, f"...{snippet}..."))
    return results


# ---------------- SHARED ----------------
def detect_format(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return "PDF"
    if ext == ".epub":
        return "EPUB"
    return "UNKNOWN"


def image_to_base64(png_bytes):
    return base64.b64encode(png_bytes).decode()


# ---------------- TEXT-TO-SPEECH ----------------
def text_to_speech(text, lang="en"):
    """Return mp3 bytes using gTTS, or None if unavailable."""
    try:
        from gtts import gTTS
        text = text.strip()[:3000]  # keep requests reasonable
        if not text:
            return None
        buf = io.BytesIO()
        tts = gTTS(text=text, lang=lang)
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        st.warning(f"Text-to-speech unavailable right now ({e}).")
        return None


# ---------------- TRANSLATION ----------------
LANGUAGES = {
    "English": "en", "Spanish": "es", "French": "fr", "German": "de",
    "Hindi": "hi", "Arabic": "ar", "Chinese (Simplified)": "zh-CN",
    "Japanese": "ja", "Korean": "ko", "Portuguese": "pt", "Russian": "ru",
    "Italian": "it", "Urdu": "ur", "Bengali": "bn", "Turkish": "tr",
}


def translate_text(text, target_lang_code, source_lang_code="auto"):
    try:
        from deep_translator import GoogleTranslator
        text = text.strip()[:4500]
        if not text:
            return ""
        return GoogleTranslator(source=source_lang_code, target=target_lang_code).translate(text)
    except Exception as e:
        return f"(Translation unavailable: {e})"


# ---------------- DICTIONARY ----------------
def dictionary_lookup(word):
    """Free dictionary API lookup. Returns list of meanings or None."""
    try:
        import requests
        word = word.strip().split()[0].strip(".,!?;:\"'()")
        if not word:
            return None
        resp = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=6)
        if resp.status_code != 200:
            return None
        data = resp.json()
        entry = data[0]
        meanings = []
        phonetic = entry.get("phonetic", "")
        for m in entry.get("meanings", []):
            pos = m.get("partOfSpeech", "")
            defs = [d.get("definition") for d in m.get("definitions", [])[:2]]
            meanings.append({"pos": pos, "definitions": defs})
        return {"word": entry.get("word", word), "phonetic": phonetic, "meanings": meanings}
    except Exception:
        return None
