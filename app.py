import sys
import asyncio
import io
import base64
import random
import sqlite3
import os
import pandas as pd
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import database as db
from llm_agent import run_decision_rules

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="Nagarik RTI Assistant", layout="wide", page_icon="🏛️", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #0B0F19; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    header, #MainMenu, footer {visibility: hidden; display: none;}
    .st-emotion-cache-1jicfl2 {padding-top: 0rem;}
    
    .stButton > button[kind="primary"] {
        background-color: #FF8A00; color: white; border: none; border-radius: 8px; padding: 12px 28px; font-weight: 700; letter-spacing: 0.5px; transition: all 0.3s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #e67c00; box-shadow: 0 0 20px rgba(255, 138, 0, 0.5);
    }
    .stButton > button[kind="secondary"] {
        background-color: #131B2A; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 8px; font-weight: 600; padding: 12px 28px;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #FF8A00; color: #FF8A00;
    }
    div[data-testid="stForm"], .stTextInput>div>div>input, .stTextArea>div>div>textarea, div[data-testid="metric-container"] {
        background-color: #131B2A; border: 1px solid #1e293b; border-radius: 12px; color: white;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #FF8A00; box-shadow: 0 0 10px rgba(255, 138, 0, 0.3);
    }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 800; color: #ffffff; }
    div[data-testid="stMetricLabel"] { color: #8a94a6; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

db.init_db()

if 'page' not in st.session_state:
    st.session_state['page'] = 'home'
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'chat_open' not in st.session_state:
    st.session_state['chat_open'] = False
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [
        {"role": "assistant", "content": "Namaste! I am your RTI Legal Assistant. Ask me anything about the Right to Information Act, 2005, filing timelines, or exemptions!"}
    ]

def navigate(page_name):
    st.session_state['page'] = page_name
    st.rerun()

def generate_random_captcha():
    return "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))

def generate_rti_pdf(authority, draft_text, stable_id):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>FORM 'A' - RTI APPLICATION FORM</b>", ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=20)),
        Paragraph(f"<b>Reference ID:</b> {stable_id}", styles['Normal']),
        Paragraph(f"<b>Authority:</b> {authority}", styles['Normal']),
        Spacer(1, 15),
        Paragraph((draft_text or "").replace('\n', '<br/>'), styles['Normal']),
    ]
    doc.build(story)
    return buffer.getvalue()

