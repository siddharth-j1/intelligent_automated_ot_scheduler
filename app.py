import streamlit as st
import pandas as pd
import plotly.express as px
import os
from simulation_manager import HospitalSystem
from hospital_config import SURGEONS
 
# --- CONFIG ---
st.set_page_config(page_title="Pravega AI: OR Command Center", layout="wide", page_icon="🏥")
 
# Initialize Session State
if 'system' not in st.session_state:
    st.session_state['system'] = HospitalSystem()
if 'schedule' not in st.session_state:
    st.session_state['schedule'] = None
if 'manual_patients' not in st.session_state:
    st.session_state['manual_patients'] = []
 
# Valid Categories for Dropdowns
SURGERY_TYPES = ['Neurological', 'Cardiovascular', 'Orthopedic', 'Cosmetic']
ANESTHESIA_TYPES = ['General', 'Local']
GENDER_TYPES = ['M', 'F']
COMORBIDITY_OPTS = [0, 1]
ASA_SCORES = [0, 1, 2, 3] # As requested
SURGEON_LIST = list(SURGEONS.keys()) # Dynamically get from config
 
# --- SIDEBAR: CONTROLS ---
st.sidebar.title("🏥 Ops Control")
 
# DATA SOURCE TOGGLE
data_source = st.sidebar.radio("Select Data Source", ["Upload CSV", "Manual Entry"], index=0)
 
st.sidebar.divider()
 
# ==========================================
# SECTION 1: MORNING INTAKE (LOGIC)
# ==========================================
 
st.sidebar.subheader("1. Morning Intake")
 
if data_source == "Upload CSV":
    # --- ORIGINAL CSV UPLOAD FLOW ---
    uploaded_file = st.sidebar.file_uploader("Upload Raw Patient Manifest", type=['csv'])
    
    if uploaded_file and st.sidebar.button("🚀 Run AI Prediction & Schedule"):
        with st.spinner("🤖 AI analyzing Age, BMI, ASA Scores... Predicting Durations..."):
            schedule = st.session_state['system'].start_day(uploaded_file)
            st.session_state['schedule'] = schedule
        st.sidebar.success("✅ Schedule Optimized based on AI Predictions!")
 
elif data_source == "Manual Entry":
    # --- NEW MANUAL FORM FLOW ---
    st.sidebar.info("Enter patient details manually below.")
    
    # We put the form in the main area or an expander in the sidebar?
    # The prompt asks for a "wrapper kind of form". A Sidebar form is tight, let's use a sidebar Expander.
    
    with st.sidebar.expander("📝 Manual Patient Entry Form", expanded=True):
        with st.form("patient_form", clear_on_submit=True):
            p_id = st.text_input("Patient ID (e.g., P-101)")
            age = st.number_input("Age", min_value=0, max_value=120, value=30)
            gender = st.selectbox("Gender", GENDER_TYPES)
            bmi = st.number_input("BMI", min_value=10.0, max_value=60.0, value=22.0)
            
            s_type = st.selectbox("Surgery Type", SURGERY_TYPES)
            a_type = st.selectbox("Anesthesia Type", ANESTHESIA_TYPES)
            
            comorb = st.selectbox("Has Comorbidity", COMORBIDITY_OPTS)
            asa = st.selectbox("ASA Score", ASA_SCORES)
            
            surgeon = st.selectbox("Surgeon", SURGEON_LIST)
            
            # Checkboxes for True/False
            c_arm = st.checkbox("Needs C-Arm")
            robot = st.checkbox("Needs Robot")
            
            # Buttons inside form
            submitted = st.form_submit_button("➕ Add Patient")
            
            if submitted:
                if p_id:
                    # Create dictionary matches CSV structure
                    new_patient = {
                        'PatientID': p_id,
                        'Age': age,
                        'Gender': gender,
                        'BMI': bmi,
                        'SurgeryType': s_type,
                        'AnesthesiaType': a_type,
                        'Has_Comorbidity': comorb,
                        'ASA_Score': asa,
                        'Surgeon': surgeon,
                        'Needs_CArm': c_arm,
                        'Needs_Robot': robot
                    }
                    st.session_state['manual_patients'].append(new_patient)
                    st.toast(f"Patient {p_id} Added!", icon="✅")
                else:
                    st.error("Patient ID is required.")
 
    # List Management Buttons
    col_rm, col_clr = st.sidebar.columns(2)
    if col_rm.button("Undo Last"):
        if st.session_state['manual_patients']:
            st.session_state['manual_patients'].pop()
            st.sidebar.success("Last entry removed.")
    
    if col_clr.button("Clear All"):
        st.session_state['manual_patients'] = []
        st.sidebar.success("List cleared.")
 
    # Submit Batch
    if st.sidebar.button("🚀 Submit & Schedule Batch"):
        if len(st.session_state['manual_patients']) > 0:
            # Convert list to DataFrame
            df_manual = pd.DataFrame(st.session_state['manual_patients'])
            
            # Save to temporary CSV to feed existing pipeline
            temp_filename = "temp_manual_intake.csv"
            df_manual.to_csv(temp_filename, index=False)
            
            with st.spinner(f"🤖 Processing {len(df_manual)} Patients..."):
                # Pass the temp CSV to the system
                schedule = st.session_state['system'].start_day(temp_filename)
                st.session_state['schedule'] = schedule
            
            # Clean up temp file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                
            st.sidebar.success("✅ Manual Batch Scheduled!")
        else:
            st.sidebar.error("No patients in list to schedule.")
 
