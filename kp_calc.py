"""
KP Astrology Calculation Engine
Uses Swiss Ephemeris (pyswisseph) for precise planetary calculations.
"""

import swisseph as swe
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# ========================
# CONSTANTS
# ========================

PLANET_IDS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mars': swe.MARS,
    'Mercury': swe.MERCURY,
    'Jupiter': swe.JUPITER,
    'Venus': swe.VENUS,
    'Saturn': swe.SATURN,
    'Rahu': swe.MEAN_NODE,
    'Uranus': swe.URANUS,
    'Neptune': swe.NEPTUNE,
    'Pluto': swe.PLUTO,
}

PLANET_LIST = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']
OUTER_PLANETS = ['Uranus', 'Neptune', 'Pluto']
ALL_PLANETS = PLANET_LIST + OUTER_PLANETS

DASHA_YEARS = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7,
    'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17,
}
TOTAL_DASHA_YEARS = 120
DASHA_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']

NAKSHATRA_NAMES = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni',
    'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha',
    'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta',
    'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'
]
NAKSHATRA_LORDS = [DASHA_ORDER[i % 9] for i in range(27)]

SIGNS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]
SIGN_LORDS = {
    'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury', 'Cancer': 'Moon',
    'Leo': 'Sun', 'Virgo': 'Mercury', 'Libra': 'Venus', 'Scorpio': 'Mars',
    'Sagittarius': 'Jupiter', 'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter'
}

PLANET_SYMBOLS = {
    'Sun': '☉', 'Moon': '☽', 'Mars': '♂', 'Mercury': '☿',
    'Jupiter': '♃', 'Venus': '♀', 'Saturn': '♄',
    'Rahu': '☊', 'Ketu': '☋', 'Uranus': '♅', 'Neptune': '♆', 'Pluto': '♇'
}

PLANET_COLORS = {
    'Sun': '#FF8C00', 'Moon': '#C0C0C0', 'Mars': '#FF4444', 'Mercury': '#00CC00',
    'Jupiter': '#FFA500', 'Venus': '#FF69B4', 'Saturn': '#808080',
    'Rahu': '#6600CC', 'Ketu': '#990000', 'Uranus': '#00CCCC',
    'Neptune': '#0066FF', 'Pluto': '#663300'
}

WEEKDAY_LORDS = {0: 'Moon', 1: 'Mars', 2: 'Mercury', 3: 'Jupiter',
                 4: 'Venus', 5: 'Saturn', 6: 'Sun'}

NAK_SIZE = 360 / 27  # ~13.3333°

# ========================
# CORE UTILITY FUNCTIONS
# ========================

def dms_to_decimal(d: int, m: int, s: float) -> float:
    return d + m / 60 + s / 3600

def decimal_to_dms(decimal: float) -> Tuple[int, int, float]:
    d = int(decimal)
    m = int((decimal - d) * 60)
    s = ((decimal - d) * 60 - m) * 60
    return d, m, s

def format_dms(decimal: float) -> str:
    d, m, s = decimal_to_dms(abs(decimal))
    return f"{d}° {m:02d}' {s:04.1f}\""

def format_lon(lon: float) -> str:
    sign_num = int(lon / 30)
    deg_in_sign = lon - sign_num * 30
    d, m, s = decimal_to_dms(deg_in_sign)
    return f"{SIGNS[sign_num][:3]} {d}° {m:02d}' {s:04.1f}\""

def get_julian_day(dt: datetime) -> float:
    """Convert UTC datetime to Julian Day."""
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute / 60.0 + dt.second / 3600.0)

def set_ayanamsa(ayanamsa_type: str = 'KP'):
    if ayanamsa_type == 'KP':
        swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    elif ayanamsa_type == 'Lahiri':
        swe.set_sid_mode(swe.SIDM_LAHIRI)
    elif ayanamsa_type == 'Raman':
        swe.set_sid_mode(swe.SIDM_RAMAN)

