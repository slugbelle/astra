"""
KP Astrology App - Streamlit UI
Krishnamurti Paddhati (KP) system with Swiss Ephemeris precision.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date, time
import json
import os
import pytz
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import kp_calc as kp

# ========================
# PAGE CONFIG
# ========================

st.set_page_config(
    page_title="KP Astrology",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .planet-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.85em;
        margin: 1px;
    }
    .stTabs [data-baseweb="tab"] { font-size: 0.9em; }
    .metric-card {
        background: #1e1e2e;
        border-radius: 8px;
        padding: 12px;
        margin: 4px 0;
    }
    div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 6px; }
    .dasha-current { background: linear-gradient(90deg, #1a3a2a, #0d1a0d); border-left: 3px solid #00ff88; padding: 8px; border-radius: 4px; }
    .dasha-future { opacity: 0.7; }
    .dasha-past { opacity: 0.4; }
</style>
""", unsafe_allow_html=True)

SAVE_FILE = "saved_charts.json"

PLANET_COLOR_MAP = {
    'Sun': '#FF8C00', 'Moon': '#C0C0C0', 'Mars': '#FF5555',
    'Mercury': '#00CC66', 'Jupiter': '#FFB347', 'Venus': '#FF69B4',
    'Saturn': '#AAAAAA', 'Rahu': '#9966FF', 'Ketu': '#CC4444',
    'Uranus': '#00CCCC', 'Neptune': '#4488FF', 'Pluto': '#996633'
}

# ========================
# HELPERS
# ========================

def badge(text, color='#444466'):
    return f'<span class="planet-badge" style="background:{color};color:white;">{text}</span>'

def planet_badge(planet):
    color = PLANET_COLOR_MAP.get(planet, '#555')
    sym = kp.PLANET_SYMBOLS.get(planet, '')
    return f'<span class="planet-badge" style="background:{color};color:white;">{sym} {planet}</span>'

def load_charts():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE) as f:
            return json.load(f)
    return {}

def save_chart_to_file(name, data):
    charts = load_charts()
    charts[name] = data
    with open(SAVE_FILE, 'w') as f:
        json.dump(charts, f, indent=2)

def serialize_chart_input(birth_dt_utc, lat, lon_geo, name, ayanamsa):
    return {
        'name': name,
        'birth_dt_utc': birth_dt_utc.isoformat(),
        'lat': lat,
        'lon_geo': lon_geo,
        'ayanamsa': ayanamsa,
    }

def deserialize_chart_input(data):
    return {
        'birth_dt_utc': datetime.fromisoformat(data['birth_dt_utc']),
        'lat': data['lat'],
        'lon_geo': data['lon_geo'],
        'ayanamsa': data.get('ayanamsa', 'KP'),
        'name': data.get('name', 'Chart'),
    }

def geocode_location(place_name: str):
    """Geocode a place name to lat/lon."""
    try:
        geolocator = Nominatim(user_agent="kp_astro_app_v1")
        loc = geolocator.geocode(place_name, timeout=10)
        if loc:
            return loc.latitude, loc.longitude, loc.address
    except Exception as e:
        st.warning(f"Geocoding error: {e}")
    return None, None, None

def get_timezone(lat, lon):
    """Get timezone from coordinates."""
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    return tz_name or 'UTC'

def local_to_utc(local_dt: datetime, tz_name: str) -> datetime:
    """Convert local datetime to UTC."""
    tz = pytz.timezone(tz_name)
    local_aware = tz.localize(local_dt)
    return local_aware.astimezone(pytz.utc).replace(tzinfo=None)

def fmt_date(dt):
    if isinstance(dt, datetime):
        return dt.strftime("%d %b %Y, %H:%M")
    return str(dt)

def now_active(start, end):
    now = datetime.utcnow()
    return start <= now < end

def dasha_status(start, end):
    now = datetime.utcnow()
    if now < start:
        return 'future', '🔵'
    elif now >= end:
        return 'past', '⚪'
    else:
        return 'current', '🟢'

# ========================
# SIDEBAR: CHART INPUT
# ========================

