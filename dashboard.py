# dashboard.py
# Smart Dustbin dashboard - version 4 (simulated data, new random reading every minute)
#
# All bins are SIMULATED for now. A new random reading is created once per minute.
# Later, BIN-001 will switch to real data from the ESP32 and database.

import random
import threading
import time
from datetime import datetime, timezone

import streamlit as st

# ---------- Page setup ----------
st.set_page_config(page_title="Smart Dustbin Monitoring", page_icon="🗑️", layout="wide")

# How often (in seconds) the page checks for new data.
# New readings are still created only once per minute.
REFRESH_SECONDS = 10


# =====================================================================
# 1. DATA  (a simulator that makes a new random reading every minute)
# =====================================================================

# Where each bin starts. After that, the fill levels change by themselves.
START_BINS = [
    {"bin_id": "BIN-001", "location": "Block A, Ground floor", "fill": 62, "lid": "CLOSED"},
    {"bin_id": "BIN-002", "location": "Block A, First floor",  "fill": 18, "lid": "CLOSED"},
    {"bin_id": "BIN-003", "location": "Canteen entrance",      "fill": 87, "lid": "CLOSED"},
    {"bin_id": "BIN-004", "location": "Library",               "fill": 45, "lid": "CLOSED"},
    {"bin_id": "BIN-005", "location": "Hostel gate",           "fill": 91, "lid": "OPEN"},
]

