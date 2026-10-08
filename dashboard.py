# dashboard.py
# Smart Dustbin dashboard - version 2 (MANY bins, fake data for testing)
#
# BIN-001 is your real bin (its data will come from the ESP32 later).
# The other bins are SIMULATED so we can build the "set of dustbins" view.

import streamlit as st
import pandas as pd
from datetime import datetime

# ---------- Page setup ----------
st.set_page_config(page_title="Smart Dustbins", page_icon="🗑️", layout="wide")
st.title("Smart Dustbin Dashboard")

# ---------- The list of bins (fake data for now) ----------
# Each bin is one small "record" with its info.
# Change the locations to your real ones.
BINS = [
    {"bin_id": "BIN-001", "location": "Block A, Ground floor", "fill": 62, "lid": "CLOSED"},
    {"bin_id": "BIN-002", "location": "Block A, First floor",  "fill": 18, "lid": "CLOSED"},
    {"bin_id": "BIN-003", "location": "Canteen entrance",      "fill": 87, "lid": "CLOSED"},
    {"bin_id": "BIN-004", "location": "Library",               "fill": 45, "lid": "CLOSED"},
    {"bin_id": "BIN-005", "location": "Hostel gate",           "fill": 91, "lid": "OPEN"},
]

# ---------- Fake data controls (sidebar) ----------
# One folded-up section per bin, so the sidebar stays tidy.
st.sidebar.header("Fake data (testing only)")
bins = []   # this will hold each bin WITH the values you picked
for b in BINS:
    with st.sidebar.expander(b["bin_id"] + " - " + b["location"]):
        fill = st.slider("Fill level %", 0, 100, b["fill"], key="fill_" + b["bin_id"])
        lid = st.radio("Lid", ["CLOSED", "OPEN"],
                       index=0 if b["lid"] == "CLOSED" else 1,
                       key="lid_" + b["bin_id"])
    bins.append({"bin_id": b["bin_id"], "location": b["location"], "fill": fill, "lid": lid})

# ---------- Work out the status (same rules as the Arduino) ----------
def get_bin_status(fill):
    if fill < 50:
        return "GREEN"
    elif fill < 80:
        return "YELLOW"
    else:
        return "RED"

# Add a status to every bin
for b in bins:
    b["status"] = get_bin_status(b["fill"])

# Small dictionary to show a coloured dot next to each status
DOT = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}

# ---------- Count how many bins are in each state ----------
green_count = sum(1 for b in bins if b["status"] == "GREEN")
yellow_count = sum(1 for b in bins if b["status"] == "YELLOW")
red_bins = [b for b in bins if b["status"] == "RED"]

# ---------- Critical alert banner (only if any bin is RED) ----------
if red_bins:
    names = ", ".join(b["bin_id"] + " (" + b["location"] + ")" for b in red_bins)
    st.error("CRITICAL: please empty now -> " + names)

# ---------- Summary numbers ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total bins", len(bins))
c2.metric("🟢 Green", green_count)
c3.metric("🟡 Yellow", yellow_count)
c4.metric("🔴 Red", len(red_bins))

# ---------- Table of all bins, fullest first ----------
st.subheader("All bins (fullest first)")
sorted_bins = sorted(bins, key=lambda b: b["fill"], reverse=True)

table = pd.DataFrame({
    "Bin ID": [b["bin_id"] for b in sorted_bins],
    "Location": [b["location"] for b in sorted_bins],
    "Fill": [str(b["fill"]) + "%" for b in sorted_bins],
    "Status": [DOT[b["status"]] + " " + b["status"] for b in sorted_bins],
    "Lid": [b["lid"] for b in sorted_bins],
})
st.table(table.set_index("Bin ID"))

# ---------- Fill bar for each bin ----------
st.subheader("Fill levels")
for b in sorted_bins:
    st.write(DOT[b["status"]] + " **" + b["bin_id"] + "** - " + b["location"]
             + "  |  " + str(b["fill"]) + "%")
    st.progress(b["fill"] / 100)   # progress bar needs 0.0 to 1.0

# ---------- Last updated ----------
st.caption("Last updated: " + datetime.now().strftime("%d %b %Y, %H:%M:%S"))
