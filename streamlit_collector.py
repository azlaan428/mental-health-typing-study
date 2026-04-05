import streamlit as st
import streamlit.components.v1 as components
import time
import uuid
import random
import string
import base64
from datetime import datetime
import mysql.connector

# ─────────────────────────────────────────
# Page config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Mental Health Typing Study",
    page_icon="🧠",
    layout="wide"
)

# ─────────────────────────────────────────
# MySQL connection (credentials in st.secrets)
# ─────────────────────────────────────────
def get_db():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=int(st.secrets["mysql"]["port"]),
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            ssl_ca=st.secrets["mysql"].get("ssl_ca", None)
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# ─────────────────────────────────────────
# Session state initialization
# ─────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "stage" not in st.session_state:
    st.session_state.stage = 0
if "participant_data" not in st.session_state:
    st.session_state.participant_data = {}
if "keystroke_data" not in st.session_state:
    st.session_state.keystroke_data = []
if "task_start_time" not in st.session_state:
    st.session_state.task_start_time = None
if "consent_screenshot" not in st.session_state:
    st.session_state.consent_screenshot = None

# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────
def get_ip():
    headers = st.context.headers
    ip = headers.get("X-Forwarded-For", headers.get("X-Real-IP", "unknown"))
    return ip.split(",")[0].strip()

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
    if score <= 4:   return "Minimal"
    elif score <= 9: return "Mild"
    elif score <= 14: return "Moderate"
    elif score <= 19: return "Moderately Severe"
    else:            return "Severe"