def render_navbar():
    col_logo, col_links = st.columns([2, 3])
    with col_logo:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; padding: 10px 0;">
            <div style="background: #FF8A00; width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; color: black;">🏛️</div>
            <span style="font-size: 1.2rem; font-weight: 800; letter-spacing: 0.5px; color: white;">Nagarik RTI</span>
        </div>
        """, unsafe_allow_html=True)
    with col_links:
        cols = st.columns(3)
        if cols[1].button("Home", key="nav_home", type="secondary"):
            navigate('home')
        if not st.session_state['logged_in']:
            if cols[2].button("Sign In →", key="nav_signin", type="primary"):
                navigate('login')
        else:
            if cols[2].button("Sign Out", key="nav_signout", type="secondary"):
                st.session_state.clear()
                navigate('home')
    st.markdown("<hr style='border-color: #1e293b; margin-top: 0px;'>", unsafe_allow_html=True)

def render_home_page():
    render_navbar()
    st.html("""
    <div style="height: 65vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; position: relative; color: white; font-family: sans-serif;">
        <div style="position: absolute; width: 450px; height: 450px; background: rgba(255, 138, 0, 0.12); filter: blur(130px); border-radius: 50%; z-index: 0;"></div>
        <div style="z-index: 10;">
            <span style="background: #131B2A; color: #FF8A00; padding: 6px 18px; border-radius: 20px; font-size: 0.85rem; border: 1px solid rgba(255, 138, 0, 0.3); font-weight: 600;">
                ⚖️ RTI-Ready Governance Portal
            </span>
            <h1 style="font-size: 4.8rem; font-weight: 800; margin-top: 25px; margin-bottom: 15px; line-height: 1.1; letter-spacing: -1px;">
                Transparency, Made <span style="color: #FF8A00;">Accessible</span>
            </h1>
            <p style="color: #8a94a6; font-size: 1.15rem; max-width: 650px; margin: 0 auto 35px auto; line-height: 1.6;">
                Bridging the gap between citizens and India's administrative system. AI-powered multilingual RTI drafting, deterministic legal triage, and court-ready evidence certification — all in one platform.
            </p>
        </div>
    </div>
    """)
    col1, col2, col3 = st.columns([1, 0.45, 1])
    with col2:
        if st.button("File an RTI Request →", type="primary", use_container_width=True):
            navigate('login')
    st.html("""
    <div style="display: flex; justify-content: center; gap: 30px; margin-top: 60px; color: #64748b; font-size: 0.9rem; font-weight: 500;">
        <span>🔒 End-to-end encrypted</span>
        <span>🌐 Multilingual (हिंदी, मराठी, தமிழ், English)</span>
        <span>🤖 AI-powered Triage</span>
        <span>📄 Court-admissible outputs</span>
    </div>
    """)

def render_login_page():
    render_navbar()
    col_brand, col_login = st.columns([1.2, 1], gap="large")
    with col_brand:
        st.markdown("""
        <div style='padding: 40px 20px; text-align: left; position: relative;'>
            <h4 style='color: #FF8A00; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; font-size: 0.85rem;'>Digital RTI System</h4>
            <h1 style='color: white; font-weight: 800; font-size: 4rem; line-height: 1.1; margin-top: 15px;'>Your Rights.<br>Digitized &<br>Protected.</h1>
            <p style='color: #8a94a6; margin-top: 20px; font-size: 1.1rem; max-width: 400px; line-height: 1.5;'>File RTIs, track applications across languages, and access government data securely.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_login:
        with st.container(border=True):
            st.markdown("<h3 style='color: white; margin-bottom: 5px;'>Sign in to Nagarik RTI</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color: #8a94a6; font-size: 0.75rem; letter-spacing: 1px; margin-bottom: 20px;'>SELECT YOUR ROLE</p>", unsafe_allow_html=True)
            tab_citizen, tab_admin = st.tabs(["👤 Citizen", "🛡️ Auditor"])
            with tab_citizen:
                with st.form("citizen_login"):
                    c_user = st.text_input("Email / User ID", placeholder="e.g., citizen01")
                    c_pass = st.text_input("Password", type="password", placeholder="••••••••")
                    if st.form_submit_button("Sign In →", type="primary", use_container_width=True):
                        if c_user == "citizen01" and c_pass == "RTI@2026":
                            st.session_state['logged_in'] = True
                            st.session_state['role'] = "citizen"
                            st.session_state['user_id'] = c_user
                            navigate('dashboard')
                        else:
                            st.error("Invalid Credentials. Use citizen01 / RTI@2026")
            with tab_admin:
                with st.form("admin_login"):
                    a_user = st.text_input("Officer ID", placeholder="Admin ID")
                    a_pass = st.text_input("Password", type="password", placeholder="••••••••")
                    if st.form_submit_button("Sign In →", type="primary", use_container_width=True):
                        if a_user == "gov_admin_99" and a_pass == "SecureRoot@2026":
                            st.session_state['logged_in'] = True
                            st.session_state['role'] = "admin"
                            st.session_state['user_id'] = a_user
                            navigate('dashboard')
                        else:
                            st.error("Unauthorized Access.")
            st.caption("💡 **Demo Login:** `citizen01` / `RTI@2026` or `gov_admin_99` / `SecureRoot@2026`")

