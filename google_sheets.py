import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])

# Generate next ID
def generate_next_id(sheet_name, id_column):
    worksheet = spreadsheet.worksheet(sheet_name)
    records = worksheet.get_all_records()
    if not records:
        return "1"
    last_id = max([int(record[id_column]) for record in records if str(record[id_column]).isdigit()])
    return str(last_id + 1)

# Save customer
def save_customer(data):
    worksheet = spreadsheet.worksheet("Customers")
    customer_id = generate_next_id("Customers", "customerID")
    worksheet.append_row([customer_id] + data)
    return customer_id

# Save appointment (appointment type removed)
def save_appointment(data):
    worksheet = spreadsheet.worksheet("Appointments")
    appointment_id = generate_next_id("Appointments", "appointmentID")
    worksheet.append_row([appointment_id] + data)

# Save file metadata
def save_file_metadata(data):
    worksheet = spreadsheet.worksheet("Files")
    worksheet.append_row(data)

# Upload file to Google Drive
def upload_to_drive(file_path):
    drive_service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': os.path.basename(file_path), 'parents': [st.secrets["FOLDER_ID"]]}
    media = MediaFileUpload(file_path, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

# Update customer referral letter link
def update_customer_referral_letter(customer_username, file_link):
    worksheet = spreadsheet.worksheet("Customers")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):  # Start at row 2 because row 1 is header
        if record['customerUsername'] == customer_username:
            worksheet.update_acell(f"G{idx}", file_link)  # G column = customerReferalLetter
            break

# Get appointments (appointment type removed)
def get_appointments():
    worksheet = spreadsheet.worksheet("Appointments")
    records = worksheet.get_all_records()
    appointments = []
    for record in records:
        appointments.append({
            "appointmentID": record.get("appointmentID"),
            "customerID": record.get("customerID"),
            "Date": record.get("Date"),
            "Time": record.get("Time"),
            "Status": record.get("Status")
        })
    return appointments

# Get pharmacist schedule
def get_pharmacist_schedule():
    worksheet = spreadsheet.worksheet("Schedules")
    return worksheet.get_all_records()

# Update pharmacist schedule
def update_schedule():
    worksheet = spreadsheet.worksheet("Schedules")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    worksheet.append_row([f"Updated at {now}"])

# Update appointment status (reschedule or cancel)
def update_appointment_status(appointment_id, new_status, new_date=None, new_time=None, rejection_reason=None):
        worksheet = spreadsheet.worksheet("Appointments")
        records = worksheet.get_all_records()
        for idx, record in enumerate(records, start=2):  # Start at row 2 because row 1 is header
            if str(record['appointmentID']) == str(appointment_id):
                if new_status == "Rescheduled":
                    worksheet.update_acell(f"C{idx}", new_date)  # C = Date column
                    worksheet.update_acell(f"D{idx}", new_time)  # D = Time column
                    worksheet.update_acell(f"E{idx}", "Pending Confirmation")
                elif new_status == "Cancelled":
                    worksheet.update_acell(f"E{idx}", "Cancelled")
                elif new_status == "Confirmed":
                    worksheet.update_acell(f"E{idx}", "Confirmed")
                elif new_status == "Rejected":
                    worksheet.update_acell(f"E{idx}", "Rejected")
                    # Ensure your Google Sheet has a column for rejection reason, e.g., column F
                    if rejection_reason:
                        worksheet.update_acell(f"F{idx}", rejection_reason)
                    else: # Clear previous reason if none provided
                        worksheet.update_acell(f"F{idx}", "")
                break
    
def get_worksheet_data(sheet_name):
            """Reads all data from a specified worksheet and returns it as a Pandas DataFrame."""
            worksheet = spreadsheet.worksheet(sheet_name)
            if worksheet:
                try:
                    data = worksheet.get_all_records()
                    df = pd.DataFrame(data)
                    return df
                except Exception as e:
                    print(f"Error reading data from sheet '{sheet_name}': {e}")
                    return pd.DataFrame()
            return pd.DataFrame()

    """Retrieves all available time slots from the Pharmacist_Schedules sheet."""
    worksheet = spreadsheet.worksheet("Pharmacist_Schedules")
    records = worksheet.get_all_records()
    available_slots = []
    for record in records:
        # Only consider slots marked as "Available"
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
# You might also want a function to get all schedule slots (not just available)
def get_all_pharmacist_schedule_slots():
    """Retrieves all time slots from the Pharmacist_Schedules sheet."""
    worksheet = spreadsheet.worksheet("Pharmacist_Schedules")
    return worksheet.get_all_records()
