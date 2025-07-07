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

elif choice == "Manage Schedule":
    st.subheader("Manage Appointments (Pharmacist)")

    appointments = get_appointments() # Fetch all appointments
    # Filter for pending appointments
    pending_appointments = [appt for appt in appointments if appt.get('Status') == "Pending Confirmation"]

    if not pending_appointments:
        st.info("No pending appointments to review at this time.")
    else:
        st.write("Review the following pending appointment requests:")
        # Fetch customer data to display customer names
        customers_df = get_worksheet_data("Customers") # Assuming a function to get Customers sheet data

        for idx, appt in enumerate(pending_appointments):
            appt_id = appt.get('appointmentID')
            customer_id = appt.get('customerID')
            appt_date = appt.get('Date')
            appt_time = appt.get('Time')
            appt_status = appt.get('Status')

            customer_name = "N/A"
            referral_letter_link = "N/A"
            if not customers_df.empty and customer_id:
                # Find customer details using customerID
                customer_row = customers_df[customers_df['customerID'] == str(customer_id)]
                if not customer_row.empty:
                    customer_name = customer_row['Full Name'].iloc[0] # Assuming 'Full Name' column
                    referral_letter_link = customer_row.get('customerReferalLetter', 'N/A').iloc[0] # Assuming 'customerReferalLetter' column

            st.markdown(f"---")
            st.write(f"**Appointment ID:** {appt_id}")
            st.write(f"**Customer Name:** {customer_name}")
            st.write(f"**Requested Date:** {appt_date}")
            st.write(f"**Requested Time:** {appt_time}")
            st.write(f"**Current Status:** {appt_status}")

            if referral_letter_link and referral_letter_link != 'N/A':
                st.markdown(f"**Referral Letter:** [View Letter]({referral_letter_link})")
            else:
                st.write("**Referral Letter:** Not provided or link unavailable.")

            # Buttons for Confirm/Reject
            col_confirm, col_reject = st.columns(2)
            with col_confirm:
                if st.button(f"Confirm {appt_id}", key=f"confirm_{appt_id}_{idx}"):
                    update_appointment_status(appt_id, "Confirmed")
                    st.success(f"Appointment {appt_id} confirmed successfully!")
                    st.experimental_rerun()

            with col_reject:
                if st.button(f"Reject {appt_id}", key=f"reject_{appt_id}_{idx}"):
                    st.session_state[f'show_rejection_form_{appt_id}'] = True
                    st.experimental_rerun()

            # Rejection form (shown only if reject button is clicked)
            if st.session_state.get(f'show_rejection_form_{appt_id}', False):
                with st.form(key=f"rejection_form_{appt_id}_{idx}"):
                    rejection_reason = st.text_area(
                        f"Reason for rejecting appointment {appt_id} (optional):",
                        key=f"reason_input_{appt_id}_{idx}"
                    )
                    col_submit_reject, col_cancel_reject = st.columns(2)
                    with col_submit_reject:
                        submit_rejection = st.form_submit_button(f"Submit Rejection for {appt_id}")
                    with col_cancel_reject:
                        cancel_rejection = st.form_submit_button(f"Cancel")

                    if submit_rejection:
                        update_appointment_status(appt_id, "Rejected", rejection_reason=rejection_reason)
                        st.success(f"Appointment {appt_id} rejected successfully!")
                        st.session_state[f'show_rejection_form_{appt_id}'] = False # Hide form
                        st.experimental_rerun()
                    elif cancel_rejection:
                        st.session_state[f'show_rejection_form_{appt_id}'] = False # Hide form
                        st.experimental_rerun()

                        
elif choice == "Logout":
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''
    st.experimental_rerun()
