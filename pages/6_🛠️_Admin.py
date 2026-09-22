import streamlit as st
import os
import db
import utils
import seed_demo
from styles import APP_CSS

st.set_page_config(page_title="Admin — Inkwell", page_icon="🛠️", layout="wide")
db.init_db()
st.markdown(APP_CSS, unsafe_allow_html=True)

if st.session_state.get("user") is None:
    st.warning("Please log in from the Home page first.")
    st.stop()

user = st.session_state.user
if not user["is_admin"]:
    st.error("🚫 Admins only.")
    st.stop()

BOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "books")
COVERS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "covers")
os.makedirs(BOOKS_DIR, exist_ok=True)
os.makedirs(COVERS_DIR, exist_ok=True)

st.markdown("""
<div class="hero-banner">
    <h1>🛠️ Admin Panel</h1>
    <p>Dashboard, catalog management, users & sales — the control room.</p>
</div>
""", unsafe_allow_html=True)

tab_dash, tab_books, tab_authors, tab_users, tab_promo, tab_danger = st.tabs(
    ["📊 Dashboard", "📚 Manage Books", "✍️ Authors & Categories", "👥 Users", "📣 Promotions", "⚠️ Danger Zone"])

# ---------------- DASHBOARD ----------------
with tab_dash:
    stats = db.dashboard_stats()
    cols = st.columns(4)
    metrics = [
        ("👥 Total Users", stats["total_users"]),
        ("📚 Total Books", stats["total_books"]),
        ("✍️ Total Authors", stats["total_authors"]),
        ("💰 Total Sales", stats["total_sales"]),
    ]
    for col, (label, val) in zip(cols, metrics):
        with col:
            st.markdown(f"""<div class="metric-card"><div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div></div>""", unsafe_allow_html=True)

    cols2 = st.columns(3)
    metrics2 = [
        ("💵 Revenue", f"${stats['revenue']:.2f}"),
        ("🔥 Active Users (7d)", stats["active_users"]),
        ("⬇️ Total Downloads", stats["downloads"]),
    ]
    for col, (label, val) in zip(cols2, metrics2):
        with col:
            st.markdown(f"""<div class="metric-card"><div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div></div>""", unsafe_allow_html=True)

    st.markdown("#### 📈 Revenue over time")
    sales = db.sales_over_time()
    if sales:
        st.line_chart({s["day"]: s["total"] for s in sales})
    else:
        st.caption("No sales yet.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🏆 Most popular books")
        pop = db.most_popular_books()
        for p in pop:
            st.write(f"**{p['title']}** — {p['sales']} sale(s)")
    with c2:
        st.markdown("#### 🧾 Recent purchases")
        recent = db.recent_purchases()
        for r in recent:
            st.write(f"{r['user_name']} bought **{r['title']}** — ${r['amount']:.2f} on {r['purchase_date']}")