def tropical_to_sidereal(longitude: float, ayanamsa: float) -> float:
    return (longitude - ayanamsa) % 360

# ========================
# NAKSHATRA & SUBLORD
# ========================

def get_nakshatra_info(sidereal_lon: float) -> Dict:
    """Get full KP nakshatra, pada, star lord, sub lord, sub-sub lord."""
    nak_index = min(int(sidereal_lon / NAK_SIZE), 26)
    nak_pos = sidereal_lon - nak_index * NAK_SIZE  # 0 to NAK_SIZE
    pada = min(int(nak_pos / (NAK_SIZE / 4)) + 1, 4)
    star_lord = NAKSHATRA_LORDS[nak_index]
    star_lord_idx = DASHA_ORDER.index(star_lord)

    # Build sublord table for this nakshatra (starts from star lord)
    subs = _build_sublord_table(star_lord_idx, NAK_SIZE)

    # Find sub lord
    found_sub = _find_lord(subs, nak_pos)
    sub_lord = found_sub['planet']
    sub_pos = nak_pos - found_sub['start']
    sub_size = found_sub['size']

    # Build sub-sub lord table
    sub_lord_idx = DASHA_ORDER.index(sub_lord)
    sub_subs = _build_sublord_table(sub_lord_idx, sub_size)
    found_sub_sub = _find_lord(sub_subs, sub_pos)

    return {
        'nakshatra': NAKSHATRA_NAMES[nak_index],
        'nakshatra_num': nak_index + 1,
        'pada': pada,
        'star_lord': star_lord,
        'sub_lord': sub_lord,
        'sub_sub_lord': found_sub_sub['planet'],
        'nak_pos_deg': nak_pos,
    }

def _build_sublord_table(start_lord_idx: int, total_size: float) -> List[Dict]:
    """Build 9 subdivision records proportional to dasha years."""
    table = []
    pos = 0.0
    for i in range(9):
        planet = DASHA_ORDER[(start_lord_idx + i) % 9]
        size = (DASHA_YEARS[planet] / TOTAL_DASHA_YEARS) * total_size
        table.append({'planet': planet, 'start': pos, 'end': pos + size, 'size': size})
        pos += size
    return table

def _find_lord(table: List[Dict], pos: float) -> Dict:
    """Find the lord entry that contains pos."""
    for entry in table:
        if entry['start'] <= pos < entry['end']:
            return entry
    return table[-1]  # fallback

def get_sign_info(sidereal_lon: float) -> Dict:
    sign_num = int(sidereal_lon / 30) % 12
    sign = SIGNS[sign_num]
    degree_in_sign = sidereal_lon - sign_num * 30
    return {
        'sign': sign,
        'sign_num': sign_num,
        'degree_in_sign': degree_in_sign,
        'sign_lord': SIGN_LORDS[sign],
    }

# ========================
# PLANET POSITIONS
# ========================

def get_planet_positions(jd: float, ayanamsa: float) -> Dict:
    """Calculate all planet positions."""
    positions = {}
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    for planet_name, planet_id in PLANET_IDS.items():
        result, _ = swe.calc_ut(jd, planet_id, flags)
        trop_lon = result[0]
        speed = result[3]
        sid_lon = tropical_to_sidereal(trop_lon, ayanamsa)

        positions[planet_name] = {
            'longitude': sid_lon,
            'tropical_lon': trop_lon,
            'speed': speed,
            'retrograde': speed < 0,
            **get_sign_info(sid_lon),
            **get_nakshatra_info(sid_lon),
        }

    # Ketu = Rahu + 180°
    rahu_lon = positions['Rahu']['longitude']
    ketu_lon = (rahu_lon + 180) % 360
    positions['Ketu'] = {
        'longitude': ketu_lon,
        'tropical_lon': (positions['Rahu']['tropical_lon'] + 180) % 360,
        'speed': -positions['Rahu']['speed'],
        'retrograde': True,
        **get_sign_info(ketu_lon),
        **get_nakshatra_info(ketu_lon),
    }
    return positions

