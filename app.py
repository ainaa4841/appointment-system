import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity, get_customer_id
from google_sheets import (
    save_customer, upload_to_drive, save_appointment,
    get_appointments, get_pharmacist_schedule,
    update_schedule, update_appointment_status,
    get_all_customers,  save_report
)
import os
import pandas as pd
from collections import defaultdict

st.set_page_config(page_title="Farmasi Pantai Hillpark", layout="wide")

# Load CSS
with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("Farmasi Pantai Hillpark Appointment System")

# Session defaults
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''

menu = ["Login", "Register"]
if st.session_state.logged_in:
    menu = ["Logout"]
    if st.session_state.user_role == 'Customer':
        menu = ["Book Appointment", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        menu = ["Manage Schedule", "Update Slot Availability", "Add Report", "Logout"]

choice = st.sidebar.selectbox("Menu", menu)

# --------------------------------------------
# Register
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
            st.error("Password must be at least 8 characters and contain a special character.")
        elif check_email_exists(email):
            st.error("Email already exists. Please use a different email or login.")
        else:
            register_user(username, password, "Customer", email)
            customer_id = save_customer([username, password, full_name, email, phone, ""])
            st.success(f"Registration successful! Your customer ID is {customer_id}. Please log in.")

# --------------------------------------------
# Login
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
            st.rerun()
        else:
            st.error("Invalid credentials!")

# --------------------------------------------
# Book Appointment
elif choice == "Book Appointment":
    st.subheader("Book an Appointment")
    available_schedule = get_pharmacist_schedule()
    if not available_schedule:
        st.warning("No available slots. Please try again later.")
    else:
        available_dates = sorted(set(slot["Date"] for slot in available_schedule))
        selected_date = st.selectbox("Select Date", available_dates)
        available_times = [slot["Time"] for slot in available_schedule if slot["Date"] == selected_date]
        selected_time = st.selectbox("Select Time Slot", available_times)
        uploaded_file = st.file_uploader("Upload Referral Letter")

        if st.button("Book Appointment"):
            if not uploaded_file:
                st.error("Please upload a referral letter.")
            else:
                if not os.path.exists("uploads"):
                    os.makedirs("uploads")

                # Save the uploaded file locally
                file_path = f"uploads/{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Save appointment with referral path
                save_appointment([
                    st.session_state.customer_id,
                    selected_date,
                    selected_time,
                    "Pending Confirmation"
                ], referral_path=file_path)

                st.success(f"Appointment booked on {selected_date} at {selected_time}.")



# --------------------------------------------
# My Appointments
elif choice == "My Appointments":
    st.subheader("📋 My Appointments")

    appointments = get_appointments()
    my_appointments = [
        appt for appt in appointments
        if str(appt.get('customerID')) == str(st.session_state.customer_id)
    ]

    if not my_appointments:
        st.info("No appointments found.")
    else:
        active_appts = [appt for appt in my_appointments if appt['Status'] in ["Pending Confirmation", "Confirmed", "Rescheduled"]]
        past_appts = [appt for appt in my_appointments if appt['Status'] in ["Cancelled", "Completed"]]

        # --------------------
        # Section 1: Active
        st.markdown("### 🗓️ Upcoming Appointments")
        for idx, appt in enumerate(active_appts):
            cols = st.columns([2, 2, 2, 2, 2])
            cols[0].write(f"📅 **{appt['Date']}**")
            cols[1].write(f"🕒 **{appt['Time']}**")
            cols[2].write(f"📌 **{appt['Status']}**")

            # RESCHEDULE BUTTON
            if cols[3].button("Reschedule", key=f"reschedule_{idx}"):
                with st.form(f"reschedule_form_{idx}"):
                    st.subheader(f"Reschedule Slot for {appt['Date']} {appt['Time']}")
                    schedule = get_pharmacist_schedule()
                    booked = [(a['Date'], a['Time']) for a in get_appointments()]
                    available_slots = [
                        s for s in schedule if (s['Date'], s['Time']) not in booked
                    ]

                    dates = sorted(list(set([s['Date'] for s in available_slots])))
                    new_date = st.selectbox("New Date", dates)
                    new_times = [s['Time'] for s in available_slots if s['Date'] == new_date]
                    new_time = st.selectbox("New Time", new_times)

                    submitted = st.form_submit_button("Confirm Reschedule")
                    if submitted:
                        update_appointment_status(
                            appointment_id=appt["appointmentID"],
                            new_status="Rescheduled",
                            new_date=new_date,
                            new_time=new_time
                        )
                        st.success("Rescheduled successfully!")
                        st.rerun()

            # CANCEL BUTTON
            if cols[4].button("❌ Cancel", key=f"cancel_{idx}"):
                update_appointment_status(
                    appointment_id=appt["appointmentID"],
                    new_status="Cancelled"
                )
                st.success("❌ Appointment cancelled.")
                st.rerun()

        # --------------------
        # Section 2: Past Appointments
        if past_appts:
            st.markdown("---")
            st.markdown("### 📋 Past Appointments (Cancelled or Completed)")

            header = st.columns([2, 2, 2])
            header[0].markdown("**📅 Date**")
            header[1].markdown("**🕒 Time**")
            header[2].markdown("**📌 Status**")

            for appt in past_appts:
                row = st.columns([2, 2, 2])
                row[0].write(f"{appt['Date']}")
                row[1].write(f"{appt['Time']}")
                row[2].write(f"{appt['Status']}")


# --------------------------------------------
# Manage Schedule
elif choice == "Manage Schedule":
    st.subheader("Pharmacist: Manage Appointments & Availability")

    appointments = get_appointments()
    customers = {str(c["customerID"]): c for c in get_all_customers()}

    if not appointments:
        st.info("No appointments found.")
    else:
        # Split appointments by status
        active_appointments = [a for a in appointments if a["Status"] in ["Pending Confirmation", "Confirmed"]]
        inactive_appointments = [a for a in appointments if a["Status"] in ["Cancelled", "Completed"]]

        # ----------------------
        # Section 1: Active Appointments
        st.markdown("### 📋 Active Appointments (Pending / Confirmed)")
        for idx, appt in enumerate(active_appointments):
            cust = customers.get(str(appt["customerID"]), {})
            full_name = cust.get("Full Name", "Unknown")
            email = cust.get("Email", "N/A")
            phone = cust.get("Phone Number", "N/A")
            referral_path = appt.get("appointmentReferralLetter", "")

            st.markdown(f"""
                <div style="border: 1px solid #ccc; padding: 1px; border-radius: 6px; margin-bottom: 10px; background-color: #f9f9f9;">
            """, unsafe_allow_html=True)
            
            cols = st.columns([1, 2, 2, 1.5, 1.5, 2, 2])
            cols[0].write(f"🆔 {appt['appointmentID']}")
            cols[1].write(f"👤 {full_name}")
            cols[2].write(f"📧 {email}\n\n📱 {phone}")
            cols[3].write(f"📅 {appt['Date']}")
            cols[4].write(f"🕒 {appt['Time']}")

            # 📄 Referral download button
            if referral_path and os.path.exists(referral_path):
                with open(referral_path, "rb") as f:
                    cols[5].download_button(
                        label="📄 Download Letter",
                        data=f,
                        file_name=os.path.basename(referral_path),
                        mime="application/octet-stream",
                        key=f"download_{idx}"
                    )
            else:
                cols[5].write("—")

            # ✅ Update status
            new_status = cols[6].selectbox(
                "Status",
                ["Pending Confirmation", "Confirmed", "Cancelled", "Completed"],
                index=["Pending Confirmation", "Confirmed", "Cancelled", "Completed"].index(appt["Status"]),
                key=f"status_{idx}"
            )

            if st.button("Update", key=f"update_{idx}"):
                update_appointment_status(appt["appointmentID"], new_status)
                st.success(f"✅ Appointment {appt['appointmentID']} updated.")
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        # --------------------
        # Section 2: Past Appointments
        past_appts = [appt for appt in appointments if appt["Status"] in ["Cancelled", "Completed"]]

        if past_appts:
            st.markdown("---")
            st.markdown("### 📋 Past Appointments (Cancelled or Completed)")

            # Build customer lookup to fetch name/email/phone
            customers = {str(c["customerID"]): c for c in get_all_customers()}
            

            # Header
            header = st.columns([1, 2, 2, 1.5, 1.5, 2, 1.5])
            header[0].markdown("**🆔 ID**")
            header[1].markdown("**👤 Name**")
            header[2].markdown("**📧 Contact**")
            header[3].markdown("**📅 Date**")
            header[4].markdown("**🕒 Time**")
            header[6].markdown("**📌 Status**")
            
            for appt in past_appts:
                cust = customers.get(str(appt["customerID"]), {})
                full_name = cust.get("Full Name", "Unknown")
                email = cust.get("Email", "N/A")
                phone = cust.get("Phone Number", "N/A")
                referral_link = appt.get("appointmentReferralLetter", "")

                st.markdown(f"""
                <div style="border: 1px solid #ccc; padding: 1px; border-radius: 6px; margin-bottom: 10px; background-color: #f9f9f9;">
            """, unsafe_allow_html=True)
                cols = st.columns([1, 2, 2, 1.5, 1.5, 2, 1.5])
                cols[0].write(f"{appt['appointmentID']}")
                cols[1].write(f"{full_name}")
                cols[2].markdown(f"{email}<br>{phone}", unsafe_allow_html=True)
                cols[3].write(f"{appt['Date']}")
                cols[4].write(f"{appt['Time']}")
                cols[6].write(f"{appt['Status']}")

# --------------------------------------------
# Update Slot Availability
elif choice == "Update Slot Availability":
    st.subheader("➕ Add New Slot")
    slot_date = st.date_input("Available Date")
    slot_time = st.selectbox("Available Time", ["8:00AM-9:00AM","9:00AM-10:00AM", "10:00AM-11:00AM", "11:00AM-12:00PM","2:00PM-3:00PM", "3:00PM-4:00PM", "4:00PM-5:00PM"])
    schedule = get_pharmacist_schedule()
    if st.button("Add Slot"):
        if any(s["Date"] == str(slot_date) and s["Time"] == slot_time for s in schedule):
            st.warning("Slot already exists.")
        else:
            update_schedule(str(slot_date), slot_time)
            st.success("Slot added!")
            st.rerun()
        st.markdown("---")

    # Calendar display
    st.markdown("### 📌 Available Slots")

    if not schedule:
        st.info("No slots available.")
    else:
        df_slots = pd.DataFrame(schedule)

        for idx, row in df_slots.iterrows():
            cols = st.columns([3, 3, 1])
            cols[0].write(f"📅 Date: **{row['Date']}**")
            cols[1].write(f"🕒 Time: **{row['Time']}**")
            if cols[2].button("❌ Delete", key=f"delete_slot_{idx}"):
                from google_sheets import remove_schedule_slot
                remove_schedule_slot(row['Date'], row['Time'])
                st.success(f"Slot on {row['Date']} at {row['Time']} deleted.")
                st.rerun()


# --------------------------------------------
# Add Report
elif choice == "Add Report":
    st.subheader("Add Appointment Report")
    appt_id = st.text_input("Appointment ID")
    report_date = st.date_input("Report Date")
    content = st.text_area("Report Content")
    if st.button("Save Report"):
        save_report([appt_id, str(report_date), content])
        st.success("Report saved.")

# --------------------------------------------
# Logout
elif choice == "Logout":
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
