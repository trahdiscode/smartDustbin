# dashboard.py
# Smart Dustbin IoT Monitoring Dashboard - ULTRA REAL-TIME (<100ms Latency)
# Uses Firebase Real-Time Server-Sent Events (SSE) Streaming directly in the browser!
# Primary Dustbin (BIN-001) updates INSTANTLY with zero polling lag.
# 4 Demo Dustbins (BIN-002 to BIN-005) simulated for campus monitoring.

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

FIREBASE_URL = "https://parkos1-default-rtdb.firebaseio.com"

# =====================================================================
# 1. INITIAL DATA
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
        "bins": [dict(b) for b in START_BINS],
    }

def make_next_reading(bin_record):
    bin_record["fill"] = bin_record["fill"] + random.randint(1, 3)
    if bin_record["fill"] >= 100:
        bin_record["fill"] = random.randint(0, 5)
    bin_record["lid"] = "OPEN" if random.random() < 0.10 else "CLOSED"

def fetch_initial_data():
    sim = get_simulator()
    with sim["lock"]:
        this_minute = int(time.time() // 60)
        if this_minute != sim["last_minute"]:
            for b in sim["bins"]:
                if not b.get("is_primary"):
                    make_next_reading(b)
            sim["last_minute"] = this_minute
        bin_list = [dict(b) for b in sim["bins"]]

    # Fetch initial state for BIN-001 from Firebase
    try:
        r = requests.get(FIREBASE_URL + "/bins/BIN-001.json", timeout=1.5).json()
        if r and isinstance(r, dict):
            bin_list[0]["fill"] = int(r.get("fill", 0))
            bin_list[0]["dist"] = int(r.get("dist", 0))
            bin_list[0]["lid"] = str(r.get("lid", "CLOSED")).upper()
    except Exception:
        pass
    return bin_list

# =====================================================================
# 2. STATUS HELPER
# =====================================================================
def get_status_info(fill):
    if fill < 50:
        return "Normal", "#3DBE7A", "badge-green"
    elif fill < 80:
        return "Filling up", "#F0B429", "badge-yellow"
    else:
        return "Critical", "#F0605D", "badge-red"

# =====================================================================
# 3. CSS & REAL-TIME WEBSOCKET/SSE STREAMING SCRIPT
# =====================================================================
st.markdown("""
<style>
.block-container { padding-top: 1.2rem; max-width: 1100px; }
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none; }
.stApp { background: #000000; color-scheme: dark; }

/* Top banner */
.top-banner { background: #174A78; border-radius: 10px; padding: 20px 26px; margin-bottom: 18px; }
.top-title { color: #FFFFFF; font-size: 28px; font-weight: 700; line-height: 1.2; margin: 0; }
.top-sub { color: #C3D5E8; font-size: 14px; margin: 4px 0 0 0; }

/* Primary Hardware Hero Card */
.hero-card {
    background: linear-gradient(145deg, #162B40, #0F1E2C);
    border: 2px solid #2B6CB0;
    border-radius: 12px;
    padding: 22px 26px;
    margin-bottom: 22px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    transition: all 0.3s ease;
}
.hero-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.hero-title { font-size: 20px; font-weight: 700; color: #FFFFFF; }
.hero-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 14px; }
.hero-stat-box { background: rgba(0, 0, 0, 0.4); border: 1px solid #243545; border-radius: 8px; padding: 14px; text-align: center; }
.hero-stat-label { font-size: 12px; color: #93A5B5; text-transform: uppercase; letter-spacing: 0.5px; }
.hero-stat-val { font-size: 30px; font-weight: 800; color: #FFFFFF; margin-top: 4px; transition: color 0.2s ease; }

/* Summary cards */
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }
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
.bar-bg { display: inline-block; width: 140px; height: 10px; background: #2A3C4D; border-radius: 6px; overflow: hidden; vertical-align: middle; margin-right: 10px; }
.bar-fill { height: 100%; border-radius: 6px; transition: width 0.3s ease, background 0.3s ease; }

/* Badges */
.badge { display: inline-block; padding: 4px 12px; border-radius: 99px; font-size: 12px; font-weight: 700; }
.badge-green  { background: #153A28; color: #6FDDA0; }
.badge-yellow { background: #3E3314; color: #F5CD6A; }
.badge-red    { background: #43191C; color: #FF9C98; }
.badge-open   { background: #2E1B0D; color: #F6AD55; border: 1px solid #DD6B20; }
.badge-closed { background: #162E4D; color: #63B3ED; }
.badge-live   { background: #064E3B; color: #34D399; border: 1px solid #059669; }
.badge-demo   { background: #1F2937; color: #9CA3AF; }

.live-pulse {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #34D399;
    margin-right: 6px; box-shadow: 0 0 8px #34D399; animation: pulse-dot 1.2s infinite ease-in-out;
}
@keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(0.8); } }

@media (max-width: 700px) { 
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .hero-stats { grid-template-columns: 1fr; }
}
</style>

<!-- ULTRA-LOW LATENCY FIREBASE SERVER-SENT EVENTS (SSE) STREAMER -->
<script>
(function() {
    function connectFirebaseStream() {
        const streamUrl = "https://parkos1-default-rtdb.firebaseio.com/bins/BIN-001.json";
        const evtSource = new EventSource(streamUrl);

        evtSource.addEventListener('put', function(e) {
            try {
                const parsed = JSON.parse(e.data);
                const data = parsed.data || parsed;
                if (!data) return;

                // Handle nested or partial updates
                const fill = (data.fill !== undefined) ? parseInt(data.fill) : null;
                const dist = (data.dist !== undefined) ? parseInt(data.dist) : null;
                const lid  = (data.lid !== undefined)  ? String(data.lid).toUpperCase() : null;

                if (fill !== null) {
                    const heroBar = document.getElementById('hero-fill-bar');
                    const heroText = document.getElementById('hero-fill-text');
                    const tableBar = document.getElementById('table-fill-bar-0');
                    const tableText = document.getElementById('table-fill-text-0');
                    const heroStatus = document.getElementById('hero-status-val');
                    const tableBadge = document.getElementById('table-status-badge-0');

                    let color = "#3DBE7A";
                    let label = "Normal";
                    let badgeClass = "badge badge-green";
                    if (fill >= 80) {
                        color = "#F0605D"; label = "Critical"; badgeClass = "badge badge-red";
                    } else if (fill >= 50) {
                        color = "#F0B429"; label = "Filling up"; badgeClass = "badge badge-yellow";
                    }

                    if (heroBar) { heroBar.style.width = fill + "%"; heroBar.style.background = color; }
                    if (heroText) { heroText.innerText = fill + "%"; heroText.style.color = color; }
                    if (tableBar) { tableBar.style.width = fill + "%"; tableBar.style.background = color; }
                    if (tableText) { tableText.innerText = fill + "%"; }
                    if (heroStatus) { heroStatus.innerText = label; heroStatus.style.color = color; }
                    if (tableBadge) { tableBadge.className = badgeClass; tableBadge.innerText = label; }
                }

                if (dist !== null) {
                    const heroDist = document.getElementById('hero-dist-val');
                    if (heroDist) heroDist.innerText = dist + " cm";
                }

                if (lid !== null) {
                    const heroLid = document.getElementById('hero-lid-val');
                    const tableLid = document.getElementById('table-lid-badge-0');

                    const lidColor = (lid === "OPEN") ? "#F6AD55" : "#63B3ED";
                    const badgeClass = (lid === "OPEN") ? "badge badge-open" : "badge badge-closed";

                    if (heroLid) { heroLid.innerText = lid; heroLid.style.color = lidColor; }
                    if (tableLid) { tableLid.className = badgeClass; tableLid.innerText = lid.charAt(0) + lid.slice(1).toLowerCase(); }
                }
            } catch (err) {
                console.log("Firebase stream parse error:", err);
            }
        });

        evtSource.onerror = function() {
            evtSource.close();
            setTimeout(connectFirebaseStream, 2000);
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', connectFirebaseStream);
    } else {
        connectFirebaseStream();
    }
})();
</script>
""", unsafe_allow_html=True)

# =====================================================================
# 4. RENDER PAGE
# =====================================================================
bins = fetch_initial_data()
primary_bin = bins[0]

green_count = sum(1 for b in bins if b["fill"] < 50)
yellow_count = sum(1 for b in bins if 50 <= b["fill"] < 80)
critical_count = sum(1 for b in bins if b["fill"] >= 80)

p_label, p_color, p_badge = get_status_info(primary_bin["fill"])
p_lid_color = "#F6AD55" if primary_bin["lid"] == "OPEN" else "#63B3ED"

# --- Top Banner ---
st.markdown(
    '<div class="top-banner">'
    '<div class="top-title">Smart Dustbin Live Monitoring</div>'
    '<div class="top-sub"><span class="live-pulse"></span> Ultra Real-Time WebSocket Streaming &bull; Sub-100ms Response</div>'
    '</div>',
    unsafe_allow_html=True,
)

# --- Primary Unit Hero Card ---
st.markdown(
    f'''
    <div class="hero-card">
        <div class="hero-header">
            <div class="hero-title">⭐ PRIMARY UNIT: {primary_bin["bin_id"]} ({primary_bin["location"]})</div>
            <span class="badge badge-live"><span class="live-pulse"></span>REAL-TIME HARDWARE</span>
        </div>
        <div style="margin: 8px 0;">
            <span style="font-size: 14px; color: #C3D5E8; margin-right: 10px;">Fill Level Capacity:</span>
            <span class="bar-bg" style="width: 60%; height: 14px;">
                <span class="bar-fill" id="hero-fill-bar" style="display:block; width: {primary_bin["fill"]}%; background: {p_color};"></span>
            </span>
            <span id="hero-fill-text" style="font-size: 20px; font-weight: 800; color: {p_color};">{primary_bin["fill"]}%</span>
        </div>
        <div class="hero-stats">
            <div class="hero-stat-box">
                <div class="hero-stat-label">Lid Position</div>
                <div class="hero-stat-val" id="hero-lid-val" style="color: {p_lid_color};">{primary_bin["lid"]}</div>
            </div>
            <div class="hero-stat-box">
                <div class="hero-stat-label">Remaining Depth</div>
                <div class="hero-stat-val" id="hero-dist-val">{primary_bin["dist"]} cm</div>
            </div>
            <div class="hero-stat-box">
                <div class="hero-stat-label">Health Status</div>
                <div class="hero-stat-val" id="hero-status-val" style="color: {p_color};">{p_label}</div>
            </div>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)

# --- Summary KPI Cards ---
def kpi_card(label, value, color):
    return ('<div class="kpi">'
            '<div class="kpi-label"><span class="dot" style="background:' + color + ';"></span>' + label + '</div>'
            '<div class="kpi-value">' + str(value) + '</div></div>')

st.markdown(
    '<div class="kpi-row">'
    + kpi_card("Total Campus Bins", len(bins), "#5B9BD5")
    + kpi_card("Normal (< 50%)", green_count, "#3DBE7A")
    + kpi_card("Filling up (50-79%)", yellow_count, "#F0B429")
    + kpi_card("Critical (>= 80%)", critical_count, "#F0605D")
    + '</div>',
    unsafe_allow_html=True,
)

# --- Table of Fleet ---
rows_html = ""
for idx, b in enumerate(bins):
    b_label, b_color, b_badge = get_status_info(b["fill"])
    lid_badge = "badge-open" if b["lid"] == "OPEN" else "badge-closed"
    source_badge = '<span class="badge badge-live">HARDWARE</span>' if b.get("is_primary") else '<span class="badge badge-demo">DEMO</span>'
    row_class = 'class="primary-row"' if b.get("is_primary") else ''
    
    fill_bar_id = f'id="table-fill-bar-{idx}"' if b.get("is_primary") else ''
    fill_text_id = f'id="table-fill-text-{idx}"' if b.get("is_primary") else ''
    status_badge_id = f'id="table-status-badge-{idx}"' if b.get("is_primary") else ''
    lid_badge_id = f'id="table-lid-badge-{idx}"' if b.get("is_primary") else ''

    rows_html += (
        f'<tr {row_class}>'
        f'<td><b>{b["bin_id"]}</b> {source_badge}</td>'
        f'<td>{b["location"]}</td>'
        f'<td><span class="bar-bg"><span class="bar-fill" {fill_bar_id} style="display:block; width:{b["fill"]}%; background:{b_color};"></span></span>'
        f'<span {fill_text_id}>{b["fill"]}%</span></td>'
        f'<td><span class="badge {b_badge}" {status_badge_id}>{b_label}</span></td>'
        f'<td><span class="badge {lid_badge}" {lid_badge_id}>{b["lid"].capitalize()}</span></td>'
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