# ========================
# HOUSE CUSPS
# ========================

def get_house_cusps(jd: float, lat: float, lon_geo: float, ayanamsa: float) -> List[Dict]:
    """Calculate KP house cusps using Placidus system."""
    cusps, ascmc = swe.houses(jd, lat, lon_geo, b'P')
    # pyswisseph returns 12-element tuple: cusps[0]=H1, cusps[11]=H12
    house_cusps = []
    for i in range(12):
        trop_cusp = cusps[i]
        sid_cusp = tropical_to_sidereal(trop_cusp, ayanamsa)
        house_cusps.append({
            'house': i + 1,
            'longitude': sid_cusp,
            'tropical_lon': trop_cusp,
            **get_sign_info(sid_cusp),
            **get_nakshatra_info(sid_cusp),
        })
    return house_cusps

# ========================
# PLANET HOUSES
# ========================

def get_planet_houses(planet_positions: Dict, house_cusps: List[Dict]) -> Dict[str, int]:
    """Determine which house each planet occupies."""
    cusp_lons = [c['longitude'] for c in house_cusps]
    planet_houses = {}

    for planet_name in PLANET_LIST:
        if planet_name not in planet_positions:
            continue
        planet_lon = planet_positions[planet_name]['longitude']
        house = _find_house(planet_lon, cusp_lons)
        planet_houses[planet_name] = house

    return planet_houses

def _find_house(planet_lon: float, cusp_lons: List[float]) -> int:
    for i in range(12):
        start = cusp_lons[i]
        end = cusp_lons[(i + 1) % 12]
        if end > start:
            if start <= planet_lon < end:
                return i + 1
        else:  # wraps around 360
            if planet_lon >= start or planet_lon < end:
                return i + 1
    return 12

# ========================
# SIGNIFICATORS
# ========================

def get_significators(planet_positions: Dict, house_cusps: List[Dict],
                      planet_houses: Dict[str, int]) -> Dict[int, Dict]:
    """Calculate KP significators for all 12 houses."""
    significators = {}
    for house_num in range(1, 13):
        cusp = next(c for c in house_cusps if c['house'] == house_num)

        # Level 1: Planets in house
        in_house = [p for p, h in planet_houses.items() if h == house_num]

        # Level 2: Planets whose star lord occupies this house
        star_lord_tenants = []
        for p in PLANET_LIST:
            if p in planet_positions:
                sl = planet_positions[p]['star_lord']
                if planet_houses.get(sl, 0) == house_num and p not in in_house:
                    star_lord_tenants.append(p)

        # Level 3: Planets whose sub lord occupies this house
        sub_lord_tenants = []
        for p in PLANET_LIST:
            if p in planet_positions:
                subl = planet_positions[p]['sub_lord']
                if planet_houses.get(subl, 0) == house_num and p not in in_house and p not in star_lord_tenants:
                    sub_lord_tenants.append(p)

        significators[house_num] = {
            'cusp_sign_lord': cusp['sign_lord'],
            'cusp_star_lord': cusp['star_lord'],
            'cusp_sub_lord': cusp['sub_lord'],
            'cusp_sub_sub_lord': cusp['sub_sub_lord'],
            'planets_in_house': in_house,
            'star_lord_tenants': star_lord_tenants,
            'sub_lord_tenants': sub_lord_tenants,
        }
    return significators

# ========================
# VIMSOTTARI DASHA
# ========================

