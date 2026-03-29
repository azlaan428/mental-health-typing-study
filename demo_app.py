import streamlit as st
import numpy as np
import pandas as pd
import joblib
import time
import re
from pathlib import Path

# Page config
st.set_page_config(
    page_title="AI Depression Screening Demo",
    page_icon="🧠",
    layout="centered"
)

# Load the trained model
@st.cache_resource
def load_model():
    try:
        model = joblib.load('models/depression_classifier.pkl')
        scaler = joblib.load('models/feature_scaler.pkl')
        return model, scaler
    except:
        return None, None

model, scaler = load_model()

# Initialize session state
if 'stage' not in st.session_state:
    st.session_state.stage = 0
if 'tasks_data' not in st.session_state:
    st.session_state.tasks_data = {}
if 'task_start_time' not in st.session_state:
    st.session_state.task_start_time = None

# Task texts
COPY_TEXT = """The quick brown fox jumps over the lazy dog. Mental health is an important aspect of overall well-being. University students often face unique challenges including academic pressure, social adjustments, and future uncertainties. It is essential to recognize signs of distress early and seek appropriate support when needed."""

FREE_WRITING_PROMPT = "Please write about your typical day as a university student. Describe your daily routine, activities, and how you generally feel. Write naturally for 3-4 minutes."

def extract_linguistic_features(text):
    """Extract linguistic features from text"""
    if not text or len(text.strip()) < 10:
        return {}
    
    text = str(text).lower()
    words = re.findall(r'\b\w+\b', text)
    
    if len(words) == 0:
        return {}
    
    # Emotion words
    negative_words = set([
        'sad', 'depressed', 'unhappy', 'miserable', 'hopeless', 'worthless',
        'tired', 'exhausted', 'stressed', 'anxious', 'worried', 'afraid',
        'alone', 'lonely', 'isolated', 'empty', 'numb', 'bad', 'terrible',
        'awful', 'horrible', 'struggle', 'difficult', 'hard', 'pain', 'hurt',
        'fail', 'failure', 'weak', 'overwhelmed', 'burden', 'useless'
    ])
    
    positive_words = set([
        'happy', 'joy', 'good', 'great', 'wonderful', 'excellent', 'amazing',
        'love', 'enjoy', 'excited', 'fun', 'beautiful', 'peaceful', 'calm',
        'relaxed', 'confident', 'proud', 'satisfied', 'grateful', 'blessed',
        'hope', 'better', 'improve', 'success', 'accomplish'
    ])
    
    first_person = set(['i', 'me', 'my', 'mine', 'myself'])
    
    negative_count = sum(1 for word in words if word in negative_words)
    positive_count = sum(1 for word in words if word in positive_words)
    first_person_count = sum(1 for word in words if word in first_person)
    
    unique_words = len(set(words))
    lexical_diversity = unique_words / len(words) if len(words) > 0 else 0
    
    sentences = re.split(r'[.!?]+', text)
    sentence_count = len([s for s in sentences if s.strip()])
    
    return {
        'free_writing_word_count': len(words),
        'free_writing_unique_word_count': unique_words,
        'free_writing_lexical_diversity': lexical_diversity,
        'free_writing_negative_word_count': negative_count,
        'free_writing_positive_word_count': positive_count,
        'free_writing_negative_word_ratio': negative_count / len(words) if len(words) > 0 else 0,
        'free_writing_positive_word_ratio': positive_count / len(words) if len(words) > 0 else 0,
        'free_writing_sentiment_balance': (positive_count - negative_count) / len(words) if len(words) > 0 else 0,
        'free_writing_first_person_count': first_person_count,
        'free_writing_first_person_ratio': first_person_count / len(words) if len(words) > 0 else 0,
        'free_writing_sentence_count': sentence_count,
        'free_writing_avg_words_per_sentence': len(words) / sentence_count if sentence_count > 0 else 0
    }

def extract_features_from_tasks(copy_text, copy_duration, free_text, free_duration):
    """Extract all features needed for prediction"""
    
    features = {}
    
    # Copy task features
    copy_words = len(copy_text.split())
    copy_chars = len(copy_text)
    features['copy_task_duration'] = copy_duration
    features['copy_task_word_count'] = copy_words
    features['copy_task_char_count'] = copy_chars
    features['copy_task_wpm'] = (copy_words / copy_duration) * 60 if copy_duration > 0 else 0
    
    # Free writing basic features
    free_words = len(free_text.split())
    free_chars = len(free_text)
    features['free_writing_duration'] = free_duration
    features['free_writing_word_count'] = free_words
    features['free_writing_char_count'] = free_chars
    features['free_writing_wpm'] = (free_words / free_duration) * 60 if free_duration > 0 else 0
    
    # Linguistic features
    ling_features = extract_linguistic_features(free_text)
    features.update(ling_features)
    
    # Fill in any missing PHQ-9 features with 0 (not used for prediction)
    for i in range(1, 10):
        features[f'phq9_q{i}'] = 0
    
    return features

