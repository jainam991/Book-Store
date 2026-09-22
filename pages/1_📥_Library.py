import streamlit as st
import db
from styles import APP_CSS

st.set_page_config(page_title="My Library — Inkwell", page_icon="📥", layout="wide")
db.init_db()
st.markdown(APP_CSS, unsafe_allow_html=True)

if st.session_state.get("user") is None:
    st.warning("Please log in from the Home page first.")
    st.stop()

user = st.session_state.user

st.markdown("""
<div class="hero-banner">
    <h1>📥 My Library</h1>
    <p>Continue reading, track progress, and manage your wishlist.</p>
</div>
""", unsafe_allow_html=True)

tab_lib, tab_wish = st.tabs(["📚 My Books", "🤍 Wishlist"])

with tab_lib:
    entries = db.get_library(user["user_id"])
    if not entries:
        st.info("Your library is empty — buy or open a free book from Home to get started.")
    for e in entries:
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 4, 2])
            with c1:
                if e.get("cover_image"):
                    st.image(e["cover_image"], use_container_width=True)
                else:
                    st.markdown("📘")
            with c2:
                st.markdown(f"**{e['title']}**")
                st.caption(f"by {e.get('author_name') or 'Unknown'} · {e['format']}")
                st.progress(min(1.0, (e["progress"] or 0) / 100))
                st.caption(f"{e['progress']}% complete · page {e['last_page']+1} of {e['total_pages'] or '?'} "
                           f"· status: {e['status']} · last opened {e['last_opened']}")
            with c3:
                if st.button("📖 Continue reading", key=f"cont_{e['book_id']}", use_container_width=True):
                    st.session_state.open_book_id = e["book_id"]
                    st.switch_page("pages/2_📖_Reader.py")
                if st.button("⭐ Rate / Review", key=f"rev_{e['book_id']}", use_container_width=True):
                    st.session_state.review_book_id = e["book_id"]
                    st.switch_page("pages/5_⭐_Reviews.py")

with tab_wish:
    wish = db.get_wishlist(user["user_id"])
    if not wish:
        st.info("No wishlisted books yet — tap 🤍 on any book from Home.")
    cols = st.columns(4)
    for i, w in enumerate(wish):
        with cols[i % 4]:
            with st.container(border=True):
                if w.get("cover_image"):
                    st.image(w["cover_image"], use_container_width=True)
                st.markdown(f"**{w['title']}**")
                st.caption(w.get("author_name") or "Unknown")
                st.markdown(f"${w['price']:.2f}")
                bcol1, bcol2 = st.columns(2)
                with bcol1:
                    if st.button("🛒 Buy", key=f"wbuy_{w['book_id']}", use_container_width=True):
                        st.session_state.checkout_book_id = w["book_id"]
                        st.switch_page("pages/4_🛒_Purchase_History.py")
                with bcol2:
                    if st.button("💔 Remove", key=f"wrm_{w['book_id']}", use_container_width=True):
                        db.toggle_wishlist(user["user_id"], w["book_id"])
                        st.rerun()
