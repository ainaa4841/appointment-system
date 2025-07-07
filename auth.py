import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st
import re

# --- Google Sheets Authentication ---
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

def register_user(username, password, role, email):
    worksheet = spreadsheet.worksheet("Users")
    worksheet.append_row([username, password, role, email])

def login_user(username_or_email, password):
    worksheet = spreadsheet.worksheet("Users")
    users = worksheet.get_all_records()
    for user in users:
        if (user['Username'] == username_or_email or user['Email'] == username_or_email) and user['Password'] == password:
            return user['Role'], user['Username'], user['Email']
    return None, None, None

def get_customer_id(username):
    worksheet = spreadsheet.worksheet("Customers")
    customers = worksheet.get_all_records()
    for customer in customers:
        if customer['customerUsername'] == username:
            return str(customer['customerID'])
    return None

def check_email_exists(email):
    worksheet = spreadsheet.worksheet("Users")
    users = worksheet.get_all_records()
    for user in users:
        if user['Email'] == email:
            return True
    return False

def check_password_complexity(password):
    # Password must be at least 8 characters and contain a special character.
    if len(password) < 8 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True
