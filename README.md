
#  Intelligent Automated OT Scheduler (Team Omega)

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![OR-Tools](https://img.shields.io/badge/Optimization-Google%20OR--Tools-orange.svg)](https://developers.google.com/optimization)

An advanced AI-driven coordination engine designed to solve the NP-hard problem of **Operating Theatre (OT) scheduling**. This solution was developed to replace manual heuristics with mathematical optimization and machine learning.

##  The Problem
Hospital scheduling is a "Silent Crisis." Re-optimizing a schedule in real-time when a surgery runs late or an emergency arrives is an **NP-Hard problem**. Manual methods lead to:
* **Resource Underutilization:** Empty OTs while patients wait.
* **The Domino Effect:** One delay in the morning cancelling five surgeries in the afternoon.
* **Staff Burnout:** Unpredictable overtime and "hurry up and wait" scenarios.

##  Our Solution: The "Self-Healing" Schedule
Our system provides a multidimensional constraint satisfaction engine that aligns **Time, Space (12 OTs), and Human Resources (Surgeons)** simultaneously.

### Key Technical Pillars:
1.  **AI-Powered Predictions:** Uses a Random Forest model to predict surgery durations based on patient risk (ASA score) and procedure type, rather than using static averages.
2.  **Constraint Programming (CP-SAT):** Utilizes Google OR-Tools to solve the complex alignment of surgeons and rooms.
3.  **Code Red Emergency Handling:** A dedicated feature that instantly allocates reserved trauma rooms (OR-11) without collapsing the elective schedule.
4.  **Live Simulation:** A real-time engine that allows administrators to simulate delays and instantly "self-heal" the schedule.

---

##  Technical Architecture

###  File Structure
* `app.py`: The primary Streamlit dashboard and UI.
* `scheduler_engine.py`: The core optimization logic using `ortools.sat.python`.
* `simulation_manager.py`: Manages the lifecycle of the hospital day and re-optimization triggers.
* `hospital_config.py`: Configuration for the 12 OTs, Surgeon specialties, and Equipment.
* `surgery_model_artifacts.pkl`: Pre-trained ML model for duration prediction.

###  How it Works (The Solver logic)
The `EnterpriseScheduler` ensures:
* **No Surgeon Overlap:** A surgeon cannot be in two places at once.
* **Equipment Tracking:** High-demand tools (C-Arms, Robots) are treated as finite resources.
* **Priority Ranking:** High-risk (High ASA) patients are prioritized for earlier slots to ensure clinical safety.

---

##  Getting Started

### Prerequisites
* Python 3.9 or higher
* Pip (Python package manager)

### Installation & Setup
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/siddharthjainsid1411/Hosp_automation_schedular](https://github.com/siddharthjainsid1411/Hosp_automation_schedular)
   cd Hosp_automation_schedular

```

2. **Create a virtual environment:**
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

```


3. **Install dependencies:**
```bash
pip install -r requirements.txt

```


4. **Launch the Application:**
```bash
python -m streamlit run app.py

```



---

##  Business & Clinical Impact

| Impact Area | Benefit |
| --- | --- |
| **Operational** | Reclaims "hidden" capacity and guarantees 100% resource alignment. |
| **Financial** | Drastically cuts administrative overtime and prevents revenue loss from cancellations. |
| **Clinical** | Reduces staff burnout and ensures high-risk patients are treated with priority. |

---

##  Team Omega

* **Team Leader:** Suyog Jare ([suyogjare@iisc.ac.in](mailto:suyogjare@iisc.ac.in))
* **Institution:** IISc (Indian Institute of Science)
