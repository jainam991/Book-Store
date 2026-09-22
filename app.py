import streamlit as st
import db
import seed_demo
from styles import APP_CSS, stars_html

st.set_page_config(page_title="Inkwell — E-Book Store", page_icon="📚", layout="wide")
db.init_db()
seed_demo.seed_if_empty()
st.markdown(APP_CSS, unsafe_allow_html=True)

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None


def login_ui():
    st.markdown("""
    <div class="hero-banner">
        <h1>📚 Inkwell</h1>
        <p>Your entire library — PDF & EPUB — in one beautifully designed app.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔑 Log in", "🆕 Create account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True, type="primary")
            if submitted:
                user = db.verify_login(email.strip().lower(), password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
        st.caption("Demo admin — email: `admin@bookstore.com` · password: `admin123`")

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Full name")
            email2 = st.text_input("Email ")
            phone = st.text_input("Phone")
            pw = st.text_input("Password ", type="password")
            submitted2 = st.form_submit_button("Create account", use_container_width=True, type="primary")
            if submitted2:
                if not (name and email2 and pw):
                    st.error("Name, email and password are required.")
                else:
                    ok, msg = db.create_user(name, email2.strip().lower(), phone, pw)
                    if ok:
                        st.success(msg + " Please log in.")
                    else:
                        st.error(msg)


def render_book_grid(books, user_id, cols_per_row=4):
    if not books:
        st.info("No books found.")
        return
    rows = [books[i:i + cols_per_row] for i in range(0, len(books), cols_per_row)]
    for row in rows:
        cols = st.columns(cols_per_row)
        for col, book in zip(cols, row):
            with col:
                with st.container(border=True):
                    if book.get("cover_image"):
                        st.image(book["cover_image"], use_container_width=True)
                    else:
                        st.markdown(
                            f"<div style='height:170px;border-radius:10px;background:linear-gradient(135deg,#6C5CE7,#A78BFA);"
                            f"display:flex;align-items:center;justify-content:center;color:white;font-weight:700;"
                            f"text-align:center;padding:10px'>{book['title']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='book-title'>{book['title']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='book-author'>{book.get('author_name') or 'Unknown author'}</div>",
                                unsafe_allow_html=True)
                    avg, cnt = db.book_rating_summary(book["book_id"])
                    st.markdown(f"<span class='stars'>{stars_html(avg)}</span> "
                                f"<span style='color:#999;font-size:0.8rem'>({cnt})</span>", unsafe_allow_html=True)

                    owned = db.owns_book(user_id, book["book_id"])
                    price = book.get("price") or 0
                    if owned or price == 0:
                        st.markdown("<span class='badge-owned'>✓ In your library</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span class='price-tag'>${price:.2f}</span>", unsafe_allow_html=True)

                    b1, b2 = st.columns(2)
                    with b1:
                        if owned or price == 0:
                            if st.button("📖 Read", key=f"read_{book['book_id']}", use_container_width=True):
                                if price == 0 and not owned:
                                    db.add_to_library(user_id, book["book_id"])
                                st.session_state.open_book_id = book["book_id"]
                                st.switch_page("pages/2_📖_Reader.py")
                        else:
                            if st.button("🛒 Buy", key=f"buy_{book['book_id']}", use_container_width=True):
                                st.session_state.checkout_book_id = book["book_id"]
                                st.switch_page("pages/4_🛒_Purchase_History.py")
                    with b2:
                        wl = db.is_wishlisted(user_id, book["book_id"])
                        label = "💔 Remove" if wl else "🤍 Wishlist"
                        if st.button(label, key=f"wish_{book['book_id']}", use_container_width=True):
                            db.toggle_wishlist(user_id, book["book_id"])
                            st.rerun()


def main_app():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 👋 Hi, {user['name'].split()[0]}")
        if user.get("profile_image"):
            st.image(user["profile_image"], width=70)
        unread = db.unread_count(user["user_id"])
        st.caption(f"🔔 {unread} unread notification(s)" if unread else "🔔 No new notifications")
        st.divider()
        if user["is_admin"]:
            st.success("Admin account")
        if st.button("🚪 Log out", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        st.divider()
        st.caption("Use the pages menu above ⬆️ to navigate: Browse, Reader, Library, "
                   "Purchases, Notifications, Reviews" + (", Admin" if user["is_admin"] else ""))

    st.markdown("""
    <div class="hero-banner">
        <h1>📚 Discover your next read</h1>
        <p>Search, sample, buy, and read — all in one place.</p>
    </div>
    """, unsafe_allow_html=True)

    search_col, cat_col = st.columns([3, 1])
    with search_col:
        search = st.text_input("🔍 Search books or authors", placeholder="Try 'Atomic Habits' or 'Orwell'")
    with cat_col:
        cats = ["All"] + [c["name"] for c in db.list_categories()]
        chosen_cat = st.selectbox("Category", cats)

    cat_id = None
    if chosen_cat != "All":
        for c in db.list_categories():
            if c["name"] == chosen_cat:
                cat_id = c["category_id"]

    books = db.list_books(search=search or None, category_id=cat_id)
    st.markdown(f"**{len(books)} book(s)** found")
    render_book_grid(books, user["user_id"])


if st.session_state.user is None:
    login_ui()
else:
    main_app()