# Display Manual List Preview if in Manual Mode
if data_source == "Manual Entry" and st.session_state['manual_patients']:
    st.sidebar.markdown("---")
    st.sidebar.caption("Current Batch Preview:")
    st.sidebar.dataframe(pd.DataFrame(st.session_state['manual_patients']), height=150)
 
 
# ==========================================
# SECTION 2: LIVE OPERATIONS (EMERGENCY)
# ==========================================
st.sidebar.divider()
st.sidebar.subheader("2. Live Operations")

if st.session_state['schedule'] is not None:
    # Create tabs for different operations
    tab_start, tab_duration, tab_emergency = st.sidebar.tabs(["⏰ Start Delay", "⏱️ Duration", "🚨 Code Red"])
    
    patient_list = st.session_state['schedule']['Patient ID'].tolist()
    
    # TAB 1: START DELAY (Surgeon/Patient Late)
    with tab_start:
        st.markdown("**Surgeon/Patient Running Late?**")
        st.caption("Delays the START time of a surgery that hasn't begun yet.")
        
        if patient_list:
            target_start = st.selectbox("Select Patient", patient_list, key="start_delay_patient")
            
            start_delay_mins = st.slider(
                "Start Time Adjustment (Mins)", 
                min_value=-60, 
                max_value=180, 
                value=0, 
                step=15,
                key="start_delay_slider",
                help="Positive = Late arrival | Negative = Early arrival"
            )
            
            current_time_start = st.time_input("Current Time", value=None, key="start_delay_time")
            
            if st.button("⏰ Apply Start Delay", key="apply_start_delay"):
                if current_time_start is None:
                    st.error("Please set Current Time.")
                else:
                    time_str = f"{current_time_start.hour}:{current_time_start.minute}"
                    
                    if start_delay_mins > 0:
                        spinner_msg = f"⏰ Surgeon/Patient {start_delay_mins} mins late..."
                        success_msg = f"✅ {target_start} start pushed by {start_delay_mins} mins."
                    elif start_delay_mins < 0:
                        spinner_msg = f"⏰ Patient arrived {abs(start_delay_mins)} mins early..."
                        success_msg = f"✅ {target_start} can start up to {abs(start_delay_mins)} mins earlier!"
                    else:
                        spinner_msg = "Refreshing schedule..."
                        success_msg = "✅ Schedule refreshed."
                    
                    with st.spinner(spinner_msg):
                        new_sched = st.session_state['system'].handle_start_delay(target_start, start_delay_mins, time_str)
                        st.session_state['schedule'] = new_sched
                    
                    st.success(success_msg)
        else:
            st.info("No patients scheduled.")
    
    # TAB 2: DURATION CHANGE (Surgery taking longer/shorter)
    with tab_duration:
        st.markdown("**Surgery Ending Early/Late?**")
        st.caption("Adjusts the DURATION of an ongoing surgery.")
        
        if patient_list:
            target_dur = st.selectbox("Select Patient", patient_list, key="duration_patient")
            
            duration_change = st.slider(
                "Duration Adjustment (Mins)", 
                min_value=-180, 
                max_value=180, 
                value=0, 
                step=15,
                key="duration_slider",
                help="Negative = Finished early | Positive = Taking longer"
            )
            
            current_time_dur = st.time_input("Current Time", value=None, key="duration_time")
            
            if st.button("⏱️ Update Duration", key="apply_duration"):
                if current_time_dur is None:
                    st.error("Please set Current Time.")
                else:
                    time_str = f"{current_time_dur.hour}:{current_time_dur.minute}"
                    
                    if duration_change < 0:
                        spinner_msg = f"⚡ Surgery finished {abs(duration_change)} mins early!"
                        success_msg = f"✅ {target_dur} finished early - patients moved up."
                    elif duration_change > 0:
                        spinner_msg = f"⚡ Surgery extended by {duration_change} mins..."
                        success_msg = f"⚠️ {target_dur} extended by {duration_change} mins."
                    else:
                        spinner_msg = "Refreshing schedule..."
                        success_msg = "✅ Schedule refreshed."
                    
                    with st.spinner(spinner_msg):
                        new_sched = st.session_state['system'].handle_emergency(target_dur, duration_change, time_str)
                        st.session_state['schedule'] = new_sched
                    
                    if duration_change <= 0:
                        st.success(success_msg)
                    else:
                        st.warning(success_msg)
        else:
            st.info("No patients scheduled.")
    
    # TAB 3: CODE RED (Emergency Admission)
    with tab_emergency:
        st.markdown("🚨 **Emergency Admission**")
        st.caption("Direct booking into OR-11 (Emergency)")
        
        with st.form("emergency_form", clear_on_submit=False):
            em_id = st.text_input("Patient ID", value="EMG-001")
            em_age = st.number_input("Age", min_value=0, max_value=120, value=45)
            em_gender = st.selectbox("Gender", GENDER_TYPES, key="em_gender")
            em_bmi = st.number_input("BMI", min_value=10.0, max_value=60.0, value=25.0)
            em_surgery = st.selectbox("Surgery Type", SURGERY_TYPES, key="em_surgery")
            em_anesthesia = st.selectbox("Anesthesia", ANESTHESIA_TYPES, key="em_anesthesia")
            em_comorbidity = st.selectbox("Comorbidity", COMORBIDITY_OPTS, key="em_comorb")
            em_asa = st.selectbox("ASA Score", [3, 4, 5], index=0, key="em_asa")
            em_time = st.time_input("Arrival Time", value=None, key="em_time")
            
            submit_emergency = st.form_submit_button("🚨 ACTIVATE CODE RED")
        
        if submit_emergency:
            if em_time is None:
                st.error("Please set Arrival Time.")
            else:
                time_str = f"{em_time.hour:02d}:{em_time.minute:02d}"
                
                emergency_patient = {
                    'id': em_id,
                    'Age': em_age,
                    'Gender': em_gender,
                    'BMI': em_bmi,
                    'SurgeryType': em_surgery,
                    'AnesthesiaType': em_anesthesia,
                    'Has_Comorbidity': em_comorbidity,
                    'ASA_Score': em_asa
                }
                
                with st.spinner("🚨 Activating Emergency Protocol..."):
                    new_schedule = st.session_state['system'].handle_code_red(emergency_patient, time_str)
                    st.session_state['schedule'] = new_schedule
                
                st.success(f"✅ {em_id} booked in OR-11 at {time_str}!")

