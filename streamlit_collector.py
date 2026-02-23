import streamlit as st
import json
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Page config
st.set_page_config(
    page_title="Mental Health Typing Study",
    page_icon="🧠",
    layout="wide"
)

# Google Sheets Setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = '13wRfdAzoYEx65KKSLnoDeyEcVbsc82VlQbV7NAyMb00'

def get_google_sheet():
    """Connect to Google Sheet"""
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

# Initialize session state
if 'stage' not in st.session_state:
    st.session_state.stage = 0
if 'participant_data' not in st.session_state:
    st.session_state.participant_data = {}
if 'keystroke_data' not in st.session_state:
    st.session_state.keystroke_data = []
if 'task_start_time' not in st.session_state:
    st.session_state.task_start_time = None

# Copy text for task 1
COPY_TEXT = """The quick brown fox jumps over the lazy dog. Mental health is an important aspect of overall well-being. University students often face unique challenges including academic pressure, social adjustments, and future uncertainties. It is essential to recognize signs of distress early and seek appropriate support when needed."""

FREE_WRITING_PROMPT = "Please write about your typical day as a university student. Describe your daily routine, activities, and how you generally feel. Write naturally for 3-4 minutes."

PHQ9_QUESTIONS = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself or that you are a failure",
    "Trouble concentrating on things",
    "Moving or speaking slowly, or being fidgety/restless",
    "Thoughts that you would be better off dead or hurting yourself"
]

def interpret_phq9(score):
    if score <= 4:
        return "Minimal"
    elif score <= 9:
        return "Mild"
    elif score <= 14:
        return "Moderate"
    elif score <= 19:
        return "Moderately Severe"
    else:
        return "Severe"

def save_to_google_sheets():
    """Save participant data to Google Sheets"""
    try:
        sheet = get_google_sheet()
        if sheet is None:
            return False
        
        # Prepare row data
        participant_id = st.session_state.participant_data['demographics']['participant_id']
        
        # Check if sheet is empty (add headers)
        if sheet.row_count == 0 or sheet.row_values(1) == []:
            headers = [
                'participant_id', 'age', 'gender', 'year_of_study',
                'phq9_total', 'phq9_severity', 'depression_label',
                'phq9_q1', 'phq9_q2', 'phq9_q3', 'phq9_q4', 'phq9_q5',
                'phq9_q6', 'phq9_q7', 'phq9_q8', 'phq9_q9',
                'copy_task_duration', 'copy_task_word_count', 'copy_task_char_count',
                'free_writing_duration', 'free_writing_word_count', 'free_writing_char_count',
                'copy_task_text', 'free_writing_text', 'collection_date'
            ]
            sheet.append_row(headers)
        
        # Prepare data row
        row_data = [
            participant_id,
            st.session_state.participant_data['demographics']['age'],
            st.session_state.participant_data['demographics']['gender'],
            st.session_state.participant_data['demographics']['year_of_study'],
            st.session_state.participant_data['phq9']['total_score'],
            st.session_state.participant_data['phq9']['severity'],
            1 if st.session_state.participant_data['phq9']['total_score'] >= 10 else 0
        ]
        
        # Add PHQ-9 individual scores
        row_data.extend(st.session_state.participant_data['phq9']['individual_scores'])
        
        # Add typing task data
        copy_task = st.session_state.keystroke_data[0] if len(st.session_state.keystroke_data) > 0 else {}
        free_task = st.session_state.keystroke_data[1] if len(st.session_state.keystroke_data) > 1 else {}
        
        row_data.extend([
            copy_task.get('duration', 0),
            len(copy_task.get('text_content', '').split()),
            len(copy_task.get('text_content', '')),
            free_task.get('duration', 0),
            len(free_task.get('text_content', '').split()),
            len(free_task.get('text_content', '')),
            copy_task.get('text_content', ''),
            free_task.get('text_content', ''),
            datetime.now().isoformat()
        ])
        
        # Append to sheet
        sheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {e}")
        return False

