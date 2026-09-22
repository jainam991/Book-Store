"""styles.py — shared CSS for the whole app + reading-mode themes."""

APP_CSS = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }

:root{
  --accent: #6C5CE7;
  --accent-soft: #EDE9FE;
}

.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1150px; }

/* Book cover card */
.book-card {
  border-radius: 14px;
  padding: 10px;
  background: var(--background-color, #fff);
  box-shadow: 0 2px 10px rgba(0,0,0,0.07);
  transition: transform .15s ease, box-shadow .15s ease;
  height: 100%;
}
.book-card:hover { transform: translateY(-3px); box-shadow: 0 8px 22px rgba(0,0,0,0.14); }
.book-title { font-weight: 700; font-size: 0.98rem; margin: 6px 0 2px 0; line-height: 1.25; }
.book-author { color: #888; font-size: 0.83rem; margin-bottom: 4px; }
.price-tag {
  display:inline-block; background: var(--accent-soft); color: var(--accent);
  font-weight: 700; padding: 2px 10px; border-radius: 20px; font-size: 0.82rem;
}
.badge-owned {
  display:inline-block; background:#DCFCE7; color:#166534; font-weight:600;
  padding:2px 10px; border-radius:20px; font-size:0.78rem;
}
.stars { color: #F5A623; font-size: 0.95rem; letter-spacing: 1px;}

.hero-banner {
  background: linear-gradient(120deg, #6C5CE7 0%, #A78BFA 60%, #F0ABFC 100%);
  border-radius: 20px; padding: 28px 32px; margin-bottom: 1.4rem;
  min-height: 40px;
}
.hero-banner h1, .hero-banner p, .hero-banner * {
  color: #FFFFFF !important;
  -webkit-text-fill-color: #FFFFFF !important;
}
.hero-banner h1 { margin: 0; font-size: 1.9rem; font-weight: 800; }
.hero-banner p { opacity: 0.92; margin-top: 6px; }

.metric-card {
  border-radius: 16px; padding: 18px 20px; background: var(--background-color, #fff);
  box-shadow: 0 2px 10px rgba(0,0,0,0.07);
}
.metric-value { font-size: 1.6rem; font-weight: 800; }
.metric-label { color: #888; font-size: 0.82rem; text-transform: uppercase; letter-spacing: .04em;}

.notif-card { border-left: 4px solid var(--accent); padding: 10px 14px; border-radius: 10px;
  background: var(--accent-soft); margin-bottom: 8px; }
.notif-unread { border-left-color: #E11D48; }

hr { margin: 0.6rem 0 1.2rem 0; }
</style>
"""

# Reading-mode themes applied INSIDE the reader panel only
READER_THEMES = {
    "Light": {"bg": "#FFFFFF", "fg": "#1a1a1a"},
    "Dark": {"bg": "#121212", "fg": "#E6E6E6"},
    "Sepia": {"bg": "#F4ECD8", "fg": "#4b3b2b"},
}


def reader_container_css(theme="Light", font_size=18, font_family="Serif",
                          line_spacing=1.6, alignment="left", brightness=100):
    colors = READER_THEMES.get(theme, READER_THEMES["Light"])
    family_map = {
        "Serif": "Georgia, 'Times New Roman', serif",
        "Sans-serif": "'Segoe UI', Arial, sans-serif",
        "Monospace": "'Courier New', monospace",
        "Dyslexic-friendly": "'Comic Sans MS', 'Comic Sans', cursive",
    }
    family = family_map.get(font_family, family_map["Serif"])
    return f"""
    <style>
    .reader-panel {{
        background-color: {colors['bg']};
        color: {colors['fg']};
        font-family: {family};
        font-size: {font_size}px;
        line-height: {line_spacing};
        text-align: {alignment};
        padding: 28px 34px;
        border-radius: 14px;
        filter: brightness({brightness}%);
        box-shadow: 0 2px 14px rgba(0,0,0,0.12);
        min-height: 420px;
        overflow-wrap: break-word;
    }}
    .reader-panel img {{ max-width: 100%; height: auto; }}
    .reader-panel mark {{ padding: 0 2px; border-radius: 3px; }}
    </style>
    """


def stars_html(rating):
    rating = round(rating or 0)
    return "★" * rating + "☆" * (5 - rating)
