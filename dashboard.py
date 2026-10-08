# dashboard.py
# Smart Dustbin dashboard - version 1 (fake data for testing)

import streamlit as st
from datetime import datetime

# ---------- Fixed info about this bin ----------
# Later the ESP32 will send these. For now we type them in.
BIN_ID = "BIN-001"
LOCATION = "Block A, Ground floor"   # change this to your real location

# ---------- Page setup ----------
st.set_page_config(page_title="Smart Dustbin", page_icon="🗑️")
st.title("Smart Dustbin Dashboard")

# ---------- Fake data controls (sidebar) ----------
# These stand in for the real sensor until the database is ready.
st.sidebar.header("Fake data (testing only)")
fill_percent = st.sidebar.slider("Fill level %", 0, 100, 62)
lid_status = st.sidebar.radio("Lid", ["CLOSED", "OPEN"])

# ---------- Work out the status (same rules as the Arduino) ----------
def get_bin_status(fill):
    if fill < 50:
        return "GREEN"
    elif fill < 80:
        return "YELLOW"
    else:
        return "RED"

bin_status = get_bin_status(fill_percent)

# ---------- Critical alert banner (only when RED) ----------
if bin_status == "RED":
    st.error("CRITICAL: Bin is almost full. Please empty it now!")

# ---------- Bin details ----------
st.subheader(f"{BIN_ID}  |  {LOCATION}")

# Two columns side by side
col1, col2 = st.columns(2)
col1.metric("Fill level", f"{fill_percent}%")
col2.metric("Lid", lid_status)

# A progress bar needs a value between 0.0 and 1.0
st.progress(fill_percent / 100)

# ---------- Status colour box ----------
if bin_status == "GREEN":
    st.success("Status: GREEN - plenty of space")
elif bin_status == "YELLOW":
    st.warning("Status: YELLOW - filling up")
else:
    st.error("Status: RED - full")

# ---------- Last updated ----------
st.caption("Last updated: " + datetime.now().strftime("%d %b %Y, %H:%M:%S"))