@st.cache_resource
def get_simulator():
    """Create the simulator ONCE and share it with everyone who opens the page.
    (Without this, every visitor would see different random numbers.)"""
    return {
        "lock": threading.Lock(),                # stops two visitors changing data at the same moment
        "last_minute": int(time.time() // 60),   # which minute we last made a reading for
        "updated_at": datetime.now(timezone.utc),
        "bins": [dict(b) for b in START_BINS],
    }

def make_next_reading(bin_record):
    """Change ONE bin by one minute's worth of random filling."""
    # Garbage only goes UP: add 1 to 5 percent.
    bin_record["fill"] = bin_record["fill"] + random.randint(1, 5)
    # If the bin is full, pretend someone emptied it (back to 0 to 5 percent).
    if bin_record["fill"] >= 100:
        bin_record["fill"] = random.randint(0, 5)
    # The lid is only open for a few seconds in real life, so 1 reading in 10.
    bin_record["lid"] = "OPEN" if random.random() < 0.10 else "CLOSED"

def load_bins():
    """Return (list of bins, time of the last new reading).
    RIGHT NOW: simulated. LATER: this will read real rows from Supabase."""
    sim = get_simulator()
    with sim["lock"]:
        this_minute = int(time.time() // 60)
        minutes_passed = this_minute - sim["last_minute"]
        if minutes_passed > 0:
            # Make one reading per minute that passed (at most 30, in case the app was asleep).
            for _ in range(min(minutes_passed, 30)):
                for b in sim["bins"]:
                    make_next_reading(b)
            sim["last_minute"] = this_minute
            sim["updated_at"] = datetime.now(timezone.utc)
        # Return COPIES so the page cannot accidentally change the shared data.
        return [dict(b) for b in sim["bins"]], sim["updated_at"]


# =====================================================================
# 2. RULES  (same thresholds as the Arduino code)
# =====================================================================
def get_bin_status(fill):
    """Turn a fill percentage into GREEN, YELLOW or RED."""
    if fill < 50:
        return "GREEN"
    elif fill < 80:
        return "YELLOW"
    else:
        return "RED"

# How each status is shown on screen: a word, a bar colour, and a badge style.
STATUS_STYLE = {
    "GREEN":  {"label": "Normal",     "color": "#2E9E5B", "badge": "badge-green"},
    "YELLOW": {"label": "Filling up", "color": "#E0A100", "badge": "badge-yellow"},
    "RED":    {"label": "Critical",   "color": "#D64545", "badge": "badge-red"},
}


# =====================================================================
# 3. LOOK  (CSS = the styling instructions for the page)
# =====================================================================
st.markdown("""
<style>
.block-container { padding-top: 1.6rem; max-width: 1100px; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
.stApp { background: #F4F6F9; color-scheme: light; }

/* Top banner */
.top-banner { background: #12355B; border-radius: 10px; padding: 22px 28px; margin-bottom: 18px; }
.top-title { color: #FFFFFF; font-size: 30px; font-weight: 700; line-height: 1.2; margin: 0; }
.top-sub { color: #B9C8DA; font-size: 14px; margin: 6px 0 0 0; }

/* Critical alert */
.alert-box { position: relative; overflow: hidden; background: #FBE3E3; color: #7A1D1D;
             padding: 14px 18px 14px 26px; border-radius: 8px; margin-bottom: 18px; font-size: 15px; }
.alert-box::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0;
                     width: 6px; background: #D64545; }

/* Four summary cards */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
.kpi { background: #FFFFFF; border-radius: 10px; padding: 16px 18px;
       box-shadow: 0 1px 3px rgba(18, 53, 91, 0.10); }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
       margin-right: 8px; vertical-align: middle; }
.kpi-label { color: #5B6B7F; font-size: 13px; font-weight: 600; }
.kpi-value { color: #1B2A3A; font-size: 34px; font-weight: 700; line-height: 1.2; }

/* Bin table */
.section-title { color: #1B2A3A; font-size: 18px; font-weight: 700; margin: 16px 0 4px 10px; }
.table-wrap { background: #FFFFFF; border-radius: 10px; padding: 6px 18px 10px 18px;
              box-shadow: 0 1px 3px rgba(18, 53, 91, 0.10); overflow-x: auto; }
table.bins { width: 100%; border-collapse: collapse; font-size: 15px; }
table.bins th { text-align: left; color: #5B6B7F; font-size: 13px; font-weight: 600;
                padding: 12px 10px; border-bottom: 2px solid #E3E8EF; }
table.bins td { padding: 14px 10px; border-bottom: 1px solid #EEF1F5; color: #1B2A3A;
                vertical-align: middle; white-space: nowrap; }
table.bins tr:last-child td { border-bottom: none; }

/* Fill bar */
.bar-bg { display: inline-block; width: 150px; height: 10px; background: #E8ECF2;
          border-radius: 6px; overflow: hidden; vertical-align: middle; margin-right: 10px; }
.bar-fill { height: 100%; border-radius: 6px; }

/* Small coloured labels (badges) */
.badge { display: inline-block; padding: 3px 11px; border-radius: 99px; font-size: 13px; font-weight: 600; }
.badge-green  { background: #E3F5EA; color: #1E7A46; }
.badge-yellow { background: #FFF3CD; color: #8A6100; }
.badge-red    { background: #FBE3E3; color: #B02A2A; }
.badge-open   { background: #E1ECFA; color: #1F5AA6; }
.badge-closed { background: #EDF0F4; color: #4A5A6C; }

/* On phones, show the summary cards two per row */
@media (max-width: 700px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# 4 and 5. PREPARE THE NUMBERS AND DRAW THE PAGE
# This function re-runs by itself every REFRESH_SECONDS, so the page
# updates without you pressing refresh.
# =====================================================================
@st.fragment(run_every=REFRESH_SECONDS)
def show_dashboard():
    bins, updated_at = load_bins()

    # Add a status to every bin
    for b in bins:
        b["status"] = get_bin_status(b["fill"])

    # Highest fill first
    bins = sorted(bins, key=lambda b: b["fill"], reverse=True)

    # Count bins in each state
    green_count = sum(1 for b in bins if b["status"] == "GREEN")
    yellow_count = sum(1 for b in bins if b["status"] == "YELLOW")
    red_bins = [b for b in bins if b["status"] == "RED"]


    # =====================================================================
    # 5. DRAW THE PAGE
    # =====================================================================

    # --- Top banner ---
    updated_text = updated_at.strftime("%d %b %Y, %H:%M:%S") + " UTC"
    st.markdown(
        '<div class="top-banner">'
        '<div class="top-title">Smart Dustbin Monitoring</div>'
        '<div class="top-sub">Fill level, status and lid state of every bin. Last reading ' + updated_text + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- Critical alert (only if at least one bin is RED) ---
    if red_bins:
        names = ", ".join(b["bin_id"] + " (" + b["location"] + ")" for b in red_bins)
        st.markdown(
            '<div class="alert-box"><b>Action required.</b> These bins are 80% full or more '
            'and need emptying: ' + names + '.</div>',
            unsafe_allow_html=True,
        )

    # --- Four summary cards ---
    def kpi_card(label, value, color):
        """Build the HTML for one summary card. 'color' is the colour of the small dot."""
        return ('<div class="kpi">'
            '<div class="kpi-label"><span class="dot" style="background:' + color + ';"></span>' + label + '</div>'
                '<div class="kpi-value">' + str(value) + '</div></div>')

    st.markdown(
        '<div class="kpi-row">'
        + kpi_card("Total bins", len(bins), "#12355B")
        + kpi_card("Normal (under 50%)", green_count, STATUS_STYLE["GREEN"]["color"])
        + kpi_card("Filling up (50 to 79%)", yellow_count, STATUS_STYLE["YELLOW"]["color"])
        + kpi_card("Critical (80% and above)", len(red_bins), STATUS_STYLE["RED"]["color"])
        + '</div>',
        unsafe_allow_html=True,
    )

    # --- Table of all bins ---
    rows_html = ""
    for b in bins:
        style = STATUS_STYLE[b["status"]]
        lid_badge = "badge-open" if b["lid"] == "OPEN" else "badge-closed"
        rows_html += (
            '<tr>'
            '<td><b>' + b["bin_id"] + '</b></td>'
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
        '<tr><th>Bin ID</th><th>Location</th><th>Fill level</th><th>Status</th><th>Lid</th></tr>'
        + rows_html +
        '</table>'
        '</div>',
        unsafe_allow_html=True,
    )


show_dashboard()
