#!/usr/bin/env python3
"""Dubai, Live: a GitHub profile banner whose sky follows the real sun over Dubai.

Usage:
  python dubai_live.py --out assets/dubai-live.svg                 # now, with live weather
  python dubai_live.py --out x.svg --at 2026-11-02T17:40 --offline # a specific Dubai time
Stdlib only. Weather comes from Open-Meteo (free, no key); if it fails, the banner still renders.
"""
import argparse, datetime as dt, json, math, random, urllib.request

LAT, LON = 25.2048, 55.2708
TZ = dt.timezone(dt.timedelta(hours=4))  # Gulf Standard Time, no DST
W, H, HOR = 1200, 340, 262
SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# ------------------------------------------------------------------ astronomy
def sun_position(t_utc):
    """NOAA approximation -> (elevation°, azimuth°)."""
    doy = t_utc.timetuple().tm_yday
    hr = t_utc.hour + t_utc.minute / 60 + t_utc.second / 3600
    g = 2 * math.pi / 365 * (doy - 1 + (hr - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    tst = hr * 60 + eqt + 4 * LON
    ha = math.radians(tst / 4 - 180)
    lat = math.radians(LAT)
    cz = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha)
    elev = 90 - math.degrees(math.acos(max(-1, min(1, cz))))
    az = (math.degrees(math.atan2(math.sin(ha), math.cos(ha) * math.sin(lat) - math.tan(dec) * math.cos(lat))) + 180) % 360
    return elev, az


def moon_phase(t_utc):
    """-> (age fraction 0..1, illuminated fraction)."""
    ref = dt.datetime(2000, 1, 6, 18, 14, tzinfo=dt.timezone.utc)
    P = 29.530588853
    age = ((t_utc - ref).total_seconds() / 86400) % P / P
    return age, (1 - math.cos(2 * math.pi * age)) / 2

# ------------------------------------------------------------------ palette
def hx(c): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
def mix(a, b, t):
    a, b = hx(a), hx(b)
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))

# sun elevation -> sky top, mid, low, horizon, water, building, haze
KEYS = [
    (-90, ["#03050f", "#0e1233", "#1f1d45", "#3a2a55", "#05060f", "#0b0f22", "#5a3d6a"]),  # night
    (-14, ["#060a22", "#1a1f52", "#3a2f6a", "#6b3f6a", "#0a0b1c", "#0d1228", "#8a4f6e"]),  # astronomical twilight
    (-7,  ["#14215a", "#3b4290", "#9a5a8a", "#e0807a", "#141331", "#151a36", "#e08a7a"]),  # blue hour
    (-1,  ["#2a3f86", "#6e74b8", "#e8907e", "#ffb86b", "#2a2340", "#2a2742", "#ffb07a"]),  # sunrise / sunset
    (5,   ["#3f6cb4", "#8aa9d8", "#f2c79a", "#ffd79a", "#3a4560", "#3e4560", "#ffcf9a"]),  # golden hour
    (15,  ["#2f78d0", "#6aaae6", "#b6d8f0", "#efe2c6", "#2f5f8a", "#4b5a74", "#f0dcb8"]),  # morning / afternoon
    (90,  ["#1f6fd1", "#5aa2e8", "#a9d3f2", "#eadfc8", "#2a5b88", "#56657e", "#eadcc0"]),  # midday
]

def palette(elev):
    for (e0, c0), (e1, c1) in zip(KEYS, KEYS[1:]):
        if elev <= e1:
            t = max(0, min(1, (elev - e0) / (e1 - e0)))
            return [mix(a, b, t) for a, b in zip(c0, c1)]
    return KEYS[-1][1]

def clamp01(x): return max(0.0, min(1.0, x))

# ------------------------------------------------------------------ weather
WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog",
       51: "drizzle", 53: "drizzle", 55: "drizzle", 61: "rain", 63: "rain", 65: "heavy rain",
       80: "showers", 81: "showers", 82: "storms", 95: "thunderstorm", 96: "thunderstorm", 99: "thunderstorm"}

