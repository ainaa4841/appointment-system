import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity, get_customer_id
from google_sheets import (
    save_customer, save_appointment, save_file_metadata,
    upload_to_drive, get_appointments, get_pharmacist_schedule,
    update_schedule, update_appointment_status
)
import os

st.set_page_config(page_title="Farmasi Pantai Hillpark", layout="wide")

with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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
        menu = ["Manage Schedule", "Logout"]

choice = st.sidebar.selectbox("Menu", menu)

if choice == "Register":
    st.subheader("Customer Registration")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")

    if st.button("Register"):
        if not username or not password or not full_name or not email or not phone:
            st.error("Please fill in all required fields.")
        elif not check_password_complexity(password):
            st.error("Password must be at least 8 characters and contain a special character.")
        elif check_email_exists(email):
            st.error("Email already exists. Please use a different email or login.")
        else:
            register_user(username, password, "Customer", email)
            customer_id = save_customer([username, password, full_name, email, phone, ""])
            st.success(f"Registration successful! Your customer ID is {customer_id}. Please log in.")

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
            st.error("Invalid credentials!")

elif choice == "Book Appointment":
    st.subheader("Book an Appointment")
    date = st.date_input("Select Date")
    time = st.selectbox("Select Time Slot", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"])
    uploaded_file = st.file_uploader("Upload Referral Letter")

    if st.button("Book Appointment"):
        if not uploaded_file:
            st.error("Please upload a referral letter.")
        else:
            if not os.path.exists("uploads"):
                os.makedirs("uploads")

            file_path = f"uploads/{uploaded_file.name}"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            file_id = upload_to_drive(file_path)
            file_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

            save_file_metadata([st.session_state.user_username, uploaded_file.name, file_id])

            from google_sheets import update_customer_referral_letter
            update_customer_referral_letter(st.session_state.user_username, file_link)

            save_appointment([st.session_state.customer_id, str(date), time, "Pending Confirmation"])

            st.success(f"Appointment booked on {date} at {time}. Status: Pending Confirmation.")

elif choice == "My Appointments":
    st.subheader("My Appointments")
    appointments = get_appointments()
    my_appointments = [
        appt for appt in appointments if str(appt['customerID']) == str(st.session_state.customer_id)
    ]

    if not my_appointments:
        st.info("No appointments found.")
    else:
        for idx, appt in enumerate(my_appointments):
            st.write(f"Date: {appt['Date']}, Time: {appt['Time']}, Status: {appt['Status']}")

            reschedule_button = st.button(f"Reschedule {appt['Date']} {appt['Time']}", key=f"reschedule_{idx}")
            cancel_button = st.button(f"Cancel {appt['Date']} {appt['Time']}", key=f"cancel_{idx}")

            if reschedule_button:
                new_date = st.date_input(f"Select new date for {appt['Date']} {appt['Time']}", key=f"new_date_{idx}")
                new_time = st.selectbox(f"Select new time for {appt['Date']} {appt['Time']}", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"], key=f"new_time_{idx}")
                if st.button(f"Confirm Reschedule {appt['Date']} {appt['Time']}", key=f"confirm_{idx}"):
                    update_appointment_status(appt['appointmentID'], "Rescheduled", str(new_date), new_time)
                    st.success(f"Appointment rescheduled to {new_date} at {new_time}. Status: Pending Confirmation.")
                    st.experimental_rerun()

            if cancel_button:
                update_appointment_status(appt['appointmentID'], "Cancelled")
                st.success("Appointment cancelled successfully!")
                st.experimental_rerun()

elif choice == "Manage Schedule":
    st.subheader("Pending Appointments")

    appointments = get_appointments()
    pending_appointments = [appt for appt in appointments if appt['Status'] == "Pending Confirmation"]

    if not pending_appointments:
        st.info("No pending appointments to review.")
    else:
        for idx, appt in enumerate(pending_appointments):
            st.write(f"Appointment ID: {appt['appointmentID']}")
            st.write(f"Customer ID: {appt['customerID']}")
            st.write(f"Date: {appt['Date']}")
            st.write(f"Time: {appt['Time']}")
            st.write("---")

            confirm_button = st.button(f"Confirm {appt['appointmentID']}", key=f"confirm_{idx}")
            reject_button = st.button(f"Reject {appt['appointmentID']}", key=f"reject_{idx}")

            if confirm_button:
                update_appointment_status(appt['appointmentID'], "Confirmed")
                st.success(f"Appointment {appt['appointmentID']} confirmed successfully!")
                st.experimental_rerun()

            if reject_button:
                rejection_reason = st.text_input(f"Rejection reason for {appt['appointmentID']}", key=f"reason_{idx}")
                if st.button(f"Submit Rejection {appt['appointmentID']}", key=f"submit_rejection_{idx}"):
                    update_appointment_status(appt['appointmentID'], "Rejected", rejection_reason=rejection_reason)
                    st.success(f"Appointment {appt['appointmentID']} rejected successfully!")
                    st.experimental_rerun()


elif choice == "Logout":
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''
    st.experimental_rerun()
