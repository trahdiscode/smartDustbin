# dashboard.py
# Smart Dustbin dashboard - version 3 (professional look, no manual sliders)
#
# The page shows a FIXED set of sample bins for now.
# Later, the function load_bins() will read real data from the database.
# Nothing else in this file needs to change when that happens.

import streamlit as st
from datetime import datetime

# ---------- Page setup ----------
st.set_page_config(page_title="Smart Dustbin Monitoring", page_icon="🗑️", layout="wide")


# =====================================================================
# 1. DATA  (this is the only part we will replace later)
# =====================================================================
def load_bins():
    """Return the list of bins.
    RIGHT NOW: fixed sample data typed in by hand.
    LATER: this function will read the latest row of each bin from Supabase.
    """
    return [
        {"bin_id": "BIN-001", "location": "Block A, Ground floor", "fill": 62, "lid": "CLOSED"},
        {"bin_id": "BIN-002", "location": "Block A, First floor",  "fill": 18, "lid": "CLOSED"},
        {"bin_id": "BIN-003", "location": "Canteen entrance",      "fill": 87, "lid": "CLOSED"},
        {"bin_id": "BIN-004", "location": "Library",               "fill": 45, "lid": "CLOSED"},
        {"bin_id": "BIN-005", "location": "Hostel gate",           "fill": 91, "lid": "OPEN"},
    ]


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

/* Top banner */
.top-banner { background: #12355B; border-radius: 10px; padding: 22px 28px; margin-bottom: 18px; }
.top-title { color: #FFFFFF; font-size: 26px; font-weight: 700; margin: 0; }
.top-sub { color: #B9C8DA; font-size: 14px; margin: 4px 0 0 0; }

/* Critical alert */
.alert-box { background: #FBE3E3; border-left: 5px solid #D64545; color: #7A1D1D;
             padding: 14px 18px; border-radius: 8px; margin-bottom: 18px; font-size: 15px; }

/* Four summary cards */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
.kpi { background: #FFFFFF; border-radius: 10px; padding: 16px 18px;
       box-shadow: 0 1px 3px rgba(18, 53, 91, 0.10); }
.kpi-label { color: #5B6B7F; font-size: 13px; font-weight: 600; }
.kpi-value { color: #1B2A3A; font-size: 34px; font-weight: 700; line-height: 1.2; }

/* Bin table */
.section-title { color: #1B2A3A; font-size: 18px; font-weight: 700; margin: 6px 0 10px 0; }
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

.footnote { color: #5B6B7F; font-size: 13px; margin-top: 14px; }

/* On phones, show the summary cards two per row */
@media (max-width: 700px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# 4. PREPARE THE NUMBERS
# =====================================================================
bins = load_bins()

# Add a status to every bin
for b in bins:
    b["status"] = get_bin_status(b["fill"])

# Fullest bin first
bins = sorted(bins, key=lambda b: b["fill"], reverse=True)

# Count bins in each state
green_count = sum(1 for b in bins if b["status"] == "GREEN")
yellow_count = sum(1 for b in bins if b["status"] == "YELLOW")
red_bins = [b for b in bins if b["status"] == "RED"]


# =====================================================================
# 5. DRAW THE PAGE
# =====================================================================

# --- Top banner ---
now_text = datetime.now().strftime("%d %b %Y, %H:%M:%S")
st.markdown(
    '<div class="top-banner">'
    '<p class="top-title">Smart Dustbin Monitoring</p>'
    '<p class="top-sub">Fill level, status and lid state of every bin. Page loaded ' + now_text + '</p>'
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
    """Build the HTML for one summary card. 'color' is the colour of its left edge."""
    return ('<div class="kpi" style="border-left: 5px solid ' + color + ';">'
            '<div class="kpi-label">' + label + '</div>'
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
    '<div class="section-title">All bins, fullest first</div>'
    '<div class="table-wrap"><table class="bins">'
    '<tr><th>Bin ID</th><th>Location</th><th>Fill level</th><th>Status</th><th>Lid</th></tr>'
    + rows_html +
    '</table></div>',
    unsafe_allow_html=True,
)

# --- Honest note about the data ---
st.markdown(
    '<div class="footnote">Showing sample data. Live readings from the ESP32 will '
    'replace this in a later phase.</div>',
    unsafe_allow_html=True,
)
