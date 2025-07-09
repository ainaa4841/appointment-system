import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json
import streamlit as st
import os
import mimetypes
from googleapiclient.http import MediaFileUpload


scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
FOLDER_ID = st.secrets["FOLDER_ID"]


def generate_next_id(sheet, col_name):
    records = spreadsheet.worksheet(sheet).get_all_records()
    if not records: return 1
    return int(records[-1][col_name]) + 1

def save_customer(data):
    ws = spreadsheet.worksheet("Customers")
    cid = generate_next_id("Customers", "customerID")
    ws.append_row([cid] + data)
    return cid

def save_appointment(data, referral_path=None):
    worksheet = spreadsheet.worksheet("Appointments")
    appointment_id = generate_next_id("Appointments", "appointmentID")
    if referral_path is None:
        referral_path = ""
    worksheet.append_row([appointment_id] + data + [referral_path])  # Add referral path to appointment
    remove_schedule_slot(data[1], data[2])  # data[1] = date, data[2] = time




def save_file_metadata(data):
    ws = spreadsheet.worksheet("Files")
    ws.append_row(data)



def get_appointments():
    ws = spreadsheet.worksheet("Appointments")
    return ws.get_all_records()

def update_schedule(date, time):
    ws = spreadsheet.worksheet("Schedules")
    ws.append_row([date, time])

def get_pharmacist_schedule():
    return spreadsheet.worksheet("Schedules").get_all_records()

def update_appointment_status(appointment_id, new_status=None, new_date=None, new_time=None):
    import gspread
    from google.oauth2 import service_account
    import streamlit as st

    creds = service_account.Credentials.from_service_account_info(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SPREADSHEET_ID"]).worksheet("Appointments")

    headers = sheet.row_values(1)
    records = sheet.get_all_records()

    for idx, row in enumerate(records):
        if str(row["appointmentID"]) == str(appointment_id):
            row_number = idx + 2  # Account for header row

            if new_status:
                col_index = headers.index("Status") + 1
                sheet.update_cell(row_number, col_index, new_status)

            if new_date:
                col_index = headers.index("Date") + 1
                sheet.update_cell(row_number, col_index, new_date)

            if new_time:
                col_index = headers.index("Time") + 1
                sheet.update_cell(row_number, col_index, new_time)

            break




def get_all_customers():
    return spreadsheet.worksheet("Customers").get_all_records()

def save_report(data):
    ws = spreadsheet.worksheet("Reports")
    rid = generate_next_id("Reports", "reportID")
    ws.append_row([rid] + data)

def remove_schedule_slot(date, time):
    worksheet = spreadsheet.worksheet("Schedules")
    records = worksheet.get_all_records()
    date = str(date).strip().lower()
    time = str(time).strip().lower()

    for idx, record in enumerate(records, start=2):
        rec_date = str(record["Date"]).strip().lower()
        rec_time = str(record["Time"]).strip().lower()
        if rec_date == date and rec_time == time:
            worksheet.delete_rows(idx)
            return
    print(f"[DEBUG] Slot not found for deletion: {date} - {time}")

def upload_to_drive(file_path):
    drive_service = build("drive", "v3", credentials=creds)
    file_metadata = {
        "name": os.path.basename(file_path),
        "parents": [FOLDER_ID]
    }
    mimetype, _ = mimetypes.guess_type(file_path)
    media = MediaFileUpload(file_path, mimetype=mimetype)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    return uploaded_file.get("id")


def restore_schedule_slot(date, time):
    worksheet = spreadsheet.worksheet("Schedules")
    records = worksheet.get_all_records()
    for record in records:
        rec_date = str(record["Date"]).strip().lower()
        rec_time = str(record["Time"]).strip().lower()
        if rec_date == str(date).strip().lower() and rec_time == str(time).strip().lower():
            return  # already exists
    worksheet.append_row([date, time])

def get_all_reports():
    ws = spreadsheet.worksheet("Reports")
    return ws.get_all_records()

