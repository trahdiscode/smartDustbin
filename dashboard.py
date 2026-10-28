# dashboard.py
# Smart Dustbin IoT Monitoring Dashboard
# Primary Dustbin (BIN-001) is LIVE from Hardware (Arduino + ESP32 via Firebase)
# 4 Demo Dustbins (BIN-002 to BIN-005) simulated for full campus monitoring

import random
import threading
import time
from datetime import datetime, timedelta, timezone
import requests
import streamlit as st

# ---------- Page setup ----------
st.set_page_config(page_title="Smart Dustbin Monitoring", page_icon="🗑️", layout="wide")

# India Standard Time = UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))

# Live refresh interval (2 seconds for instant hardware feedback)
REFRESH_SECONDS = 2

# =====================================================================
# FIREBASE REALTIME DATABASE CONFIGURATION
# =====================================================================
FIREBASE_URL = "https://parkos1-default-rtdb.firebaseio.com"


# =====================================================================
# 1. DATA (Live Firebase for BIN-001 + 4 Demo Campus Bins)
# =====================================================================
START_BINS = [
    {"bin_id": "BIN-001", "location": "Primary Hardware Unit", "fill": 0, "dist": 0, "lid": "CLOSED", "is_primary": True},
    {"bin_id": "BIN-002", "location": "Demo: Block A, Floor 1", "fill": 24, "dist": 16, "lid": "CLOSED", "is_primary": False},
    {"bin_id": "BIN-003", "location": "Demo: Canteen Entrance", "fill": 82, "dist": 6,  "lid": "CLOSED", "is_primary": False},
    {"bin_id": "BIN-004", "location": "Demo: Main Library",     "fill": 55, "dist": 11, "lid": "CLOSED", "is_primary": False},
    {"bin_id": "BIN-005", "location": "Demo: Hostel Gate",      "fill": 89, "dist": 4,  "lid": "OPEN",   "is_primary": False},
]