def get_dasha_tree(moon_lon: float, birth_dt: datetime) -> List[Dict]:
    """
    Calculate Vimsottari Dasha tree with Maha, Antar, and Pratyantar.
    Returns list of Maha dashas covering 3 full cycles (360 years).
    """
    nak_index = min(int(moon_lon / NAK_SIZE), 26)
    nak_pos = moon_lon - nak_index * NAK_SIZE
    star_lord = NAKSHATRA_LORDS[nak_index]
    star_lord_idx = DASHA_ORDER.index(star_lord)

    # Fraction of first dasha elapsed
    first_dasha_years = DASHA_YEARS[star_lord]
    # The entire nakshatra corresponds to first_dasha_years
    elapsed_fraction = nak_pos / NAK_SIZE
    elapsed_years = elapsed_fraction * first_dasha_years
    remaining_years = first_dasha_years - elapsed_years

    # Virtual start of the first dasha (may be before birth)
    virtual_start = birth_dt - timedelta(days=elapsed_years * 365.25)

    dashas = []
    current_dt = virtual_start
    idx = star_lord_idx

    for _ in range(27):  # ~3 full cycles of 9
        planet = DASHA_ORDER[idx % 9]
        years = DASHA_YEARS[planet]
        days = years * 365.25
        end_dt = current_dt + timedelta(days=days)
        antardashas = _calc_antardashas(planet, current_dt, years)
        dashas.append({
            'planet': planet,
            'start': current_dt,
            'end': end_dt,
            'years': years,
            'antardashas': antardashas,
        })
        current_dt = end_dt
        idx += 1

    return dashas

def _calc_antardashas(maha_planet: str, maha_start: datetime, maha_years: float) -> List[Dict]:
    maha_idx = DASHA_ORDER.index(maha_planet)
    total_days = maha_years * 365.25
    antardashas = []
    current_dt = maha_start
    for i in range(9):
        planet = DASHA_ORDER[(maha_idx + i) % 9]
        days = (DASHA_YEARS[planet] / TOTAL_DASHA_YEARS) * total_days
        end_dt = current_dt + timedelta(days=days)
        pratyantars = _calc_pratyantars(planet, current_dt, days)
        antardashas.append({
            'planet': planet,
            'start': current_dt,
            'end': end_dt,
            'pratyantardashas': pratyantars,
        })
        current_dt = end_dt
    return antardashas

def _calc_pratyantars(antar_planet: str, antar_start: datetime, antar_days: float) -> List[Dict]:
    antar_idx = DASHA_ORDER.index(antar_planet)
    pratyantars = []
    current_dt = antar_start
    for i in range(9):
        planet = DASHA_ORDER[(antar_idx + i) % 9]
        days = (DASHA_YEARS[planet] / TOTAL_DASHA_YEARS) * antar_days
        end_dt = current_dt + timedelta(days=days)
        pratyantars.append({'planet': planet, 'start': current_dt, 'end': end_dt})
        current_dt = end_dt
    return pratyantars

def get_current_dasha(dashas: List[Dict], target_dt: datetime) -> Dict:
    """Find active Maha/Antar/Pratyantar at target_dt."""
    result = {'maha': None, 'antar': None, 'pratyantar': None}
    for maha in dashas:
        if maha['start'] <= target_dt < maha['end']:
            result['maha'] = maha
            for antar in maha['antardashas']:
                if antar['start'] <= target_dt < antar['end']:
                    result['antar'] = antar
                    for pratyantar in antar['pratyantardashas']:
                        if pratyantar['start'] <= target_dt < pratyantar['end']:
                            result['pratyantar'] = pratyantar
                            break
                    break
            break
    return result

# ========================
# DIVISIONAL CHARTS
# ========================

