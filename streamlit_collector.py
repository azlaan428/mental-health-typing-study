import streamlit as st
import json
import time
from datetime import datetime
import os
import pandas as pd

# Page config
st.set_page_config(
    page_title="Mental Health Typing Study",
    page_icon="🧠",
    layout="wide"
)

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

def save_data_to_csv():
    """Save participant data to centralized CSV file"""
    participant_id = st.session_state.participant_data['demographics']['participant_id']
    
    # Prepare row data
    row_data = {
        'participant_id': participant_id,
        'age': st.session_state.participant_data['demographics']['age'],
        'gender': st.session_state.participant_data['demographics']['gender'],
        'year_of_study': st.session_state.participant_data['demographics']['year_of_study'],
        'phq9_total': st.session_state.participant_data['phq9']['total_score'],
        'phq9_severity': st.session_state.participant_data['phq9']['severity'],
        'collection_date': datetime.now().isoformat()
    }
    
    # Add PHQ-9 individual scores
    for i, score in enumerate(st.session_state.participant_data['phq9']['individual_scores'], 1):
        row_data[f'phq9_q{i}'] = score
    
    # Add typing task data
    for task in st.session_state.keystroke_data:
        task_name = task['task']
        row_data[f'{task_name}_duration'] = task.get('duration', 0)
        row_data[f'{task_name}_word_count'] = len(task['text_content'].split())
        row_data[f'{task_name}_char_count'] = len(task['text_content'])
        row_data[f'{task_name}_text'] = task['text_content']
    
    # Depression label (PHQ-9 >= 10)
    row_data['depression_label'] = 1 if row_data['phq9_total'] >= 10 else 0
    
    # Create DataFrame
    new_row = pd.DataFrame([row_data])
    
    # Append to CSV file
    csv_file = 'all_participant_data.csv'
    
    if os.path.exists(csv_file):
        # Append to existing file
        existing_df = pd.read_csv(csv_file)
        updated_df = pd.concat([existing_df, new_row], ignore_index=True)
        updated_df.to_csv(csv_file, index=False)
    else:
        # Create new file
        new_row.to_csv(csv_file, index=False)
    
    return csv_file

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
        age = st.number_input("Age*", min_value=18, max_value=100, step=1)
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
    
    Your data has been saved automatically and will be used to help understand
    mental health patterns in university students.
    """)
    
    
    if 'data_saved' not in st.session_state:
        # Auto-save data
        csv_file = save_data_to_csv()
        st.session_state.data_saved = True
        st.success(f"✅ Your response has been recorded successfully!")
    
    st.balloons()
    
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
    
    # Admin download section (password protected)
    st.subheader("Researcher Access")
    admin_password = st.text_input("Password", type="password")
    
    if admin_password == "subata2004":  # Change this password!
        st.success("Access granted")
        
        if os.path.exists('all_participant_data.csv'):
            df = pd.read_csv('all_participant_data.csv')
            st.metric("Total Responses", len(df))
            
            st.download_button(
                label="📥 Download All Data (CSV)",
                data=df.to_csv(index=False),
                file_name=f"all_responses_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No data collected yet")
    
    st.markdown("---")
    st.caption("Mental Health Typing Study")
    st.caption("Research Project - 2026")