def render_citizen_dashboard():
    render_navbar()
    if "info_input" not in st.session_state:
        st.session_state["info_input"] = ""
    if "dept_input" not in st.session_state:
        st.session_state["dept_input"] = ""
    if "state_input" not in st.session_state:
        st.session_state["state_input"] = ""

    with st.sidebar:
        st.markdown("### ⚡ QUICK TEST PRESETS")
        if st.button("🏗️ TC1: Valid RTI (Records)", type="secondary", use_container_width=True):
            st.session_state["info_input"] = "Provide expenditure reports and contractor invoices for public park development in Ward 12."
            st.session_state["dept_input"] = "Urban Development Department"
            st.session_state["state_input"] = "Tamil Nadu"
            st.rerun()
        if st.button("🚧 TC2: Grievance (Repair)", type="secondary", use_container_width=True):
            st.session_state["info_input"] = "My street light has been broken for 3 weeks, please send a technician to fix it."
            st.session_state["dept_input"] = "Municipal Corporation"
            st.session_state["state_input"] = "Maharashtra"
            st.rerun()
        if st.button("🔒 TC3: PII Violation (Privacy)", type="secondary", use_container_width=True):
            st.session_state["info_input"] = "Give me the personal property tax files and asset declarations of my neighbor."
            st.session_state["dept_input"] = "Revenue Department"
            st.session_state["state_input"] = "Karnataka"
            st.rerun()

    st.markdown("### 📝 File a New RTI Request")
    pref_lang = st.selectbox("🌐 Preferred Processing Language (Auto-Translates Local Dialects to English)", ["English", "Hindi (हिंदी)", "Marathi (मराठी)", "Tamil (தமிழ்)"])

    with st.form("rti_input_form"):
        info_needed = st.text_area("Detailed Information Required", key="info_input", height=120, placeholder="Describe official documents, budgets, or public records in English or your regional language...")
        c1, c2 = st.columns(2)
        dept = c1.text_input("Target Department", key="dept_input", placeholder="e.g., Public Works Department")
        state = c2.text_input("State", key="state_input", placeholder="e.g., Karnataka")
        submitted = st.form_submit_button("🚀 Run AI Analysis & Draft", type="primary", use_container_width=True)

    if submitted:
        if len(info_needed.strip()) < 10:
            st.error("⚠️ Validation Failed: Please provide detailed information (at least 10 characters).")
        else:
            ai_processing_text = info_needed
            if pref_lang != "English":
                ai_processing_text = f"The citizen wrote this in {pref_lang}. Please translate their intent to English, evaluate the RTI laws, and draft the final formal application entirely in English. Original text: {info_needed}"

            stable_id = db.save_initial_input(info_needed, dept, state)
            st.session_state['current_id'] = stable_id
            st.session_state['portal_step'] = 1
            st.session_state['c1'] = generate_random_captcha()
            st.session_state['c2'] = generate_random_captcha()
            
            spinner_text = f"🧠 AI translating from {pref_lang} & evaluating legal rules..." if pref_lang != "English" else "🧠 AI evaluating legal rules & Section 8(1)(j) privacy clauses..."
            with st.spinner(spinner_text):
                decision = run_decision_rules(ai_processing_text, dept, state)
                db.update_decision(stable_id, decision.category, decision.public_authority or "", decision.draft_text or "", decision.reasoning)
            st.session_state['category'] = decision.category
            st.rerun()

    if 'current_id' in st.session_state:
        req = db.get_request(st.session_state['current_id'])
        st.markdown("---")
        st.markdown("### ⚖️ Agent Decision Results")
        with st.expander("🔍 View AI Reasoning & Traceability Evidence", expanded=False):
            st.write(f"**Stable ID:** `{req['stable_id']}`")
            st.info(req['decision_reason'])

        if req['llm_category'] == "Grievance":
            st.warning("⚠️ **Classified as Service Grievance.** RTI is for public records, not physical repairs or actions.")
            st.markdown("[👉 Click Here to File on CPGRAMS Grievance Portal (pgportal.gov.in)](https://pgportal.gov.in/)", unsafe_allow_html=True)
        elif req['llm_category'] == "PII_Violation":
            st.error("🚨 **Blocked: Third-Party Personal Data Privacy Violation.**")
            st.caption("Request violates Section 8(1)(j) of the RTI Act regarding personal information without proven public interest.")
        elif req['llm_category'] == "RTI":
            with st.container(border=True):
                st.success("✅ **Valid RTI Request Mapped**")
                st.write(f"**Target Authority:** `{req['mapped_authority']}`")
                st.text_area("Final Drafted RTI Application", req['drafted_text'], height=150, disabled=True)
                colA, colB = st.columns([1, 1])
                with colA:
                    pdf_bytes = generate_rti_pdf(req['mapped_authority'], req['drafted_text'], req['stable_id'])
                    st.download_button("📄 Download Formatted PDF", data=pdf_bytes, file_name=f"RTI_{req['stable_id']}.pdf", mime="application/pdf", use_container_width=True, type="primary")
                with colB:
                    if req['status'] == "Pending_Approval":
                        if st.button("🏛️ Open Portal Gateway & File", type="primary", use_container_width=True):
                            st.session_state['show_portal'] = True
                            st.rerun()

            if req['status'] == "Pending_Approval" and st.session_state.get('show_portal', False):
                st.markdown("---")
                with st.container(border=True):
                    st.markdown("### 🌐 Official Portal Filing Gateway (Secure Session)")
                    if 'c1' not in st.session_state:
                        st.session_state['c1'] = generate_random_captcha()
                    if 'c2' not in st.session_state:
                        st.session_state['c2'] = generate_random_captcha()
                    if 'portal_step' not in st.session_state:
                        st.session_state['portal_step'] = 1

                    step = st.session_state['portal_step']
                    if step == 1:
                        st.markdown("#### **Step 1 of 2: Initial Security Check**")
                        user_c1 = st.text_input("Enter CAPTCHA Code shown below:", key="input_c1")
                        st.markdown(f"<div style='background:#1e293b; border:2px dashed #FF8A00; padding:12px; text-align:center; font-size:1.4rem; font-weight:900; letter-spacing:6px; color:#FF8A00; border-radius:8px;'>{st.session_state['c1']}</div>", unsafe_allow_html=True)
                        if st.button("Verify & Proceed to Payment ➡️", type="primary"):
                            if user_c1.strip().upper() == st.session_state['c1']:
                                st.success("✅ CAPTCHA Verified!")
                                st.session_state['portal_step'] = 2
                                st.rerun()
                            else:
                                st.error("❌ Invalid Code!")
                                st.session_state['c1'] = generate_random_captcha()
                                st.rerun()
                    elif step == 2:
                        st.markdown("#### **Step 2 of 2: Fee Payment**")
                        st.write("Application Fee: **₹ 10.00**")
                        user_c2 = st.text_input("Enter Final CAPTCHA:", key="input_c2")
                        st.markdown(f"<div style='background:#1e293b; border:2px dashed #FF8A00; padding:12px; text-align:center; font-size:1.4rem; font-weight:900; letter-spacing:6px; color:#FF8A00; border-radius:8px;'>{st.session_state['c2']}</div>", unsafe_allow_html=True)
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            if st.button("🔒 Pay ₹10 & Submit RTI", type="primary"):
                                if user_c2.strip().upper() == st.session_state['c2']:
                                    reg_id = f"RTI-GOV-2026-{random.randint(1000, 9999)}"
                                    db.update_final_result(req['stable_id'], reg_id, "30 Days", "rtionline.gov.in (Embedded Gateway)")
                                    st.session_state['show_portal'] = False
                                    st.success("🎉 Filing Complete!")
                                    st.rerun()
                                else:
                                    st.error("❌ Invalid Code!")
                                    st.session_state['c2'] = generate_random_captcha()
                                    st.rerun()
                        with col_p2:
                            if st.button("❌ Cancel", type="secondary"):
                                st.session_state['show_portal'] = False
                                st.rerun()

            if req['status'] == "Filed":
                st.balloons()
                st.markdown("### 🏆 Submission Dashboard")
                m1, m2, m3 = st.columns(3)
                m1.metric(label="Status", value="FILED ✅")
                m2.metric(label="Reg Number", value=req['actual_registration_number'])
                m3.metric(label="Deadline", value=req['response_deadline'])
                st.caption(f"🔒 Authenticated Source: {req['target_url']} | Trace ID: {req['stable_id']}")

