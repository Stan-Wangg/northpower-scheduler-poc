# app.py — Frontend-only Daily Scheduler (POC)
# --------------------------------------------------
# No backend required. Runs in memory with JSON import/export.
# How to run locally:
#   pip install streamlit pandas
#   streamlit run app.py
# On Streamlit Cloud:
#   repo:  contains app.py and requirements.txt (streamlit, pandas)

from __future__ import annotations
import json
from datetime import date, timedelta
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Northpower • Daily Scheduler (POC)", layout="wide")

# -----------------------------
# Session state bootstrapping
# -----------------------------
if "schedules" not in st.session_state:
    # schedules keyed by schedule_id; each value is a dict payload
    st.session_state.schedules: Dict[str, Dict[str, Any]] = {}
if "employees_df" not in st.session_state:
    # Default sample employees (DWW) so the POC works out-of-the-box
    st.session_state.employees_df = pd.DataFrame([
        {"EMPLOYEE_ID":"E-SAMG","EMPLOYEE_NAME":"Sam G","ROLE_CODE":"FLM","BUSINESS_UNIT":"DWW","STATUS":"ACTIVE"},
        {"EMPLOYEE_ID":"E-CHRISB","EMPLOYEE_NAME":"Chris B","ROLE_CODE":"LM","BUSINESS_UNIT":"DWW","STATUS":"ACTIVE"},
        {"EMPLOYEE_ID":"E-JAKEA","EMPLOYEE_NAME":"Jake A","ROLE_CODE":"LM","BUSINESS_UNIT":"DWW","STATUS":"ACTIVE"},
        {"EMPLOYEE_ID":"E-ETHANP","EMPLOYEE_NAME":"Ethan P","ROLE_CODE":"TRLM","BUSINESS_UNIT":"DWW","STATUS":"ACTIVE"},
    ])
if "prefill_resources" not in st.session_state:
    st.session_state.prefill_resources = None

BUSINESS_UNITS = ["DWW", "Connections", "Lines", "Civil", "Faults"]
PROJECT_STATUS_OPTIONS = ["Scheduled", "De-energised", "Energised", "On Hold", "Cancelled", "Completed"]
SCHEDULE_STATUS = ["SCHEDULED", "CANCELLED", "COMPLETED"]

# -----------------------------
# Helpers
# -----------------------------
def schedule_id_for(work_order: str, the_date: date) -> str:
    return f"{(work_order or 'WO')}-{the_date.strftime('%Y%m%d')}"

def flatten_for_table(schedules: Dict[str, Dict[str, Any]], target_date: date, bu: str) -> pd.DataFrame:
    """Build the 'Today's schedules' table."""
    rows: List[Dict[str, Any]] = []
    for sid, rec in schedules.items():
        if rec.get("schedule_date") != target_date.isoformat():
            continue
        if rec.get("business_unit") != bu:
            continue
        resources = rec.get("resources", [])
        if not resources:
            rows.append({
                "Date": rec["schedule_date"],
                "BU": rec["business_unit"],
                "Work Order": rec.get("work_order_number",""),
                "Job Description": rec.get("job_description",""),
                "Customer": rec.get("customer",""),
                "Work Type": rec.get("work_type",""),
                "Project Manager": rec.get("project_manager",""),
                "Task": rec.get("task_information",""),
                "Project Status": rec.get("project_status",""),
                "Employee": "—",
                "Role": "—",
                "Booked Hours": rec.get("hours_per_resource", None),
            })
        else:
            for r in resources:
                # Use the same uppercase keys we store on save
                rows.append({
                    "Date": rec["schedule_date"],
                    "BU": rec["business_unit"],
                    "Work Order": rec.get("work_order_number",""),
                    "Job Description": rec.get("job_description",""),
                    "Customer": rec.get("customer",""),
                    "Work Type": rec.get("work_type",""),
                    "Project Manager": rec.get("project_manager",""),
                    "Task": rec.get("task_information",""),
                    "Project Status": rec.get("project_status",""),
                    "Employee": r.get("EMPLOYEE_NAME",""),
                    "Role": r.get("ROLE_CODE",""),
                    "Booked Hours": r.get("BOOKED_HOURS", None),
                })
    return pd.DataFrame(rows)