def sidebar_input():
    st.sidebar.title("🔭 KP Astrology")

    tab = st.sidebar.radio("", ["New Chart", "Load Saved"], horizontal=True)

    if tab == "Load Saved":
        charts = load_charts()
        if not charts:
            st.sidebar.info("No saved charts yet.")
            return None
        chart_name = st.sidebar.selectbox("Select chart", list(charts.keys()))
        if st.sidebar.button("Load", type="primary"):
            data = deserialize_chart_input(charts[chart_name])
            with st.spinner(f"Calculating {chart_name}..."):
                chart = kp.calculate_chart(
                    data['birth_dt_utc'], data['lat'], data['lon_geo'], data['ayanamsa']
                )
                chart['name'] = data['name']
                st.session_state['chart'] = chart
                st.session_state['chart_input'] = data
        if 'chart' in st.session_state:
            if st.sidebar.button("🗑️ Delete this chart"):
                charts = load_charts()
                if chart_name in charts:
                    del charts[chart_name]
                    with open(SAVE_FILE, 'w') as f:
                        json.dump(charts, f, indent=2)
                    st.sidebar.success("Deleted.")
        return None

    # --- New Chart ---
    st.sidebar.subheader("Birth Details")
    chart_name = st.sidebar.text_input("Name / Label", value="My Chart")
    birth_date = st.sidebar.date_input("Birth Date", value=date(1990, 1, 1),
                                        min_value=date(1800, 1, 1), max_value=date(2100, 1, 1))
    birth_time = st.sidebar.time_input("Birth Time (local)", value=time(12, 0))
    place = st.sidebar.text_input("Birth Place", value="New York, USA")
    ayanamsa = st.sidebar.selectbox("Ayanamsa", ['KP', 'Lahiri', 'Raman'], index=0)

    if st.sidebar.button("📍 Geocode & Calculate", type="primary"):
        with st.spinner("Geocoding..."):
            lat, lon_geo, address = geocode_location(place)

        if lat is None:
            st.sidebar.error("Could not find that location. Try a more specific name.")
            return None

        tz_name = get_timezone(lat, lon_geo)
        local_dt = datetime.combine(birth_date, birth_time)
        birth_dt_utc = local_to_utc(local_dt, tz_name)

        st.sidebar.success(f"📍 {address[:60]}...")
        st.sidebar.info(f"🕐 TZ: {tz_name}  →  UTC: {birth_dt_utc.strftime('%H:%M')}")

        with st.spinner("Calculating chart..."):
            chart = kp.calculate_chart(birth_dt_utc, lat, lon_geo, ayanamsa)
            chart['name'] = chart_name

        st.session_state['chart'] = chart
        st.session_state['chart_input'] = {
            'birth_dt_utc': birth_dt_utc, 'lat': lat, 'lon_geo': lon_geo,
            'ayanamsa': ayanamsa, 'name': chart_name, 'timezone': tz_name,
            'birth_place': address,
        }

        if st.sidebar.checkbox("💾 Save this chart", value=True):
            save_chart_to_file(chart_name, serialize_chart_input(
                birth_dt_utc, lat, lon_geo, chart_name, ayanamsa))
            st.sidebar.success("Saved!")

    st.sidebar.divider()
    st.sidebar.caption("🔭 KP Astrology App\nSwiss Ephemeris precision")
    return None

# ========================
# TAB: PLANETS
# ========================