# ─────────────────────────────────────────
# Save to MySQL
# ─────────────────────────────────────────
def save_to_mysql():
    try:
        conn = get_db()
        if conn is None:
            return False
        cursor = conn.cursor()

        pid   = st.session_state.participant_data["demographics"]["participant_id"]
        sid   = st.session_state.session_id
        ip    = get_ip()
        demo  = st.session_state.participant_data["demographics"]
        phq9  = st.session_state.participant_data["phq9"]
        copy_task  = st.session_state.keystroke_data[0] if len(st.session_state.keystroke_data) > 0 else {}
        free_task  = st.session_state.keystroke_data[1] if len(st.session_state.keystroke_data) > 1 else {}
        now   = datetime.now()

        # participants
        cursor.execute("""
            INSERT INTO participants
                (participant_id, session_id, ip_address, age, gender,
                 year_of_study, consent_timestamp, data_version, collection_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (pid, sid, ip, demo["age"], demo["gender"], demo["year_of_study"], now, "v2", now))

        # phq9_responses
        cursor.execute("""
            INSERT INTO phq9_responses
                (participant_id, phq9_total, phq9_severity, depression_label,
                 q1,q2,q3,q4,q5,q6,q7,q8,q9)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            pid, phq9["total_score"], phq9["severity"],
            1 if phq9["total_score"] >= 10 else 0,
            *phq9["individual_scores"]
        ))

        # typing_data
        cursor.execute("""
            INSERT INTO typing_data
                (participant_id,
                 copy_task_duration, copy_task_word_count, copy_task_char_count, copy_task_text,
                 free_writing_duration, free_writing_word_count, free_writing_char_count, free_writing_text)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            pid,
            copy_task.get("duration", 0),
            len(copy_task.get("text_content", "").split()),
            len(copy_task.get("text_content", "")),
            copy_task.get("text_content", ""),
            free_task.get("duration", 0),
            len(free_task.get("text_content", "").split()),
            len(free_task.get("text_content", "")),
            free_task.get("text_content", ""),
        ))

        # consent_records
        cursor.execute("""
            INSERT INTO consent_records
                (participant_id, session_id, ip_address, consent_timestamp,
                 screenshot_base64, data_version, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            pid, sid, ip, now,
            st.session_state.consent_screenshot,
            "v2", None
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        st.error(f"Error saving to database: {e}")
        return False

# ─────────────────────────────────────────
# Stage 0: Consent & Demographics
# ─────────────────────────────────────────
if st.session_state.stage == 0:
    st.title("🧠 Mental Health Typing Study")
    st.markdown("---")
    st.header("Participant Information & Consent")

    # Consent section with id for screenshot capture
    st.markdown('<div id="consent-section">', unsafe_allow_html=True)

    with st.expander("📋 Study Information (Click to read)", expanded=True):
        st.markdown("""
        This study investigates typing patterns and mental health in university students.

        **Your participation involves:**
        - Answering demographic questions
        - Completing PHQ-9 questionnaire (depression screening)
        - Two typing tasks (15 minutes total)

        **Your data will be:**
        - Anonymized and used only for research purposes
        - Kept confidential

        **Data collected includes:**
        - Your typed responses and PHQ-9 scores
        - Your IP address, recorded solely for detecting duplicate submissions
          and assessing geographic distribution. It will not be used to identify you personally.

        You may withdraw at any time without penalty.
        """)

    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Demographics")

    if "auto_participant_id" not in st.session_state:
        st.session_state.auto_participant_id = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        )

    st.info(f"Your Participant ID: **{st.session_state.auto_participant_id}**")

    col1, col2 = st.columns(2)
    with col1:
        age    = st.number_input("Age*", min_value=18, max_value=100, step=1)
        gender = st.selectbox("Gender*", ["", "Male", "Female", "Other", "Prefer not to say"])
    with col2:
        year    = st.selectbox("Year of Study*", ["", "1st", "2nd", "3rd", "4th", "5th"])
        consent = st.checkbox(
            "I consent to participate in this study, including the collection of my IP address "
            "for research validation purposes.*"
        )

    # Inject html2canvas screenshot capture
    components.html("""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script>
        function captureConsent() {
            const target = window.parent.document.getElementById('consent-section');
            if (!target) return;
            html2canvas(target).then(canvas => {
                const dataUrl = canvas.toDataURL('image/png');
                window.parent.postMessage({type: 'consent_screenshot', data: dataUrl}, '*');
            });
        }
        window.addEventListener('message', function(e) {
            if (e.data && e.data.type === 'trigger_capture') captureConsent();
        });
        </script>
    """, height=0)

    if st.button("Continue to Questionnaire", type="primary"):
        if not all([age, gender, year, consent]):
            st.error("Please fill all required fields and provide consent.")
        else:
            st.session_state.participant_data["demographics"] = {
                "participant_id": st.session_state.auto_participant_id,
                "age": age,
                "gender": gender,
                "year_of_study": year,
                "timestamp": datetime.now().isoformat()
            }
            # Trigger screenshot capture via JS before moving on
            components.html("""
                <script>
                window.parent.postMessage({type: 'trigger_capture'}, '*');
                </script>
            """, height=0)
            st.session_state.stage = 1
            st.rerun()

# ─────────────────────────────────────────
# Stage 1: PHQ-9
# ─────────────────────────────────────────
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
        responses.append(int(response.split("(")[1].split(")")[0]))
        st.markdown("")

    if st.button("Continue to Typing Tasks", type="primary"):
        total_score = sum(responses)
        st.session_state.participant_data["phq9"] = {
            "individual_scores": responses,
            "total_score": total_score,
            "severity": interpret_phq9(total_score)
        }
        if total_score >= 20:
            st.warning("⚠️ Your responses indicate significant distress. Please consider speaking with a mental health professional. Resources will be provided at the end.")
            time.sleep(3)
        st.session_state.stage = 2
        st.rerun()

# ─────────────────────────────────────────
# Stage 2: Copy Task
# ─────────────────────────────────────────
elif st.session_state.stage == 2:
    st.title("✍️ Task 1: Copy Text")
    st.markdown("---")
    st.info("Please type the text shown below exactly as written. Type naturally at your normal pace.")
    st.text_area("Reference Text", value=COPY_TEXT, height=150, disabled=True, key="copy_reference")

    if "copy_task_started" not in st.session_state:
        st.session_state.copy_task_started = False
        st.session_state.copy_task_text = ""

    if not st.session_state.copy_task_started:
        if st.button("Start Task", type="primary"):
            st.session_state.copy_task_started = True
            st.session_state.task_start_time = time.time()
            st.rerun()
    else:
        typed_text = st.text_area("Your typing:", value=st.session_state.copy_task_text, height=150, key="copy_input")
        st.session_state.copy_task_text = typed_text
        st.caption(f"Words typed: {len(typed_text.split())}")

        if st.button("Complete Task", type="primary"):
            if len(typed_text.strip()) < 50:
                st.error("Please type more text before completing.")
            else:
                st.session_state.keystroke_data.append({
                    "task": "copy_task",
                    "start_time": st.session_state.task_start_time,
                    "end_time": time.time(),
                    "text_content": typed_text,
                    "duration": time.time() - st.session_state.task_start_time
                })
                st.session_state.stage = 3
                st.session_state.copy_task_started = False
                st.rerun()

# ─────────────────────────────────────────
# Stage 3: Free Writing
# ─────────────────────────────────────────
elif st.session_state.stage == 3:
    st.title("✍️ Task 2: Free Writing")
    st.markdown("---")
    st.info(FREE_WRITING_PROMPT)

    if "free_task_started" not in st.session_state:
        st.session_state.free_task_started = False
        st.session_state.free_task_text = ""

    if not st.session_state.free_task_started:
        if st.button("Start Task", type="primary"):
            st.session_state.free_task_started = True
            st.session_state.task_start_time = time.time()
            st.rerun()
    else:
        typed_text = st.text_area("Write here (aim for 3-4 minutes):", value=st.session_state.free_task_text, height=200, key="free_input")
        st.session_state.free_task_text = typed_text

        elapsed = time.time() - st.session_state.task_start_time
        col1, col2 = st.columns(2)
        with col1: st.caption(f"⏱️ Time: {int(elapsed // 60)}:{int(elapsed % 60):02d}")
        with col2: st.caption(f"📝 Words: {len(typed_text.split())}")

        if st.button("Complete Task", type="primary"):
            if len(typed_text.strip()) < 50:
                st.error("Please write more before completing.")
            else:
                st.session_state.keystroke_data.append({
                    "task": "free_writing",
                    "start_time": st.session_state.task_start_time,
                    "end_time": time.time(),
                    "text_content": typed_text,
                    "duration": time.time() - st.session_state.task_start_time
                })
                st.session_state.stage = 4
                st.session_state.free_task_started = False
                st.rerun()

# ─────────────────────────────────────────
# Stage 4: Completion
# ─────────────────────────────────────────
elif st.session_state.stage == 4:
    st.title("✅ Study Completed!")
    st.markdown("---")
    st.success("Thank you for participating! Your data is being saved...")

    if "data_saved" not in st.session_state:
        with st.spinner("Saving your response..."):
            success = save_to_mysql()
        if success:
            st.session_state.data_saved = True
            st.success("✅ Response saved successfully!")
            st.balloons()
        else:
            st.error("❌ Error saving data. Please contact the researcher.")

    st.info("""
    **Mental Health Resources:**
    - University Counseling Center: [Contact Info]
    - National Mental Health Helpline: [Number]
    - Crisis Support: [Emergency Contact]

    Questions? Contact: [Your Name] | [Your Email]
    """)

    if st.button("Next Participant", type="primary"):
        st.session_state.clear()
        st.rerun()

# ─────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────
with st.sidebar:
    st.header("Progress")
    for i, name in enumerate(["Consent", "PHQ-9", "Copy Task", "Free Writing", "Complete"]):
        if i < st.session_state.stage:   st.success(f"✅ {name}")
        elif i == st.session_state.stage: st.info(f"▶️ {name}")
        else:                              st.text(f"⏸️ {name}")
    st.markdown("---")
    st.caption("Mental Health Typing Study")
    st.caption("Research Project - 2026")