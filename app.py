import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity, get_customer_id
from google_sheets import (
    save_customer, save_appointment, save_file_metadata,
    upload_to_drive, get_appointments, get_pharmacist_schedule, # This get_pharmacist_schedule is likely for old "Schedules" sheet
    update_schedule, update_appointment_status, get_worksheet_data,
    save_pharmacist_schedule_slot, get_pharmacist_available_slots,
    update_schedule_slot_status, get_all_pharmacist_schedule_slots # New imports
)
import pandas as pd
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

enu = ["Login", "Register"]
if st.session_state.logged_in:
    if st.session_state.user_role == 'Customer':
        menu = ["Book Appointment", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        # Updated menu for Pharmacist
        menu = ["Manage Pending Appointments", "Set Availability", "View Schedule", "Logout"]
                
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

                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    file_id = upload_to_drive(file_path)
                    file_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                    save_file_metadata([st.session_state.user_username, uploaded_file.name, file_id])
                    # 2. Update customer's referral letter link in Customers sheet
                    update_customer_referral_letter(st.session_state.user_username, file_link)
                    # 3. Save the appointment
                    # Add selected_pharmacist_username to the appointment data
                    # Ensure your Appointments sheet has a column for PharmacistUsername
                    # (e.g., after customerID, before Date)
                    appointment_data = [
                        st.session_state.customer_id,
                        selected_pharmacist_username, # New: Store assigned pharmacist
                        selected_date,
                        selected_time,
                        "Pending Confirmation"
                    ]
                    save_appointment(appointment_data)
                    # 4. Mark the selected schedule slot as "Booked"
                    update_schedule_slot_status(selected_schedule_id, "Booked")
                    st.success(f"Appointment booked on {selected_date} at {selected_time} with {selected_pharmacist_username}. Status: Pending Confirmation.")
                    st.info("The pharmacist will review your request and confirm the appointment.")
                    st.experimental_rerun()

elif choice == "My Appointments":
    st.subheader("My Appointments")
    appointments = get_appointments() # This fetches all appointments

    # Ensure customer_id is correctly set and used for filtering
    current_customer_id = st.session_state.customer_id
    if not current_customer_id:
        st.warning("Please log in as a customer to view your appointments.")
        my_appointments = [] # No customer ID, no appointments to show
    else:
        # Filter appointments for the logged-in customer
        # Ensure both sides of the comparison are treated as strings for robustness
        my_appointments = [
            appt for appt in appointments
            if str(appt.get('customerID')) == str(current_customer_id)
        ]

    if not my_appointments:
        st.info("No appointments found for your account.")
    else:
        st.write("Here are your appointments:")
        for idx, appt in enumerate(my_appointments):
            # Use .get() to safely access dictionary keys, providing a default if not found
            appt_date = appt.get('Date', 'N/A')
            appt_time = appt.get('Time', 'N/A')
            appt_status = appt.get('Status', 'N/A')
            appt_id = appt.get('appointmentID', f"appt_{idx}") # Use a fallback ID for keys

            st.markdown(f"---")
            st.write(f"**Appointment ID:** {appt_id}")
            st.write(f"**Date:** {appt_date}")
            st.write(f"**Time:** {appt_time}")
            st.write(f"**Status:** {appt_status}")

            # Reschedule and Cancel buttons
            # Ensure unique keys for buttons, especially when iterating
            reschedule_key = f"reschedule_{appt_id}_{idx}"
            cancel_key = f"cancel_{appt_id}_{idx}"

            col1, col2 = st.columns(2) # Use columns for better layout

            with col1:
                if st.button(f"Reschedule", key=reschedule_key):
                    st.session_state[f'reschedule_active_{appt_id}'] = True
                    st.session_state[f'cancel_active_{appt_id}'] = False # Deactivate cancel if reschedule is clicked
                    st.experimental_rerun() # Rerun to show date/time pickers

            with col2:
                if st.button(f"Cancel", key=cancel_key):
                    st.session_state[f'cancel_active_{appt_id}'] = True
                    st.session_state[f'reschedule_active_{appt_id}'] = False # Deactivate reschedule if cancel is clicked
                    st.experimental_rerun() # Rerun to confirm cancellation

            # Reschedule form
            if st.session_state.get(f'reschedule_active_{appt_id}', False):
                st.markdown(f"**Reschedule Appointment {appt_id}:**")
                new_date = st.date_input(f"Select new date for {appt_id}", value=pd.to_datetime(appt_date) if appt_date != 'N/A' else None, key=f"new_date_{appt_id}_{idx}")
                new_time = st.selectbox(f"Select new time for {appt_id}", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"], index=["9:00AM", "11:00AM", "2:00PM", "4:00PM"].index(appt_time) if appt_time != 'N/A' and appt_time in ["9:00AM", "11:00AM", "2:00PM", "4:00PM"] else 0, key=f"new_time_{appt_id}_{idx}")
                if st.button(f"Confirm Reschedule for {appt_id}", key=f"confirm_reschedule_{appt_id}_{idx}"):
                    update_appointment_status(appt_id, "Rescheduled", str(new_date), new_time)
                    st.success(f"Appointment {appt_id} rescheduled to {new_date} at {new_time}. Status: Pending Confirmation.")
                    st.session_state[f'reschedule_active_{appt_id}'] = False # Hide form after submission
                    st.experimental_rerun()

            # Cancel confirmation
            if st.session_state.get(f'cancel_active_{appt_id}', False):
                st.warning(f"Are you sure you want to cancel appointment {appt_id}?")
                col_cancel_yes, col_cancel_no = st.columns(2)
                with col_cancel_yes:
                    if st.button(f"Yes, Cancel {appt_id}", key=f"confirm_cancel_{appt_id}_{idx}"):
                        update_appointment_status(appt_id, "Cancelled")
                        st.success(f"Appointment {appt_id} cancelled successfully!")
                        st.session_state[f'cancel_active_{appt_id}'] = False # Hide form after submission
                        st.experimental_rerun()
                with col_cancel_no:
                    if st.button(f"No, Keep {appt_id}", key=f"deny_cancel_{appt_id}_{idx}"):
                        st.session_state[f'cancel_active_{appt_id}'] = False # Hide form
                        st.experimental_rerun()

        st.dataframe(df_schedule[['Date', 'Time', 'Status']]) # Display relevant columns
        # Optional: Allow pharmacist to mark a slot as "Unavailable" if needed
        st.markdown("---")
        st.write("Mark a slot as Unavailable:")
        slot_options = [f"{s['Date']} {s['Time']} ({s['Status']})" for s in pharmacist_slots if s['Status'] == "Available"]
        if slot_options:
            selected_slot_str = st.selectbox("Select slot to mark as Unavailable", slot_options)
            if st.button("Mark as Unavailable"):
                # Find the ScheduleID for the selected slot
                selected_slot_parts = selected_slot_str.split(' ')
                selected_date = selected_slot_parts[0]
                selected_time = selected_slot_parts[1]
                slot_to_update_id = None
                for slot in pharmacist_slots:
                    if (slot.get('Date') == selected_date and
                        slot.get('Time') == selected_time and
                        slot.get('Status') == "Available"):
                        slot_to_update_id = slot.get('ScheduleID')
                        break
                if slot_to_update_id:
                    update_schedule_slot_status(slot_to_update_id, "Unavailable")
                    st.success(f"Slot {selected_date} {selected_time} marked as Unavailable.")
                    st.experimental_rerun()
                else:
                    st.error("Could not find the selected slot or it's not available.")
        else:
            st.info("No available slots to mark as unavailable.")
        st.dataframe(df_schedule[['Date', 'Time', 'Status']]) # Display relevant columns
        # Optional: Allow pharmacist to mark a slot as "Unavailable" if needed
        st.markdown("---")
        st.write("Mark a slot as Unavailable:")
        slot_options = [f"{s['Date']} {s['Time']} ({s['Status']})" for s in pharmacist_slots if s['Status'] == "Available"]
        if slot_options:
            selected_slot_str = st.selectbox("Select slot to mark as Unavailable", slot_options)
            if st.button("Mark as Unavailable"):
                # Find the ScheduleID for the selected slot
                selected_slot_parts = selected_slot_str.split(' ')
                selected_date = selected_slot_parts[0]
                selected_time = selected_slot_parts[1]
                slot_to_update_id = None
                for slot in pharmacist_slots:
                    if (slot.get('Date') == selected_date and
                        slot.get('Time') == selected_time and
                        slot.get('Status') == "Available"):
                        slot_to_update_id = slot.get('ScheduleID')
                        break
                if slot_to_update_id:
                    update_schedule_slot_status(slot_to_update_id, "Unavailable")
                    st.success(f"Slot {selected_date} {selected_time} marked as Unavailable.")
                    st.experimental_rerun()
                else:
                    st.error("Could not find the selected slot or it's not available.")
        else:
            st.info("No available slots to mark as unavailable.")
                        
elif choice == "Logout":
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''
    st.experimental_rerun()
