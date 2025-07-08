import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
import streamlit as st
import json
import os
from datetime import datetime

# --- Setup ---
credentials_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
credentials = service_account.Credentials.from_service_account_info(
    credentials_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(st.secrets["SPREADSHEET_ID"])

drive_service = build("drive", "v3", credentials=credentials)

# --- Sheet Helpers ---
def get_worksheet(name):
    return sheet.worksheet(name)

def get_worksheet_data(name):
    return get_worksheet(name).get_all_records()

# --- Save Customer ---
def save_customer(data):
    ws = get_worksheet("Customers")
    records = ws.get_all_records()
    next_id = len(records) + 1
    ws.append_row([next_id] + data)
    return next_id

# --- Upload File to Drive ---
def upload_to_drive(file_path):
    file_metadata = {
        "name": os.path.basename(file_path),
        "parents": [st.secrets["FOLDER_ID"]]
    }
    media = MediaFileUpload(file_path, resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id"
    ).execute()
    return uploaded_file.get("id")

def save_file_metadata(data):
    get_worksheet("Files").append_row(data)

# --- Appointment ---
def save_appointment(data):
    ws = get_worksheet("Appointments")
    records = ws.get_all_records()
    next_id = len(records) + 1
    ws.append_row([next_id] + data)

def get_appointments():
    ws = get_worksheet("Appointments")
    data = ws.get_all_records()
    return data

def update_appointment_status(appointment_id, new_status):
    ws = get_worksheet("Appointments")
    data = ws.get_all_values()
    headers = data[0]
    for i, row in enumerate(data[1:], start=2):
        if str(row[0]) == str(appointment_id):
            status_col = headers.index("Status") + 1
            ws.update_cell(i, status_col, new_status)
            break

# --- Pharmacist Schedule ---
def save_pharmacist_schedule_slot(data):
    ws = get_worksheet("PharmacistSchedule")
    records = ws.get_all_records()
    next_id = len(records) + 1
    ws.append_row([next_id] + data)

def get_pharmacist_available_slots():
    ws = get_worksheet("PharmacistSchedule")
    return [r for r in ws.get_all_records() if r["Status"] == "Available"]

def get_all_pharmacist_schedule_slots():
    return get_worksheet("PharmacistSchedule").get_all_records()

def update_schedule_slot_status(schedule_id, new_status):
    ws = get_worksheet("PharmacistSchedule")
    data = ws.get_all_values()
    headers = data[0]
    for i, row in enumerate(data[1:], start=2):
        if str(row[0]) == str(sch