def render_admin_dashboard():
    render_navbar()
    st.markdown("<h2>🛡️ Central RTI Auditor Dashboard</h2><p style='color: #8a94a6;'>Review AI-generated RTI drafts, approve or edit, and dispatch.</p><hr>", unsafe_allow_html=True)
    with sqlite3.connect("rti_database.db") as conn:
        df = pd.read_sql_query("SELECT * FROM requests ORDER BY execution_timestamp DESC", conn)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total RTIs", len(df))
    m2.metric("Pending Review", len(df[df['status'] == 'Pending_Approval']))
    m3.metric("Successfully Filed", len(df[df['status'] == 'Filed']))
    m4.metric("Privacy Blocks (Sec 8)", len(df[df['llm_category'] == 'PII_Violation']))

    st.markdown("<br>", unsafe_allow_html=True)
    list_col, detail_col = st.columns([1, 2], gap="large")
    with list_col:
        st.markdown("**RECENT REQUEST LOGS**")
        options = [f"{row['stable_id']} ({row['llm_category']})" for _, row in df.iterrows()] if not df.empty else []
        if options:
            selected_opt = st.selectbox("Select Request ID", options, label_visibility="collapsed")
            selected_id = selected_opt.split(" ")[0]
            selected_row = df[df['stable_id'] == selected_id].iloc[0]
        else:
            st.info("No requests logged yet.")
            selected_row = None
    with detail_col:
        if selected_row is not None:
            st.markdown(f"### Trace ID: {selected_row['stable_id']}")
            st.write(f"**Target Authority:** `{selected_row['mapped_authority'] or 'N/A'}`")
            st.write(f"**Category:** `{selected_row['llm_category']}` | **Status:** `{selected_row['status']}`")
            st.markdown("<br>**Drafted RTI Content / Reasoning**", unsafe_allow_html=True)
            st.text_area("", value=selected_row['drafted_text'] or selected_row['decision_reason'], height=200, disabled=True, label_visibility="collapsed")
            if selected_row['llm_category'] == 'RTI':
                pdf = generate_rti_pdf(selected_row['mapped_authority'], selected_row['drafted_text'], selected_row['stable_id'])
                st.download_button("⬇️ Download Official Form A PDF", pdf, file_name=f"RTI_{selected_row['stable_id']}.pdf", type="primary")