# Stage 0: Consent & Demographics
if st.session_state.stage == 0:
    st.title("🧠 Mental Health Typing Study")
    st.markdown("---")
    
    st.header("Participant Information & Consent")
    
    with st.expander("📋 Study Information (Click to read)", expanded=True):
        st.markdown("""
        This study investigates typing patterns and mental health in university students.
        
        **Your participation involves:**
        - Answering demographic questions
        - Completing PHQ-9 questionnaire (depression screening)
        - Two typing tasks (15 minutes total)
        
        **Your data will be:**
        - Anonymized and encrypted
        - Used only for research purposes
        - Kept confidential
        
        You may withdraw at any time without penalty.
        """)
    
    st.subheader("Demographics")
    
    # Auto-generate participant ID
    import random
    import string
    if 'auto_participant_id' not in st.session_state:
        st.session_state.auto_participant_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    st.info(f"Your Participant ID: **{st.session_state.auto_participant_id}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.number_input("Age*", min_value=16, max_value=100, step=1)
        gender = st.selectbox("Gender*", ["", "Male", "Female", "Other", "Prefer not to say"])
    
    with col2:
        year = st.selectbox("Year of Study*", ["", "1st", "2nd", "3rd", "4th", "5th"])
        consent = st.checkbox("I consent to participate in this study*")
    
    participant_id = st.session_state.auto_participant_id
    
    if st.button("Continue to Questionnaire", type="primary"):
        if not all([age, gender, year, consent]):
            st.error("Please fill all required fields and provide consent")
        else:
            st.session_state.participant_data['demographics'] = {
                'participant_id': participant_id,
                'age': age,
                'gender': gender,
                'year_of_study': year,
                'timestamp': datetime.now().isoformat()
            }
            st.session_state.stage = 1
            st.rerun()

# Stage 1: PHQ-9 Questionnaire
elif st.session_state.stage == 1:
    st.title("📝 PHQ-9: Patient Health Questionnaire")
    st.markdown("---")
    
    st.info("Over the last 2 weeks, how often have you been bothered by the following problems?")
    
    responses = []
    
    for i, question in enumerate(PHQ9_QUESTIONS, 1):
        st.markdown(f"**{i}. {question}**")
        response = st.radio(
            f"Q{i}",
            options=["Not at all (0)", "Several days (1)", "More than half the days (2)", "Nearly every day (3)"],
            key=f"phq9_{i}",
            label_visibility="collapsed"
        )
        responses.append(int(response.split('(')[1].split(')')[0]))
        st.markdown("")
    
    if st.button("Continue to Typing Tasks", type="primary"):
        total_score = sum(responses)
        severity = interpret_phq9(total_score)
        
        st.session_state.participant_data['phq9'] = {
            'individual_scores': responses,
            'total_score': total_score,
            'severity': severity
        }
        
        if total_score >= 20:
            st.warning("""
            ⚠️ Your responses indicate you may be experiencing significant distress.
            Please consider speaking with a mental health professional.
            Resources will be provided at the end of this study.
            """)
            time.sleep(3)
        
        st.session_state.stage = 2
        st.rerun()

# Stage 2: Copy Task
elif st.session_state.stage == 2:
    st.title("✍️ Task 1: Copy Text")
    st.markdown("---")
    
    st.info("Please type the text shown below exactly as written. Type naturally at your normal pace.")
    
    st.markdown("**Text to copy:**")
    st.text_area("Reference Text", value=COPY_TEXT, height=150, disabled=True, key="copy_reference")
    
    st.markdown("**Type here:**")
    
    if 'copy_task_started' not in st.session_state:
        st.session_state.copy_task_started = False
        st.session_state.copy_task_text = ""
    
    if not st.session_state.copy_task_started:
        if st.button("Start Task", type="primary"):
            st.session_state.copy_task_started = True
            st.session_state.task_start_time = time.time()
            st.rerun()
    else:
        typed_text = st.text_area(
            "Your typing:",
            value=st.session_state.copy_task_text,
            height=150,
            key="copy_input"
        )
        
        st.session_state.copy_task_text = typed_text
        
        word_count = len(typed_text.split())
        st.caption(f"Words typed: {word_count}")
        
        if st.button("Complete Task", type="primary"):
            if len(typed_text.strip()) < 50:
                st.error("Please type more text before completing")
            else:
                task_data = {
                    'task': 'copy_task',
                    'start_time': st.session_state.task_start_time,
                    'end_time': time.time(),
                    'text_content': typed_text,
                    'duration': time.time() - st.session_state.task_start_time
                }
                st.session_state.keystroke_data.append(task_data)
                st.session_state.stage = 3
                st.session_state.copy_task_started = False
                st.rerun()

# Stage 3: Free Writing Task
elif st.session_state.stage == 3:
    st.title("✍️ Task 2: Free Writing")
    st.markdown("---")
    
    st.info(FREE_WRITING_PROMPT)
    
    if 'free_task_started' not in st.session_state:
        st.session_state.free_task_started = False
        st.session_state.free_task_text = ""
    
    if not st.session_state.free_task_started:
        if st.button("Start Task", type="primary"):
            st.session_state.free_task_started = True
            st.session_state.task_start_time = time.time()
            st.rerun()
    else:
        typed_text = st.text_area(
            "Write here (aim for 3-4 minutes):",
            value=st.session_state.free_task_text,
            height=200,
            key="free_input"
        )
        
        st.session_state.free_task_text = typed_text
        
        elapsed = time.time() - st.session_state.task_start_time
        word_count = len(typed_text.split())
        
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"⏱️ Time: {int(elapsed // 60)}:{int(elapsed % 60):02d}")
        with col2:
            st.caption(f"📝 Words: {word_count}")
        
        if st.button("Complete Task", type="primary"):
            if len(typed_text.strip()) < 50:
                st.error("Please write more before completing")
            else:
                task_data = {
                    'task': 'free_writing',
                    'start_time': st.session_state.task_start_time,
                    'end_time': time.time(),
                    'text_content': typed_text,
                    'duration': time.time() - st.session_state.task_start_time
                }
                st.session_state.keystroke_data.append(task_data)
                st.session_state.stage = 4
                st.session_state.free_task_started = False
                st.rerun()

# Stage 4: Completion
elif st.session_state.stage == 4:
    st.title("✅ Study Completed!")
    st.markdown("---")
    
    st.success("""
    Thank you for participating in this study!
    
    Your data is being saved...
    """)
    
    if 'data_saved' not in st.session_state:
        # Save to Google Sheets
        with st.spinner("Saving your response..."):
            success = save_to_google_sheets()
        
        if success:
            st.session_state.data_saved = True
            st.success("✅ Your response has been saved successfully!")
            st.balloons()
        else:
            st.error("❌ Error saving data. Please contact the researcher.")
    
    
    if st.button("Close"):
        st.session_state.clear()
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("Progress")
    stages = ["Consent", "PHQ-9", "Copy Task", "Free Writing", "Complete"]
    for i, stage_name in enumerate(stages):
        if i < st.session_state.stage:
            st.success(f"✅ {stage_name}")
        elif i == st.session_state.stage:
            st.info(f"▶️ {stage_name}")
        else:
            st.text(f"⏸️ {stage_name}")
    
    st.markdown("---")
    st.caption("Mental Health Typing Study")
    st.caption("Research Project - 2026")