DIVISIONAL_NAMES = {
    1: 'D1 - Rashi (Birth Chart)',
    2: 'D2 - Hora (Wealth)',
    3: 'D3 - Drekkana (Siblings)',
    4: 'D4 - Chaturthamsha (Fortune)',
    7: 'D7 - Saptamsha (Children)',
    9: 'D9 - Navamsha (Marriage/Dharma)',
    10: 'D10 - Dashamsha (Career)',
    12: 'D12 - Dwadashamsha (Parents)',
    16: 'D16 - Shodashamsha (Vehicles)',
    20: 'D20 - Vimsamsha (Spiritual)',
    24: 'D24 - Chaturvimsamsha (Education)',
    27: 'D27 - Saptavimsamsha (Strength)',
    30: 'D30 - Trimsamsha (Evils)',
    40: 'D40 - Khavedamsha (Auspicious)',
    45: 'D45 - Akshavedamsha (All)',
    60: 'D60 - Shashtiamsha (Past Life)',
}

def get_divisional_longitude(lon: float, division: int) -> float:
    """
    Calculate divisional chart longitude.
    Uses standard Parashari divisional formulas.
    """
    if division == 1:
        return lon

    sign_num = int(lon / 30) % 12
    deg = lon - sign_num * 30  # 0–30°

    if division == 2:  # Hora
        # Odd signs (0,2,4,6,8,10): 0-15°=Leo, 15-30°=Cancer
        # Even signs (1,3,5,7,9,11): 0-15°=Cancer, 15-30°=Leo
        if sign_num % 2 == 0:  # odd signs
            new_sign = 4 if deg < 15 else 3  # Leo=4, Cancer=3
        else:  # even signs
            new_sign = 3 if deg < 15 else 4
        pos_in_new = (deg % 15) * 2
        return new_sign * 30 + pos_in_new

    elif division == 3:  # Drekkana
        part = int(deg / 10)
        # Aries-type: same sign, 5th, 9th
        # General rule: each third maps to same trine
        new_sign = (sign_num + part * 4) % 12
        pos_in_new = (deg % 10) * 3
        return new_sign * 30 + pos_in_new

    elif division == 9:  # Navamsha
        part = int(deg / (30 / 9))  # 0-8
        # Fire signs start Aries, Earth start Capricorn, Air start Libra, Water start Cancer
        fire = [0, 4, 8]
        earth = [1, 5, 9]
        air = [2, 6, 10]
        water = [3, 7, 11]
        if sign_num in fire:
            start = 0
        elif sign_num in earth:
            start = 9
        elif sign_num in air:
            start = 6
        else:
            start = 3
        new_sign = (start + part) % 12
        pos_in_new = (deg % (30 / 9)) * 9
        return new_sign * 30 + pos_in_new

    elif division == 30:  # Trimsamsha - special rules
        # Odd signs: 0-5 Mars, 5-10 Saturn, 10-18 Jupiter, 18-25 Mercury, 25-30 Venus
        # Even signs: 0-5 Venus, 5-12 Mercury, 12-20 Jupiter, 20-25 Saturn, 25-30 Mars
        if sign_num % 2 == 0:  # odd signs
            if deg < 5: new_sign = (sign_num + 0) % 12  # Mars-Aries
            elif deg < 10: new_sign = (sign_num + 9) % 12  # Saturn-Cap
            elif deg < 18: new_sign = (sign_num + 2) % 12  # Jupiter-Pis
            elif deg < 25: new_sign = (sign_num + 5) % 12  # Mercury-Gem
            else: new_sign = (sign_num + 1) % 12  # Venus-Tau
        else:  # even signs
            if deg < 5: new_sign = (sign_num + 1) % 12
            elif deg < 12: new_sign = (sign_num + 5) % 12
            elif deg < 20: new_sign = (sign_num + 2) % 12
            elif deg < 25: new_sign = (sign_num + 9) % 12
            else: new_sign = (sign_num + 0) % 12
        return new_sign * 30 + (deg / 30) * 30

    else:
        # Generic formula: divide sign into `division` equal parts
        part_size = 30.0 / division
        part = int(deg / part_size)
        new_sign = (sign_num * division + part) % 12
        pos_in_new = (deg % part_size) * division
        return new_sign * 30 + pos_in_new

