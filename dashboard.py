# dashboard.py
# Smart Dustbin IoT Monitoring Dashboard - Real-Time Multi-Bin System
# Live Hardware:
#   - BIN-001: Proximity Lid Actuator (Servo) + Fill Level Sensor
#   - BIN-002: Fill Level Sensor (Ultrasonic) - Open Top
# Campus Simulated:
#   - BIN-003, BIN-004, BIN-005: Demo campus locations
# Calibration:
#   - Height: 16 cm
#   - Green (< 50% / distance 8 to 16 cm / fillness 0 to 8 cm)
#   - Orange (50% to 74% / distance 4 to 8 cm / fillness 8 to 12 cm)
#   - Red (>= 75% / distance < 4 cm / fillness 12 to 16 cm)

import random
import threading
import time
from datetime import datetime, timedelta, timezone
import requests
import streamlit as st

# ---------- Page setup ----------
st.set_page_config(page_title="Smart Dustbin Live Monitoring", page_icon="🗑️", layout="wide")

# India Standard Time = UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))

FIREBASE_URL = "https://parkos1-default-rtdb.firebaseio.com/bins.json"

# =====================================================================
# 1. DEMO DATA SIMULATOR FOR CAMPUS BINS (BIN-003, BIN-004, BIN-005)
# =====================================================================
START_DEMO_BINS = [
    {"bin_id": "BIN-003", "location": "Canteen Entrance", "fill": 78, "dist": 4,  "lid": "CLOSED"},
    {"bin_id": "BIN-004", "location": "Main Library",     "fill": 56, "dist": 7,  "lid": "CLOSED"},
    {"bin_id": "BIN-005", "location": "Hostel Gate",      "fill": 88, "dist": 2,  "lid": "OPEN"},
]

