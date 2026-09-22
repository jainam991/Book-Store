# 📚 Inkwell — E-Book Store & Reader (Streamlit)

A full e-book platform built entirely in Python/Streamlit + SQLite: browse & buy
books, a PDF/EPUB reader with bookmarks/highlights/notes/search/TTS/translation,
purchase history, notifications, ratings & reviews, and an admin dashboard.

## What's implemented vs. simplified

| Area | Status |
|---|---|
| PDF/EPUB reading, page & scroll mode, TOC, search | ✅ Fully working (PyMuPDF + ebooklib) |
| Bookmarks, highlights, notes | ✅ Working. Highlighting is "paste the snippet to highlight" rather than click-drag text selection — Streamlit has no native text-selection API, this is the practical workaround |
| Font/size/spacing/alignment, Light/Dark/Sepia, brightness | ✅ Fully working, saved per-user |
| Reading progress %, current/total page, resume position | ✅ Fully working, auto-saved to SQLite |
| Full-screen / orientation | ✅ Focus mode hides chrome; true orientation lock is a mobile-browser/OS feature, noted in-app |
| Text-to-speech | ✅ via gTTS (needs outbound internet at runtime) |
| Translation | ✅ via deep-translator / Google Translate (needs outbound internet) |
| Dictionary | ✅ via free dictionaryapi.dev |
| Purchases | ✅ Simulated checkout & transaction ledger — swap in Stripe/Razorpay/PayPal for real payments |
| Notifications | ✅ Auto-fired on purchase/new release/broadcast; reminders are a manual test button (wire to a cron job for real scheduling) |
| Ratings & reviews | ✅ Full CRUD + like + report |
| Admin dashboard | ✅ Users, books, authors, sales, revenue, active users, downloads, most popular, recent purchases, revenue chart |
| Database | ✅ SQLite, schema matches your spec (Users, Books, Authors, Categories, Library, Wishlist, Purchases, Reviews, Bookmarks, Notifications) + Highlights/Settings added |

**Important limitation:** Streamlit Community Cloud's filesystem is *ephemeral* —
the SQLite DB and any admin-uploaded book files reset whenever the app reboots
or you push a new commit. Great for a demo/portfolio; for a real product, swap:
- SQLite → Postgres (Supabase / Neon / Railway — a few line changes in `db.py`)
- Local file storage → S3 / Cloudflare R2 / Supabase Storage for book files & covers

Every DB call lives in `db.py` and every file path is centralized, specifically
so that swap is contained.

## Project structure

```
ebook_platform/
├── app.py                        # Home / Browse + login/signup
├── db.py                         # SQLite schema + all data access
├── utils.py                      # PDF/EPUB parsing, TTS, translation, dictionary
├── styles.py                     # Shared CSS + reader theming
├── seed_demo.py                  # Auto-generates 6 sample books on first run
├── requirements.txt
├── .streamlit/config.toml        # Theme
└── pages/
    ├── 1_📥_Library.py           # Continue reading, progress, wishlist
    ├── 2_📖_Reader.py            # The reading engine
    ├── 3_🔔_Notifications.py
    ├── 4_🛒_Purchase_History.py  # Includes simulated checkout
    ├── 5_⭐_Reviews.py
    └── 6_🛠️_Admin.py            # Admin-only dashboard & catalog management
```

Demo admin login (auto-seeded): **admin@bookstore.com** / **admin123**

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

It opens at `http://localhost:8501`. On first run it auto-generates 6 sample
PDF books with covers so the store isn't empty — no manual setup needed.

## Deploy to Streamlit Community Cloud (free) — step by step

1. **Push this folder to GitHub.**
   ```bash
   cd ebook_platform
   git init
   git add .
   git commit -m "Initial commit — Inkwell e-book platform"
   git branch -M main
   git remote add origin https://github.com/<your-username>/inkwell-ebook.git
   git push -u origin main
   ```
   (Create the empty repo on GitHub first if you haven't.)

2. **Go to** [share.streamlit.io](https://share.streamlit.io) **and sign in** with your GitHub account.

3. Click **"New app"**.

4. Fill in:
   - **Repository:** `<your-username>/inkwell-ebook`
   - **Branch:** `main`
   - **Main file path:** `app.py`

5. Click **"Advanced settings"** (optional but recommended):
   - Python version: 3.11
   - No secrets are required for this app to run as-is (everything is local SQLite + free APIs).

6. Click **"Deploy"**. First build takes 2-4 minutes (installing PyMuPDF, ebooklib, etc.).

7. Your app is live at `https://<something>.streamlit.app`. Share that link.

8. **Redeploying after changes:** just `git push` to `main` — Streamlit Cloud
   auto-redetects and redeploys. Remember: the DB resets on every redeploy
   unless you've migrated to an external database (see limitation above).

### Optional: keep data across redeploys (recommended before sharing widely)
Swap SQLite for a free Postgres instance (e.g. [Supabase](https://supabase.com) or
[Neon](https://neon.tech)):
1. Create a free Postgres DB there, grab the connection string.
2. Add it as a Streamlit **secret**: Settings → Secrets →
   `DATABASE_URL = "postgresql://..."`.
3. In `db.py`, replace `sqlite3.connect(DB_PATH)` with `psycopg2.connect(st.secrets["DATABASE_URL"])`
   and swap `?` placeholders for `%s` (psycopg2 syntax). The rest of the app's
   logic (every function signature) stays identical.

## Extending toward production
- Real payments: Stripe Checkout session created in `make_purchase()`, webhook confirms `payment_status`.
- Real file delivery: generate signed S3 URLs instead of local paths in `books.file_url`.
- Scheduled reading reminders: a small cron (GitHub Actions / Cloud Scheduler) hitting a script that calls `db.push_notification()` for inactive users.
- Real-time TTS quality: swap gTTS for a paid TTS API (ElevenLabs, Azure, AWS Polly) if voice quality matters.