@st.cache_resource
def get_simulator():
    return {
        "lock": threading.Lock(),
        "last_minute": int(time.time() // 60),
        "updated_at": datetime.now(timezone.utc),
        "bins": [dict(b) for b in START_BINS],
    }

def make_next_reading(bin_record):
    """Simulates fill progression for demo bins only."""
    bin_record["fill"] = bin_record["fill"] + random.randint(1, 4)
    if bin_record["fill"] >= 100:
        bin_record["fill"] = random.randint(0, 5)
    bin_record["lid"] = "OPEN" if random.random() < 0.12 else "CLOSED"

def fetch_live_bin001():
    """Fetch real-time telemetry from Firebase Realtime Database."""
    try:
        url = FIREBASE_URL.rstrip('/') + "/bins/BIN-001.json"
        res = requests.get(url, timeout=2.0)
        if res.status_code == 200 and res.json():
            return res.json()
    except Exception:
        pass
    return None

def load_bins():
    """Return (list of bins, updated_at timestamp, is_live_connected)."""
    sim = get_simulator()
    with sim["lock"]:
        this_minute = int(time.time() // 60)
        minutes_passed = this_minute - sim["last_minute"]
        if minutes_passed > 0:
            for _ in range(min(minutes_passed, 30)):
                for b in sim["bins"]:
                    if not b.get("is_primary", False):  # Only simulate demo bins
                        make_next_reading(b)
            sim["last_minute"] = this_minute
            sim["updated_at"] = datetime.now(timezone.utc)

        bin_list = [dict(b) for b in sim["bins"]]

        # OVERWRITE PRIMARY BIN (BIN-001) WITH LIVE FIREBASE HARDWARE DATA
        live_data = fetch_live_bin001()
        is_live = False
        if live_data and isinstance(live_data, dict):
            bin_list[0]["fill"] = int(live_data.get("fill", 0))
            bin_list[0]["dist"] = int(live_data.get("dist", 0))
            bin_list[0]["lid"] = str(live_data.get("lid", "CLOSED")).upper()
            bin_list[0]["source"] = "LIVE HARDWARE 🟢"
            is_live = True
        else:
            bin_list[0]["source"] = "WAITING FOR ESP32 🟡"

        return bin_list, sim["updated_at"], is_live


# =====================================================================
# 2. STATUS RULES
# =====================================================================
def get_bin_status(fill):
    if fill < 50:
        return "GREEN"
    elif fill < 80:
        return "YELLOW"
    else:
        return "RED"

STATUS_STYLE = {
    "GREEN":  {"label": "Normal",     "color": "#3DBE7A", "badge": "badge-green"},
    "YELLOW": {"label": "Filling up", "color": "#F0B429", "badge": "badge-yellow"},
    "RED":    {"label": "Critical",   "color": "#F0605D", "badge": "badge-red"},
}


# =====================================================================
# 3. STYLES (Modern Dark Theme)
# =====================================================================
st.markdown("""
<style>
.block-container { padding-top: 1.5rem; max-width: 1100px; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
.stApp { background: #000000; color-scheme: dark; }

/* Top banner */
.top-banner { background: #174A78; border-radius: 10px; padding: 22px 28px; margin-bottom: 18px; }
.top-title { color: #FFFFFF; font-size: 28px; font-weight: 700; line-height: 1.2; margin: 0; }
.top-sub { color: #C3D5E8; font-size: 14px; margin: 6px 0 0 0; }

/* Primary Hardware Hero Card */
.hero-card {
    background: linear-gradient(145deg, #162B40, #0F1E2C);
    border: 2px solid #2B6CB0;
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 22px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}
.hero-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.hero-title { font-size: 20px; font-weight: 700; color: #FFFFFF; }
.hero-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 12px; }
.hero-stat-box { background: rgba(0, 0, 0, 0.35); border: 1px solid #243545; border-radius: 8px; padding: 12px 16px; text-align: center; }
.hero-stat-label { font-size: 12px; color: #93A5B5; text-transform: uppercase; letter-spacing: 0.5px; }
.hero-stat-val { font-size: 28px; font-weight: 800; color: #FFFFFF; margin-top: 4px; }

/* Critical alert */
.alert-box { position: relative; overflow: hidden; background: #3A1A1E; color: #FFC9C7;
             padding: 14px 18px 14px 26px; border-radius: 8px; margin-bottom: 18px; font-size: 15px; }
.alert-box::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0;
                     width: 6px; background: #F0605D; }

/* Summary cards */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
.kpi { background: #15222E; border: 1px solid #243545; border-radius: 10px; padding: 16px 18px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
       margin-right: 8px; vertical-align: middle; }
.kpi-label { color: #93A5B5; font-size: 13px; font-weight: 600; }
.kpi-value { color: #E6EEF5; font-size: 32px; font-weight: 700; line-height: 1.2; }

/* Table */
.section-title { color: #E6EEF5; font-size: 18px; font-weight: 700; margin: 16px 0 8px 10px; }
.table-wrap { background: #15222E; border: 1px solid #243545; border-radius: 10px;
              padding: 6px 18px 10px 18px; overflow-x: auto; }
table.bins { width: 100%; border-collapse: collapse; font-size: 15px; }
table.bins th { text-align: left; color: #93A5B5; font-size: 13px; font-weight: 600;
                padding: 12px 10px; border-bottom: 2px solid #243545; }
table.bins td { padding: 14px 10px; border-bottom: 1px solid #1F3040; color: #E6EEF5;
                vertical-align: middle; white-space: nowrap; }
table.bins tr:last-child td { border-bottom: none; }
tr.primary-row { background: rgba(43, 108, 176, 0.18); font-weight: 600; }

/* Fill bar */
.bar-bg { display: inline-block; width: 140px; height: 10px; background: #2A3C4D;
          border-radius: 6px; overflow: hidden; vertical-align: middle; margin-right: 10px; }
.bar-fill { height: 100%; border-radius: 6px; }

/* Badges */
.badge { display: inline-block; padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 700; }
.badge-green  { background: #153A28; color: #6FDDA0; }
.badge-yellow { background: #3E3314; color: #F5CD6A; }
.badge-red    { background: #43191C; color: #FF9C98; }
.badge-open   { background: #2E1B0D; color: #F6AD55; border: 1px solid #DD6B20; }
.badge-closed { background: #162E4D; color: #63B3ED; }
.badge-live   { background: #064E3B; color: #34D399; border: 1px solid #059669; }
.badge-demo   { background: #1F2937; color: #9CA3AF; }

@media (max-width: 700px) { 
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .hero-stats { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)


# =====================================================================
# 4. DRAW THE LIVE PAGE
# =====================================================================
@st.fragment(run_every=REFRESH_SECONDS)
def show_dashboard():
    bins, updated_at, is_live = load_bins()

    for b in bins:
        b["status"] = get_bin_status(b["fill"])

    primary_bin = bins[0]  # BIN-001 (Always primary hardware)
    demo_bins = bins[1:]   # BIN-002 through BIN-005 (Campus demo)

    green_count = sum(1 for b in bins if b["status"] == "GREEN")
    yellow_count = sum(1 for b in bins if b["status"] == "YELLOW")
    red_bins = [b for b in bins if b["status"] == "RED"]

    # Top banner
    updated_text = datetime.now(IST).strftime("%d %b %Y, %H:%M:%S") + " IST"
    st.markdown(
        '<div class="top-banner">'
        '<div class="top-title">Smart Dustbin Monitoring System</div>'
        '<div class="top-sub">Campus IoT Network &bull; Live Telemetry Sync at ' + updated_text + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ==================== PRIMARY DUSTBIN HERO CARD ====================
    p_style = STATUS_STYLE[primary_bin["status"]]
    p_lid_color = "#F6AD55" if primary_bin["lid"] == "OPEN" else "#63B3ED"
    
    st.markdown(
        f'''
        <div class="hero-card">
            <div class="hero-header">
                <div class="hero-title">⭐ PRIMARY UNIT: {primary_bin["bin_id"]} ({primary_bin["location"]})</div>
                <span class="badge badge-live">LIVE HARDWARE 🟢</span>
            </div>
            <div style="margin: 8px 0;">
                <span style="font-size: 14px; color: #C3D5E8; margin-right: 10px;">Fill Level Capacity:</span>
                <span class="bar-bg" style="width: 60%; height: 14px;">
                    <span class="bar-fill" style="display:block; width: {primary_bin["fill"]}%; background: {p_style["color"]};"></span>
                </span>
                <span style="font-size: 18px; font-weight: 800; color: {p_style["color"]};">{primary_bin["fill"]}%</span>
            </div>
            <div class="hero-stats">
                <div class="hero-stat-box">
                    <div class="hero-stat-label">Lid Position</div>
                    <div class="hero-stat-val" style="color: {p_lid_color};">{primary_bin["lid"]}</div>
                </div>
                <div class="hero-stat-box">
                    <div class="hero-stat-label">Remaining Depth</div>
                    <div class="hero-stat-val">{primary_bin["dist"]} cm</div>
                </div>
                <div class="hero-stat-box">
                    <div class="hero-stat-label">Bin Health</div>
                    <div class="hero-stat-val" style="color: {p_style["color"]};">{p_style["label"]}</div>
                </div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # Critical alert banner
    if red_bins:
        names = ", ".join(b["bin_id"] + " (" + b["location"] + ")" for b in red_bins)
        st.markdown(
            '<div class="alert-box"><b>Action required.</b> Bins at 80% or higher capacity: ' + names + '.</div>',
            unsafe_allow_html=True,
        )

    # 4 KPI Summary Cards
    def kpi_card(label, value, color):
        return ('<div class="kpi">'
                '<div class="kpi-label"><span class="dot" style="background:' + color + ';"></span>' + label + '</div>'
                '<div class="kpi-value">' + str(value) + '</div></div>')

    st.markdown(
        '<div class="kpi-row">'
        + kpi_card("Total Monitored Bins", len(bins), "#5B9BD5")
        + kpi_card("Normal (< 50%)", green_count, STATUS_STYLE["GREEN"]["color"])
        + kpi_card("Filling up (50-79%)", yellow_count, STATUS_STYLE["YELLOW"]["color"])
        + kpi_card("Critical (>= 80%)", len(red_bins), STATUS_STYLE["RED"]["color"])
        + '</div>',
        unsafe_allow_html=True,
    )

    # Table of all bins (Primary Bin pinned at top, followed by 4 demo bins)
    rows_html = ""
    for b in bins:
        style = STATUS_STYLE[b["status"]]
        lid_badge = "badge-open" if b["lid"] == "OPEN" else "badge-closed"
        source_badge = '<span class="badge badge-live">HARDWARE</span>' if b.get("is_primary") else '<span class="badge badge-demo">DEMO</span>'
        row_class = 'class="primary-row"' if b.get("is_primary") else ''
        
        rows_html += (
            f'<tr {row_class}>'
            f'<td><b>{b["bin_id"]}</b> {source_badge}</td>'
            f'<td>{b["location"]}</td>'
            f'<td><span class="bar-bg"><span class="bar-fill" style="display:block; width:{b["fill"]}%; background:{style["color"]};"></span></span>'
            f'{b["fill"]}%</td>'
            f'<td><span class="badge {style["badge"]}">{style["label"]}</span></td>'
            f'<td><span class="badge {lid_badge}">{b["lid"].capitalize()}</span></td>'
            f'</tr>'
        )

    st.markdown(
        '<div class="table-wrap">'
        '<div class="section-title">Campus Dustbin Fleet Status</div>'
        '<table class="bins">'
        '<tr><th>Bin ID</th><th>Location</th><th>Fill Level</th><th>Status</th><th>Lid State</th></tr>'
        + rows_html +
        '</table>'
        '</div>',
        unsafe_allow_html=True,
    )

show_dashboard()
