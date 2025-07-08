import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import uuid

# --- Setup Credentials ---
SERVICE_ACCOUNT_INFO = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)
client = gspread.authorize(creds)

SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
FOLDER_ID = st.secrets["FOLDER_ID"]
spreadsheet = client.open_by_key(SPREADSHEET_ID)

# --- Sheet Getters ---
def get_sheet(name):
    return spreadsheet.worksheet(name)

def get_worksheet_data(sheet_name):
    worksheet = get_sheet(sheet_name)
    records = worksheet.get_all_records()
    return records

# --- Save Customer ---
def save_customer(data):
    ws = get_sheet("Customers")
    customer_id = str(len(ws.get_all_values()))
    ws.append_row([customer_id] + data)
    return customer_id

# --- Upload to Google Drive ---
def upload_to_drive(local_file_path):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds_drive = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=["https://www.googleapis.com/auth/drive"])
    drive_service = build('drive', 'v3', credentials=creds_drive)

    file_metadata = {
        'name': local_file_path.split("/")[-1],
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(local_file_path, resumable=True)
    uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return uploaded.get('id')

# --- Save Appointment ---
def save_appointment(data):
    ws = get_sheet("Appointments")
    appointment_id = str(len(ws.get_all_values()))
    ws.append_row([appointment_id] + data)

# --- Get Appointments ---
def get_appointments():
    ws = get_sheet("Appointments")
    data = ws.get_all_records()
    return data

# --- Update Appointment Status ---
def update_appointment_status(appointment_id, new_status, rejection_reason=""):
    ws = get_sheet("Appointments")
    all_data = ws.get_all_values()

    header = all_data[0]
    for i, row in enumerate(all_data[1:], start=2):  # Skip header row
        if row[0] == str(appointment_id):
            status_col = header.index("Status")
            ws.update_cell(i, status_col + 1, new_status)
            return

# --- Pharmacist Schedule Management ---
def save_pharmacist_schedule_slot(data):
    ws = get_sheet("PharmacistSchedule")
    schedule_id = str(uuid.uuid4())[:8]
    ws.append_row([schedule_id] + data)

def get_pharmacist_available_slots():
    ws = get_sheet("PharmacistSchedule")
    rows = ws.get_all_records()
    return [r for r in rows if r['Status'] == 'Available']

def update_schedule_slot_status(schedule_id, new_status):
    ws = get_sheet("PharmacistSchedule")
    data = ws.get_all_values()
    header = data[0]

    for i, row in enumerate(data[1:], start=2):  # Skip header
        if row[0] == schedule_id:
            status_col = header.index("Status")
            ws.update_cell(i, status_col + 1, new_status)
            return

def get_all_pharmacist_schedule_slots():
    return get_sheet("PharmacistSchedule").get_all_records()
