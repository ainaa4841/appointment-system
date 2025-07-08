import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity, get_customer_id
from google_sheets import (
    save_customer, save_appointment, save_file_metadata,
    upload_to_drive, get_appointments, get_worksheet_data,
    save_pharmacist_schedule_slot, get_pharmacist_available_slots,
    update_schedule_slot_status, get_all_pharmacist_schedule_slots,
    update_appointment_status
)
import os
import pandas as pd

st.set_page_config(page_title="Farmasi Pantai Hillpark", layout="wide")

try:
    with open("MultipleFiles/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("CSS file not found.")

st.title("Farmasi Pantai Hillpark Appointment System")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''

menu = ["Login", "Register"]
if st.session_state.logged_in:
    if st.session_state.user_role == 'Customer':
        menu = ["Book Appointment", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        menu = ["Manage Pending Appointments", "Set Availability", "View My Schedule", "Logout"]

choice = st.sidebar.selectbox("Menu", menu)

# ---------------- Registration ----------------
if choice == "Register":
    st.subheader("Customer Registration")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")

    if st.button("Register"):
        if not all([username, password, full_name, email, phone]):
            st.error("Please fill in all required fields.")
        elif not check_password_complexity(password):
            st.error("Password must be at least 8 characters with a special character.")
        elif check_email_exists(email):
            st.error("Email already exists.")
        else:
            register_user(username, password, "Customer", email)
            customer_id = save_customer([username, password, full_name, email, phone])
            st.success(f"Registered! Your ID: {customer_id}")

# ---------------- Login ----------------
elif choice == "Login":
    st.subheader("Login")
    username_or_email = st.text_input("Username or Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role, username, email = login_user(username_or_email, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.user_role = role
            st.session_state.user_username = username
            st.session_state.user_email = email
            if role == "Customer":
                st.session_state.customer_id = get_customer_id(username)
            st.experimental_rerun()
        else:
            st.error("Invalid credentials.")

# ---------------- Book Appointment ----------------
elif choice == "Book Appointment":
    st.subheader("Book an Appointment")
    available_slots = get_pharmacist_available_slots()

    if not available_slots:
        st.info("No slots available.")
    else:
        display_options = []
        actual_slots = []
        for slot in available_slots:
            display_options.append(f"{slot['Date']} {slot['Time']} (Pharmacist: {slot['PharmacistUsername']})")
            actual_slots.append(slot)

        selected_index = st.selectbox("Select slot", range(len(display_options)), format_func=lambda i: display_options[i])
        selected_slot = actual_slots[selected_index]

        st.write(f"Selected: {selected_slot['Date']} at {selected_slot['Time']} with {selected_slot['PharmacistUsername']}")

        uploaded_file = st.file_uploader("Upload Referral Letter", type=["pdf", "jpg", "png"])

        if st.button("Book Appointment"):
            if not uploaded_file:
                st.error("Please upload referral letter.")
            else:
                if not os.path.exists("uploads"):
                    os.makedirs("uploads")
                file_path = f"uploads/{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                file_id = upload_to_drive(file_path)
                file_link = f"https://drive.google.com/uc?export=download&id={file_id}"
                save_file_metadata([st.session_state.user_username, uploaded_file.name, file_id])

                appointment_data = [
                    st.session_state.customer_id,
                    selected_slot['PharmacistUsername'],
                    selected_slot['Date'],
                    selected_slot['Time'],
                    "Pending Confirmation",
                    "",  # RejectionReason
                    selected_slot['ScheduleID'],
                    file_link  # <- appointmentReferalLetter
                ]
                save_appointment(appointment_data)
                update_schedule_slot_status(selected_slot['ScheduleID'], "Booked")

                st.success("Appointment booked. Await pharmacist confirmation.")
                st.experimental_rerun()

# ---------------- My Appointments ----------------
elif choice == "My Appointments":
    st.subheader("My Appointments")
    appointments = get_appointments()
    my_appts = [a for a in appointments if a['customerID'] == st.session_state.customer_id]

    if not my_appts:
        st.info("No appointments.")
    else:
        for appt in my_appts:
            st.markdown("---")
            st.write(f"**Date:** {appt['Date']} at {appt['Time']}")
            st.write(f"**Pharmacist:** {appt['PharmacistUsername']}")
            st.write(f"**Status:** {appt['Status']}")
            if appt['Status'] == "Rejected" and appt.get('RejectionReason'):
                st.error(f"Reason: {appt['RejectionReason']}")
            if appt.get('appointmentReferalLetter'):
                st.markdown(f"[Download Referral Letter]({appt['appointmentReferalLetter']})")

# ---------------- Manage Pending Appointments ----------------
elif choice == "Manage Pending Appointments":
    st.subheader("Pending Appointments")
    appointments = get_appointments()
    pending = [a for a in appointments if a['Status'] == "Pending Confirmation" and a['PharmacistUsername'] == st.session_state.user_username]

    for appt in pending:
        st.markdown("---")
        st.write(f"**Appointment ID:** {appt['appointmentID']}")
        st.write(f"**Date/Time:** {appt['Date']} at {appt['Time']}")
        st.write(f"**Customer ID:** {appt['customerID']}")
        if appt.get("appointmentReferalLetter"):
            st.markdown(f"[Download Referral Letter]({appt['appointmentReferalLetter']})")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Confirm {appt['appointmentID']}"):
                update_appointment_status(appt['appointmentID'], "Confirmed")
                st.success(f"Appointment {appt['appointmentID']} confirmed.")
                st.experimental_rerun()
        with col2:
            if st.button(f"Reject {appt['appointmentID']}"):
                reason = st.text_input("Reason for rejection:")
                if reason:
                    update_appointment_status(appt['appointmentID'], "Rejected", rejection_reason=reason)
                    update_schedule_slot_status(appt['ScheduleID'], "Available")
                    st.success(f"Appointment {appt['appointmentID']} rejected.")
                    st.experimental_rerun()

# ---------------- Set Availability ----------------
elif choice == "Set Availability":
    st.subheader("Set Your Availability")
    date = st.date_input("Select date")
    time = st.selectbox("Time", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"])
    if st.button("Add Slot"):
        existing = get_all_pharmacist_schedule_slots()
        for slot in existing:
            if slot['PharmacistUsername'] == st.session_state.user_username and slot['Date'] == str(date) and slot['Time'] == time:
                st.warning("Slot already exists.")
                break
        else:
            save_pharmacist_schedule_slot([st.session_state.user_username, str(date), time, "Available"])
            st.success(f"Slot added: {date} {time}")
            st.experimental_rerun()

# ---------------- View My Schedule ----------------
elif choice == "View My Schedule":
    st.subheader("My Schedule")
    slots = get_all_pharmacist_schedule_slots()
    mine = [s for s in slots if s['PharmacistUsername'] == st.session_state.user_username]
    df = pd.DataFrame(mine)
    if not df.empty:
        st.dataframe(df[['Date', 'Time', 'Status']])
    else:
        st.info("No schedule slots found.")

# ---------------- Logout ----------------
elif choice == "Logout":
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()
