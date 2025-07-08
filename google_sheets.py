import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import uuid

# --- Google Sheets & Drive Setup ---
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

spreadsheet = client.open("PharmacyAppointmentSystem")
customers_sheet = spreadsheet.worksheet("Customers")
appointments_sheet = spreadsheet.worksheet("Appointments")
schedules_sheet = spreadsheet.worksheet("PharmacistSchedules")
files_sheet = spreadsheet.worksheet("Files")

# --- Drive API for file uploads ---
drive_service = build('drive', 'v3', credentials=creds)

def upload_to_drive(filepath):
    file_metadata = {
        'name': filepath.split("/")[-1],
        'parents': ['YOUR_FOLDER_ID']  # <-- Replace with actual folder ID
    }
    media = MediaFileUpload(filepath, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get("id")

def save_file_metadata(data):
    files_sheet.append_row(data)

# --- Customer handling ---
def save_customer(data):
    customer_id = str(uuid.uuid4())
    customers_sheet.append_row([customer_id] + data + [""])  # Final "" for old referral column (no longer used)
    return customer_id

# --- Appointment handling ---
def save_appointment(data):
    appointment_id = str(uuid.uuid4())
    appointments_sheet.append_row([appointment_id] + data)

def get_appointments():
    rows = appointments_sheet.get_all_values()
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:]]

def update_appointment_status(appointment_id, new_status, rejection_reason=""):
    all_data = appointments_sheet.get_all_values()
    headers = all_data[0]

    id_idx = headers.index("appointmentID")
    status_idx = headers.index("Status")
    reason_idx = headers.index("RejectionReason")

    for i, row in enumerate(all_data[1:], start=2):
        if row[id_idx] == appointment_id:
            appointments_sheet.update_cell(i, status_idx + 1, new_status)
            appointments_sheet.update_cell(i, reason_idx + 1, rejection_reason)
            break

# --- Pharmacist Schedule Management ---
def save_pharmacist_schedule_slot(data):
    schedule_id = str(uuid.uuid4())
    schedules_sheet.append_row([schedule_id] + data)

def get_pharmacist_available_slots():
    rows = schedules_sheet.get_all_values()
    headers = rows[0]
    result = []
    for row in rows[1:]:
        slot = dict(zip(headers, row))
        if slot["Status"] == "Available":
            result.append(slot)
    return result

def get_all_pharmacist_schedule_slots():
    rows = schedules_sheet.get_all_values()
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:]]

def update_schedule_slot_status(schedule_id, new_status):
    rows = schedules_sheet.get_all_values()
    headers = rows[0]
    id_idx = headers.index("ScheduleID")
    status_idx = headers.index("Status")

    for i, row in enumerate(rows[1:], start=2):
        if row[id_idx] == schedule_id:
            schedules_sheet.update_cell(i, status_idx + 1, new_status)
            break

# --- Utility ---
def get_worksheet_data(sheet_name):
    ws = spreadsheet.worksheet(sheet_name)
    rows = ws.get_all_values()
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:]]
