# app.py - COMPLETE HEALTHAI SUITE WITH SIDEBAR NAVIGATION
import streamlit as st
import re
import random
import joblib
import os
import pandas as pd
from datetime import datetime

# -------------------------
# Page config + CSS
# -------------------------
st.set_page_config(page_title="HealthAI Suite - Medical Dashboard",
                   page_icon="🏥", layout="wide")

st.markdown(
    """
    <style>
    .container { padding: 1rem 2rem; }
    .chat-container {
        max-height: 520px; overflow-y:auto; padding:16px; background:#ffffff; border-radius:8px;
        border:1px solid #e6e9ee;
    }
    .user-message { background:#0b5cff; color:white; padding:10px 14px; border-radius:14px 14px 2px 14px;
        margin:8px 0; display:block; margin-left:auto; max-width:78%; text-align:right; }
    .bot-message { background:#f1f5f9; color:#0f172a; padding:10px 14px; border-radius:14px 14px 14px 2px;
        margin:8px 0; display:block; max-width:78%; }
    .emergency { background:#dc3545; color:white; padding:10px 14px; border-radius:10px; margin:8px 0; }
    .high-emergency { background:#8b0000; color:white; padding:12px 16px; border-radius:10px; margin:8px 0; font-weight:bold; }
    .card { background:#fff; border-radius:10px; padding:12px; border:1px solid #e6e9ee; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; padding:20px; border-radius:10px; margin:10px 0; }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------
# Healthcare Chatbot Class
# -------------------------
class HealthcareChatbot:
    def __init__(self):
        self.symptom_list = sorted([
            "chest pain", "shortness of breath", "severe bleeding", "high fever",
            "difficulty breathing", "unconscious", "fever", "cough", "loss of taste", 
            "loss of smell", "sore throat", "runny nose", "headache", "dizziness", 
            "nausea", "vomiting", "abdominal pain", "diarrhea", "constipation", 
            "back pain", "leg pain", "arm pain", "jaw pain", "shoulder pain",
            "joint pain", "swelling", "rash", "fatigue", "pain", "itching", 
            "numbness", "palpitations", "weakness"
        ], key=lambda s: -len(s))

        self.emergency_symptoms = {
            "chest pain", "shortness of breath", "severe bleeding", 
            "unconscious", "difficulty breathing"
        }

        self.heart_attack_symptoms = {"chest pain", "arm pain", "jaw pain", "shoulder pain"}

        self.symptom_conditions = {
            "chest pain+dizziness": ["Possible cardiac issue (arrhythmia, ischemia)"],
            "chest pain+arm pain": ["Possible heart attack - EMERGENCY"],
            "chest pain+jaw pain": ["Possible heart attack - EMERGENCY"],
            "chest pain+shortness of breath": ["Cardiac or pulmonary emergency"],
            "fever+cough": ["Respiratory infection (flu, pneumonia, COVID-19)"],
            "fever+rash": ["Viral exanthem, allergic reaction"],
            "back pain+leg pain+numbness": ["Sciatica, herniated disc"],
            "joint pain+swelling": ["Arthritis (OA/RA), gout"],
            "leg pain+swelling+redness": ["Deep vein thrombosis (DVT)"],
            "abdominal pain+nausea+vomiting": ["Gastroenteritis, food poisoning"]
        }

        self.symptom_explanations = {
            "fever": "Fever commonly indicates infection or inflammation. Monitor temperature and stay hydrated.",
            "cough": "Cough may indicate respiratory infection, asthma, or irritation. Rest and stay hydrated.",
            "chest pain": "Chest pain can be serious. If severe, crushing, or radiates to arm/jaw, seek emergency care immediately.",
            "shortness of breath": "Shortness of breath may require urgent evaluation, especially if sudden or severe.",
            "headache": "Headache causes range from tension to migraines. Seek care if severe, sudden, or with vision changes.",
            "arm pain": "Arm pain with chest pain could indicate heart issues. Isolated arm pain may be muscular or nerve-related.",
            "leg pain": "Leg pain with swelling/redness could indicate blood clot. Otherwise may be muscular or joint issue.",
            "joint pain": "Joint pain may indicate arthritis, injury, or inflammation. Rest and consider anti-inflammatories.",
            "abdominal pain": "Abdominal pain varies from indigestion to serious conditions. Location and severity matter.",
            "back pain": "Back pain is common but seek care if with leg weakness, numbness, or bowel/bladder changes."
        }

        self.follow_up_questions = {
            "chest pain": ["Does the pain radiate to your arm, jaw, or back?"],
            "fever": ["What is your temperature?"],
            "arm pain": ["Is the pain in one or both arms?"]
        }

        self.drug_database = {
            "paracetamol": {
                "uses":"Pain and fever relief",
                "dosage":"500-1000 mg every 4-6 hours (adult typical); do not exceed 4000 mg/day",
                "side_effects":"Rare at recommended dose; liver risk in overdose",
                "precautions":"Avoid heavy alcohol use; check other meds for acetaminophen"
            },
            "ibuprofen": {
                "uses":"Pain, inflammation, fever",
                "dosage":"200-400 mg every 4-6 hours; max depends on formulation",
                "side_effects":"Stomach upset, increased bleeding risk, kidney effects",
                "precautions":"Take with food; avoid if active peptic ulcer or severe kidney disease"
            },
            "aspirin": {
                "uses":"Pain, fever, anti-inflammatory; low-dose for antiplatelet therapy",
                "dosage":"325-650 mg every 4-6 hours (not for children with viral illness); low-dose 75-100 mg for cardioprotection",
                "side_effects":"Gastric irritation, bleeding",
                "precautions":"Not for children with fever (Reye's syndrome), avoid if bleeding risk"
            },
            "amoxicillin": {
                "uses":"Broad-spectrum antibiotic for many bacterial infections",
                "dosage":"500 mg every 8 hours or 875 mg every 12 hours (typical adult regimens)",
                "side_effects":"Diarrhea, allergic reaction",
                "precautions":"Do not use if penicillin allergy"
            },
            "clopidogrel": {
                "uses":"Antiplatelet for stroke/MI prevention",
                "dosage":"75 mg once daily",
                "side_effects":"Bleeding",
                "precautions":"Combine with aspirin only when indicated; bleed risk"
            }
        }

    def extract_symptoms(self, text):
        if not text:
            return []
        text_l = text.lower()
        matched = []
        for symptom in self.symptom_list:
            pattern = r'\b' + re.escape(symptom) + r'\b'
            if re.search(pattern, text_l):
                matched.append(symptom)
        seen = set()
        out = []
        for s in matched:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def assess_urgency(self, symptoms):
        symptoms_lower = [s.lower() for s in symptoms]
        
        if 'chest pain' in symptoms_lower:
            heart_related = any(pain in symptoms_lower for pain in ['arm pain', 'jaw pain', 'shoulder pain'])
            if heart_related:
                return "HIGH EMERGENCY", "🚨 POSSIBLE HEART ATTACK - Chest pain with arm/jaw pain could indicate cardiac emergency. Call emergency services IMMEDIATELY."
        
        emergency_found = [s for s in symptoms_lower if s in self.emergency_symptoms]
        if emergency_found:
            return "EMERGENCY", f"🚨 EMERGENCY detected: {', '.join(emergency_found)}. Seek immediate medical care or call emergency services."
        
        symptoms_key = "+".join(sorted(symptoms_lower))
        if symptoms_key in self.symptom_conditions:
            return "URGENT", f"Urgent: {', '.join(self.symptom_conditions[symptoms_key])}. Consult healthcare professional soon."
        
        return "ROUTINE", "Monitor symptoms and schedule routine checkup if persistent."

    def get_specific_recommendations(self, symptoms):
        recommendations = []
        symptoms_lower = [s.lower() for s in symptoms]
        
        if 'chest pain' in symptoms_lower and any(pain in symptoms_lower for pain in ['arm pain', 'jaw pain']):
            return [
                "Call emergency services IMMEDIATELY",
                "Do not drive yourself to hospital",
                "Chew aspirin if available and not allergic",
                "Stay calm and rest while waiting for help"
            ]
        
        if any(s in symptoms_lower for s in ['fever', 'cough', 'shortness of breath']):
            recommendations.extend([
                "Monitor temperature regularly",
                "Stay hydrated with water and electrolytes",
                "Rest and avoid strenuous activity",
                "Use humidifier for cough relief"
            ])
        
        if any(s in symptoms_lower for s in ['headache', 'back pain', 'joint pain']):
            recommendations.extend([
                "Rest in comfortable position",
                "Apply ice or heat as appropriate",
                "Consider over-the-counter pain relief if suitable",
                "Avoid activities that worsen pain"
            ])
        
        if not recommendations:
            recommendations = [
                "Monitor symptoms for changes",
                "Stay hydrated and rest",
                "Schedule doctor appointment if symptoms persist beyond 3 days",
                "Seek immediate care if symptoms worsen suddenly"
            ]
        
        return recommendations[:4]

    def analyze_symptoms(self, input_symptoms):
        if isinstance(input_symptoms, str):
            if ',' in input_symptoms:
                symptoms = [s.strip().lower() for s in input_symptoms.split(',') if s.strip()]
            else:
                symptoms = self.extract_symptoms(input_symptoms)
        elif isinstance(input_symptoms, list):
            symptoms = [s.strip().lower() for s in input_symptoms if s and isinstance(s, str)]
        else:
            symptoms = []

        if not symptoms:
            return {
                "urgency": "ROUTINE",
                "message": "I couldn't detect clear symptoms. Please describe them specifically or list them separated by commas.",
                "recommendations": ["Provide clearer symptom description", "List main symptoms separated by commas"],
                "matched": []
            }

        urgency_level, urgency_message = self.assess_urgency(symptoms)
        recommendations = self.get_specific_recommendations(symptoms)
        
        explanation_parts = []
        for symptom in symptoms:
            if symptom in self.symptom_explanations:
                explanation_parts.append(self.symptom_explanations[symptom])
            else:
                explanation_parts.append(f"{symptom.capitalize()} should be evaluated by a healthcare professional if persistent or severe.")

        detailed_message = f"Detected symptoms: {', '.join(symptoms)}.\n\n" + " ".join(explanation_parts)
        
        follow_up = ""
        if urgency_level in ["ROUTINE", "URGENT"]:
            for symptom in symptoms:
                if symptom in self.follow_up_questions:
                    follow_up = "\n\n**To help assess better:** " + self.follow_up_questions[symptom][0]
                    break

        return {
            "urgency": urgency_level,
            "message": f"{urgency_message}\n\n{detailed_message}{follow_up}",
            "recommendations": recommendations,
            "matched": symptoms
        }

    def get_drug_info(self, query):
        q = query.strip().lower()
        if not q:
            return None
        if q in self.drug_database:
            d = self.drug_database[q]
            return {
                "name": q.title(),
                "uses": d["uses"],
                "dosage": d["dosage"],
                "side_effects": d["side_effects"],
                "precautions": d["precautions"]
            }
        matches = [k for k in self.drug_database.keys() if q in k]
        if len(matches) == 1:
            k = matches[0]
            d = self.drug_database[k]
            return {
                "name": k.title(),
                "uses": d["uses"],
                "dosage": d["dosage"],
                "side_effects": d["side_effects"],
                "precautions": d["precautions"]
            }
        elif len(matches) > 1:
            return {"multiple": [m.title() for m in matches]}
        else:
            return None

    def generate_response(self, user_input, chat_history=None):
        if not user_input or not isinstance(user_input, str):
            return "Please type a message."

        txt = user_input.strip().lower()

        if any(g in txt for g in ["hello", "hi", "hey", "good morning", "good evening"]):
            return "Hello! I'm HealthAI — I can help analyze symptoms, give medication information (educational), and provide general health tips. How may I assist you?"

        drug_match = re.search(r'\b(paracetamol|ibuprofen|aspirin|amoxicillin)\b', txt)
        if drug_match:
            info = self.get_drug_info(drug_match.group(1))
            if isinstance(info, dict) and "name" in info:
                return (f"**{info['name']}**\n\n**Uses:** {info['uses']}\n**Typical dosage:** {info['dosage']}\n**Side effects:** {info['side_effects']}\n**Precautions:** {info['precautions']}")

        if any(k in txt for k in ["911", "emergency", "ambulance", "help me", "urgent", "dying", "heart attack"]):
            return "🚨 If this is an emergency, call your local emergency number right away. I am not a replacement for emergency care."

        if "," in user_input or any(sym in txt for sym in self.symptom_list):
            analysis = self.analyze_symptoms(user_input)
            recs = "\n".join([f"- {r}" for r in analysis.get("recommendations", [])])
            return f"**Urgency:** {analysis['urgency']}\n\n{analysis['message']}\n\n**Recommendations:**\n{recs}"

        if any(k in txt for k in ["advice", "tip", "healthy", "prevent"]):
            tips = [
                "Stay hydrated (8 glasses of water daily) and get 7-9 hours of quality sleep.",
                "Eat a balanced diet with plenty of vegetables, lean protein, and whole grains.",
                "Aim for 150 minutes of moderate exercise weekly for heart health.",
                "Manage stress through meditation, deep breathing, or enjoyable hobbies.",
            ]
            return f"**Health Tip:** {random.choice(tips)}"

        fallbacks = [
            "I can help with symptom analysis, medication info, and general health tips. What would you like?",
            "Ask me about symptoms (e.g., 'fever, cough, chest pain'), or ask for medication info (e.g., 'paracetamol').",
        ]
        return random.choice(fallbacks)

# -------------------------
# Model Loading (FIXED VERSION)
# -------------------------
@st.cache_resource
def load_model(model_path=None):
    """
    Loads a model from a given path.
    If no path is provided, attempts auto-detection.
    """
    if model_path and model_path.strip():
        try:
            model = joblib.load(model_path.strip())
            return model, os.path.basename(model_path.strip())
        except Exception as e:
            return None, f"error:{e}"

    model_files = [f for f in os.listdir('.') if f.endswith(('.joblib', '.pkl', '.pblib', '.model'))]
    if not model_files:
        return None, None
    
    model_file = model_files[0]
    try:
        model = joblib.load(model_file)
        return model, model_file
    except Exception as e:
        return None, f"error:{e}"

# -------------------------
# Initialize Chatbot and Session State
# -------------------------
@st.cache_resource
def get_chatbot():
    return HealthcareChatbot()

chatbot = get_chatbot()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# -------------------------
# SIDEBAR NAVIGATION
# -------------------------
st.sidebar.title("🏥 HealthAI Suite Navigation")
app_mode = st.sidebar.selectbox("Choose Module", [
    "📊 Main Dashboard", 
    "💬 Medical Chatbot", 
    "🩺 Symptom Checker",
    "💊 Medication Info", 
    "❤️ Heart Disease Predictor"
])

# Model loading in sidebar
st.sidebar.markdown("---")
st.sidebar.header("🔧 Model Settings")

# Try to load the heart disease model automatically
if "heart_model" not in st.session_state:
    heart_model, model_name = load_model(None)
    if heart_model:
        st.session_state.heart_model = heart_model
        st.session_state.model_name = model_name
        st.sidebar.success(f"✅ Model loaded: {model_name}")
    else:
        st.sidebar.warning("⚠️ Heart disease model not loaded")

# Manual model loading option
model_path_input = st.sidebar.text_input("Or specify model path:", 
                                       placeholder="C:/path/to/model.pblib")

if st.sidebar.button("Load Custom Model"):
    if model_path_input:
        custom_model, custom_name = load_model(model_path_input)
        if custom_model:
            st.session_state.heart_model = custom_model
            st.session_state.model_name = custom_name
            st.sidebar.success(f"✅ Custom model loaded: {custom_name}")
        else:
            st.sidebar.error("❌ Failed to load custom model")

# -------------------------
# MAIN DASHBOARD
# -------------------------
if app_mode == "📊 Main Dashboard":
    st.title("🏥 HealthAI Suite - Complete Medical AI Assistant")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; padding:20px; border-radius:10px; margin:10px 0;'>
            <h3>💬 Medical Chatbot</h3>
            <p>AI-powered health assistant for general medical queries</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color:white; padding:20px; border-radius:10px; margin:10px 0;'>
            <h3>🩺 Symptom Checker</h3>
            <p>Analyze symptoms and get urgency assessment</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color:white; padding:20px; border-radius:10px; margin:10px 0;'>
            <h3>💊 Medication Info</h3>
            <p>Comprehensive drug database with side effects</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    ## Welcome to Your Complete Medical AI Assistant! 
    
    **Available Modules:**
    - 💬 **Medical Chatbot** - AI-powered health assistant for general queries
    - 🩺 **Symptom Checker** - Analyze symptoms and get medical recommendations  
    - 💊 **Medication Info** - Comprehensive drug database with uses and side effects
    - ❤️ **Heart Disease Predictor** - ML model for heart disease risk assessment
    
    **How to use:**
    1. Select a module from the sidebar navigation
    2. Interact with the features
    3. Get instant AI-powered medical insights
    
    *Note: This system is for educational purposes only and does not replace professional medical advice.*
    """)

