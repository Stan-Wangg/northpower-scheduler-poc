# app.py — Daily Scheduler (POC) + Calendar View
# --------------------------------------------------
# Runs in memory with JSON import/export.
# Requirements: streamlit, pandas
# Optional branding: .streamlit/config.toml with your theme.

from __future__ import annotations
import json
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

# -----------------------------------
# Page setup
# -----------------------------------
st.set_page_config(page_title="Northpower • Daily Scheduler (POC)", layout="wide")

# (Optional) small CSS polish for buttons/headers with brand orange #F05A28
st.markdown(
    """
    <style>
    .stMarkdown h1 { color:#F05A28 !important; font-weight:700 !important; }
    div.stButton > button:first-child {
        background-color:#F05A28; color:#fff; border-radius:6px; font-weight:700;
    }
    div.stButton > button:first-child:hover { background-color:#d94e21; color:#fff; }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------
# Session state bootstrapping
# -----------------------------------
if "schedules" not in st.session_state:
    st.session_state.schedules: Dict[str, Dict[str, Any]] = {}
if "prefill_resources" not in st.session_state:
    st.session_state.prefill_resources = None

# -----------------------------------
# Dropdown Options
# -----------------------------------
BUSINESS_UNITS = ["DTS", "DDS", "DAR", "DWW", "DCN", "DES", "DRM"]

PROJECT_MANAGER_OPTIONS = ["John Donald", "Lyndon Connolly", "Neil Jones"]

PROJECT_STATUS_OPTIONS = [
    "Live Line", "Shut Down HV", "Shut Down LV", "De-energised",
    "Subcontractor only", "Tentative", "Unplanned", "Training",
    "9 Hr Break", "Leave", "Planning - Office based"
]

SCHEDULE_STATUS = ["SCHEDULED", "CANCELLED", "COMPLETED"]

CUSTOMER_WORK_TYPE_OPTIONS = [
    "VEC - CIW CSUB", "VEC - CIW SUBDV", "VEC - Asset replacment",
    "VEC - Capital Contestable", "VEC - Capital - Non Contestable",
    "VEC - Streetlights", "Non VECTOR Customer Works", "Leave",
    "Non Charge", "Training",
]

RESOURCES_BOOKED_OPTIONS = [
    "Callum Mc - LM", "Carlo D - TRLM", "Chris B - LM", "Ethan P - TRLM",
    "Howard C - FLM", "Jake A - LM", "Joel G - LM", "John C - TRLM",
    "Luke B - LM", "Mack I - GB LM", "Mike I - FLM", "Poutama LE - TRLM",
    "Sam G - FLM", "Steve R - SU", "Toby E - TRLM"
]

# -----------------------------------
# Helpers
# -----------------------------------
def schedule_id_for(work_order: str, sched_date: date) -> str:
    return f"{work_order}-{sched_date.strftime('%Y%m%d')}"

def month_days(year: int, month: int):
    """Yield dates covering the month, padded to start Monday / end Sunday."""
    first = date(year, month, 1)
    start = first - timedelta(days=first.weekday())  # Monday start
    _, last_day = monthrange(year, month)
    last = date(year, month, last_day)
    end = last + timedelta(days=(6 - last.weekday()))  # Sunday end
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)

def schedules_for_iso(iso_d: str):
    """List of schedule dicts for a given YYYY-MM-DD."""
    return [rec for rec in st.session_state.schedules.values()
            if rec.get("schedule_date") == iso_d]

# -----------------------------------
# Tabs: Scheduler | Calendar
# -----------------------------------
st.title("📅 Northpower Daily Scheduler (POC)")
tab_sched, tab_cal = st.tabs(["📝 Scheduler", "📆 Calendar"])

# ===================================
# TAB: Scheduler
# ===================================
with tab_sched:

    selected_date = st.date_input("Select schedule date", value=date.today(), key="sched_date")
    selected_bu = st.selectbox(
        "Business Unit (required)",
        BUSINESS_UNITS,
        index=None,
        placeholder="Select..."
    )

    with st.form("schedule_form", clear_on_submit=False):
        col1, col2 = st.columns([1, 1])

        with col1:
            work_order_number = st.text_input("Work Order Number (required)", value="")
            customer_work_type = st.selectbox(
                "Customer / Work Type (required)",
                CUSTOMER_WORK_TYPE_OPTIONS,
                index=None,
                placeholder="Select..."
            )
            project_manager = st.selectbox(
                "Project Manager (required)",
                PROJECT_MANAGER_OPTIONS,
                index=None,
                placeholder="Select..."
            )

        with col2:
            job_description = st.text_area(
                "Job Description (required)",
                value="",
                height=80
            )

        st.markdown("**Task & Status**")
        task_information = st.text_area("Task Information (required)", value="", height=70)

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            project_status = st.selectbox(
                "Project Status (required)",
                PROJECT_STATUS_OPTIONS,
                index=None,
                placeholder="Select status"
            )
        with c2:
            resources_booked = st.multiselect(
                "Resources Booked (required)",
                RESOURCES_BOOKED_OPTIONS,
                default=[]
            )
        with c3:
            hours_per_resource = st.number_input(
                "Hours per resource (required)",
                min_value=0.5,
                max_value=24.0,
                value=None,
                step=0.5,
                format="%.1f"
            )

        c4, c5 = st.columns([1, 2])
        with c4:
            schedule_status = st.selectbox("Schedule status", SCHEDULE_STATUS, index=0)
        with c5:
            notes = st.text_input("Notes", value="")

        left_submit = st.form_submit_button("💾 Save Schedule", type="primary", use_container_width=True)

    # Validation + Save
    if left_submit:
        missing = []
        if not selected_bu: missing.append("Business Unit")
        if not work_order_number.strip(): missing.append("Work Order Number")
        if not customer_work_type: missing.append("Customer / Work Type")
        if not job_description.strip(): missing.append("Job Description")
        if not project_manager: missing.append("Project Manager")
        if not task_information.strip(): missing.append("Task Information")
        if not project_status: missing.append("Project Status")
        if not resources_booked: missing.append("Resources Booked")
        if hours_per_resource is None: missing.append("Hours per Resource")

        if missing:
            st.error(f"⚠️ Please fill in all required fields: {', '.join(missing)}")
        else:
            sid = schedule_id_for(work_order_number, selected_date)
            payload: Dict[str, Any] = {
                "schedule_id": sid,
                "schedule_date": selected_date.isoformat(),
                "business_unit": selected_bu,
                "work_order_number": work_order_number,
                "customer_work_type": customer_work_type,
                "job_description": job_description,
                "project_manager": project_manager,
                "task_information": task_information,
                "project_status": project_status,
                "resources_booked": resources_booked,  # list
                "hours_per_resource": float(hours_per_resource),
                "status": schedule_status,
                "notes": notes,
            }
            st.session_state.schedules[sid] = payload
            st.success("✅ Schedule saved in memory (POC).")

# ===================================
# TAB: Calendar (Option A)
# ===================================
with tab_cal:
    st.subheader("Calendar overview")

    # Month selector (defaults to current month)
    sel_month = st.date_input("Month", value=date.today().replace(day=1), key="cal_month")
    yyyy, mm = sel_month.year, sel_month.month

    # Build counts per day for the month
    day_counts: Dict[str, int] = {}
    for rec in st.session_state.schedules.values():
        d = rec.get("schedule_date")
        if not d:
            continue
        if d.startswith(f"{yyyy:04d}-{mm:02d}-"):
            day_counts[d] = day_counts.get(d, 0) + 1

    # Month label + weekday header
    st.caption(f"{datetime(yyyy, mm, 1):%B %Y}")
    hdr = st.columns(7)
    for i, wd in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        hdr[i].markdown(f"**{wd}**")

    # Render month grid
    selected_day = st.session_state.get("calendar_selected_day")
    colset = None
    for i, d in enumerate(month_days(yyyy, mm)):
        if i % 7 == 0:
            colset = st.columns(7)

        iso_d = d.isoformat()
        in_month = (d.month == mm)
        count = day_counts.get(iso_d, 0)

        with colset[i % 7]:
            # Day tile
            opacity = "0.45" if not in_month else "1.0"
            st.markdown(
                f"""
                <div style="padding:8px;border-radius:8px;border:1px solid #444; opacity:{opacity}">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:600;">{d.day}</span>
                    <span style="background:#F05A28;color:white;border-radius:12px;padding:0 8px;font-size:12px;">{count}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            # Click to view details for this day
            if st.button("View", key=f"view-{iso_d}"):
                st.session_state.calendar_selected_day = iso_d
                selected_day = iso_d

    st.markdown("---")
    # Detail panel
    if selected_day and selected_day.startswith(f"{yyyy:04d}-{mm:02d}-"):
        day_list = schedules_for_iso(selected_day)
        st.subheader(f"Schedules for {selected_day} ({len(day_list)})")
        if not day_list:
            st.info("No schedules for this day.")
        else:
            rows = []
            for rec in day_list:
                bu = rec.get("business_unit","")
                wo = rec.get("work_order_number","")
                cwt = rec.get("customer_work_type","")
                pm = rec.get("project_manager","")
                stat = rec.get("project_status","")
                hrs = rec.get("hours_per_resource", None)
                notes = rec.get("notes","")
                booked = rec.get("resources_booked", [])
                if booked:
                    for b in booked:
                        rows.append({
                            "BU": bu, "Work Order": wo, "Customer / Work Type": cwt,
                            "PM": pm, "Status": stat, "Booked": b, "Hrs/Res": hrs, "Notes": notes
                        })
                else:
                    rows.append({
                        "BU": bu, "Work Order": wo, "Customer / Work Type": cwt,
                        "PM": pm, "Status": stat, "Booked": "—", "Hrs/Res": hrs, "Notes": notes
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.info("Select a day in the grid to see details.")