def fetch_weather():
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
           "&current=temperature_2m,weather_code&timezone=Asia%2FDubai")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            cur = json.load(r)["current"]
        return round(cur["temperature_2m"]), int(cur["weather_code"])
    except Exception:
        return None, 0

# ------------------------------------------------------------------ captions
def caption(local, elev):
    h = local.hour
    if -4 < elev < 8 and h < 12: return "Sunrise over Dubai. First coffee, first commit."
    if -4 < elev < 2 and h >= 12: return "Sunset over Dubai. One more deploy before dinner."
    if h < 5: return f"It's {local.strftime('%-I%p').lower()} in Dubai. I'm probably still deploying."
    if h < 9: return "Morning in Dubai. Reviewing PRs before the heat does."
    if h < 12: return "Late morning in Dubai. Deep work hours."
    if h < 14: return "Midday in Dubai. Too hot outside, perfect for shipping."
    if elev > 2: return "Golden hour in Dubai. Best light for a deploy." if elev < 15 else "Afternoon in Dubai. Shipping."
    if elev > -12: return "Blue hour in Dubai. The city switches on."
    return "Evening in Dubai. Side projects o'clock."


# ------------------------------------------------------------------ moon drawing
def moon_svg(cx, cy, r, age, lit_col, dark_col):
    k = math.cos(2 * math.pi * age)            # 1 new, -1 full
    rx = abs(k) * r
    sweep = 0 if k > 0 else 1                   # crescent vs gibbous terminator
    d = f"M{cx},{cy-r} A{r},{r} 0 0 1 {cx},{cy+r} A{rx:.2f},{r} 0 0 {sweep} {cx},{cy-r}Z"
    flip = f' transform="translate({2*cx},0) scale(-1,1)"' if age > 0.5 else ""  # waning: lit on left
    return (f'<circle cx="{cx}" cy="{cy}" r="{r*3.6}" fill="url(#moonglow)"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{dark_col}" opacity=".55"/>'
            f'<path d="{d}" fill="{lit_col}"{flip}/>')