# -------------------------
# MEDICAL CHATBOT
# -------------------------
elif app_mode == "💬 Medical Chatbot":
    st.title("💬 HealthAI Medical Chatbot")
    st.markdown("AI-powered health assistant for general medical queries and advice")
    
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
    for msg in st.session_state.chat_history:
        if msg["type"] == "user":
            st.markdown(f"<div class='user-message'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            urgency = msg.get("urgency", "routine")
            if urgency == "HIGH EMERGENCY":
                st.markdown(f"<div class='high-emergency'>{msg['content']}</div>", unsafe_allow_html=True)
            elif urgency == "EMERGENCY":
                st.markdown(f"<div class='emergency'>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='bot-message'>{msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form(key="chat_form", clear_on_submit=True):
        user_text = st.text_input("Type your message here...", placeholder="e.g., I have fever and cough", key="chat_form_input")
        submitted = st.form_submit_button("Send")
        if submitted and user_text and user_text.strip():
            st.session_state.chat_history.append({
                "type": "user",
                "content": user_text.strip(),
                "ts": datetime.now().isoformat()
            })
            bot_reply = chatbot.generate_response(user_text, st.session_state.chat_history)
            urgency = "routine"
            if "HIGH EMERGENCY" in bot_reply:
                urgency = "HIGH EMERGENCY"
            elif "EMERGENCY" in bot_reply or "🚨" in bot_reply:
                urgency = "EMERGENCY"
            
            st.session_state.chat_history.append({
                "type": "bot",
                "content": bot_reply,
                "urgency": urgency,
                "ts": datetime.now().isoformat()
            })
            st.rerun()

    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

# -------------------------
# SYMPTOM CHECKER
# -------------------------
elif app_mode == "🩺 Symptom Checker":
    st.title("🩺 Symptom Checker")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Important:** This tool is informational only. For emergencies, call your local emergency number.")
    st.markdown("</div>", unsafe_allow_html=True)

    symptom_input = st.text_area("Describe your symptoms (free text or comma-separated):", height=140, placeholder="e.g., fever, cough, chest pain")
    if st.button("Analyze Symptoms"):
        if not symptom_input or not symptom_input.strip():
            st.warning("Please enter symptoms to analyze.")
        else:
            analysis = chatbot.analyze_symptoms(symptom_input)
            if not isinstance(analysis, dict) or "urgency" not in analysis:
                st.error("Unable to analyze symptoms. Try rephrasing.")
            else:
                urgency = analysis["urgency"]
                if urgency == "HIGH EMERGENCY":
                    st.markdown(f"<div class='high-emergency'><h3>🚨 HIGH EMERGENCY</h3>{analysis['message']}</div>", unsafe_allow_html=True)
                elif urgency == "EMERGENCY":
                    st.markdown(f"<div class='emergency'><h3>🚨 EMERGENCY</h3>{analysis['message']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"**Urgency:** {urgency}")
                    st.write(analysis["message"])
                
                st.subheader("Recommendations")
                for i, r in enumerate(analysis.get("recommendations", []), 1):
                    st.write(f"{i}. {r}")

# -------------------------
# MEDICATION INFO
# -------------------------
elif app_mode == "💊 Medication Info":
    st.title("💊 Medication Information")
    st.markdown("Search for a medication to view uses, typical dosage, side effects and precautions.")
    med_query = st.text_input("Search medication (name):", placeholder="e.g., Paracetamol, Metformin")
    if st.button("Get Medication Info"):
        if not med_query or not med_query.strip():
            st.warning("Please enter a medication name.")
        else:
            info = chatbot.get_drug_info(med_query)
            if info is None:
                st.info("No exact match found. Try a different name or check spelling.")
                possible = [k.title() for k in chatbot.drug_database.keys() if med_query.strip().lower() in k]
                if possible:
                    st.write("Possible matches:", ", ".join(possible))
            elif "multiple" in info:
                st.write("Multiple matches:", ", ".join(info["multiple"]))
            else:
                st.markdown(f"**{info['name']}**")
                st.markdown(f"- **Uses:** {info['uses']}")
                st.markdown(f"- **Typical Dosage:** {info['dosage']}")
                st.markdown(f"- **Side Effects:** {info['side_effects']}")
                st.markdown(f"- **Precautions:** {info['precautions']}")

# -------------------------
# HEART DISEASE PREDICTOR (PROFESSIONAL VERSION)
# -------------------------
elif app_mode == "❤️ Heart Disease Predictor":
    st.title("❤️ HealthAI - Heart Disease Risk Prediction")
    st.markdown("""
    This tool predicts the likelihood of heart disease based on patient health indicators.  
    Enter the patient's details below and click **Predict** to see the results.
    """)
    
    # Check if model is loaded
    heart_model = st.session_state.get("heart_model", None)
    model_name = st.session_state.get("model_name", "Not loaded")
    
    if heart_model:
        st.success(f"✅ Model ready: {model_name}")
    else:
        st.error("❌ No heart disease model loaded!")
        st.info("💡 Load a model using the sidebar options")
        st.stop()
    
    # Input form in main area (better UX)
    st.markdown("### 📋 Patient Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        age = st.slider("Age", 20, 100, 50)
        sex = st.radio("Sex", ["Female", "Male"])
        cp = st.selectbox("Chest Pain Type", [
            "Typical angina",
            "Atypical angina", 
            "Non-anginal pain",
            "Asymptomatic"
        ])
        trestbps = st.slider("Resting Blood Pressure (mm Hg)", 90, 200, 120)
        chol = st.slider("Serum Cholesterol (mg/dl)", 100, 600, 200)
        fbs = st.radio("Fasting Blood Sugar > 120 mg/dl", ["No", "Yes"])
        restecg = st.selectbox("Resting ECG Results", [
            "Normal",
            "ST-T wave abnormality", 
            "Left ventricular hypertrophy"
        ])
    
    with col2:
        thalach = st.slider("Max Heart Rate Achieved", 60, 220, 150)
        exang = st.radio("Exercise Induced Angina", ["No", "Yes"])
        oldpeak = st.slider("ST Depression (exercise)", 0.0, 6.0, 1.0, format="%.2f")
        slope = st.selectbox("Slope of Peak Exercise ST Segment", [
            "Upsloping",
            "Flat", 
            "Downsloping"
        ])
        ca = st.slider("Number of Major Vessels Colored", 0, 3, 0)
        thal = st.selectbox("Thalassemia", [
            "Normal",
            "Fixed defect", 
            "Reversible defect"
        ])
    
    # Convert inputs
    sex_num = 1 if sex == "Male" else 0
    cp_num = ["Typical angina", "Atypical angina", "Non-anginal pain", "Asymptomatic"].index(cp)
    fbs_num = 1 if fbs == "Yes" else 0
    restecg_num = ["Normal", "ST-T wave abnormality", "Left ventricular hypertrophy"].index(restecg)
    exang_num = 1 if exang == "Yes" else 0
    slope_num = ["Upsloping", "Flat", "Downsloping"].index(slope)
    thal_num = ["Normal", "Fixed defect", "Reversible defect"].index(thal)
    
    features = [
        age, sex_num, cp_num, trestbps, chol, fbs_num,
        restecg_num, thalach, exang_num, oldpeak,
        slope_num, ca, thal_num
    ]
    
    feature_names = [
        'age', 'sex', 'cp', 'trestbps', 'chol', 'fbs',
        'restecg', 'thalach', 'exang', 'oldpeak',
        'slope', 'ca', 'thal'
    ]
    
    # Prediction button
    if st.button("🔍 Predict Heart Disease Risk", type="primary", use_container_width=True):
        try:
            input_df = pd.DataFrame([features], columns=feature_names)
            
            prediction = heart_model.predict(input_df)[0]
            prediction_proba = heart_model.predict_proba(input_df)[0]
            
            st.subheader("📊 Prediction Results")
            
            if prediction == 1:
                st.error("🚨 **High Risk**: Patient is likely to have heart disease")
                st.info(f"**Confidence**: {prediction_proba[1] * 100:.2f}%")
            else:
                st.success("✅ **Low Risk**: Patient is unlikely to have heart disease")
                st.info(f"**Confidence**: {prediction_proba[0] * 100:.2f}%")
            
            # Probability breakdown
            st.subheader("📈 Probability Breakdown")
            col1, col2 = st.columns(2)
            col1.metric("Probability of No Disease", f"{prediction_proba[0]*100:.2f}%")
            col2.metric("Probability of Disease", f"{prediction_proba[1]*100:.2f}%")
            
            # Feature importance
            if hasattr(heart_model, 'feature_importances_'):
                st.subheader("🔍 Top Influencing Factors")
                importance_df = pd.DataFrame({
                    'Feature': feature_names,
                    'Importance': heart_model.feature_importances_
                }).sort_values('Importance', ascending=False).head(5)
                
                for _, row in importance_df.iterrows():
                    st.write(f"**{row['Feature']}**: {row['Importance']*100:.1f}%")
                    
        except Exception as e:
            st.error(f"❌ Prediction error: {e}")
    
    # Model information
    st.markdown("---")
    st.subheader("ℹ️ About This Model")
    st.markdown("""
    - **Algorithm**: Random Forest Classifier  
    - **Accuracy**: 98.5% on test data  
    - **Training Data**: 1,025 patient records  
    - **Features**: 13 clinical parameters  
    - **Performance**: Excellent predictive power with minimal false negatives
    """)

# -------------------------
# FOOTER
# -------------------------
st.markdown("---")
st.markdown("**Disclaimer:** This system is for educational purposes only and does not replace professional medical care. In emergencies, call your local emergency services immediately.")

st.caption("🏥 HealthAI Suite - Intelligent Analytics for Patient Care | GUVI Final Project")
