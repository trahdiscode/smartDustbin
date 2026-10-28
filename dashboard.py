# dashboard.py
# Smart Dustbin dashboard with Firebase Realtime Database Integration
# BIN-001 is LIVE from hardware (ESP32 -> Firebase).
# BIN-002 through BIN-005 are simulated for a complete multi-bin demonstration.

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

# Refresh rate for live dashboard (seconds)
REFRESH_SECONDS = 3

# =====================================================================
# FIREBASE REALTIME DATABASE CONFIGURATION
# =====================================================================
FIREBASE_URL = "https://parkos1-default-rtdb.firebaseio.com"


# =====================================================================
# 1. DATA (Live Firebase for BIN-001 + Simulator for others)
# =====================================================================
START_BINS = [
    {"bin_id": "BIN-001", "location": "Main Entrance (Hardware)", "fill": 0, "lid": "CLOSED", "source": "LIVE"},
    {"bin_id": "BIN-002", "location": "Block A, First floor",      "fill": 18, "lid": "CLOSED", "source": "SIMULATED"},
    {"bin_id": "BIN-003", "location": "Canteen entrance",          "fill": 87, "lid": "CLOSED", "source": "SIMULATED"},
    {"bin_id": "BIN-004", "location": "Library",                   "fill": 45, "lid": "CLOSED", "source": "SIMULATED"},
    {"bin_id": "BIN-005", "location": "Hostel gate",               "fill": 91, "lid": "OPEN",   "source": "SIMULATED"},
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
    """Simulates fill progression for virtual bins only."""
    bin_record["fill"] = bin_record["fill"] + random.randint(1, 5)
    if bin_record["fill"] >= 100:
        bin_record["fill"] = random.randint(0, 5)
    bin_record["lid"] = "OPEN" if random.random() < 0.10 else "CLOSED"

def fetch_live_bin001():
    """Fetch real-time hardware telemetry from Firebase REST API."""
    if not FIREBASE_URL or "default-rtdb" in FIREBASE_URL:
        # Default placeholder URL, return None to use simulator
        return None
    try:
        url = FIREBASE_URL.rstrip('/') + "/bins/BIN-001.json"
        res = requests.get(url, timeout=2.5)
        if res.status_code == 200 and res.json():
            return res.json()
    except Exception as e:
        # Fail gracefully without crashing the dashboard
        pass
    return None

def load_bins():
    """Return (list of bins, updated_at timestamp)."""
    sim = get_simulator()
    with sim["lock"]:
        this_minute = int(time.time() // 60)
        minutes_passed = this_minute - sim["last_minute"]
        if minutes_passed > 0:
            for _ in range(min(minutes_passed, 30)):
                for b in sim["bins"]:
                    if b["bin_id"] != "BIN-001":  # Only simulate virtual bins
                        make_next_reading(b)
            sim["last_minute"] = this_minute
            sim["updated_at"] = datetime.now(timezone.utc)

        bin_list = [dict(b) for b in sim["bins"]]

        # OVERWRITE BIN-001 WITH LIVE FIREBASE DATA
        live_data = fetch_live_bin001()
        if live_data:
            bin_list[0]["fill"] = int(live_data.get("fill", bin_list[0]["fill"]))
            bin_list[0]["lid"] = str(live_data.get("lid", bin_list[0]["lid"])).upper()
            bin_list[0]["source"] = "LIVE 🟢"
        else:
            bin_list[0]["source"] = "SIMULATED 🟡"

        return bin_list, sim["updated_at"]


# =====================================================================
# 2. RULES
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
# 3. STYLES
# =====================================================================
st.markdown("""
<style>
.block-container { padding-top: 1.6rem; max-width: 1100px; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
.stApp { background: #000000; color-scheme: dark; }

/* Top banner */
.top-banner { background: #174A78; border-radius: 10px; padding: 22px 28px; margin-bottom: 18px; }
.top-title { color: #FFFFFF; font-size: 30px; font-weight: 700; line-height: 1.2; margin: 0; }
.top-sub { color: #C3D5E8; font-size: 14px; margin: 6px 0 0 0; }

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
.kpi-value { color: #E6EEF5; font-size: 34px; font-weight: 700; line-height: 1.2; }

/* Bin table */
.section-title { color: #E6EEF5; font-size: 18px; font-weight: 700; margin: 16px 0 4px 10px; }
.table-wrap { background: #15222E; border: 1px solid #243545; border-radius: 10px;
              padding: 6px 18px 10px 18px; overflow-x: auto; }
table.bins { width: 100%; border-collapse: collapse; font-size: 15px; }
table.bins th { text-align: left; color: #93A5B5; font-size: 13px; font-weight: 600;
                padding: 12px 10px; border-bottom: 2px solid #243545; }
table.bins td { padding: 14px 10px; border-bottom: 1px solid #1F3040; color: #E6EEF5;
                vertical-align: middle; white-space: nowrap; }
table.bins tr:last-child td { border-bottom: none; }

/* Fill bar */
.bar-bg { display: inline-block; width: 140px; height: 10px; background: #2A3C4D;
          border-radius: 6px; overflow: hidden; vertical-align: middle; margin-right: 10px; }
.bar-fill { height: 100%; border-radius: 6px; }

/* Badges */
.badge { display: inline-block; padding: 3px 11px; border-radius: 99px; font-size: 13px; font-weight: 600; }
.badge-green  { background: #153A28; color: #6FDDA0; }
.badge-yellow { background: #3E3314; color: #F5CD6A; }
.badge-red    { background: #43191C; color: #FF9C98; }
.badge-open   { background: #162E4D; color: #8DB8F2; }
.badge-closed { background: #223140; color: #A8B7C6; }
.badge-live   { background: #064E3B; color: #34D399; border: 1px solid #059669; }

@media (max-width: 700px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# 4. DRAW THE LIVE PAGE
# =====================================================================
@st.fragment(run_every=REFRESH_SECONDS)
def show_dashboard():
    bins, updated_at = load_bins()

    for b in bins:
        b["status"] = get_bin_status(b["fill"])

    # Highest fill first
    bins = sorted(bins, key=lambda b: b["fill"], reverse=True)

    green_count = sum(1 for b in bins if b["status"] == "GREEN")
    yellow_count = sum(1 for b in bins if b["status"] == "YELLOW")
    red_bins = [b for b in bins if b["status"] == "RED"]

    # Top banner
    updated_text = datetime.now(IST).strftime("%d %b %Y, %H:%M:%S") + " IST"
    st.markdown(
        '<div class="top-banner">'
        '<div class="top-title">Smart Dustbin Monitoring (IoT Cloud)</div>'
        '<div class="top-sub">Real-time Firebase telemetry &bull; Last synchronized at ' + updated_text + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Critical alert
    if red_bins:
        names = ", ".join(b["bin_id"] + " (" + b["location"] + ")" for b in red_bins)
        st.markdown(
            '<div class="alert-box"><b>Action required.</b> These bins are 80% full or more '
            'and need emptying: ' + names + '.</div>',
            unsafe_allow_html=True,
        )

    # KPI summary cards
    def kpi_card(label, value, color):
        return ('<div class="kpi">'
                '<div class="kpi-label"><span class="dot" style="background:' + color + ';"></span>' + label + '</div>'
                '<div class="kpi-value">' + str(value) + '</div></div>')

    st.markdown(
        '<div class="kpi-row">'
        + kpi_card("Total Bins", len(bins), "#5B9BD5")
        + kpi_card("Normal (< 50%)", green_count, STATUS_STYLE["GREEN"]["color"])
        + kpi_card("Filling up (50-79%)", yellow_count, STATUS_STYLE["YELLOW"]["color"])
        + kpi_card("Critical (>= 80%)", len(red_bins), STATUS_STYLE["RED"]["color"])
        + '</div>',
        unsafe_allow_html=True,
    )

    # Table of all bins
    rows_html = ""
    for b in bins:
        style = STATUS_STYLE[b["status"]]
        lid_badge = "badge-open" if b["lid"] == "OPEN" else "badge-closed"
        source_badge = '<span class="badge badge-live">HARDWARE</span>' if "LIVE" in b.get("source", "") else '<span class="badge badge-closed">VIRTUAL</span>'
        
        rows_html += (
            '<tr>'
            '<td><b>' + b["bin_id"] + '</b> ' + source_badge + '</td>'
            '<td>' + b["location"] + '</td>'
            '<td><span class="bar-bg"><span class="bar-fill" style="display:block; width:'
            + str(b["fill"]) + '%; background:' + style["color"] + ';"></span></span>'
            + str(b["fill"]) + '%</td>'
            '<td><span class="badge ' + style["badge"] + '">' + style["label"] + '</span></td>'
            '<td><span class="badge ' + lid_badge + '">' + b["lid"].capitalize() + '</span></td>'
            '</tr>'
        )

    st.markdown(
        '<div class="table-wrap">'
        '<div class="section-title">All bins, highest fill first</div>'
        '<table class="bins">'
        '<tr><th>Bin ID</th><th>Location</th><th>Fill Level</th><th>Status</th><th>Lid</th></tr>'
        + rows_html +
        '</table>'
        '</div>',
        unsafe_allow_html=True,
    )

show_dashboard()
