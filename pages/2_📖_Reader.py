import streamlit as st
import db
import utils
from styles import APP_CSS, reader_container_css

st.set_page_config(page_title="Reader — Inkwell", page_icon="📖", layout="wide")
db.init_db()
st.markdown(APP_CSS, unsafe_allow_html=True)

if st.session_state.get("user") is None:
    st.warning("Please log in from the Home page first.")
    st.stop()

user = st.session_state.user
book_id = st.session_state.get("open_book_id")

if not book_id:
    st.info("Pick a book from Home or your Library to start reading.")
    st.stop()

book = db.get_book(book_id)
if not book:
    st.error("Book not found.")
    st.stop()

if not (db.owns_book(user["user_id"], book_id) or (book.get("price") or 0) == 0):
    st.error("You don't own this book yet.")
    if st.button("Go buy it"):
        st.session_state.checkout_book_id = book_id
        st.switch_page("pages/4_🛒_Purchase_History.py")
    st.stop()

db.add_to_library(user["user_id"], book_id)
db.increment_downloads(book_id)
file_path = book["file_url"]
fmt = book["format"]

# ---------------- SETTINGS STATE ----------------
settings = db.get_reader_settings(user["user_id"])
lib_entry = db.get_library_entry(user["user_id"], book_id) or {}

if "focus_mode" not in st.session_state:
    st.session_state.focus_mode = False

# ---------------- TOP BAR ----------------
top1, top2, top3 = st.columns([5, 2, 1])
with top1:
    st.markdown(f"### 📖 {book['title']}")
    st.caption(f"by {book.get('author_name') or 'Unknown'} · {fmt}")
with top2:
    st.session_state.focus_mode = st.toggle("🖥️ Full-screen / focus mode", value=st.session_state.focus_mode)
with top3:
    if st.button("⬅ Back"):
        st.switch_page("app.py")

if st.session_state.focus_mode:
    st.markdown("<style>section[data-testid='stSidebar']{display:none;} header{visibility:hidden;}</style>",
                unsafe_allow_html=True)
    st.caption("📱 Tip: rotate your phone to landscape for a wider page, or use your browser/device's own "
               "full-screen and orientation-lock controls — Streamlit reads whatever orientation your device is in.")

# ---------------- LOAD CONTENT ----------------
if fmt == "PDF":
    total_units = utils.pdf_page_count(file_path)
    unit_label = "page"
else:
    chapters = utils.epub_chapters(file_path)
    total_units = len(chapters)
    unit_label = "section"

if total_units == 0:
    st.error("Could not read this file.")
    st.stop()

default_page = lib_entry.get("last_page", 0) or 0
if "current_page" not in st.session_state or st.session_state.get("_loaded_book") != book_id:
    st.session_state.current_page = min(default_page, total_units - 1)
    st.session_state._loaded_book = book_id

