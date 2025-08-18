# app.py — Frontend-only Daily Scheduler (POC) with Northpower branding
# --------------------------------------------------
# Requirements: streamlit, pandas
# How to run locally:
#   pip install streamlit pandas
#   streamlit run app.py

from __future__ import annotations
import json
from datetime import date
from typing import Dict, Any
import pandas as pd
import streamlit as st

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="Northpower • Daily Scheduler (POC)", layout="wide")

# Inject custom CSS for brand styling
st.markdown(
    """
    <style>
    /* Main title */
    .css-10trblm {
        color: #F05A28 !important;
        font-weight: 700 !important;
    }
    /* Button */
    div.stButton > button:first-child {
        background-color: #F05A28;
        color: white;
        border-radius: 6px;
        font-weight: bold;
    }
    div.stButton > button:first-child:hover {
        background-color: #d94e21;
        color: white;
    }
    /* Labels */
    label {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# Session state bootstrapping
# -----------------------------
if "schedules" not in st.session_state:
    st.session_state.schedules: Dict[str, Dict[str, Any]] = {}

# -----------------------------
# Options
# -----------------------------
BUSINESS_UNITS = ["DTS", "DDS", "DAR", "DWW", "DCN", "DES", "DRM"]

PROJECT_MANAGER_OPTIONS = ["John Donald", "Lyndon Connolly", "Neil Jones"]

PROJECT_STATUS_OPTIONS = [
    "Live Line",
    "Shut Down HV",
    "Shut Down LV",
    "De-energised",
    "Subcontractor only",
    "Tentative",
    "Unplanned",
    "Training",
    "9 Hr Break",
    "Leave",
    "Planning - Office based"
]

SCHEDULE_STATUS = ["SCHEDULED", "CANCELLED", "COMPLETED"]

CUSTOMER_WORK_TYPE_OPTIONS = [
    "VEC - CIW CSUB",
    "VEC - CIW SUBDV",
    "VEC - Asset replacment",
    "VEC - Capital Contestable",
    "VEC - Capital - Non Contestable",
    "VEC - Streetlights",
    "Non VECTOR Customer Works",
    "Leave",
    "Non Charge",
    "Training",
]

RESOURCES_BOOKED_OPTIONS = [
    "Callum Mc - LM",
    "Carlo D - TRLM",
    "Chris B - LM",
    "Ethan P - TRLM",
    "Howard C - FLM",
    "Jake A - LM",
    "Joel G - LM",
    "John C - TRLM",
    "Luke B - LM",
    "Mack I - GB LM",
    "Mike I - FLM",
    "Poutama LE - TRLM",
    "Sam G - FLM",
    "Steve R - SU",
    "Toby E - TRLM"
]

# -----------------------------
# Helper to generate schedule ID
# -----------------------------
def schedule_id_for(work_order: str, sched_date: date) -> str:
    return f"{work_order}-{sched_date.strftime('%Y%m%d')}"

# -----------------------------
# UI
# -----------------------------
st.title("📅 Northpower Daily Scheduler (POC)")

selected_date = st.date_input("Select schedule date", value=date.today())
selected_bu = st.selectbox("Business Unit", BUSINESS_UNITS, index=None, placeholder="Select...")

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
        job_description = st.text_area("Job Description (required)", value="", height=80)

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
            step=0.5,
            format="%.1f"
        )

    c4, c5 = st.columns([1, 2])
    with c4:
        schedule_status = st.selectbox("Schedule status", SCHEDULE_STATUS, index=0)
    with c5:
        notes = st.text_input("Notes", value="")

    left_submit = st.form_submit_button("💾 Save Schedule", type="primary", use_container_width=True)

# -----------------------------
# Validation + Save
# -----------------------------
if left_submit:
    missing_fields = []
    if not work_order_number.strip():
        missing_fields.append("Work Order Number")
    if not customer_work_type:
        missing_fields.append("Customer / Work Type")
    if not job_description.strip():
        missing_fields.append("Job Description")
    if not project_manager:
        missing_fields.append("Project Manager")
    if not task_information.strip():
        missing_fields.append("Task Information")
    if not project_status:
        missing_fields.append("Project Status")
    if not resources_booked:
        missing_fields.append("Resources Booked")
    if not hours_per_resource:
        missing_fields.append("Hours per Resource")
    if not selected_bu:
        missing_fields.append("Business Unit")

    if missing_fields:
        st.error(f"⚠️ Please fill in all required fields: {', '.join(missing_fields)}")
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
            "resources_booked": resources_booked,
            "hours_per_resource": float(hours_per_resource),
            "status": schedule_status,
            "notes": notes,
        }
        st.session_state.schedules[sid] = payload
        st.success("✅ Schedule saved in memory (POC).")
