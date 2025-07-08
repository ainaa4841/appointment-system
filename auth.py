import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import json

# Setup Google Sheets credentials
def get_gspread_client():
    credentials_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_auth_sheet():
    client = get_gspread_client()
    sheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
    return sheet.worksheet("Users")

def check_email_exists(email):
    sheet = get_auth_sheet()
    users = sheet.get_all_records()
    return any(user["Email"] == email for user in users)

def check_password_complexity(password):
    return len(password) >= 8 and any(c in "!@#$%^&*()-_+=" for c in password)

def register_user(username, password, role, email):
    sheet = get_auth_sheet()
    sheet.append_row([username, password, role, email])

def login_user(username_or_email, password):
    sheet = get_auth_sheet()
    users = sheet.get_all_records()
    for user in users:
        if (user["Username"] == username_or_email or user["Email"] == username_or_email) and user["Password"] == password:
            return user["Role"], user["Username"], user["Email"]
    return None, None, None

def get_customer_id(username):
    client = get_gspread_client()
    customer_sheet = client.open_by_key(st.secrets["SPREADSHEET_ID"]).worksheet("Customers")
    customers = customer_sheet.get_all_records()
    for customer in customers:
        if customer["customerUsername"] == username:
            return customer["customerID"]
    return ""