# ------------------------------------------------------------------ render
def render(t_local, temp=None, code=0):
    t_utc = t_local.astimezone(dt.timezone.utc)
    elev, az = sun_position(t_utc)
    age, illum = moon_phase(t_utc)
    top, mid, low, horizon, water, bcol, haze = palette(elev)
    day = elev > 8
    star_op = clamp01((-elev - 6) / 8)                 # stars appear below -6°
    lit_frac = 0.06 + 0.26 * clamp01((-elev + 2) / 10) # windows switch on through dusk
    glow_op = clamp01(1 - abs(elev - 0) / 14) * 0.9    # sunrise/sunset horizon glow
    cloudy = code in (2, 3, 45, 48) or code >= 51
    rainy = code >= 51
    dim = 0.3 if (code in (3, 45, 48) or code >= 51) else 1.0  # overcast hides sun, moon, stars
    star_op *= dim

    # sun placement: azimuth 90°(E)->x120 ... 270°(W)->x1080
    sx = 520 + (az - 90) / 180 * 640   # east 520 · south 840 · west 1160 (keeps the text clear)
    sx = max(-40, min(W + 40, sx))
    sy = HOR - 8 - (HOR - 60) * (max(elev, 0) / 60) ** 0.6 + (min(elev, 0) * -4)
    sun_col = mix("#ff7a3d", "#fff6d8", clamp01(elev / 18))

    rng = random.Random(7)
    out = []

    # stars
    if star_op > 0:
        s = []
        for _ in range(160):
            x, y = rng.uniform(0, W), rng.uniform(0, HOR - 60)
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(.3,1.4):.2f}" fill="#fff" class="tw" '
                     f'style="animation-delay:{rng.uniform(0,6):.2f}s;animation-duration:{rng.uniform(2.5,6):.2f}s"/>')
        out.append(f'<g opacity="{star_op:.2f}">{"".join(s)}</g>')
    else:
        rng.random()

    # horizon glow from the sun (even when just below the horizon)
    if glow_op > 0.02:
        gx = max(80, min(W - 80, sx))
        out.append(f'<ellipse cx="{gx:.0f}" cy="{HOR}" rx="520" ry="170" fill="url(#hglow)" opacity="{glow_op:.2f}"/>')

    # moon (when the sun is low or down)
    if elev < 6 and illum > 0.03:
        mx = 500 if (elev > -3 and sx > W / 2) else 1040  # keep clear of the setting sun
        out.append(f'<g opacity="{clamp01((6-elev)/8)*dim:.2f}">' + moon_svg(mx, 78, 22, age, "#fff3d1", top) + '</g>')

    # sun
    if elev > -3:
        out.append(f'<g opacity="{dim}"><circle cx="{sx:.0f}" cy="{sy:.0f}" r="90" fill="url(#sunglow)"/>'
                   f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="{24 if elev>10 else 28}" fill="{sun_col}"/></g>')

    # clouds
    if cloudy:
        ccol = mix("#2a2c48", "#f4f1ea", clamp01((elev + 4) / 16))
        for i in range(6):
            cx, cy = 520 + i * 130 + rng.uniform(-30, 30), rng.uniform(36, 120)
            out.append(f'<g class="cl" style="animation-delay:{-i*7}s" opacity=".75" fill="{ccol}">'
                       f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="70" ry="16"/><ellipse cx="{cx-25:.0f}" cy="{cy-10:.0f}" rx="34" ry="16"/>'
                       f'<ellipse cx="{cx+20:.0f}" cy="{cy-14:.0f}" rx="28" ry="18"/></g>')

    # dust haze band
    out.append(f'<rect class="haze" x="-60" y="{HOR-100}" width="{W+120}" height="100" fill="url(#hz)"/>')

    # skyline
    sk = []
    win_lit = ["#ffd27a", "#ffe9b8", "#9fd3ff"]
    glass = mix("#9fc2e6", "#cfe4f5", clamp01(elev / 40))
    x = 0
    while x < W:
        w = rng.randint(18, 46)
        h = rng.randint(40, 120)
        if x < 470: h = rng.randint(18, 52)
        if 520 < x < 680: h = rng.randint(70, 140)
        shade = mix(bcol, "#000000", rng.uniform(0, .18))
        sk.append(f'<rect x="{x}" y="{HOR-h}" width="{w}" height="{h}" fill="{shade}"/>')
        if day or elev > 0:
            sk.append(f'<rect x="{x}" y="{HOR-h}" width="{max(2,w//4)}" height="{h}" fill="#fff" opacity=".07"/>')
        for wy in range(HOR - h + 8, HOR - 6, 9):
            for wx in range(x + 4, x + w - 5, 7):
                r = rng.random(); c = rng.choice(win_lit); flick = rng.random() < .18; o = rng.uniform(.45, .95); dl = rng.uniform(0, 8)
                if r < lit_frac:
                    cls = f' class="fl" style="animation-delay:{dl:.1f}s"' if flick and not day else ""
                    sk.append(f'<rect x="{wx}" y="{wy}" width="3" height="4" fill="{c}" opacity="{o:.2f}"{cls}/>')
                elif day and r < 0.32:
                    sk.append(f'<rect x="{wx}" y="{wy}" width="3" height="4" fill="{glass}" opacity=".35"/>')
        x += w + rng.randint(-4, 3)
    # supertall
    cx = 760
    tall = mix(bcol, "#000000", .05)
    band = mix("#ffd9a0", "#e9f2fb", clamp01(elev / 10))
    band_op = .35 if elev < 0 else .45
    for half, y0, y1 in [(34, 0, 70), (26, 70, 120), (19, 120, 165), (13, 165, 200), (8, 200, 228), (4, 228, 244)]:
        sk.append(f'<rect x="{cx-half}" y="{HOR-y1}" width="{half*2}" height="{y1-y0}" fill="{tall}"/>')
        for wy in range(HOR - y1 + 5, HOR - y0 - 3, 7):
            sk.append(f'<rect x="{cx-half+3}" y="{wy}" width="{half*2-6}" height="1.4" fill="{band}" opacity="{band_op}"/>')
        if elev > -2:  # sunlit edge on the side facing the sun
            side = cx - half if sx < cx else cx + half - 4
            sk.append(f'<rect x="{side}" y="{HOR-y1}" width="4" height="{y1-y0}" fill="{sun_col}" opacity=".35"/>')
    sk.append(f'<line x1="{cx}" y1="{HOR-244}" x2="{cx}" y2="{HOR-262}" stroke="{tall}" stroke-width="2"/>')
    if elev < 4:
        sk.append(f'<circle cx="{cx}" cy="{HOR-262}" r="2.2" fill="#ff4d5e" class="beacon"/>')
    out.append("".join(sk))

    # water + reflections
    out.append(f'<rect y="{HOR}" width="{W}" height="{H-HOR}" fill="url(#sea)"/>')
    rcol = "#ffd27a" if elev < 0 else mix("#ffd9a0", "#ffffff", clamp01(elev / 20))
    rop = 0.3 if elev < 0 else 0.45
    for _ in range(70):
        y, x, w = rng.uniform(HOR + 6, H - 4), rng.uniform(0, W), rng.uniform(10, 60)
        out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="1.2" fill="{rcol}" opacity="{rng.uniform(.08,rop):.2f}" '
                   f'class="sh" style="animation-delay:{rng.uniform(0,4):.1f}s"/>')
    if elev > -2:  # sun path on the water
        out.append(f'<rect x="{sx-40:.0f}" y="{HOR}" width="80" height="{H-HOR}" fill="url(#path)" filter="url(#soft)" opacity="{clamp01((elev+2)/6)*.6:.2f}"/>')

    # rain
    if rainy:
        r = "".join(f'<line x1="{rng.uniform(0,W):.0f}" y1="{rng.uniform(-40,H):.0f}" x2="{0:.0f}" y2="0" />' for _ in range(0))
        drops = []
        for _ in range(90):
            x0, y0 = rng.uniform(0, W + 60), rng.uniform(-H, 0)
            drops.append(f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x0-6:.0f}" y2="{y0+16:.0f}"/>')
        out.append(f'<g class="rain" stroke="#cfe3ff" stroke-opacity=".45" stroke-width="1">{"".join(drops)}</g>')

    # text
    fg = "#0d1b2e" if day else "#ffffff"
    sub = "#24467a" if day else "#c9b8ff"
    muted = "#3a5576" if day else "#ece8ff"
    pill_bg = "#ffffff" if day else "#ffffff"
    pill_op = ".55" if day else ".07"
    hhmm = t_local.strftime("%H:%M")
    wx = WMO.get(code, "clear")
    parts = [f"{hhmm} GST"]
    if temp is not None: parts.append(f"{temp}°C")
    parts.append(wx)
    if elev < 6: parts.append(f"moon {round(illum*100)}%")
    else: parts.append(f"sun {round(elev)}° up")
    status = " · ".join(parts)
    pw = 96 + len(status) * 7.1
    scrim = ""
    if not day:
        scrim = '<rect width="520" height="220" fill="url(#scrim)"/>'

    body = "\n".join(out)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Dubai skyline at {hhmm}, {wx}">
