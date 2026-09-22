import streamlit as st
import db
from styles import APP_CSS

st.set_page_config(page_title="Purchase History — Inkwell", page_icon="🛒", layout="wide")
db.init_db()
st.markdown(APP_CSS, unsafe_allow_html=True)

if st.session_state.get("user") is None:
    st.warning("Please log in from the Home page first.")
    st.stop()

user = st.session_state.user

st.markdown('<div class="hero-banner"><h1>🛒 Purchase History</h1><p>Every transaction, in one place.</p></div>', unsafe_allow_html=True)

# ---------------- CHECKOUT FLOW ----------------
checkout_id = st.session_state.get("checkout_book_id")
if checkout_id:
    book = db.get_book(checkout_id)
    if book and not db.owns_book(user["user_id"], checkout_id):
        with st.container(border=True):
            st.markdown("### 💳 Checkout")
            c1, c2 = st.columns([1, 3])
            with c1:
                if book.get("cover_image"):
                    st.image(book["cover_image"], width=120)
            with c2:
                st.markdown(f"**{book['title']}** by {book.get('author_name') or 'Unknown'}")
                st.markdown(f"### ${book['price']:.2f}")
            st.caption("This is a simulated payment for demo purposes — no real card is charged. "
                       "Wire in Stripe/Razorpay/PayPal here for production.")
            pay_method = st.radio("Payment method", ["Credit/Debit Card", "PayPal", "UPI", "Wallet balance"],
                                   horizontal=True)
            if pay_method == "Credit/Debit Card":
                cc1, cc2, cc3 = st.columns(3)
                cc1.text_input("Card number", "4242 4242 4242 4242")
                cc2.text_input("Expiry", "12/29")
                cc3.text_input("CVV", "123", type="password")
            if st.button("✅ Confirm & Pay", type="primary", use_container_width=True):
                txn = db.make_purchase(user["user_id"], checkout_id, book["price"])
                st.success(f"Payment successful! Transaction ID: {txn}")
                st.balloons()
                del st.session_state.checkout_book_id
                st.rerun()
        st.divider()
    else:
        if "checkout_book_id" in st.session_state:
            del st.session_state.checkout_book_id

# ---------------- HISTORY TABLE ----------------
purchases = db.get_purchases(user["user_id"])
if not purchases:
    st.info("No purchases yet — head to Home to find your next book.")
else:
    for p in purchases:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([1, 3, 2, 2, 2])
            with c1:
                if p.get("cover_image"):
                    st.image(p["cover_image"], use_container_width=True)
            with c2:
                st.markdown(f"**{p['title']}**")
                st.caption(p["format"])
            with c3:
                st.caption("Transaction ID")
                st.code(p["transaction_id"], language=None)
            with c4:
                st.caption("Date")
                st.write(p["purchase_date"])
                st.caption("Amount")
                st.write(f"${p['amount']:.2f}")
            with c5:
                status_color = "🟢" if p["payment_status"] == "Success" else "🔴"
                st.write(f"{status_color} {p['payment_status']}")
                if st.button("📖 Read now", key=f"histread_{p['purchase_id']}", use_container_width=True):
                    st.session_state.open_book_id = p["book_id"]
                    st.switch_page("pages/2_📖_Reader.py")
