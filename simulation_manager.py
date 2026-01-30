# simulation_manager.py
import pandas as pd
import joblib
from scheduler_engine import EnterpriseScheduler
from hospital_config import ROOMS, SURGEONS, EQUIPMENT, EMERGENCY_RESERVE_ROOM, EMERGENCY_RESERVE_SURGEONS

class HospitalSystem:
    def __init__(self):
        # Filter out emergency reserves from regular scheduling
        self.regular_rooms = [r for r in ROOMS if r['id'] != EMERGENCY_RESERVE_ROOM['id']]
        self.regular_surgeons = {k: v for k, v in SURGEONS.items() if k not in EMERGENCY_RESERVE_SURGEONS.values()}
        
        self.scheduler = EnterpriseScheduler(self.regular_rooms, self.regular_surgeons, EQUIPMENT)
        self.current_schedule = None
        self.active_patients = [] # Stores full dicts
        
        # Load AI Model
        try:
            self.artifacts = joblib.load("surgery_model_artifacts.pkl")
            self.model = self.artifacts['model']
            print("✅ AI Model Loaded Successfully")
        except:
            print("⚠️ Model not found. Using fallback durations.")
            self.model = None

    def predict_duration(self, patient_row):
        """Uses XGBoost to predict duration based on patient data"""
        if not self.model: return 120 # Fallback
        
        # Prepare input vector (Must match training columns exactly)
        # Input: Age, Gender(0/1), BMI, SurgeryType(0-3), Anesthesia(0/1), ASA, Comorb
        try:
            # We use the encoders saved in artifacts to transform text -> int
            # Inside simulation_manager.py -> predict_duration method
            # Inside simulation_manager.py -> predict_duration method
            input_df = pd.DataFrame([{
                'Age': patient_row['Age'],
                'Gender': self.artifacts['le_gender'].transform([patient_row['Gender']])[0],
                'BMI': patient_row['BMI'],
                'SurgeryType': self.artifacts['le_surgery'].transform([patient_row['SurgeryType']])[0],
                'AnesthesiaType': self.artifacts['le_anesthesia'].transform([patient_row['AnesthesiaType']])[0],
                'ASA_Score': patient_row['ASA_Score'],
                'Has_Comorbidity': patient_row['Has_Comorbidity'] # Direct mapping now!
            }])
            return int(self.model.predict(input_df)[0])
        except Exception as e:
            print(f"Prediction Error for {patient_row['PatientID']}: {e}")
            return 90 # Safe fallback

    def start_day(self, csv_file):
        """1. Load CSV -> 2. AI Predict -> 3. Optimize"""
        df = pd.read_csv(csv_file)
        
        patients_payload = []
        for _, row in df.iterrows():
            # 1. AI Prediction
            pred_duration = self.predict_duration(row)
            
            # 2. Build Patient Object
            p_obj = {
                'id': row['PatientID'],
                'type': row['SurgeryType'],
                'surgeon': row['Surgeon'],
                'duration': pred_duration,
                'asa_score': row['ASA_Score'],
                'needs_c_arm': row.get('Needs_CArm', False),
                'needs_robot': row.get('Needs_Robot', False)
                # ready_time not set = defaults to DAY_START (no extra constraint)
            }
            patients_payload.append(p_obj)
            
        self.active_patients = patients_payload
        
        # 3. Optimize (scheduler already initialized with filtered rooms/surgeons)
        self.current_schedule = self.scheduler.solve(self.active_patients)
        return self.current_schedule

    def handle_start_delay(self, patient_id, delay_mins, current_time_str):
        """
        Handles delayed START time (surgeon/patient is late).
        This is different from duration change - the surgery hasn't started yet.
        
        delay_mins: Minutes to ADD to scheduled start (positive = late, negative = early)
        """
        print(f"⏰ Start Delay: {patient_id} start adjusted by {'+' if delay_mins > 0 else ''}{delay_mins} mins")
        
        h, m = map(int, current_time_str.split(':'))
        current_mins = h * 60 + m
        
        target_p = next((p for p in self.active_patients if p['id'] == patient_id), None)
        
        if target_p:
            # Get the originally scheduled start time
            scheduled_start = 8 * 60  # Default 8 AM
            if self.current_schedule is not None:
                row = self.current_schedule[self.current_schedule['Patient ID'] == patient_id]
                if not row.empty:
                    scheduled_start = row.iloc[0]['start_mins']
            
            # New ready time = scheduled start + delay (but not before current time for positive delays)
            if delay_mins >= 0:
                new_ready_time = max(scheduled_start + delay_mins, current_mins)
            else:
                # For early arrivals, allow earlier start but not before current time
                new_ready_time = max(scheduled_start + delay_mins, current_mins)
            
            target_p['ready_time'] = new_ready_time
            print(f"   New ready time: {new_ready_time//60:02d}:{new_ready_time%60:02d}")
        
        # Re-optimize: Unpin this patient, pin others appropriately
        return self._recalculate_schedule(current_mins, unpin_patient=patient_id)

    def handle_emergency(self, patient_id, added_delay, current_time_hhmm):
        """
        Handles DURATION change (surgery taking longer/shorter than expected).
        Re-optimizes schedule while pinning past events.
        
        added_delay: Can be negative (finished early) or positive (taking longer)
        """
        if added_delay != 0:
            print(f"⏱️ Duration Change: {patient_id} {'+' if added_delay > 0 else ''}{added_delay} mins")
        
        # Convert HH:MM to minutes
        h, m = map(int, current_time_hhmm.split(':'))
        current_mins = h * 60 + m
        
        # 1. Update Duration (ensure minimum 30 mins)
        target_p = next((p for p in self.active_patients if p['id'] == patient_id), None)
        if target_p:
            target_p['duration'] = max(30, target_p['duration'] + added_delay)
            
        # 2. Recalculate with pinning
        return self._recalculate_schedule(current_mins)

    def _recalculate_schedule(self, current_mins, unpin_patient=None):
        """
        Recalculates schedule, pinning past surgeries but allowing future ones to move.
        unpin_patient: If set, this patient won't be pinned even if in the past.
        """
        if self.current_schedule is not None:
            for p in self.active_patients:
                pid = p['id']
                
                # Skip pinning for the specified patient (they're being rescheduled)
                if pid == unpin_patient:
                    p.pop('fixed_start', None)
                    p.pop('fixed_room', None)
                    # ready_time already set by the calling function
                    continue
                
                # Find scheduled start time
                sched_row = self.current_schedule[self.current_schedule['Patient ID'] == pid]
                if sched_row.empty:
                    continue
                
                start_mins = sched_row.iloc[0]['start_mins']
                assigned_room = sched_row.iloc[0]['Room']
                
                if start_mins < current_mins:
                    # STARTED IN PAST -> PIN IT
                    p['fixed_start'] = start_mins
                    p['fixed_room'] = assigned_room
                else:
                    # FUTURE -> FREE TO MOVE (But not before now)
                    p.pop('fixed_start', None)
                    p.pop('fixed_room', None)
                    p['min_start_time'] = current_mins
        
        self.current_schedule = self.scheduler.solve(self.active_patients)
        return self.current_schedule

    def handle_code_red(self, patient_details, current_time_str):
        """
        Emergency bypass: Books directly into Emergency Reserve Room without re-optimization.
        Used for true emergencies that need immediate attention.
        
        patient_details: dict with keys 'id', 'Age', 'Gender', 'BMI', 'SurgeryType', 
                        'AnesthesiaType', 'Has_Comorbidity', 'ASA_Score'
        current_time_str: string like "10:30"
        """
        print(f"🚨 CODE RED: Emergency case {patient_details['id']} - Direct booking initiated")
        
        # 1. Convert Current Time to Minutes (e.g., "10:30" -> 630)
        h, m = map(int, current_time_str.split(':'))
        current_mins = h * 60 + m
        
        # 2. Get Predicted Duration using AI model
        duration = self.predict_duration(patient_details)
        
        # 3. Assign Reserved Resources
        surgery_type = patient_details['SurgeryType']
        assigned_surgeon = EMERGENCY_RESERVE_SURGEONS.get(surgery_type, 'Dr. Grey')  # Default to Dr. Grey
        
        # 4. Calculate end time
        end_mins = current_mins + duration
        
        # 5. Create the Schedule Row
        new_row = {
            "Patient ID": patient_details['id'],
            "Type": surgery_type,
            "Surgeon": assigned_surgeon,
            "Room": EMERGENCY_RESERVE_ROOM['name'],
            "Start Time": f"{current_mins//60:02d}:{current_mins%60:02d}",
            "End Time": f"{end_mins//60:02d}:{end_mins%60:02d}",
            "Duration": duration,
            "start_mins": current_mins,
            "end_mins": end_mins,
            "Risk (ASA)": patient_details.get('ASA_Score', 3)  # Emergency cases are typically high risk
        }
        
        # 6. Append to existing schedule
        if self.current_schedule is None:
            self.current_schedule = pd.DataFrame([new_row])
        else:
            self.current_schedule = pd.concat([self.current_schedule, pd.DataFrame([new_row])], ignore_index=True)
        
        # Sort by start time for proper visualization
        self.current_schedule = self.current_schedule.sort_values('start_mins').reset_index(drop=True)
        
        print(f"✅ Emergency booked: {patient_details['id']} in {EMERGENCY_RESERVE_ROOM['name']} at {current_time_str}")
        return self.current_schedule