<style>
.tw{{animation:tw 4s ease-in-out infinite}}@keyframes tw{{0%,100%{{opacity:.15}}50%{{opacity:1}}}}
.fl{{animation:fl 7s steps(1) infinite}}@keyframes fl{{0%,60%{{opacity:.9}}61%,80%{{opacity:0}}81%{{opacity:.9}}}}
.beacon,.live{{animation:bc 1.5s ease-in-out infinite}}@keyframes bc{{0%,100%{{opacity:.2}}50%{{opacity:1}}}}
.sh{{animation:sh 3s ease-in-out infinite}}@keyframes sh{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(6px)}}}}
.type{{animation:ty 2.2s steps(34) .4s both}}@keyframes ty{{from{{clip-path:inset(0 100% 0 0)}}to{{clip-path:inset(0 0 0 0)}}}}
.haze{{animation:hz 18s ease-in-out infinite alternate}}@keyframes hz{{from{{transform:translateX(-40px)}}to{{transform:translateX(40px)}}}}
.cl{{animation:cl 40s linear infinite alternate}}@keyframes cl{{to{{transform:translateX(60px)}}}}
.rain{{animation:rn .8s linear infinite}}@keyframes rn{{to{{transform:translate(-20px,{H}px)}}}}
</style>
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset=".5" stop-color="{mid}"/><stop offset=".82" stop-color="{low}"/><stop offset="1" stop-color="{horizon}"/></linearGradient>
<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{mix(water, horizon, .25)}"/><stop offset="1" stop-color="{mix(water, '#000000', .45)}"/></linearGradient>
<radialGradient id="moonglow"><stop offset="0" stop-color="#fff6dc" stop-opacity=".45"/><stop offset="1" stop-color="#fff6dc" stop-opacity="0"/></radialGradient>
<radialGradient id="sunglow"><stop offset="0" stop-color="{sun_col}" stop-opacity=".8"/><stop offset="1" stop-color="{sun_col}" stop-opacity="0"/></radialGradient>
<radialGradient id="hglow" cy="1" r="1"><stop offset="0" stop-color="#ffb070" stop-opacity=".85"/><stop offset=".5" stop-color="#ff7a6a" stop-opacity=".25"/><stop offset="1" stop-color="#ff7a6a" stop-opacity="0"/></radialGradient>
<linearGradient id="hz" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{haze}" stop-opacity="0"/><stop offset="1" stop-color="{haze}" stop-opacity=".3"/></linearGradient>
<linearGradient id="path" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sun_col}"/><stop offset="1" stop-color="{sun_col}" stop-opacity="0"/></linearGradient>
<filter id="soft" x="-50%" width="200%"><feGaussianBlur stdDeviation="10 2"/></filter>
<linearGradient id="scrim" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".25"/><stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>
</defs>
<rect width="{W}" height="{HOR}" fill="url(#sky)"/>
{body}
{scrim}
<g font-family="{SANS}">
  <text x="48" y="74" font-size="40" font-weight="700" fill="{fg}" letter-spacing="-.5">Sleman Safiah</text>
  <g class="type"><text x="50" y="106" font-family="{MONO}" font-size="16" fill="{sub}">&gt; senior full-stack engineer · dubai</text></g>
  <g transform="translate(48,128)">
    <rect width="{pw:.0f}" height="34" rx="17" fill="{pill_bg}" fill-opacity="{pill_op}" stroke="{fg}" stroke-opacity=".15"/>
    <circle cx="20" cy="17" r="4.5" fill="#ff4d5e" class="live"/>
    <text x="34" y="22" font-size="13" fill="{fg}" font-weight="600" letter-spacing="1.2">LIVE</text>
    <text x="74" y="22" font-size="13" fill="{fg}" opacity=".9">{status}</text>
  </g>
  <text x="48" y="190" font-size="13" fill="{muted}" font-style="italic">{caption(t_local, elev)}</text>
</g>
</svg>'''


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dubai-live.svg")
    ap.add_argument("--at", help="Dubai local time, e.g. 2026-11-02T17:40 (default: now)")
    ap.add_argument("--offline", action="store_true", help="skip the weather fetch")
    ap.add_argument("--temp", type=int); ap.add_argument("--code", type=int, default=None)
    a = ap.parse_args()
    t = dt.datetime.fromisoformat(a.at).replace(tzinfo=TZ) if a.at else dt.datetime.now(TZ)
    temp, code = (None, 0) if a.offline else fetch_weather()
    if a.temp is not None: temp = a.temp
    if a.code is not None: code = a.code
    open(a.out, "w").write(render(t, temp, code))
    e, _ = sun_position(t.astimezone(dt.timezone.utc))
    print(f"{a.out}: {t:%Y-%m-%d %H:%M} GST, sun {e:.1f}°, temp {temp}, code {code}")
