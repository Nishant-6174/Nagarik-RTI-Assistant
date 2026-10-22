import sys
import asyncio
import io
import base64
import random
from pathlib import Path
import streamlit as st

# Fix for Windows asyncio subprocess policy with Playwright
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import database as db
from llm_agent import run_decision_rules

# ReportLab imports for generating formal RTI PDFs
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ==========================================
# 1. PAGE CONFIG & ADVANCED GLASSMORPHIC CSS
# ==========================================
st.set_page_config(page_title="Nagarik RTI Engine", layout="centered", page_icon="🏛️", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Deep Space Background */
    .stApp { 
        background: radial-gradient(circle at 50% 0%, #1a1f35 0%, #0a0e17 80%);
        color: #e2e8f0;
    }
    
    #MainMenu, footer {visibility: hidden;}

    /* Advanced Primary Button Styling (Neon Glow) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00c6ff 0%, #0072ff 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 800;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 198, 255, 0.4);
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 198, 255, 0.6);
    }

    /* Advanced Form Container (Frosted Glass) */
    div[data-testid="stForm"] {
        background: rgba(20, 25, 40, 0.4);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 35px 30px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }

    /* Input Fields styling */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: rgba(10, 14, 23, 0.6);
        border: 1px solid rgba(0, 198, 255, 0.2);
        border-radius: 10px;
        color: white;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
        border-color: #00c6ff;
        background-color: rgba(10, 14, 23, 0.9);
        box-shadow: 0 0 10px rgba(0, 198, 255, 0.3);
    }
    
    /* Result Cards (Glassmorphism) */
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* CAPTCHA Display Box Styling */
    .captcha-display {
        background: #1e293b;
        border: 2px dashed #00c6ff;
        padding: 12px;
        text-align: center;
        font-size: 1.4rem;
        font-weight: 900;
        letter-spacing: 6px;
        color: #38bdf8;
        border-radius: 8px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 3D HERO COMPONENT (GYROSCOPE LOGO)
# ==========================================
def render_3d_hero():
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body, html { margin: 0; padding: 0; overflow: hidden; background: transparent !important; }
            #canvas-container { width: 100vw; height: 160px; display: flex; justify-content: center; background: transparent !important; }
        </style>
    </head>
    <body>
        <div id="canvas-container"></div>
        <script>
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 160, 0.1, 1000);
            camera.position.z = 5.5; 
            const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
            renderer.setClearColor( 0x000000, 0 ); 
            renderer.setSize(window.innerWidth, 160);
            document.getElementById('canvas-container').appendChild(renderer.domElement);
            
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
            scene.add(ambientLight);
            const pointLight = new THREE.PointLight(0x00f2fe, 3, 50);
            pointLight.position.set(5, 5, 5);
            scene.add(pointLight);

            const coreGeo = new THREE.SphereGeometry(0.5, 32, 32);
            const coreMat = new THREE.MeshStandardMaterial({ color: 0xffaa00, roughness: 0.2, metalness: 0.8, emissive: 0xffaa00, emissiveIntensity: 0.6 });
            const core = new THREE.Mesh(coreGeo, coreMat);
            scene.add(core);

            const ring1Geo = new THREE.TorusGeometry(1.0, 0.04, 16, 100);
            const ring1Mat = new THREE.MeshStandardMaterial({ color: 0x00f2fe, roughness: 0.1, metalness: 0.9, emissive: 0x00f2fe, emissiveIntensity: 0.8 });
            const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
            ring1.rotation.x = Math.PI / 2;
            scene.add(ring1);

            const ring2Geo = new THREE.TorusGeometry(1.5, 0.05, 16, 100);
            const ring2Mat = new THREE.MeshStandardMaterial({ color: 0x0072ff, roughness: 0.2, metalness: 0.8, emissive: 0x0072ff, emissiveIntensity: 0.4 });
            const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
            scene.add(ring2);

            function animate() {
                requestAnimationFrame(animate);
                ring1.rotation.y += 0.03;
                ring1.rotation.x += 0.015;
                ring2.rotation.y -= 0.01;
                ring2.rotation.z -= 0.02;
                core.rotation.y += 0.005;
                renderer.render(scene, camera);
            }
            animate();
        </script>
    </body>
    </html>
    """
    b64_html = base64.b64encode(html_code.encode('utf-8')).decode('utf-8')
    st.markdown(f'<iframe src="data:text/html;base64,{b64_html}" width="100%" height="170" style="border:none; overflow:hidden; background: transparent !important;" allowtransparency="true"></iframe>', unsafe_allow_html=True)

# ==========================================
# 3. HELPER FUNCTIONS & DB
# ==========================================
db.init_db()

def generate_rti_pdf(authority: str, draft_text: str, stable_id: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>FORM 'A' - RTI APPLICATION FORM</b>", ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=20)),
        Paragraph("<b>Under Section 6(1) of the Right to Information Act, 2005</b>", ParagraphStyle('Sub', parent=styles['Normal'], alignment=1, spaceAfter=15)),
        Spacer(1, 10),
        Paragraph(f"<b>Application Reference ID:</b> {stable_id}", styles['Normal']),
        Paragraph(f"<b>Target Public Authority:</b> {authority}", styles['Normal']),
        Spacer(1, 15),
        Paragraph("<b>Application Details:</b>", ParagraphStyle('Sub2', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold')),
        Paragraph(draft_text.replace('\n', '<br/>'), styles['Normal']),
        Spacer(1, 30),
        Paragraph("<b>Application Fee:</b> Rs. 10/- Paid via Gateway / Stamp", styles['Normal']),
        Spacer(1, 20),
        Paragraph("__________________________________________<br/><b>Signature / Verification of Applicant</b>", styles['Normal'])
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_random_captcha():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(chars, k=5))

# ==========================================
# 4. SIDEBAR PRESETS
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8297/8297075.png", width=60)
    st.markdown("## Nagarik RTI\n**AI Automation Engine**")
    st.markdown("---")
    st.caption("⚡ QUICK TEST PRESETS")
    if st.button("🏗️ TC1: Valid RTI (Records)", use_container_width=True):
        st.session_state.update({"info": "Provide expenditure reports and contractor invoices for public park development in Ward 12.", "dept": "Urban Development Department", "state": "Tamil Nadu"})
    if st.button("🚧 TC2: Grievance (Repair)", use_container_width=True):
        st.session_state.update({"info": "My street light has been broken for 3 weeks, please send a technician to fix it.", "dept": "Municipal Corporation", "state": "Maharashtra"})
    if st.button("🔒 TC3: PII Violation (Privacy)", use_container_width=True):
        st.session_state.update({"info": "Give me the personal property tax files and asset declarations of my neighbor.", "dept": "Revenue Department", "state": "Karnataka"})

info_val = st.session_state.get("info", "")
dept_val = st.session_state.get("dept", "")
state_val = st.session_state.get("state", "")

# ==========================================
# 5. MAIN FORM INPUTS
# ==========================================
render_3d_hero()
st.markdown("<h1 style='text-align: center; color: white; font-weight: 800; letter-spacing: 2px;'>NAGARIK RTI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #00c6ff; margin-bottom: 30px; letter-spacing: 1px; font-size: 1.1em;'>AI-Powered Legal Routing & Filing Engine</p>", unsafe_allow_html=True)

with st.form("input_form"):
    st.markdown("### 📝 Application Details")
    info_needed = st.text_area("Detailed Information Required", value=info_val, height=100, placeholder="Describe official documents, budgets, or public records...")
    
    col1, col2 = st.columns(2)
    with col1:
        dept = st.text_input("Target Department", value=dept_val, placeholder="e.g., Public Works Department")
    with col2:
        state = st.text_input("State", value=state_val, placeholder="e.g., Karnataka")
        
    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button("🚀 Run AI Analysis", type="primary", use_container_width=True)

if submitted:
    if len(info_needed) < 10:
        st.error("⚠️ Validation Failed: Please provide detailed information.")
    else:
        stable_id = db.save_initial_input(info_needed, dept, state)
        st.session_state['current_id'] = stable_id
        # Reset portal session flags for new request
        st.session_state['portal_step'] = 1
        st.session_state['c1'] = generate_random_captcha()
        st.session_state['c2'] = generate_random_captcha()
        
        with st.spinner("🧠 AI evaluating legal rules & Section 8(1)(j) privacy clauses..."):
            decision = run_decision_rules(info_needed, dept, state)
            db.update_decision(stable_id, decision.category, decision.public_authority or "", decision.draft_text or "", decision.reasoning)
        
        st.session_state['category'] = decision.category
        st.rerun()

# ==========================================
# 6. OUTPUT & EMBEDDED PORTAL FILING FLOW
# ==========================================
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
                st.download_button("📄 Download Formatted PDF", data=pdf_bytes, file_name=f"RTI_{req['stable_id']}.pdf", mime="application/pdf", use_container_width=True)
            
            with colB:
                if req['status'] == "Pending_Approval":
                    if st.button("🏛️ Open Portal Gateway & File", type="primary", use_container_width=True):
                        st.session_state['show_portal'] = True
                        st.rerun()

        # EMBEDDED GOVERNMENT PORTAL SIMULATION (Opens directly on the current page!)
        if req['status'] == "Pending_Approval" and st.session_state.get('show_portal', False):
            st.markdown("---")
            with st.container(border=True):
                st.markdown("### 🌐 Official Portal Filing Gateway (Secure Session)")
                
                # Initialize CAPTCHAs in session state if not present
                if 'c1' not in st.session_state:
                    st.session_state['c1'] = generate_random_captcha()
                if 'c2' not in st.session_state:
                    st.session_state['c2'] = generate_random_captcha()
                if 'portal_step' not in st.session_state:
                    st.session_state['portal_step'] = 1

                step = st.session_state['portal_step']

                if step == 1:
                    st.markdown("#### **Step 1 of 2: Department & Initial Security Check**")
                    st.info(f"Target Authority: **{req['mapped_authority']}**")
                    
                    user_c1 = st.text_input("Enter CAPTCHA Code shown below:", key="input_c1")
                    st.markdown(f"<div class='captcha-display'>{st.session_state['c1']}</div>", unsafe_allow_html=True)
                    
                    if st.button("Verify & Proceed to Payment ➡️"):
                        if user_c1.strip().upper() == st.session_state['c1']:
                            st.success("✅ CAPTCHA 1 Verified Successfully!")
                            st.session_state['portal_step'] = 2
                            st.rerun()
                        else:
                            st.error("❌ Invalid CAPTCHA Code! Generating new code...")
                            st.session_state['c1'] = generate_random_captcha()
                            st.rerun()

                elif step == 2:
                    st.markdown("#### **Step 2 of 2: Fee Payment & Final Verification**")
                    st.write("Application Fee: **₹ 10.00** (Standard under RTI Act 2005)")
                    
                    user_c2 = st.text_input("Enter Final Payment CAPTCHA Code:", key="input_c2")
                    st.markdown(f"<div class='captcha-display'>{st.session_state['c2']}</div>", unsafe_allow_html=True)
                    
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        if st.button("🔒 Pay ₹10 & Submit RTI"):
                            if user_c2.strip().upper() == st.session_state['c2']:
                                reg_id = f"RTI-GOV-2026-{random.randint(1000, 9999)}"
                                db.update_final_result(req['stable_id'], reg_id, "30 Days (Standard under RTI Act 2005)", "https://rtionline.gov.in (Embedded Gateway)")
                                st.session_state['show_portal'] = False
                                st.success("🎉 Filing Complete!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid Payment CAPTCHA! Generating new code...")
                                st.session_state['c2'] = generate_random_captcha()
                                st.rerun()
                    with col_p2:
                        if st.button("❌ Cancel / Close"):
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