def get_divisional_chart(planet_positions: Dict, division: int) -> Dict[str, Dict]:
    """Calculate divisional chart positions for all planets."""
    div_chart = {}
    for planet_name in PLANET_LIST:
        if planet_name in planet_positions:
            d_lon = get_divisional_longitude(planet_positions[planet_name]['longitude'], division)
            div_chart[planet_name] = {
                'longitude': d_lon,
                **get_sign_info(d_lon),
                **get_nakshatra_info(d_lon),
            }
    return div_chart

# ========================
# RULING PLANETS
# ========================

def get_ruling_planets(planet_positions: Dict, house_cusps: List[Dict],
                       ref_dt: datetime = None) -> Dict:
    """Calculate KP ruling planets."""
    if ref_dt is None:
        ref_dt = datetime.utcnow()

    day_lord = WEEKDAY_LORDS[ref_dt.weekday()]
    lagna = house_cusps[0] if house_cusps else {}
    moon = planet_positions.get('Moon', {})

    lagna_sign_lord = lagna.get('sign_lord', '')
    lagna_star_lord = lagna.get('star_lord', '')
    moon_sign_lord = moon.get('sign_lord', '')
    moon_star_lord = moon.get('star_lord', '')

    # Collect unique ruling planets
    all_rps = []
    for p in [day_lord, lagna_sign_lord, lagna_star_lord, moon_sign_lord, moon_star_lord]:
        if p and p not in all_rps:
            all_rps.append(p)

    return {
        'day_lord': day_lord,
        'lagna_sign_lord': lagna_sign_lord,
        'lagna_star_lord': lagna_star_lord,
        'moon_sign_lord': moon_sign_lord,
        'moon_star_lord': moon_star_lord,
        'all': all_rps,
    }

# ========================
# MAIN CHART FUNCTION
# ========================

def calculate_chart(birth_dt_utc: datetime, lat: float, lon_geo: float,
                    ayanamsa_type: str = 'KP') -> Dict:
    """Calculate a complete KP chart."""
    set_ayanamsa(ayanamsa_type)
    jd = get_julian_day(birth_dt_utc)
    ayanamsa = swe.get_ayanamsa(jd)

    planet_positions = get_planet_positions(jd, ayanamsa)
    house_cusps = get_house_cusps(jd, lat, lon_geo, ayanamsa)
    planet_houses = get_planet_houses(planet_positions, house_cusps)
    significators = get_significators(planet_positions, house_cusps, planet_houses)

    moon_lon = planet_positions['Moon']['longitude']
    dashas = get_dasha_tree(moon_lon, birth_dt_utc)
    current_dasha = get_current_dasha(dashas, datetime.utcnow())

    return {
        'jd': jd,
        'ayanamsa': ayanamsa,
        'ayanamsa_type': ayanamsa_type,
        'planet_positions': planet_positions,
        'house_cusps': house_cusps,
        'planet_houses': planet_houses,
        'significators': significators,
        'dashas': dashas,
        'current_dasha': current_dasha,
        'birth_dt_utc': birth_dt_utc,
        'lat': lat,
        'lon_geo': lon_geo,
    }

def calculate_transit_chart(lat: float, lon_geo: float, ayanamsa_type: str = 'KP') -> Dict:
    """Calculate current transit chart."""
    set_ayanamsa(ayanamsa_type)
    now_utc = datetime.utcnow()
    jd = get_julian_day(now_utc)
    ayanamsa = swe.get_ayanamsa(jd)
    planet_positions = get_planet_positions(jd, ayanamsa)
    house_cusps = get_house_cusps(jd, lat, lon_geo, ayanamsa)
    ruling_planets = get_ruling_planets(planet_positions, house_cusps, now_utc)
    return {
        'datetime_utc': now_utc,
        'planet_positions': planet_positions,
        'house_cusps': house_cusps,
        'ruling_planets': ruling_planets,
        'ayanamsa': ayanamsa,
    }