def make_prediction(features_dict):
    """Make depression prediction"""
    if model is None or scaler is None:
        return None, None
    
    # Create feature array in correct order
    expected_features = [
        'phq9_q1', 'phq9_q2', 'phq9_q3', 'phq9_q4', 'phq9_q5', 
        'phq9_q6', 'phq9_q7', 'phq9_q8', 'phq9_q9',
        'copy_task_duration', 'copy_task_word_count', 'copy_task_char_count', 'copy_task_wpm',
        'free_writing_duration', 'free_writing_word_count', 'free_writing_char_count', 'free_writing_wpm',
        'free_writing_lexical_diversity', 'free_writing_negative_word_count', 'free_writing_positive_word_count',
        'free_writing_negative_word_ratio', 'free_writing_positive_word_ratio', 'free_writing_sentiment_balance',
        'free_writing_first_person_count', 'free_writing_first_person_ratio',
        'free_writing_sentence_count', 'free_writing_avg_words_per_sentence',
        'free_writing_unique_word_count'
    ]
    
    # Build feature vector
    feature_vector = []
    for feat in expected_features:
        feature_vector.append(features_dict.get(feat, 0))
    
    # Scale and predict
    X = np.array(feature_vector).reshape(1, -1)
    X_scaled = scaler.transform(X)
    
    prediction = model.predict(X_scaled)[0]
    probability = model.predict_proba(X_scaled)[0]
    
    return prediction, probability

# Main UI
st.title("🧠 AI Depression Screening Demo")
st.markdown("---")

if model is None:
    st.error("⚠️ Model files not found. Please ensure 'models/depression_classifier.pkl' and 'models/feature_scaler.pkl' exist.")
    st.stop()

# Stage 0: Welcome
if st.session_state.stage == 0:
    st.header("Welcome to the AI Depression Screening Demo")
    
    st.info("""
    This demonstration uses artificial intelligence to analyze typing patterns and language use 
    to assess potential depression risk.
    
    **How it works:**
    1. Complete two brief typing tasks (10 minutes)
    2. AI analyzes your typing speed, language patterns, and emotional tone
    3. Receive instant risk assessment
    
    **Important:**
    - This is a research demonstration, NOT a diagnostic tool
    - Results are for educational purposes only
    - Always consult a healthcare professional for medical advice
    """)
    
    st.markdown("### Research Background")
    st.write("""
    This AI model was trained on 40 university students and achieved 87.5% accuracy 
    in identifying depression based on typing patterns and linguistic markers.
    
    Key features the AI analyzes:
    - Typing speed and fluency
    - Use of negative emotion words
    - First-person pronoun usage
    - Sentiment balance
    - Lexical diversity
    """)
    
    if st.button("Start Demo", type="primary"):
        st.session_state.stage = 1
        st.rerun()

# Stage 1: Copy Task
elif st.session_state.stage == 1:
    st.header("Task 1: Copy Text")
    
    st.info("Type the text shown below exactly as written. Type naturally at your normal pace.")
    
    st.markdown("**Text to copy:**")
    st.text_area("Reference", value=COPY_TEXT, height=150, disabled=True)
    
    st.markdown("**Type here:**")
    
    if 'copy_started' not in st.session_state:
        st.session_state.copy_started = False
        st.session_state.copy_text = ""
    
    if not st.session_state.copy_started:
        if st.button("Start Typing", type="primary"):
            st.session_state.copy_started = True
            st.session_state.task_start_time = time.time()
            st.rerun()
    else:
        typed = st.text_area("Your typing:", value=st.session_state.copy_text, height=150, key="copy_input")
        st.session_state.copy_text = typed
        
        st.caption(f"Words: {len(typed.split())}")
        
        if st.button("Complete Task", type="primary"):
            if len(typed.strip()) < 30:
                st.error("Please type more text")
            else:
                duration = time.time() - st.session_state.task_start_time
                st.session_state.tasks_data['copy_text'] = typed
                st.session_state.tasks_data['copy_duration'] = duration
                st.session_state.stage = 2
                st.session_state.copy_started = False
                st.rerun()