@st.cache_resource
def get_simulator():
    return {
        "lock": threading.Lock(),
        "last_minute": int(time.time() // 60),
        "demo_bins": [dict(b) for b in START_DEMO_BINS],
    }

def step_demo_bins(demo_bins):
    for b in demo_bins:
        b["fill"] += random.randint(1, 3)
        if b["fill"] >= 100:
            b["fill"] = random.randint(0, 5)
        b["lid"] = "OPEN" if random.random() < 0.10 else "CLOSED"

def fetch_all_bins():
    sim = get_simulator()
    with sim["lock"]:
        this_minute = int(time.time() // 60)
        if this_minute != sim["last_minute"]:
            step_demo_bins(sim["demo_bins"])
            sim["last_minute"] = this_minute
        demos = [dict(b) for b in sim["demo_bins"]]

    # Default states for hardware units (16 cm height calibration)
    bin1 = {
        "bin_id": "BIN-001",
        "location": "Block A (Smart Lid + Level)",
        "fill": 0,
        "dist": 16,
        "lid": "CLOSED",
        "status": "NORMAL",
        "is_primary": True,
        "has_servo": True,
        "online": False
    }

    bin2 = {
        "bin_id": "BIN-002",
        "location": "Block B (Fill Level Sensor)",
        "fill": 0,
        "dist": 16,
        "lid": "N/A",
        "status": "NORMAL",
        "is_primary": True,
        "has_servo": False,
        "online": False
    }

    try:
        r = requests.get(FIREBASE_URL, timeout=1.2).json()
        if r and isinstance(r, dict):
            # Parse BIN-001
            if "BIN-001" in r and isinstance(r["BIN-001"], dict):
                d1 = r["BIN-001"]
                bin1["fill"] = int(d1.get("fill", 0))
                bin1["dist"] = int(d1.get("dist", 16))
                bin1["lid"] = str(d1.get("lid", "CLOSED")).upper()
                bin1["status"] = str(d1.get("status", "NORMAL")).upper()
                bin1["online"] = True

            # Parse BIN-002
            if "BIN-002" in r and isinstance(r["BIN-002"], dict):
                d2 = r["BIN-002"]
                bin2["fill"] = int(d2.get("fill", 0))
                bin2["dist"] = int(d2.get("dist", 16))
                bin2["lid"] = str(d2.get("lid", "N/A")).upper()
                bin2["status"] = str(d2.get("status", "NORMAL")).upper()
                bin2["online"] = True
    except Exception:
        pass

    for d in demos:
        d["is_primary"] = False
        d["has_servo"] = True
        d["online"] = True
        d["status"] = "NORMAL"

    return [bin1, bin2] + demos

# =====================================================================
# 2. STATUS HELPERS (16 cm Bin: <50% Normal, 50-74% Orange, >=75% Red)
# =====================================================================
def get_status_info(fill):
    if fill < 50:
        return "Normal", "#3DBE7A", "badge-green"
    elif fill < 75:
        return "Filling up", "#F59E0B", "badge-yellow"
    else:
        return "Critical", "#F0605D", "badge-red"

# =====================================================================
# 3. CSS STYLING
# =====================================================================
st.markdown("""
<style>
.block-container { padding-top: 1.2rem; max-width: 1150px; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
.stApp { background: #000000; color-scheme: dark; }

/* Top banner */
.top-banner { background: #174A78; border-radius: 10px; padding: 20px 26px; margin-bottom: 20px; }
.top-title { color: #FFFFFF; font-size: 28px; font-weight: 700; line-height: 1.2; margin: 0; }
.top-sub { color: #C3D5E8; font-size: 14px; margin: 4px 0 0 0; }

/* Hero Cards */
.hero-card {
    background: linear-gradient(145deg, #162B40, #0F1E2C);
    border: 2px solid #2B6CB0;
    border-radius: 12px;
    padding: 20px 22px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    margin-bottom: 14px;
}
.hero-card.card-bin2 {
    border-color: #3182CE;
    background: linear-gradient(145deg, #15273B, #0E1A26);
}

.hero-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.hero-title { font-size: 17px; font-weight: 700; color: #FFFFFF; }
.hero-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-top: 14px; }
.hero-stat-box { background: rgba(0, 0, 0, 0.45); border: 1px solid #243545; border-radius: 8px; padding: 14px 10px; text-align: center; }
.hero-stat-label { font-size: 12px; color: #93A5B5; text-transform: uppercase; letter-spacing: 0.5px; }
.hero-stat-val { font-size: 24px; font-weight: 800; color: #FFFFFF; margin-top: 4px; }

/* Summary cards */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; margin-top: 8px; }
.kpi { background: #15222E; border: 1px solid #243545; border-radius: 10px; padding: 16px 18px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; vertical-align: middle; }
.kpi-label { color: #93A5B5; font-size: 13px; font-weight: 600; }
.kpi-value { color: #E6EEF5; font-size: 32px; font-weight: 700; line-height: 1.2; }

/* Table */
.section-title { color: #E6EEF5; font-size: 18px; font-weight: 700; margin: 16px 0 8px 10px; }
.table-wrap { background: #15222E; border: 1px solid #243545; border-radius: 10px; padding: 6px 18px 10px 18px; overflow-x: auto; }
table.bins { width: 100%; border-collapse: collapse; font-size: 15px; }
table.bins th { text-align: left; color: #93A5B5; font-size: 13px; font-weight: 600; padding: 12px 10px; border-bottom: 2px solid #243545; }
table.bins td { padding: 14px 10px; border-bottom: 1px solid #1F3040; color: #E6EEF5; vertical-align: middle; white-space: nowrap; }
table.bins tr:last-child td { border-bottom: none; }
tr.primary-row { background: rgba(43, 108, 176, 0.22); font-weight: 600; }

/* Fill bar */
.bar-bg { display: inline-block; width: 130px; height: 10px; background: #2A3C4D; border-radius: 6px; overflow: hidden; vertical-align: middle; margin-right: 10px; }
.bar-fill { height: 100%; border-radius: 6px; }

/* Badges */
.badge { display: inline-block; padding: 4px 11px; border-radius: 99px; font-size: 12px; font-weight: 700; }
.badge-green  { background: #153A28; color: #6FDDA0; }
.badge-yellow { background: #3E3314; color: #F5CD6A; }
.badge-red    { background: #43191C; color: #FF9C98; }
.badge-open   { background: #2E1B0D; color: #F6AD55; border: 1px solid #DD6B20; }
.badge-closed { background: #162E4D; color: #63B3ED; }
.badge-na     { background: #202937; color: #94A3B8; }
.badge-live   { background: #064E3B; color: #34D399; border: 1px solid #059669; }
.badge-demo   { background: #1F2937; color: #9CA3AF; }

.live-pulse {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #34D399;
    margin-right: 6px; box-shadow: 0 0 8px #34D399; animation: pulse-dot 1.2s infinite ease-in-out;
}
@keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(0.8); } }

@media (max-width: 820px) { 
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
}
</style>
""", unsafe_allow_html=True)


# =====================================================================
# 4. LIVE DASHBOARD COMPONENT (Auto-refreshes every 1 second)
# =====================================================================
@st.fragment(run_every=1)
def render_dashboard():
    bins = fetch_all_bins()
    bin1 = bins[0]
    bin2 = bins[1]

    now_ist = datetime.now(IST).strftime("%I:%M:%S %p IST")

    # Banner
    st.markdown(
        f"""<div class="top-banner">
<div class="top-title">Smart Dustbin Live Fleet Monitoring</div>
<div class="top-sub"><span class="live-pulse"></span> Multi-Unit Cloud Feed &bull; Updated: {now_ist}</div>
</div>""",
        unsafe_allow_html=True,
    )

    # Function to build clean, un-indented HTML string for a hardware card (without Health section)
    def build_card_html(b, card_class=""):
        p_label, p_color, _ = get_status_info(b["fill"])
        lid_display = b["lid"]
        lid_color = "#94A3B8"
        if b["lid"] == "OPEN":
            lid_color = "#F6AD55"
        elif b["lid"] == "CLOSED":
            lid_color = "#63B3ED"
        elif b["lid"] == "N/A":
            lid_display = "Open Top"
            lid_color = "#94A3B8"

        return f"""<div class="hero-card {card_class}">
<div class="hero-header">
<div class="hero-title">⭐ {b['bin_id']}: {b['location']}</div>
<span class="badge badge-live"><span class="live-pulse"></span>HARDWARE</span>
</div>
<div style="margin: 8px 0;">
<span style="font-size: 13px; color: #C3D5E8; margin-right: 8px;">Fill Capacity:</span>
<span class="bar-bg" style="width: 55%; height: 12px;">
<span class="bar-fill" style="display:block; width: {b['fill']}%; background: {p_color};"></span>
</span>
<span style="font-size: 20px; font-weight: 800; color: {p_color};">{b['fill']}%</span>
</div>
<div class="hero-stats">
<div class="hero-stat-box">
<div class="hero-stat-label">Lid Position</div>
<div class="hero-stat-val" style="color: {lid_color};">{lid_display}</div>
</div>
<div class="hero-stat-box">
<div class="hero-stat-label">Remaining Depth</div>
<div class="hero-stat-val">{b['dist']} cm</div>
</div>
</div>
</div>"""

    # Side-by-side columns using native Streamlit columns
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(build_card_html(bin1), unsafe_allow_html=True)
    with col2:
        st.markdown(build_card_html(bin2, "card-bin2"), unsafe_allow_html=True)

    # Summary KPI Cards (16 cm calibration thresholds: <50%, 50-74%, >=75%)
    green_count = sum(1 for b in bins if b["fill"] < 50)
    yellow_count = sum(1 for b in bins if 50 <= b["fill"] < 75)
    critical_count = sum(1 for b in bins if b["fill"] >= 75)

    def kpi_card(label, value, color):
        return f"""<div class="kpi">
<div class="kpi-label"><span class="dot" style="background:{color};"></span>{label}</div>
<div class="kpi-value">{value}</div>
</div>"""

    st.markdown(
        f"""<div class="kpi-row">
{kpi_card("Total Fleet Bins", len(bins), "#5B9BD5")}
{kpi_card("Normal (< 50%)", green_count, "#3DBE7A")}
{kpi_card("Filling up (50-74%)", yellow_count, "#F59E0B")}
{kpi_card("Critical (>= 75%)", critical_count, "#F0605D")}
</div>""",
        unsafe_allow_html=True,
    )

    # Fleet Table
    rows_html = ""
    for b in bins:
        b_label, b_color, b_badge = get_status_info(b["fill"])
        
        if b["lid"] == "OPEN":
            lid_badge = '<span class="badge badge-open">Open</span>'
        elif b["lid"] == "CLOSED":
            lid_badge = '<span class="badge badge-closed">Closed</span>'
        else:
            lid_badge = '<span class="badge badge-na">Open Top</span>'

        source_badge = '<span class="badge badge-live">HARDWARE</span>' if b.get("is_primary") else '<span class="badge badge-demo">DEMO</span>'
        row_class = 'class="primary-row"' if b.get("is_primary") else ''

        rows_html += f"""<tr {row_class}>
<td><b>{b['bin_id']}</b> {source_badge}</td>
<td>{b['location']}</td>
<td><span class="bar-bg"><span class="bar-fill" style="display:block; width:{b['fill']}%; background:{b_color};"></span></span><span>{b['fill']}%</span></td>
<td><span class="badge {b_badge}">{b_label}</span></td>
<td>{lid_badge}</td>
</tr>"""

    st.markdown(
        f"""<div class="table-wrap">
<div class="section-title">Campus Dustbin Fleet Status</div>
<table class="bins">
<tr><th>Bin ID</th><th>Location</th><th>Fill Level</th><th>Status</th><th>Lid State</th></tr>
{rows_html}
</table>
</div>""",
        unsafe_allow_html=True,
    )

# Execute the auto-refreshing dashboard
render_dashboard()
