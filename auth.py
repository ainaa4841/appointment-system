import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Google Sheets Auth Setup ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

spreadsheet = client.open("PharmacyAppointmentSystem")
users_sheet = spreadsheet.worksheet("Users")
customers_sheet = spreadsheet.worksheet("Customers")

def check_email_exists(email):
    users = users_sheet.get_all_records()
    return any(u['Email'].lower() == email.lower() for u in users)

def check_password_complexity(password):
    return len(password) >= 8 and any(c in "!@#$%^&*()_+-=" for c in password)

def register_user(username, password, role, email):
    users_sheet.append_row([username, password, role, email])

def login_user(username_or_email, password):
    users = users_sheet.get_all_values()
    headers = users[0]
    for row in users[1:]:
        user = dict(zip(headers, row))
        if (username_or_email == user['Username'] or username_or_email == user['Email']) and password == user['Password']:
            return user['Role'], user['Username'], user['Email']
    return None, None, None

def get_customer_id(username):
    customers = customers_sheet.get_all_values()
    headers = customers[0]
    for row in customers[1:]:
        data = dict(zip(headers, row))
        if data["customerUsername"] == username:
            return data["customerID"]
    return None
