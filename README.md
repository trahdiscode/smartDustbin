# Smart Dustbin Dashboard

Streamlit dashboard for an ESP32 + Arduino smart dustbin
(Embedded Systems course project).

Shows fill level, Green/Yellow/Red status, lid state and a
critical alert when the bin is 80% full or more.

Currently runs on fake data from a sidebar slider.
Real data from the database comes in a later phase.

## Run locally

    pip install -r requirements.txt
    streamlit run dashboard.py