def render_rti_chatbot():
    st.markdown("""
    <style>
        .chat-float-btn {
            position: fixed; bottom: 25px; right: 25px; z-index: 99999; background-color: #FF8A00; color: white; border-radius: 50%; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 20px rgba(255, 138, 0, 0.6); cursor: pointer; font-size: 24px;
        }
    </style>
    """, unsafe_allow_html=True)

    if st.button("💬", key="chat_toggle_btn", help="Ask RTI Legal Assistant"):
        st.session_state['chat_open'] = not st.session_state['chat_open']
        st.rerun()

    if st.session_state['chat_open']:
        with st.container(border=True):
            cols_h = st.columns([5, 1])
            cols_h[0].markdown("### 🤖 RTI Legal Assistant (Groq Powered)")
            if cols_h[1].button("✖", key="close_chat"):
                st.session_state['chat_open'] = False
                st.rerun()

            st.caption("Ask questions about the Right to Information Act, 2005, filing timelines, or exemptions!")
            chat_container = st.container(height=300)
            with chat_container:
                for msg in st.session_state['chat_history']:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])

            if user_query := st.chat_input("Ask about RTI laws..."):
                st.session_state['chat_history'].append({"role": "user", "content": user_query})
                api_key = os.environ.get("GROQ_API_KEY")
                if api_key:
                    try:
                        client = Groq(api_key=api_key)
                        system_prompt = "You are an expert legal assistant specializing in the Indian Right to Information (RTI) Act, 2005. Answer citizen questions accurately regarding Section 6(1) filing, timelines (30 days), appellate authorities, and Section 8 exemptions."
                        messages = [{"role": "system", "content": system_prompt}] + [{"role": m["role"], "content": m["content"]} for m in st.session_state['chat_history']]
                        response = client.chat.completions.create(
                            model='openai/gpt-oss-120b',
                            messages=messages,
                            temperature=0.3,
                        )
                        bot_reply = response.choices[0].message.content
                    except Exception as e:
                        bot_reply = f"⚠️ Error connecting to Groq AI: {e}"
                else:
                    bot_reply = "⚠️ GROQ_API_KEY is missing from environment variables."

                st.session_state['chat_history'].append({"role": "assistant", "content": bot_reply})
                st.rerun()

if st.session_state['page'] == 'home':
    render_home_page()
elif st.session_state['page'] == 'login':
    render_login_page()
elif st.session_state['page'] == 'dashboard':
    if not st.session_state['logged_in']:
        navigate('login')
    elif st.session_state['role'] == 'citizen':
        render_citizen_dashboard()
    elif st.session_state['role'] == 'admin':
        render_admin_dashboard()

render_rti_chatbot()