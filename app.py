import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity, get_customer_id
from google_sheets import (
    save_customer, save_appointment, save_file_metadata,
    upload_to_drive, get_appointments, get_worksheet_data, # get_pharmacist_schedule removed as it's old
    update_appointment_status, update_customer_referral_letter,
    save_pharmacist_schedule_slot, get_pharmacist_available_slots,
    update_schedule_slot_status, get_all_pharmacist_schedule_slots
)
import os
import pandas as pd # For DataFrame operations and date handling

st.set_page_config(page_title="Farmasi Pantai Hillpark", layout="wide")

# Load custom CSS
try:
    with open("MultipleFiles/style.css") as f: # Adjusted path
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("CSS file not found. Styling might be affected.")

st.title("Farmasi Pantai Hillpark Appointment System")

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''

# Dynamic menu based on login status and role
menu = ["Login", "Register"]
if st.session_state.logged_in:
    if st.session_state.user_role == 'Customer':
        menu = ["Book Appointment", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        menu = ["Manage Pending Appointments", "Set Availability", "View My Schedule", "Logout"]

choice = st.sidebar.selectbox("Menu", menu)

# --- Registration Section ---
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
            # Register user in 'Users' sheet
            register_user(username, password, "Customer", email)
            # Save customer details in 'Customers' sheet
            # Ensure 'Customers' sheet columns match: customerID, username, password, full_name, email, phone, referral_letter_link
            customer_id = save_customer([username, password, full_name, email, phone, ""])
            st.success(f"Registration successful! Your customer ID is {customer_id}. Please log in.")

# --- Login Section ---
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

# --- Book Appointment Section (Customer) ---
elif choice == "Book Appointment":
    st.subheader("Book an Appointment")

    available_slots = get_pharmacist_available_slots()

    if not available_slots:
        st.info("No available appointment slots at the moment. Please check back later.")
    else:
        # Group slots by date for better display
        slots_by_date = {}
        for slot in available_slots:
            date_str = slot['Date']
            if date_str not in slots_by_date:
                slots_by_date[date_str] = []
            slots_by_date[date_str].append(slot)

        # Sort dates
        sorted_dates = sorted(slots_by_date.keys())

        # Create options for the selectbox
        display_options = []
        actual_slot_objects = [] # To store the actual slot dictionaries

        for date_str in sorted_dates:
            # Sort times for each date
            for slot in sorted(slots_by_date[date_str], key=lambda x: x['Time']):
                display_options.append(f"{slot['Date']} at {slot['Time']} (Pharmacist: {slot['PharmacistUsername']})")
                actual_slot_objects.append(slot)

        if not display_options:
            st.info("No available appointment slots at the moment. Please check back later.")
        else:
            selected_option_index = st.selectbox(
                "Select an available date and time slot:",
                options=range(len(display_options)),
                format_func=lambda x: display_options[x],
                key="appointment_slot_selector"
            )

            selected_slot = actual_slot_objects[selected_option_index]
            selected_date = selected_slot['Date']
            selected_time = selected_slot['Time']
            selected_pharmacist_username = selected_slot['PharmacistUsername']
            selected_schedule_id = selected_slot['ScheduleID']

            st.write(f"You have selected: **{selected_date} at {selected_time}** with **{selected_pharmacist_username}**.")

            uploaded_file = st.file_uploader("Upload Referral Letter (PDF, JPG, PNG)", type=["pdf", "jpg", "png"])

            if st.button("Book Appointment"):
                if not uploaded_file:
                    st.error("Please upload a referral letter.")
                else:
                    # 1. Save the uploaded file
                    if not os.path.exists("uploads"):
                        os.makedirs("uploads")

                    file_path = f"uploads/{uploaded_file.name}"
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    file_id = upload_to_drive(file_path)
                    file_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

                    save_file_metadata([st.session_state.user_username, uploaded_file.name, file_id])

                    # 2. Update customer's referral letter link in Customers sheet
                    update_customer_referral_letter(st.session_state.user_username, file_link)

                    # 3. Save the appointment
                    # Ensure your Appointments sheet has columns: appointmentID, customerID, PharmacistUsername, Date, Time, Status, RejectionReason
                    appointment_data = [
                        st.session_state.customer_id,
                        selected_pharmacist_username,
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

# --- My Appointments Section (Customer) ---
elif choice == "My Appointments":
    st.subheader("My Appointments")
    appointments = get_appointments() # This fetches all appointments

    current_customer_id = st.session_state.customer_id
    if not current_customer_id:
        st.warning("Please log in as a customer to view your appointments.")
        my_appointments = []
    else:
        my_appointments = [
            appt for appt in appointments
            if str(appt.get('customerID')) == str(current_customer_id)
        ]

    if not my_appointments:
        st.info("No appointments found for your account.")
    else:
        st.write("Here are your appointments:")
        for idx, appt in enumerate(my_appointments):
            appt_date = appt.get('Date', 'N/A')
            appt_time = appt.get('Time', 'N/A')
            appt_status = appt.get('Status', 'N/A')
            appt_id = appt.get('appointmentID', f"appt_{idx}")
            pharmacist_username = appt.get('PharmacistUsername', 'N/A')
            rejection_reason = appt.get('RejectionReason', '')

            st.markdown(f"---")
            st.write(f"**Appointment ID:** {appt_id}")
            st.write(f"**Pharmacist:** {pharmacist_username}")
            st.write(f"**Date:** {appt_date}")
            st.write(f"**Time:** {appt_time}")
            st.write(f"**Status:** {appt_status}")
            if appt_status == "Rejected" and rejection_reason:
                st.error(f"**Rejection Reason:** {rejection_reason}")

            # Initialize session state for reschedule/cancel forms if not present
            if f'reschedule_active_{appt_id}' not in st.session_state:
                st.session_state[f'reschedule_active_{appt_id}'] = False
            if f'cancel_active_{appt_id}' not in st.session_state:
                st.session_state[f'cancel_active_{appt_id}'] = False

            # Only show buttons if status allows (e.g., not already cancelled/confirmed/rejected)
            if appt_status in ["Pending Confirmation", "Confirmed"]:
                col1, col2 = st.columns(2)

                with col1:
                    if st.button(f"Reschedule", key=f"reschedule_btn_{appt_id}_{idx}"):
                        st.session_state[f'reschedule_active_{appt_id}'] = True
                        st.session_state[f'cancel_active_{appt_id}'] = False
                        st.experimental_rerun()

                with col2:
                    if st.button(f"Cancel", key=f"cancel_btn_{appt_id}_{idx}"):
                        st.session_state[f'cancel_active_{appt_id}'] = True
                        st.session_state[f'reschedule_active_{appt_id}'] = False
                        st.experimental_rerun()

            # Reschedule form
            if st.session_state.get(f'reschedule_active_{appt_id}', False):
                st.markdown(f"**Reschedule Appointment {appt_id}:**")
                # Fetch available slots for rescheduling
                reschedule_available_slots = get_pharmacist_available_slots()
                reschedule_display_options = []
                reschedule_actual_slot_objects = []

                for slot in reschedule_available_slots:
                    reschedule_display_options.append(f"{slot['Date']} at {slot['Time']} (Pharmacist: {slot['PharmacistUsername']})")
                    reschedule_actual_slot_objects.append(slot)

                if not reschedule_display_options:
                    st.info("No available slots for rescheduling at the moment.")
                    if st.button("Close Reschedule", key=f"close_reschedule_{appt_id}_{idx}"):
                        st.session_state[f'reschedule_active_{appt_id}'] = False
                        st.experimental_rerun()
                else:
                    selected_reschedule_option_index = st.selectbox(
                        "Select new date and time slot:",
                        options=range(len(reschedule_display_options)),
                        format_func=lambda x: reschedule_display_options[x],
                        key=f"reschedule_slot_selector_{appt_id}_{idx}"
                    )
                    new_slot = reschedule_actual_slot_objects[selected_reschedule_option_index]
                    new_date = new_slot['Date']
                    new_time = new_slot['Time']
                    new_pharmacist_username = new_slot['PharmacistUsername']
                    new_schedule_id = new_slot['ScheduleID']

                    if st.button(f"Confirm Reschedule for {appt_id}", key=f"confirm_reschedule_{appt_id}_{idx}"):
                        # 1. Update the old appointment status to Rescheduled
                        update_appointment_status(appt_id, "Rescheduled", str(new_date), new_time)

                        # 2. Mark the NEW selected schedule slot as "Booked"
                        update_schedule_slot_status(new_schedule_id, "Booked")

                        # 3. (Optional but recommended) Mark the OLD schedule slot as "Available" again
                        # This requires knowing the ScheduleID of the original booking.
                        # For simplicity here, we're not doing it, but in a real system,
                        # you'd store the ScheduleID in the Appointments sheet when booking.
                        # If you add ScheduleID to Appointments sheet, you can retrieve it here.

                        st.success(f"Appointment {appt_id} rescheduled to {new_date} at {new_time} with {new_pharmacist_username}. Status: Pending Confirmation.")
                        st.session_state[f'reschedule_active_{appt_id}'] = False
                        st.experimental_rerun()

            # Cancel confirmation
            if st.session_state.get(f'cancel_active_{appt_id}', False):
                st.warning(f"Are you sure you want to cancel appointment {appt_id}?")
                col_cancel_yes, col_cancel_no = st.columns(2)
                with col_cancel_yes:
                    if st.button(f"Yes, Cancel {appt_id}", key=f"confirm_cancel_{appt_id}_{idx}"):
                        update_appointment_status(appt_id, "Cancelled")
                        # (Optional but recommended) Mark the corresponding schedule slot as "Available" again
                        # This requires knowing the ScheduleID of the original booking.
                        st.success(f"Appointment {appt_id} cancelled successfully!")
                        st.session_state[f'cancel_active_{appt_id}'] = False
                        st.experimental_rerun()
                with col_cancel_no:
                    if st.button(f"No, Keep {appt_id}", key=f"deny_cancel_{appt_id}_{idx}"):
                        st.session_state[f'cancel_active_{appt_id}'] = False
                        st.experimental_rerun()

# --- Manage Pending Appointments Section (Pharmacist) ---
elif choice == "Manage Pending Appointments":
    st.subheader("Manage Pending Appointments (Pharmacist)")

    appointments = get_appointments()
    # Filter for pending appointments assigned to this pharmacist
    pending_appointments = [
        appt for appt in appointments
        if appt.get('Status') == "Pending Confirmation" and
           appt.get('PharmacistUsername') == st.session_state.user_username
    ]

    if not pending_appointments:
        st.info("No pending appointments to review at this time.")
    else:
        st.write("Review the following pending appointment requests:")
        customers_df = get_worksheet_data("Customers")

        for idx, appt in enumerate(pending_appointments):
            appt_id = appt.get('appointmentID')
            customer_id = appt.get('customerID')
            appt_date = appt.get('Date')
            appt_time = appt.get('Time')
            appt_status = appt.get('Status')

            customer_name = "N/A"
            referral_letter_link = "N/A"
            if not customers_df.empty and customer_id:
                customer_row = customers_df[customers_df['customerID'] == str(customer_id)]
                if not customer_row.empty:
                    customer_name = customer_row['Full Name'].iloc[0]
                    referral_letter_link = customer_row.get('customerReferalLetter', 'N/A').iloc[0]

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

            col_confirm, col_reject = st.columns(2)
            with col_confirm:
                if st.button(f"Confirm {appt_id}", key=f"confirm_appt_{appt_id}_{idx}"):
                    # When confirming, also mark the corresponding schedule slot as "Booked"
                    all_slots = get_all_pharmacist_schedule_slots()
                    found_slot_id = None
                    for slot in all_slots:
                        if (slot.get('PharmacistUsername') == st.session_state.user_username and
                            slot.get('Date') == appt_date and
                            slot.get('Time') == appt_time and
                            slot.get('Status') == "Booked"): # It should already be 'Booked' from customer booking
                            found_slot_id = slot.get('ScheduleID')
                            break

                    if found_slot_id:
                        # No need to update slot status again if it's already 'Booked'
                        update_appointment_status(appt_id, "Confirmed")
                        st.success(f"Appointment {appt_id} confirmed!")
                    else:
                        st.warning(f"Could not find the corresponding booked slot for {appt_date} at {appt_time}. Appointment {appt_id} confirmed but slot status not verified.")
                        update_appointment_status(appt_id, "Confirmed")
                    st.experimental_rerun()

            with col_reject:
                if st.button(f"Reject {appt_id}", key=f"reject_appt_{appt_id}_{idx}"):
                    st.session_state[f'show_rejection_form_{appt_id}'] = True
                    st.experimental_rerun()

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
                        # When rejecting, mark the corresponding schedule slot as "Available" again
                        all_slots = get_all_pharmacist_schedule_slots()
                        found_slot_id = None
                        for slot in all_slots:
                            if (slot.get('PharmacistUsername') == st.session_state.user_username and
                                slot.get('Date') == appt_date and
                                slot.get('Time') == appt_time and
                                slot.get('Status') == "Booked"): # It should be 'Booked' if it was pending
                                found_slot_id = slot.get('ScheduleID')
                                break
                        if found_slot_id:
                            update_schedule_slot_status(found_slot_id, "Available")
                            st.success(f"Appointment {appt_id} rejected and slot marked as available.")
                        else:
                            st.success(f"Appointment {appt_id} rejected. Could not find corresponding slot to free up.")

                        st.session_state[f'show_rejection_form_{appt_id}'] = False
                        st.experimental_rerun()
                    elif cancel_rejection:
                        st.session_state[f'show_rejection_form_{appt_id}'] = False
                        st.experimental_rerun()

# --- Set Availability Section (Pharmacist) ---
elif choice == "Set Availability":
    st.subheader("Set Your Availability (Pharmacist)")
    st.write("Add new time slots when you are available for consultations.")

    with st.form("set_availability_form"):
        available_date = st.date_input("Select Date", key="available_date_input")
        available_time = st.selectbox("Select Time Slot", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"], key="available_time_select")
        submit_availability = st.form_submit_button("Add Available Slot")

        if submit_availability:
            if not available_date or not available_time:
                st.error("Please select both date and time.")
            else:
                all_slots = get_all_pharmacist_schedule_slots()
                is_duplicate = False
                for slot in all_slots:
                    if (slot.get('PharmacistUsername') == st.session_state.user_username and
                        slot.get('Date') == str(available_date) and
                        slot.get('Time') == available_time):
                        is_duplicate = True
                        break

                if is_duplicate:
                    st.warning(f"You have already added availability for {available_date} at {available_time}.")
                else:
                    data_to_save = [
                        st.session_state.user_username,
                        str(available_date),
                        available_time,
                        "Available"
                    ]
                    save_pharmacist_schedule_slot(data_to_save)
                    st.success(f"Availability added for {available_date} at {available_time}.")
                    st.experimental_rerun()

# --- View My Schedule Section (Pharmacist) ---
elif choice == "View My Schedule":
    st.subheader("My Schedule (Pharmacist)")
    st.write("Here you can view all your scheduled and available time slots.")

    my_schedule_slots = get_all_pharmacist_schedule_slots()
    pharmacist_slots = [
        slot for slot in my_schedule_slots
        if slot.get('PharmacistUsername') == st.session_state.user_username
    ]

    if not pharmacist_slots:
        st.info("You have not set any availability yet.")
    else:
        df_schedule = pd.DataFrame(pharmacist_slots)
        df_schedule['Date'] = pd.to_datetime(df_schedule['Date']) # Convert to datetime for proper sorting
        df_schedule = df_schedule.sort_values(by=['Date', 'Time'])
        df_schedule['Date'] = df_schedule['Date'].dt.strftime('%Y-%m-%d') # Convert back to string for display
        st.dataframe(df_schedule[['Date', 'Time', 'Status']])

        st.markdown("---")
        st.write("Mark a slot as Unavailable:")
        # Filter for slots that are currently 'Available' or 'Booked' to allow marking as 'Unavailable'
        markable_slots = [s for s in pharmacist_slots if s['Status'] in ["Available", "Booked"]]
        slot_options = [f"{s['Date']} {s['Time']} ({s['Status']})" for s in markable_slots]

        if slot_options:
            selected_slot_str = st.selectbox("Select slot to mark as Unavailable", slot_options, key="mark_unavailable_select")
            if st.button("Mark as Unavailable", key="mark_unavailable_btn"):
                selected_slot_parts = selected_slot_str.split(' ')
                selected_date = selected_slot_parts[0]
                selected_time = selected_slot_parts[1]

                slot_to_update_id = None
                for slot in markable_slots:
                    if (slot.get('Date') == selected_date and
                        slot.get('Time') == selected_time): # Match by date and time
                        slot_to_update_id = slot.get('ScheduleID')
                        break

                if slot_to_update_id:
                    update_schedule_slot_status(slot_to_update_id, "Unavailable")
                    st.success(f"Slot {selected_date} {selected_time} marked as Unavailable.")
                    st.experimental_rerun()
                else:
                    st.error("Could not find the selected slot.")
        else:
            st.info("No available or booked slots to mark as unavailable.")


# --- Logout Section ---
elif choice == "Logout":
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''
    st.experimental_rerun()
