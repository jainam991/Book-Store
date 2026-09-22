import streamlit as st
import db
from styles import APP_CSS

st.set_page_config(page_title="Notifications — Inkwell", page_icon="🔔", layout="wide")
db.init_db()
st.markdown(APP_CSS, unsafe_allow_html=True)

if st.session_state.get("user") is None:
    st.warning("Please log in from the Home page first.")
    st.stop()

user = st.session_state.user

st.markdown('<div class="hero-banner"><h1>🔔 Notifications</h1><p>New releases, recommendations, price drops, promos, purchases, downloads, reminders & author updates.</p></div>', unsafe_allow_html=True)

ICONS = {
    "new_release": "📚", "recommendation": "✨", "price_drop": "💸", "promo": "🎁",
    "purchase": "✅", "download": "⬇️", "reminder": "⏰", "author_update": "✍️", "system": "⚙️",
}

notifs = db.get_notifications(user["user_id"])

c1, c2 = st.columns([4, 1])
with c1:
    st.caption(f"{len(notifs)} total")
with c2:
    if st.button("Mark all as read", use_container_width=True):
        for n in notifs:
            db.mark_notification_read(n["notification_id"])
        st.rerun()

if not notifs:
    st.info("You're all caught up — no notifications yet.")

for n in notifs:
    unread_cls = "notif-unread" if n["status"] == "unread" else ""
    icon = ICONS.get(n["type"], "🔔")
    st.markdown(f"""
    <div class="notif-card {unread_cls}">
        <b>{icon} {n['title']}</b><br>
        {n['message']}<br>
        <span style='color:#888;font-size:0.78rem'>{n['created_at']}</span>
    </div>
    """, unsafe_allow_html=True)
    if n["status"] == "unread":
        if st.button("Mark read", key=f"read_{n['notification_id']}"):
            db.mark_notification_read(n["notification_id"])
            st.rerun()

st.divider()
st.markdown("#### ⏰ Reading reminders")
st.caption("Simulated here — in production, hook this up to a scheduled job (e.g. cron / Cloud Scheduler) "
           "that calls `db.push_notification()` daily for users who haven't opened a book recently.")
if st.button("Send me a test reading reminder"):
    db.push_notification(user["user_id"], "Time to read!",
                          "You haven't opened a book in a while — pick up where you left off.", "reminder")
    st.success("Sent — refresh to see it above.")