# ---------------- SIDEBAR: TOC / BOOKMARKS / HIGHLIGHTS / SETTINGS / TOOLS ----------------
with st.sidebar:
    st.markdown("## 🧭 Navigate & tools")
    tab_toc, tab_bm, tab_hl, tab_set, tab_tools = st.tabs(
        ["📑 TOC", "🔖 Marks", "🖍️ Highlights", "🎨 Display", "🛠️ Tools"])

    with tab_toc:
        if fmt == "PDF":
            toc = utils.pdf_toc(file_path)
            if toc:
                for level, title, page in toc:
                    indent = "&nbsp;" * (level - 1) * 3
                    if st.button(f"{title}", key=f"toc_{page}_{title}", use_container_width=True):
                        st.session_state.current_page = max(0, page - 1)
                        st.rerun()
            else:
                st.caption("No table of contents embedded in this PDF.")
        else:
            for i, ch in enumerate(chapters):
                if st.button(ch["title"], key=f"toc_ep_{i}", use_container_width=True):
                    st.session_state.current_page = i
                    st.rerun()

    with tab_bm:
        st.caption("Bookmark your spot with an optional note.")
        bm_note = st.text_input("Note (optional)", key="bm_note_input")
        if st.button("🔖 Bookmark this page", use_container_width=True):
            db.add_bookmark(user["user_id"], book_id, st.session_state.current_page, bm_note)
            st.success("Bookmarked!")
        st.divider()
        bms = db.get_bookmarks(user["user_id"], book_id)
        if not bms:
            st.caption("No bookmarks yet.")
        for bm in bms:
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(f"{unit_label.title()} {bm['page']+1}" + (f" — {bm['note']}" if bm["note"] else ""),
                             key=f"gobm_{bm['id']}", use_container_width=True):
                    st.session_state.current_page = bm["page"]
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"delbm_{bm['id']}"):
                    db.delete_bookmark(bm["id"])
                    st.rerun()

    with tab_hl:
        hls = db.get_highlights(user["user_id"], book_id)
        if not hls:
            st.caption("No highlights yet — add one below from the current page.")
        for hl in hls:
            with st.container(border=True):
                st.markdown(f"<span style='background:{hl['color']}'>&nbsp;{hl['text'][:80]}&nbsp;</span>",
                            unsafe_allow_html=True)
                st.caption(f"{unit_label.title()} {hl['page']+1}" + (f" · note: {hl['note']}" if hl["note"] else ""))
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Go to", key=f"gohl_{hl['id']}", use_container_width=True):
                        st.session_state.current_page = hl["page"]
                        st.rerun()
                with c2:
                    if st.button("Delete", key=f"delhl_{hl['id']}", use_container_width=True):
                        db.delete_highlight(hl["id"])
                        st.rerun()

    with tab_set:
        view_mode = st.radio("Layout", ["Page mode", "Scroll mode"],
                              index=0 if st.session_state.get("view_mode", "Page mode") == "Page mode" else 1)
        st.session_state.view_mode = view_mode

        theme = st.selectbox("Reading mode", ["Light", "Dark", "Sepia"],
                              index=["Light", "Dark", "Sepia"].index(settings["theme"]))
        font_family = st.selectbox("Font", ["Serif", "Sans-serif", "Monospace", "Dyslexic-friendly"],
                                    index=["Serif", "Sans-serif", "Monospace", "Dyslexic-friendly"].index(settings["font_family"]))
        font_size = st.slider("Font size", 12, 32, settings["font_size"])
        line_spacing = st.slider("Line spacing", 1.0, 2.5, float(settings["line_spacing"]), 0.1)
        alignment = st.selectbox("Text alignment", ["left", "justify", "center", "right"],
                                  index=["left", "justify", "center", "right"].index(settings["alignment"]))
        brightness = st.slider("Brightness", 40, 130, settings["brightness"])

        if (theme, font_family, font_size, line_spacing, alignment, brightness) != (
            settings["theme"], settings["font_family"], settings["font_size"],
            settings["line_spacing"], settings["alignment"], settings["brightness"]
        ):
            db.save_reader_settings(user["user_id"], theme=theme, font_family=font_family, font_size=font_size,
                                     line_spacing=line_spacing, alignment=alignment, brightness=brightness)
            settings = db.get_reader_settings(user["user_id"])

    with tab_tools:
        st.markdown("**🔎 Search inside book**")
        query = st.text_input("Search text", key="search_query")
        if query:
            results = utils.pdf_search(file_path, query) if fmt == "PDF" else utils.epub_search(file_path, query)
            st.caption(f"{len(results)} match(es)")
            for pg, snippet in results[:25]:
                if st.button(f"{unit_label.title()} {pg+1}: {snippet}", key=f"srch_{pg}_{snippet[:10]}"):
                    st.session_state.current_page = pg
                    st.rerun()

        st.divider()
        st.markdown("**🌐 Translate current text**")
        target = st.selectbox("Translate to", list(utils.LANGUAGES.keys()), index=0, key="translate_lang")
        if st.button("Translate this page", use_container_width=True):
            src_text = utils.pdf_page_text(file_path, st.session_state.current_page) if fmt == "PDF" \
                else chapters[st.session_state.current_page]["text"]
            translated = utils.translate_text(src_text, utils.LANGUAGES[target])
            st.session_state.translated_text = translated

        st.divider()
        st.markdown("**📔 Dictionary**")
        word = st.text_input("Look up a word", key="dict_word")
        if word:
            result = utils.dictionary_lookup(word)
            if result:
                st.markdown(f"**{result['word']}** _{result['phonetic']}_")
                for m in result["meanings"]:
                    st.caption(f"*{m['pos']}*")
                    for d in m["definitions"]:
                        st.write(f"- {d}")
            else:
                st.caption("No definition found (or offline).")

        st.divider()
        st.markdown("**🔊 Text-to-speech**")
        tts_lang = st.selectbox("Voice language", list(utils.LANGUAGES.keys()), index=0, key="tts_lang")
        if st.button("🔊 Read this page aloud", use_container_width=True):
            src_text = utils.pdf_page_text(file_path, st.session_state.current_page) if fmt == "PDF" \
                else chapters[st.session_state.current_page]["text"]
            audio = utils.text_to_speech(src_text, utils.LANGUAGES[tts_lang])
            if audio:
                st.session_state.tts_audio = audio