def tab_planets(chart):
    planets = chart['planet_positions']
    planet_houses = chart['planet_houses']

    st.subheader("🪐 Planetary Positions")

    rows = []
    for p in kp.PLANET_LIST + kp.OUTER_PLANETS:
        if p not in planets:
            continue
        d = planets[p]
        house = planet_houses.get(p, '-')
        retro = '℞' if d.get('retrograde') else ''
        rows.append({
            'Planet': f"{kp.PLANET_SYMBOLS.get(p,'')} {p} {retro}",
            'Longitude': kp.format_lon(d['longitude']),
            'Sign': d['sign'],
            'Deg': f"{d['degree_in_sign']:.2f}°",
            'Sign Lord': d['sign_lord'],
            'Nakshatra': d['nakshatra'],
            'Pada': d['pada'],
            'Star Lord': d['star_lord'],
            'Sub Lord': d['sub_lord'],
            'Sub-Sub Lord': d['sub_sub_lord'],
            'House': house,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     'Planet': st.column_config.TextColumn(width='medium'),
                     'Longitude': st.column_config.TextColumn(width='medium'),
                     'Nakshatra': st.column_config.TextColumn(width='medium'),
                 })

    # Ascendant info
    st.subheader("🏠 Ascendant (Lagna)")
    asc = chart['house_cusps'][0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sign", asc['sign'])
    col2.metric("Star Lord", asc['star_lord'])
    col3.metric("Sub Lord", asc['sub_lord'])
    col4.metric("Degree", f"{asc['degree_in_sign']:.2f}°")

# ========================
# TAB: HOUSES
# ========================

def tab_houses(chart):
    st.subheader("🏠 House Cusps (Placidus / KP)")
    cusps = chart['house_cusps']
    planet_houses = chart['planet_houses']

    # Which planets in each house
    house_occupants = {}
    for p, h in planet_houses.items():
        house_occupants.setdefault(h, []).append(p)

    rows = []
    for c in cusps:
        h = c['house']
        occupants = ', '.join(house_occupants.get(h, [])) or '—'
        rows.append({
            'House': h,
            'Cusp Longitude': kp.format_lon(c['longitude']),
            'Sign': c['sign'],
            'Sign Lord': c['sign_lord'],
            'Nakshatra': c['nakshatra'],
            'Star Lord': c['star_lord'],
            'Sub Lord': c['sub_lord'],
            'Sub-Sub Lord': c['sub_sub_lord'],
            'Planets': occupants,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ========================
# TAB: SIGNIFICATORS
# ========================

def tab_significators(chart):
    st.subheader("🎯 KP Significators")
    sigs = chart['significators']

    st.markdown("""
    **Level 1** — Planets *occupying* the house
    **Level 2** — Planets whose *star lord* occupies the house
    **Level 3** — Planets whose *sub lord* occupies the house
    **Cusp lords** — Sign Lord · Star Lord · Sub Lord of the house cusp
    """)

    for h in range(1, 13):
        sig = sigs[h]
        with st.expander(f"**House {h}** — Cusp: {sig['cusp_sign_lord']} / {sig['cusp_star_lord']} / {sig['cusp_sub_lord']}"):
            col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
            col1.markdown("**Cusp Lords**")
            col1.markdown(f"Sign: **{sig['cusp_sign_lord']}**")
            col1.markdown(f"Star: **{sig['cusp_star_lord']}**")
            col1.markdown(f"Sub: **{sig['cusp_sub_lord']}**")
            col1.markdown(f"Sub-Sub: **{sig['cusp_sub_sub_lord']}**")

            col2.markdown("**L1 — In House**")
            if sig['planets_in_house']:
                col2.markdown(' '.join([planet_badge(p) for p in sig['planets_in_house']]),
                               unsafe_allow_html=True)
            else:
                col2.caption("None")

            col3.markdown("**L2 — Star Lord Tenants**")
            if sig['star_lord_tenants']:
                col3.markdown(' '.join([planet_badge(p) for p in sig['star_lord_tenants']]),
                               unsafe_allow_html=True)
            else:
                col3.caption("None")

            col4.markdown("**L3 — Sub Lord Tenants**")
            if sig['sub_lord_tenants']:
                col4.markdown(' '.join([planet_badge(p) for p in sig['sub_lord_tenants']]),
                               unsafe_allow_html=True)
            else:
                col4.caption("None")

# ========================
# TAB: DASHA
# ========================

def tab_dasha(chart):
    st.subheader("⏳ Vimsottari Dasha")

    dashas = chart['dashas']
    now = datetime.utcnow()

    current = chart['current_dasha']
    if current['maha']:
        maha = current['maha']
        antar = current['antar']
        pratyantar = current['pratyantar']

        st.markdown("### 🟢 Currently Active")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**Maha Dasha**  \n{planet_badge(maha['planet'])}", unsafe_allow_html=True)
        col1.caption(f"{fmt_date(maha['start'])} → {fmt_date(maha['end'])}")
        if antar:
            col2.markdown(f"**Antardasha**  \n{planet_badge(antar['planet'])}", unsafe_allow_html=True)
            col2.caption(f"{fmt_date(antar['start'])} → {fmt_date(antar['end'])}")
        if pratyantar:
            col3.markdown(f"**Pratyantar**  \n{planet_badge(pratyantar['planet'])}", unsafe_allow_html=True)
            col3.caption(f"{fmt_date(pratyantar['start'])} → {fmt_date(pratyantar['end'])}")

        st.divider()

    # Full dasha tree
    st.markdown("### 📅 Full Dasha Timeline")

    # Only show dashas relevant to current birth chart period (near now)
    # Show past 2 dashas + current + next 3
    visible_dashas = [d for d in dashas if d['end'] > now - timedelta(days=30 * 365)][:8]

    for maha in visible_dashas:
        status, icon = dasha_status(maha['start'], maha['end'])
        is_current = status == 'current'

        label = f"{icon} **{maha['planet']} Maha** — {maha['years']} yrs  ({fmt_date(maha['start'])} → {fmt_date(maha['end'])})"
        with st.expander(label, expanded=is_current):
            # Antardasha table
            rows = []
            for antar in maha['antardashas']:
                a_status, a_icon = dasha_status(antar['start'], antar['end'])
                rows.append({
                    '': a_icon,
                    'Antardasha': antar['planet'],
                    'Start': fmt_date(antar['start']),
                    'End': fmt_date(antar['end']),
                    'Duration': f"{(antar['end'] - antar['start']).days} days",
                })

            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={'': st.column_config.TextColumn(width='small')})

            # If this is the current maha, show pratyantar too
            if is_current and current['antar']:
                st.markdown(f"**Pratyantar in {current['antar']['planet']} Antardasha:**")
                prows = []
                for p in current['antar']['pratyantardashas']:
                    p_status, p_icon = dasha_status(p['start'], p['end'])
                    prows.append({
                        '': p_icon,
                        'Pratyantar': p['planet'],
                        'Start': fmt_date(p['start']),
                        'End': fmt_date(p['end']),
                        'Days': f"{(p['end'] - p['start']).days}",
                    })
                pdf = pd.DataFrame(prows)
                st.dataframe(pdf, use_container_width=True, hide_index=True,
                             column_config={'': st.column_config.TextColumn(width='small')})

# ========================
# TAB: DIVISIONALS
# ========================

def tab_divisionals(chart):
    st.subheader("📐 Divisional Charts")

    d_options = list(kp.DIVISIONAL_NAMES.keys())
    d_labels = list(kp.DIVISIONAL_NAMES.values())

    selected_label = st.selectbox("Select Divisional Chart", d_labels, index=8)  # default D9
    selected_d = d_options[d_labels.index(selected_label)]

    div_chart = kp.get_divisional_chart(chart['planet_positions'], selected_d)

    st.markdown(f"#### {kp.DIVISIONAL_NAMES[selected_d]}")

    # Group by sign
    sign_groups = {}
    for planet, pdata in div_chart.items():
        sign = pdata['sign']
        sign_groups.setdefault(sign, []).append(planet)

    # Show as sign grid
    cols = st.columns(6)
    for i, sign in enumerate(kp.SIGNS):
        with cols[i % 6]:
            planets_here = sign_groups.get(sign, [])
            st.markdown(f"**{sign}**")
            if planets_here:
                for p in planets_here:
                    sym = kp.PLANET_SYMBOLS.get(p, '')
                    color = PLANET_COLOR_MAP.get(p, '#555')
                    st.markdown(
                        f'<span style="background:{color};color:white;padding:2px 6px;'
                        f'border-radius:10px;font-size:0.8em;">{sym}{p}</span>',
                        unsafe_allow_html=True
                    )
            else:
                st.caption("—")

    st.divider()

    # Full table
    rows = []
    for p in kp.PLANET_LIST:
        if p in div_chart:
            d = div_chart[p]
            rows.append({
                'Planet': f"{kp.PLANET_SYMBOLS.get(p,'')} {p}",
                'Sign': d['sign'],
                'Degree': f"{d['degree_in_sign']:.2f}°",
                'Sign Lord': d['sign_lord'],
                'Nakshatra': d['nakshatra'],
                'Star Lord': d['star_lord'],
                'Sub Lord': d['sub_lord'],
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Multiple divisionals at once
    st.divider()
    st.markdown("#### 📊 Planet Sign Across Multiple Divisionals")
    planet_sel = st.selectbox("Select Planet", kp.PLANET_LIST, key="multi_div_planet")
    multi_rows = []
    for d in d_options:
        dc = kp.get_divisional_chart(chart['planet_positions'], d)
        if planet_sel in dc:
            info = dc[planet_sel]
            multi_rows.append({
                'Division': kp.DIVISIONAL_NAMES[d],
                'Sign': info['sign'],
                'Degree': f"{info['degree_in_sign']:.2f}°",
                'Sign Lord': info['sign_lord'],
                'Nakshatra': info['nakshatra'],
                'Star Lord': info['star_lord'],
                'Sub Lord': info['sub_lord'],
            })
    st.dataframe(pd.DataFrame(multi_rows), use_container_width=True, hide_index=True)

# ========================
# TAB: TRANSITS & RULING PLANETS
# ========================

def tab_transits(chart):
    st.subheader("🌍 Current Transits & Ruling Planets")

    lat = chart['lat']
    lon_geo = chart['lon_geo']

    if st.button("🔄 Refresh"):
        st.session_state.pop('transit_chart', None)

    if 'transit_chart' not in st.session_state:
        with st.spinner("Calculating transits..."):
            st.session_state['transit_chart'] = kp.calculate_transit_chart(lat, lon_geo, chart['ayanamsa_type'])

    transit = st.session_state['transit_chart']
    st.caption(f"As of: {transit['datetime_utc'].strftime('%Y-%m-%d %H:%M UTC')}")

    # Ruling planets
    rp = transit['ruling_planets']
    st.markdown("### ⭐ Ruling Planets")
    cols = st.columns(5)
    labels = ['Day Lord', 'Lagna Sign', 'Lagna Star', 'Moon Sign', 'Moon Star']
    vals = [rp['day_lord'], rp['lagna_sign_lord'], rp['lagna_star_lord'],
            rp['moon_sign_lord'], rp['moon_star_lord']]
    for i, (lbl, val) in enumerate(zip(labels, vals)):
        with cols[i]:
            color = PLANET_COLOR_MAP.get(val, '#555')
            st.markdown(
                f'<div style="background:{color}22;border:1px solid {color};border-radius:8px;'
                f'padding:8px;text-align:center"><b style="color:{color}">{val}</b><br>'
                f'<small style="color:#aaa">{lbl}</small></div>',
                unsafe_allow_html=True
            )

    st.divider()

    # Transit planets vs natal
    st.markdown("### 🪐 Transit Planets")
    t_planets = transit['planet_positions']
    n_planets = chart['planet_positions']
    n_houses = chart['planet_houses']

    rows = []
    for p in kp.PLANET_LIST:
        if p not in t_planets:
            continue
        td = t_planets[p]
        nd = n_planets.get(p, {})
        retro = '℞' if td.get('retrograde') else ''
        rows.append({
            'Planet': f"{kp.PLANET_SYMBOLS.get(p,'')} {p} {retro}",
            'Transit Sign': td['sign'],
            'Transit Star': td['star_lord'],
            'Transit Sub': td['sub_lord'],
            'Natal Sign': nd.get('sign', ''),
            'Natal House': n_houses.get(p, ''),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Transit chart house cusps
    with st.expander("Transit House Cusps"):
        crows = []
        for c in transit['house_cusps']:
            crows.append({
                'House': c['house'],
                'Longitude': kp.format_lon(c['longitude']),
                'Sign': c['sign'],
                'Star Lord': c['star_lord'],
                'Sub Lord': c['sub_lord'],
            })
        st.dataframe(pd.DataFrame(crows), use_container_width=True, hide_index=True)

# ========================
# TAB: CHART OVERVIEW
# ========================

def tab_overview(chart):
    inp = st.session_state.get('chart_input', {})
    name = chart.get('name', 'Chart')

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"## {name}")
        if inp:
            bdt = inp.get('birth_dt_utc', chart.get('birth_dt_utc'))
            tz = inp.get('timezone', 'UTC')
            place = inp.get('birth_place', '')
            if isinstance(bdt, datetime):
                st.markdown(f"**Birth:** {bdt.strftime('%d %B %Y, %H:%M UTC')}")
            if tz:
                st.markdown(f"**Timezone:** {tz}")
            if place:
                st.markdown(f"**Place:** {place[:80]}")
            st.markdown(f"**Coords:** {chart['lat']:.4f}°N, {chart['lon_geo']:.4f}°E")
        st.markdown(f"**Ayanamsa:** {chart['ayanamsa_type']} ({chart['ayanamsa']:.6f}°)")

    with col2:
        # Key chart points
        moon = chart['planet_positions']['Moon']
        asc = chart['house_cusps'][0]
        sun = chart['planet_positions']['Sun']

        st.metric("☉ Sun", f"{sun['sign']} - {sun['nakshatra']}")
        st.metric("☽ Moon", f"{moon['sign']} - {moon['nakshatra']}")
        st.metric("⬆ Lagna", f"{asc['sign']} - {asc['nakshatra']}")

    st.divider()

    # Current dasha summary
    cd = chart['current_dasha']
    if cd['maha']:
        st.markdown("### ⏳ Current Dasha")
        col1, col2, col3 = st.columns(3)
        with col1:
            maha = cd['maha']
            st.markdown(f"**Maha: {maha['planet']}**")
            pct = (datetime.utcnow() - maha['start']).total_seconds() / (maha['end'] - maha['start']).total_seconds()
            st.progress(min(max(pct, 0), 1), text=f"{pct*100:.0f}% complete")
            st.caption(f"Ends: {fmt_date(maha['end'])}")
        with col2:
            if cd['antar']:
                antar = cd['antar']
                st.markdown(f"**Antar: {antar['planet']}**")
                pct = (datetime.utcnow() - antar['start']).total_seconds() / (antar['end'] - antar['start']).total_seconds()
                st.progress(min(max(pct, 0), 1), text=f"{pct*100:.0f}% complete")
                st.caption(f"Ends: {fmt_date(antar['end'])}")
        with col3:
            if cd['pratyantar']:
                prat = cd['pratyantar']
                st.markdown(f"**Pratyantar: {prat['planet']}**")
                pct = (datetime.utcnow() - prat['start']).total_seconds() / (prat['end'] - prat['start']).total_seconds()
                st.progress(min(max(pct, 0), 1), text=f"{pct*100:.0f}% complete")
                st.caption(f"Ends: {fmt_date(prat['end'])}")

    st.divider()

    # House occupancy quick summary
    st.markdown("### 🏠 Planets in Houses")
    house_occupants = {}
    for p, h in chart['planet_houses'].items():
        house_occupants.setdefault(h, []).append(p)

    cols = st.columns(6)
    for h in range(1, 13):
        with cols[(h - 1) % 6]:
            planets = house_occupants.get(h, [])
            cusp = chart['house_cusps'][h - 1]
            st.markdown(f"**H{h}** — {cusp['sign'][:3]}")
            if planets:
                for p in planets:
                    sym = kp.PLANET_SYMBOLS.get(p, '')
                    color = PLANET_COLOR_MAP.get(p, '#555')
                    st.markdown(
                        f'<span style="background:{color};color:white;padding:1px 6px;'
                        f'border-radius:8px;font-size:0.75em;">{sym}{p}</span>',
                        unsafe_allow_html=True
                    )
            else:
                st.caption("—")

# ========================
# MAIN
# ========================

def main():
    sidebar_input()

    if 'chart' not in st.session_state:
        st.title("🔭 KP Astrology App")
        st.markdown("""
        Welcome! This app uses **Krishnamurti Paddhati (KP)** system with **Swiss Ephemeris** precision.

        ### Features:
        - 🪐 **Planetary positions** with Nakshatra, Pada, Star Lord, Sub Lord, Sub-Sub Lord
        - 🏠 **KP House cusps** (Placidus) with Sublords
        - 🎯 **Significators** — 3 levels of KP house significators
        - ⏳ **Vimsottari Dasha** — Maha, Antar, Pratyantar with exact dates
        - 📐 **Divisional charts** — D1 through D60 (16 divisions)
        - 🌍 **Current transits** with ruling planets
        - 💾 **Save & load** multiple charts

        ### Getting Started:
        1. Enter birth details in the **sidebar** on the left
        2. Click **📍 Geocode & Calculate**
        3. Explore the tabs above

        ---
        *Uses KP Krishnamurti Ayanamsa by default. Switch to Lahiri or Raman in the sidebar.*
        """)
        return

    chart = st.session_state['chart']
    name = chart.get('name', 'Chart')
    st.title(f"🔭 {name}")

    tabs = st.tabs(["📊 Overview", "🪐 Planets", "🏠 Houses", "🎯 Significators",
                    "⏳ Dasha", "📐 Divisionals", "🌍 Transits"])

    with tabs[0]:
        tab_overview(chart)
    with tabs[1]:
        tab_planets(chart)
    with tabs[2]:
        tab_houses(chart)
    with tabs[3]:
        tab_significators(chart)
    with tabs[4]:
        tab_dasha(chart)
    with tabs[5]:
        tab_divisionals(chart)
    with tabs[6]:
        tab_transits(chart)


if __name__ == "__main__":
    main()
