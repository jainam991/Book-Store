import streamlit as st
import db
from styles import APP_CSS, stars_html

st.set_page_config(page_title="Reviews — Inkwell", page_icon="⭐", layout="wide")
db.init_db()
st.markdown(APP_CSS, unsafe_allow_html=True)

if st.session_state.get("user") is None:
    st.warning("Please log in from the Home page first.")
    st.stop()

user = st.session_state.user

st.markdown("""
<div class="hero-banner">
    <h1>⭐ Ratings & Reviews</h1>
    <p>Share your thoughts on books you've read.</p>
</div>
""", unsafe_allow_html=True)

books = db.list_books()
titles = {b["book_id"]: f"{b['title']} — {b.get('author_name') or 'Unknown'}" for b in books}
default_id = st.session_state.get("review_book_id")
ids = list(titles.keys())
if not ids:
    st.info("No books in the store yet.")
    st.stop()

idx = ids.index(default_id) if default_id in ids else 0
selected_id = st.selectbox("Choose a book", ids, format_func=lambda i: titles[i], index=idx)
book = db.get_book(selected_id)

avg, cnt = db.book_rating_summary(selected_id)
st.markdown(f"## {book['title']}")
st.markdown(f"<span class='stars' style='font-size:1.4rem'>{stars_html(avg)}</span> "
            f"**{avg}/5** · {cnt} review(s)", unsafe_allow_html=True)

st.divider()
st.markdown("### ✍️ Write / edit your review")
with st.form("review_form"):
    rating = st.slider("Your rating", 1, 5, 5)
    text = st.text_area("Your review", placeholder="What did you think of this book?")
    submitted = st.form_submit_button("Submit review", type="primary")
    if submitted:
        if text.strip():
            db.add_review(user["user_id"], selected_id, rating, text.strip())
            st.success("Review saved!")
            st.rerun()
        else:
            st.warning("Write something first.")

st.divider()
st.markdown("### 💬 All reviews")
reviews = db.get_reviews(selected_id)
if not reviews:
    st.caption("No reviews yet — be the first!")

for r in reviews:
    with st.container(border=True):
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f"**{r['user_name']}** — {stars_html(r['rating'])}")
            st.write(r["review"])
            st.caption(r["created_at"])
        with c2:
            if st.button(f"👍 {r['likes']}", key=f"like_{r['review_id']}", use_container_width=True):
                ok = db.like_review(user["user_id"], r["review_id"])
                if not ok:
                    st.toast("You already liked this review.")
                st.rerun()
            if r["user_id"] == user["user_id"]:
                if st.button("🗑️ Delete", key=f"del_{r['review_id']}", use_container_width=True):
                    db.delete_review(r["review_id"])
                    st.rerun()
            else:
                if st.button("🚩 Report", key=f"rep_{r['review_id']}", use_container_width=True):
                    db.report_review(r["review_id"])
                    st.toast("Reported — thanks, our team will take a look.")