# Stage 2: Free Writing
elif st.session_state.stage == 2:
    st.header("Task 2: Free Writing")
    
    st.info(FREE_WRITING_PROMPT)
    
    if 'free_started' not in st.session_state:
        st.session_state.free_started = False
        st.session_state.free_text = ""
    
    if not st.session_state.free_started:
        if st.button("Start Writing", type="primary"):
            st.session_state.free_started = True
            st.session_state.task_start_time = time.time()
            st.rerun()
    else:
        typed = st.text_area("Write here:", value=st.session_state.free_text, height=200, key="free_input")
        st.session_state.free_text = typed
        
        elapsed = time.time() - st.session_state.task_start_time
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"⏱️ Time: {int(elapsed // 60)}:{int(elapsed % 60):02d}")
        with col2:
            st.caption(f"Words: {len(typed.split())}")
        
        if st.button("Complete & Analyze", type="primary"):
            if len(typed.strip()) < 30:
                st.error("Please write more")
            else:
                duration = time.time() - st.session_state.task_start_time
                st.session_state.tasks_data['free_text'] = typed
                st.session_state.tasks_data['free_duration'] = duration
                st.session_state.stage = 3
                st.rerun()

# Stage 3: Results
elif st.session_state.stage == 3:
    st.header("AI Analysis Results")
    
    with st.spinner("Analyzing your responses..."):
        time.sleep(2)  # Dramatic pause
        
        # Extract features
        features = extract_features_from_tasks(
            st.session_state.tasks_data['copy_text'],
            st.session_state.tasks_data['copy_duration'],
            st.session_state.tasks_data['free_text'],
            st.session_state.tasks_data['free_duration']
        )
        
        # Make prediction
        prediction, probability = make_prediction(features)
    
    st.success("Analysis complete!")
    
    # Display result
    st.markdown("---")
    
    if prediction == 1:
        risk_level = "ELEVATED"
        risk_color = "🔴"
        confidence = probability[1] * 100
        message = """
        The AI model has detected patterns in your typing and language that are associated 
        with depression. This suggests you may be experiencing depressive symptoms.
        """
        recommendation = """
        **Recommended Actions:**
        - Consider speaking with a mental health professional
        - Reach out to university counseling services
        - Talk to someone you trust about how you're feeling
        - Remember: seeking help is a sign of strength, not weakness
        """
    else:
        risk_level = "LOW"
        risk_color = "🟢"
        confidence = probability[0] * 100
        message = """
        The AI model did not detect strong indicators of depression in your typing patterns 
        and language use. Your responses suggest typical patterns of well-being.
        """
        recommendation = """
        **Mental Health Tips:**
        - Continue maintaining healthy habits
        - Stay connected with friends and family
        - Practice self-care and stress management
        - If you ever feel distressed, don't hesitate to seek support
        """
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Depression Risk", f"{risk_color} {risk_level}")
    with col2:
        st.metric("Model Confidence", f"{confidence:.1f}%")
    
    st.info(message)
    st.success(recommendation)
    
    # Show some analyzed features
    with st.expander("📊 What the AI Analyzed"):
        st.write("**Typing Behavior:**")
        st.write(f"- Copy task typing speed: {features['copy_task_wpm']:.1f} words/min")
        st.write(f"- Free writing speed: {features['free_writing_wpm']:.1f} words/min")
        
        st.write("\n**Language Patterns:**")
        st.write(f"- Negative emotion words: {features.get('free_writing_negative_word_count', 0)}")
        st.write(f"- Positive emotion words: {features.get('free_writing_positive_word_count', 0)}")
        st.write(f"- First-person pronouns: {features.get('free_writing_first_person_count', 0)}")
        st.write(f"- Sentiment balance: {features.get('free_writing_sentiment_balance', 0):.3f}")
        st.write(f"- Lexical diversity: {features.get('free_writing_lexical_diversity', 0):.3f}")
    
    st.markdown("---")
    st.warning("""
    **Important Disclaimer:**
    
    This is a research demonstration tool, NOT a medical diagnostic instrument. 
    The results are based on a machine learning model trained on a limited dataset 
    and should NOT be used for clinical decision-making.
    
    If you are experiencing mental health concerns, please consult a qualified 
    healthcare professional.
    """)
    
    if st.button("Try Again"):
        st.session_state.clear()
        st.rerun()

# Sidebar
with st.sidebar:
    st.header("Demo Progress")
    
    stages = ["Welcome", "Copy Task", "Free Writing", "Results"]
    for i, stage in enumerate(stages):
        if i < st.session_state.stage:
            st.success(f"✅ {stage}")
        elif i == st.session_state.stage:
            st.info(f"▶️ {stage}")
        else:
            st.text(f"⏸️ {stage}")
    
    st.markdown("---")
    st.caption("AI Depression Screening Demo")
    st.caption("Biomedical Engineering Project")
    st.caption("Model Accuracy: 87.5%")