# -----------------------------
# Sidebar — inputs & data
# -----------------------------
with st.sidebar:
    st.header("POC Controls")
    selected_date: date = st.date_input("Schedule date", value=date.today())
    selected_bu: str = st.selectbox("Business unit", BUSINESS_UNITS, index=0)

    st.markdown("---")
    st.caption("Employees data source")
    up = st.file_uploader("Upload employees.csv (optional)", type=["csv"], accept_multiple_files=False)
    if up is not None:
        try:
            df = pd.read_csv(up)
            needed = {"EMPLOYEE_ID","EMPLOYEE_NAME","ROLE_CODE","BUSINESS_UNIT","STATUS"}
            if not needed.issubset(set(df.columns)):
                st.error(f"CSV must include columns: {sorted(needed)}")
            else:
                st.session_state.employees_df = df
                st.success("Employees loaded.")
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")

# -----------------------------
# Main layout
# -----------------------------
left, right = st.columns([1.25, 1])

with left:
    st.subheader(selected_date.strftime("%A, %d %B %Y"))
    st.markdown("**Work order details**")

    with st.form("schedule_form", clear_on_submit=False):
        col1, col2 = st.columns([1, 1])
        with col1:
        work_order_number = st.text_input("Work Order Number", value="TC4216033")

        # 👇 Combine Customer + Work Type here
        customer_work_type = st.text_input(
            "Customer / Work Type",
            value="VEC - Capital - Non Contestable"
        )

        project_manager = st.text_input("Project manager", value="John Donald")

    with col2:
        job_description = st.text_area(
            "Job Description",
            value="Residential Subdivision work. Milldale 7A.",
            height=80
        )

        st.markdown("**Task & status**")
        task_information = st.text_area("Task information", value="Cabling/Installing Tuds/Jointing", height=70)

        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            project_status = st.selectbox("Project status", PROJECT_STATUS_OPTIONS, index=1)
        with c2:
            resources_booked_desc = st.text_input("Resources booked (label)", value="8 hr/resource")
        with c3:
            hours_per_resource = st.number_input("Hours per resource (numeric)", min_value=0.0, max_value=24.0, value=8.0, step=0.5)

        c4, c5 = st.columns([1, 2])
        with c4:
            schedule_status = st.selectbox("Schedule status", SCHEDULE_STATUS, index=0)
        with c5:
            notes = st.text_input("Notes", value="")

        left_submit = st.form_submit_button("Save schedule", type="primary", use_container_width=True)

with right:
    st.subheader("Resources")

    # Filter employees by BU and ACTIVE
    employees_df = st.session_state.employees_df
    if employees_df.empty:
        st.info("No employees available. Upload a CSV in the sidebar.")
        selected_labels = []
        base_selected = pd.DataFrame(columns=["EMPLOYEE_ID","EMPLOYEE_NAME","ROLE_CODE","BOOKED_HOURS"])  # empty
    else:
        ebu = employees_df[(employees_df["BUSINESS_UNIT"]==selected_bu) & (employees_df["STATUS"].str.upper()=="ACTIVE")].copy()
        if ebu.empty:
            st.warning(f"No ACTIVE employees found for BU={selected_bu}.")
        ebu["Label"] = ebu["EMPLOYEE_NAME"] + " – " + ebu["ROLE_CODE"].fillna("")
        default_labels = ["Sam G – FLM","Chris B – LM","Jake A – LM","Ethan P – TRLM"] if selected_bu=="DWW" else []
        selected_labels = st.multiselect("Select resources", options=ebu["Label"].tolist(), default=default_labels)

        # Build the base table to edit: either prefill from session or from current selection
        if st.session_state.prefill_resources is not None:
            base_selected = st.session_state.prefill_resources.copy()
            st.session_state.prefill_resources = None  # consume once
        else:
            base_selected = ebu[ebu["Label"].isin(selected_labels)][["EMPLOYEE_ID","EMPLOYEE_NAME","ROLE_CODE"]].copy()
            if not base_selected.empty:
                base_selected["BOOKED_HOURS"] = hours_per_resource

    # Editable table of selected resources
    edited = st.data_editor(
        base_selected,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
    )

    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        copy_prev = st.button("Copy previous day (same Work Order)", use_container_width=True)
    with col_btn2:
        # secondary save button on the right panel (same effect as form submit)
        right_save = st.button("Save schedule (same as above)", use_container_width=True)

