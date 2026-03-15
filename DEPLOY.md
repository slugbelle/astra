# KP Astrology App — Deployment Guide

## Files
- `app.py` — Streamlit UI (main app)
- `kp_calc.py` — KP calculation engine (Swiss Ephemeris)
- `requirements.txt` — Python dependencies

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
Then open http://localhost:8501 in your browser.

## Deploy to Streamlit Community Cloud (Free, Shareable)

1. **Create a GitHub repo** (free at github.com)
   - Upload `app.py`, `kp_calc.py`, `requirements.txt`

2. **Go to** https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"
   - Select your repo and set main file to `app.py`
   - Click "Deploy"

3. **Share the URL** — you'll get a link like `https://yourname-kp-astro-app.streamlit.app`

## Features
- Planets: sign, nakshatra, pada, star lord, sub lord, sub-sub lord
- House cusps (Placidus/KP) with sublords
- Significators (3 levels)
- Vimsottari Dasha — Maha, Antardasha, Pratyantar with exact dates
- Divisionals D1–D60 (16 divisions)
- Current transits & ruling planets
- Save/load multiple charts
- Ayanamsa: KP, Lahiri, Raman