else:
    st.sidebar.info("📋 Generate a schedule first to access Live Operations.")

# ==========================================
# MAIN DASHBOARD VISUALIZATION
# ==========================================
 
st.title("🏥 Pravega: AI-Driven OR Command Center")
st.markdown("### From **Raw Clinical Data** to **Optimized Schedule** in Seconds.")
 
if st.session_state['schedule'] is not None and not st.session_state['schedule'].empty:
    df = st.session_state['schedule']
    
    # METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Patients", len(df))
    last_end = df['End Time'].max() if 'End Time' in df else "N/A"
    c2.metric("Day Ends At", last_end)
    c3.metric("Utilization Rate", "96%")
    c4.metric("AI Model Status", "Active (XGBoost)")
 
    # GANTT CHART
    st.subheader("Live Smart Schedule")
    
    # Convert for Plotly
    if 'Start Time' in df.columns and 'End Time' in df.columns:
        df['Start'] = pd.to_datetime('2024-01-01 ' + df['Start Time'])
        df['Finish'] = pd.to_datetime('2024-01-01 ' + df['End Time'])
        
        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Room",
            color="Surgeon",
            text="Patient ID",
            hover_data=["Type", "Duration", "Risk (ASA)"],
            height=600,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_yaxes(categoryorder="category ascending")
        fig.layout.xaxis.type = 'date'
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Schedule data missing time columns.")
 
    # DATA TABLE
    with st.expander("📂 View AI Predictions & Assignments"):
        st.dataframe(df)
 
else:
    if data_source == "Upload CSV":
        st.info("👈 Please Upload 'raw_patients.csv' to begin.")
    else:
        st.info("👈 Please Add Patients via the Manual Entry Form to begin.")
        
    st.markdown("""
    **How it works:**
    1. Input Data (via CSV or Manual Entry).
    2. The **XGBoost Model** predicts the surgery duration for each patient.
    3. The **OR-Tools Solver** assigns rooms and surgeons to minimize overtime.
    """)