# -----------------------------
# Actions
# -----------------------------
if copy_prev and 'work_order_number' in locals() and work_order_number:
    prev_id = schedule_id_for(work_order_number, selected_date - timedelta(days=1))
    prev = st.session_state.schedules.get(prev_id)
    if not prev or not prev.get("resources"):
        st.warning("No previous-day resources found for this Work Order.")
    else:
        # Expect uppercase keys coming from saved payload
        prev_df = pd.DataFrame(prev["resources"])[["EMPLOYEE_ID","EMPLOYEE_NAME","ROLE_CODE","BOOKED_HOURS"]]
        st.session_state.prefill_resources = prev_df
        st.success("Copied resources from the previous day. Review/edit in the table above.")

if left_submit or right_save:
    if not work_order_number:
        st.error("Work Order Number is required.")
    else:
        sid = schedule_id_for(work_order_number, selected_date)
        # Compose schedule payload
        payload: Dict[str, Any] = {
            "schedule_id": sid,
            "schedule_date": selected_date.isoformat(),
            "business_unit": selected_bu,
            "work_order_number": work_order_number,
            "job_description": job_description,
            "customer": customer,
            "work_type": work_type,
            "project_manager": project_manager,
            "task_information": task_information,
            "project_status": project_status,
            "resources_booked_desc": resources_booked_desc,
            "hours_per_resource": float(hours_per_resource) if hours_per_resource is not None else None,
            "status": schedule_status,
            "notes": notes,
            "resources": []  # filled below
        }
        if isinstance(edited, pd.DataFrame) and not edited.empty:
            for _, r in edited.iterrows():
                payload["resources"].append({
                    "EMPLOYEE_ID": str(r.get("EMPLOYEE_ID","")),
                    "EMPLOYEE_NAME": str(r.get("EMPLOYEE_NAME","")),
                    "ROLE_CODE": str(r.get("ROLE_CODE","")),
                    "BOOKED_HOURS": float(r.get("BOOKED_HOURS", payload["hours_per_resource"]) or 0.0),
                })
        st.session_state.schedules[sid] = payload
        st.success("Schedule saved in memory (POC). Use Export to download JSON.")

# -----------------------------
# Readback table for the day
# -----------------------------
st.divider()
st.subheader("Today's schedules")
readback = flatten_for_table(st.session_state.schedules, selected_date, selected_bu)
if readback.empty:
    st.info("No schedules saved for this day/BU yet.")
else:
    st.dataframe(readback, use_container_width=True, hide_index=True)

# -----------------------------
# Import/Export of POC data
# -----------------------------
with st.expander("Import / Export POC data"):
    colx, coly = st.columns(2)
    with colx:
        if st.button("Export all schedules to JSON"):
            json_data = json.dumps({"schedules": st.session_state.schedules}, indent=2)
            st.download_button("Download schedules.json", data=json_data, file_name="schedules_poc.json", mime="application/json")
    with coly:
        file = st.file_uploader("Import schedules_poc.json", type=["json"], accept_multiple_files=False)
        if file is not None:
            try:
                data = json.load(file)
                if isinstance(data, dict) and isinstance(data.get("schedules"), dict):
                    st.session_state.schedules.update(data["schedules"])
                    st.success("Schedules imported into memory.")
                else:
                    st.error("JSON missing 'schedules' object.")
            except Exception as e:
                st.error(f"Failed to import JSON: {e}")

# -----------------------------
# Developer notes (for later backend wiring)
# -----------------------------
with st.expander("Developer mapping notes"):
    st.markdown(
        """
        **Fields captured** (aligns to future backend):
        - WORK_ORDER: work_order_number, job_description, customer, work_type, project_manager
        - DAY_SCHEDULE: schedule_id, schedule_date, business_unit, task_information, project_status,
          resources_booked_desc, hours_per_resource, status, notes
        - SCHEDULE_RESOURCE: employee_id/name, role_code, booked_hours (one row per person)

        **Schedule ID rule**: `{WORK_ORDER}-{YYYYMMDD}`. Replace when integrating with DB if needed.
        """
    )