# ---------------- PROGRESS BAR ----------------
progress_pct = round(((st.session_state.current_page + 1) / total_units) * 100, 1)
pcol1, pcol2 = st.columns([4, 1])
with pcol1:
    st.progress(progress_pct / 100)
with pcol2:
    st.caption(f"**{st.session_state.current_page + 1} / {total_units}** ({progress_pct}%)")

db.update_progress(user["user_id"], book_id, st.session_state.current_page, total_units)

if "translated_text" in st.session_state and st.session_state.translated_text:
    with st.expander("🌐 Translation", expanded=True):
        st.write(st.session_state.translated_text)
        if st.button("Clear translation"):
            del st.session_state.translated_text
            st.rerun()

if "tts_audio" in st.session_state and st.session_state.tts_audio:
    st.audio(st.session_state.tts_audio, format="audio/mp3")

# ---------------- RENDER CONTENT ----------------
css = reader_container_css(settings["theme"], settings["font_size"], settings["font_family"],
                            settings["line_spacing"], settings["alignment"], settings["brightness"])
st.markdown(css, unsafe_allow_html=True)


def render_unit(idx):
    if fmt == "PDF":
        png = utils.pdf_render_page(file_path, idx)
        st.markdown("<div class='reader-panel'>", unsafe_allow_html=True)
        st.image(png, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        html = chapters[idx]["html"]
        st.markdown(f"<div class='reader-panel'>{html}</div>", unsafe_allow_html=True)


if st.session_state.view_mode == "Page mode" if "view_mode" in st.session_state else True:
    pass

if st.session_state.get("view_mode", "Page mode") == "Scroll mode":
    lo = max(0, st.session_state.current_page - 1)
    hi = min(total_units, st.session_state.current_page + 3)
    for i in range(lo, hi):
        st.caption(f"— {unit_label} {i+1} —")
        render_unit(i)
        st.markdown("<br>", unsafe_allow_html=True)
else:
    render_unit(st.session_state.current_page)

# ---------------- HIGHLIGHT / NOTE ADDER (current page/section) ----------------
with st.expander("🖍️ Highlight text or add a note on this page"):
    st.caption("Paste/select the exact snippet from this page you'd like to highlight.")
    hc1, hc2 = st.columns([3, 1])
    with hc1:
        snippet = st.text_area("Text to highlight", height=70, key=f"snippet_{st.session_state.current_page}")
    with hc2:
        color = st.color_picker("Color", "#FFF176", key=f"color_{st.session_state.current_page}")
    note_text = st.text_input("Note (optional)", key=f"note_{st.session_state.current_page}")
    if st.button("Save highlight / note"):
        if snippet.strip():
            db.add_highlight(user["user_id"], book_id, st.session_state.current_page, snippet.strip(), color, note_text)
            st.success("Saved!")
            st.rerun()
        else:
            st.warning("Add some text to highlight first.")

# ---------------- NAVIGATION ----------------
nav1, nav2, nav3, nav4 = st.columns([1, 1, 2, 1])
with nav1:
    if st.button("⬅ Previous", use_container_width=True, disabled=st.session_state.current_page <= 0):
        st.session_state.current_page -= 1
        st.rerun()
with nav2:
    if st.button("Next ➡", use_container_width=True, disabled=st.session_state.current_page >= total_units - 1):
        st.session_state.current_page += 1
        st.rerun()
with nav3:
    jump = st.number_input(f"Jump to {unit_label}", 1, total_units, st.session_state.current_page + 1,
                            label_visibility="collapsed")
    if jump - 1 != st.session_state.current_page:
        st.session_state.current_page = jump - 1
        st.rerun()
with nav4:
    st.caption("✅ Auto-saved — pick up right where you left off next time.")