# ---------------- MANAGE BOOKS ----------------
with tab_books:
    st.markdown("### ➕ Add a new book")
    with st.form("add_book_form", clear_on_submit=True):
        title = st.text_input("Title")
        c1, c2 = st.columns(2)
        with c1:
            authors = db.list_authors()
            author_names = ["— New author —"] + [a["name"] for a in authors]
            author_choice = st.selectbox("Author", author_names)
            new_author_name = st.text_input("New author name (if selected above)")
        with c2:
            categories = db.list_categories()
            cat_choice = st.selectbox("Category", [c["name"] for c in categories]) if categories else None
        description = st.text_area("Description")
        c3, c4, c5 = st.columns(3)
        with c3:
            price = st.number_input("Price (USD)", 0.0, 999.0, 0.0, step=0.5)
        with c4:
            language = st.text_input("Language", "English")
        with c5:
            pub_date = st.date_input("Publication date")
        cover_file = st.file_uploader("Cover image (jpg/png)", type=["jpg", "jpeg", "png"])
        book_file = st.file_uploader("Book file (PDF or EPUB)", type=["pdf", "epub"])
        submitted = st.form_submit_button("Publish book", type="primary")

        if submitted:
            if not (title and book_file):
                st.error("Title and book file are required.")
            else:
                if author_choice == "— New author —" and new_author_name.strip():
                    author_id = db.add_author(new_author_name.strip())
                else:
                    author_id = next((a["author_id"] for a in authors if a["name"] == author_choice), None)

                category_id = next((c["category_id"] for c in categories if c["name"] == cat_choice), None) \
                    if categories else None

                fmt = utils.detect_format(book_file.name)
                book_path = os.path.join(BOOKS_DIR, book_file.name)
                with open(book_path, "wb") as f:
                    f.write(book_file.getbuffer())

                cover_path = None
                if cover_file:
                    cover_path = os.path.join(COVERS_DIR, cover_file.name)
                    with open(cover_path, "wb") as f:
                        f.write(cover_file.getbuffer())

                db.add_book(title, author_id, category_id, description, cover_path, book_path,
                            fmt, language, price, str(pub_date))
                st.success(f"'{title}' published! 🎉")
                st.rerun()

    st.divider()
    st.markdown("### 📚 Existing books")
    all_books = db.list_books(status=None)
    for b in all_books:
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 4, 1])
            with c1:
                if b.get("cover_image"):
                    st.image(b["cover_image"], width=70)
            with c2:
                st.markdown(f"**{b['title']}** — {b.get('author_name') or 'Unknown'}")
                st.caption(f"{b['format']} · ${b['price']:.2f} · {b['downloads']} downloads · status: {b['status']}")
            with c3:
                if st.button("🗑️ Delete", key=f"admindel_{b['book_id']}", use_container_width=True):
                    db.delete_book(b["book_id"])
                    st.rerun()

# ---------------- AUTHORS & CATEGORIES ----------------
with tab_authors:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ✍️ Authors")
        with st.form("add_author_form", clear_on_submit=True):
            aname = st.text_input("Name")
            abio = st.text_area("Biography")
            if st.form_submit_button("Add author"):
                if aname.strip():
                    db.add_author(aname.strip(), abio)
                    st.success("Author added.")
                    st.rerun()
        for a in db.list_authors():
            st.write(f"**{a['name']}** — {a['biography'] or 'No bio'}")

    with c2:
        st.markdown("### 🏷️ Categories")
        with st.form("add_cat_form", clear_on_submit=True):
            cname = st.text_input("Category name")
            if st.form_submit_button("Add category"):
                if cname.strip():
                    db.add_category(cname.strip())
                    st.success("Category added.")
                    st.rerun()
        for c in db.list_categories():
            st.write(f"- {c['name']}")

# ---------------- USERS ----------------
with tab_users:
    st.markdown("### 👥 All users")
    users = db.all_users()
    st.dataframe(users, use_container_width=True, hide_index=True)

# ---------------- PROMOTIONS / BROADCAST NOTIFICATIONS ----------------
with tab_promo:
    st.markdown("### 📣 Send a broadcast notification")
    st.caption("Goes out to every user — use for promotional offers, price drops, or announcements.")
    ntype = st.selectbox("Type", ["promo", "price_drop", "recommendation", "author_update", "system"])
    ntitle = st.text_input("Title", "🎉 Limited-time offer!")
    nmsg = st.text_area("Message", "20% off all Sci-Fi books this weekend only.")
    if st.button("Send to all users", type="primary"):
        db.broadcast_notification(ntitle, nmsg, ntype)
        st.success("Broadcast sent!")

# ---------------- DANGER ZONE ----------------
with tab_danger:
    st.markdown("### ⚠️ Reset & reseed catalog")
    st.caption(
        "Fixes duplicated demo data (e.g. books/authors/notifications appearing "
        "twice from a startup race condition in an earlier version). This wipes "
        "**books, authors, purchases, library entries, wishlists, reviews, "
        "bookmarks, highlights, and notifications**, then regenerates the 6 clean "
        "demo books. User accounts and categories are kept."
    )
    confirm = st.checkbox("I understand this deletes catalog & activity data and can't be undone.")
    if st.button("🧹 Reset & reseed now", type="primary", disabled=not confirm):
        db.factory_reset_catalog()
        seed_demo.seed_if_empty()
        st.success("Catalog reset and reseeded cleanly.")
        st.rerun()
