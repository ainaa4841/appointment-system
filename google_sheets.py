import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import pandas as pd # Added for get_worksheet_data

# Google Sheets setup
# For local development, you might use a local JSON file:
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# service_account_info = json.loads(open("data/credentials.json").read()) # Adjust path if needed
# creds = Credentials.from_service_account_info(service_account_info, scopes=scope)

# For Streamlit Cloud deployment, use st.secrets:
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["GOOGLE_SERVICE_ACCOUNT"], # Assuming your secrets are under this key
    scopes=scope
)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"]) # Assuming SPREADSHEET_ID is in secrets

# Generate next ID
def generate_next_id(sheet_name, id_column):
    worksheet = spreadsheet.worksheet(sheet_name)
    records = worksheet.get_all_records()
    if not records:
        return "1"
    # Ensure all IDs are treated as strings and convert to int for max calculation
    last_id = max([int(record[id_column]) for record in records if str(record.get(id_column, '')).isdigit()])
    return str(last_id + 1)

# Save customer
def save_customer(data):
    worksheet = spreadsheet.worksheet("Customers")
    customer_id = generate_next_id("Customers", "customerID")
    worksheet.append_row([customer_id] + data)
    return customer_id

# Save appointment (updated to include pharmacist username)
def save_appointment(data):
    worksheet = spreadsheet.worksheet("Appointments")
    appointment_id = generate_next_id("Appointments", "appointmentID")
    worksheet.append_row([appointment_id] + data) # data should now include pharmacist username

# Save file metadata
def save_file_metadata(data):
    worksheet = spreadsheet.worksheet("Files")
    worksheet.append_row(data)

# Upload file to Google Drive
def upload_to_drive(file_path):
    drive_service = build('drive', 'v3', credentials=creds)
    # Ensure FOLDER_ID is in your Streamlit secrets
    file_metadata = {'name': os.path.basename(file_path), 'parents': [st.secrets["FOLDER_ID"]]}
    media = MediaFileUpload(file_path, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

# Update customer referral letter link
def update_customer_referral_letter(customer_username, file_link):
    worksheet = spreadsheet.worksheet("Customers")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):
        if record['customerUsername'] == customer_username:
            worksheet.update_acell(f"G{idx}", file_link)  # G column = customerReferalLetter
            break

# Get appointments
def get_appointments():
    worksheet = spreadsheet.worksheet("Appointments")
    records = worksheet.get_all_records()
    appointments = []
    for record in records:
        appointments.append({
            "appointmentID": record.get("appointmentID"),
            "customerID": record.get("customerID"),
            "PharmacistUsername": record.get("PharmacistUsername"), # Added
            "Date": record.get("Date"),
            "Time": record.get("Time"),
            "Status": record.get("Status"),
            "RejectionReason": record.get("RejectionReason") # Added
        })
    return appointments

# Get pharmacist schedule (original, likely not used anymore)
def get_pharmacist_schedule():
    worksheet = spreadsheet.worksheet("Schedules")
    return worksheet.get_all_records()

# Update pharmacist schedule (original, likely not used anymore)
def update_schedule():
    worksheet = spreadsheet.worksheet("Schedules")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    worksheet.append_row([f"Updated at {now}"])

# Update appointment status (reschedule or cancel)
def update_appointment_status(appointment_id, new_status, new_date=None, new_time=None, rejection_reason=None):
    worksheet = spreadsheet.worksheet("Appointments")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):
        if str(record['appointmentID']) == str(appointment_id):
            if new_status == "Rescheduled":
                worksheet.update_acell(f"D{idx}", new_date)  # Assuming Date is D
                worksheet.update_acell(f"E{idx}", new_time)  # Assuming Time is E
                worksheet.update_acell(f"F{idx}", "Pending Confirmation") # Assuming Status is F
                worksheet.update_acell(f"G{idx}", "") # Clear rejection reason
            elif new_status == "Cancelled":
                worksheet.update_acell(f"F{idx}", "Cancelled")
                worksheet.update_acell(f"G{idx}", "") # Clear rejection reason
            elif new_status == "Confirmed":
                worksheet.update_acell(f"F{idx}", "Confirmed")
                worksheet.update_acell(f"G{idx}", "") # Clear rejection reason
            elif new_status == "Rejected":
                worksheet.update_acell(f"F{idx}", "Rejected")
                if rejection_reason:
                    worksheet.update_acell(f"G{idx}", rejection_reason) # Assuming G is for RejectionReason
                else:
                    worksheet.update_acell(f"G{idx}", "") # Clear rejection reason if none provided
            break

# New: Get data from any worksheet as DataFrame
def get_worksheet_data(sheet_name):
    """Reads all data from a specified worksheet and returns it as a Pandas DataFrame."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: Worksheet '{sheet_name}' not found in the spreadsheet.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading data from sheet '{sheet_name}': {e}")
        return pd.DataFrame()

# New: Pharmacist Schedule Management
def save_pharmacist_schedule_slot(data):
    """Saves a new available time slot for a pharmacist."""
    worksheet = spreadsheet.worksheet("Pharmacist_Schedules")
    schedule_id = generate_next_id("Pharmacist_Schedules", "ScheduleID")
    worksheet.append_row([schedule_id] + data)
    return schedule_id

def get_pharmacist_available_slots():
    """Retrieves all available time slots from the Pharmacist_Schedules sheet."""
    worksheet = spreadsheet.worksheet("Pharmacist_Schedules")
    records = worksheet.get_all_records()
    available_slots = []
    for record in records:
        if record.get('Status') == "Available":
            available_slots.append({
                "ScheduleID": record.get("ScheduleID"),
                "PharmacistUsername": record.get("PharmacistUsername"),
                "Date": record.get("Date"),
                "Time": record.get("Time"),
                "Status": record.get("Status")
            })
    return available_slots

def update_schedule_slot_status(schedule_id, new_status):
    """Updates the status of a specific schedule slot (e.g., from Available to Booked)."""
    worksheet = spreadsheet.worksheet("Pharmacist_Schedules")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):
        if str(record['ScheduleID']) == str(schedule_id):
            worksheet.update_acell(f"E{idx}", new_status) # Assuming 'Status' is column E
            break

def get_all_pharmacist_schedule_slots():
    """Retrieves all time slots from the Pharmacist_Schedules sheet."""
    worksheet = spreadsheet.worksheet("Pharmacist_Schedules")
    return worksheet.get_all_records()
