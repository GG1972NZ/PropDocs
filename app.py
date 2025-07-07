
from openai import OpenAI
import streamlit as st
import fitz  # PyMuPDF
import re

client = OpenAI(api_key=st.secrets["openai_api_key"])

st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
    }
    h3 {
        color: #1a75ff;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)
st.set_page_config(page_title="PropDocs - AI Contract Analyser", layout="centered")
st.title("📄 PropDocs - AI Contract Analyser")

uploaded_file = st.file_uploader("Upload a contract (PDF, DOCX, or TXT)", type=["pdf", "txt", "docx"])
contract_text = ""

if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1].lower()
    if file_type == "pdf":
        pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        contract_text = "".join([page.get_text() for page in pdf_doc])
    elif file_type == "docx":
        from docx import Document
        doc = Document(uploaded_file)
        contract_text = "\n".join([para.text for para in doc.paragraphs])
    elif file_type == "txt":
        contract_text = uploaded_file.read().decode("utf-8")

if "feedback" not in st.session_state:
    st.session_state.feedback = ""
    st.session_state.risk_label = ""

if contract_text:
    st.subheader("📃 Contract Preview")
    st.text_area("Text Extracted", contract_text, height=300)

    st.markdown("### 📄 Contract Language (Input)")
    contract_language = st.radio("", ["Thai", "English", "Italian"], index=0, key="contract_language")

    st.markdown("### 🗣️ Analysis Output Language")
    output_language = st.radio("", ["Thai", "English", "Italian"], index=0, key="output_language")

    if st.button("🔍 Analyse contract"):
        with st.spinner("Analysing contract..."):
            if output_language == "Thai":
                system_prompt = (
                    "คุณเป็นผู้ช่วยด้านกฎหมาย วิเคราะห์เอกสารสัญญาฉบับนี้ "
                    "โดยเริ่มจากการระบุข้อมูลสำคัญ เช่น ระยะเวลาสัญญา จำนวนเงิน และสถานที่ "
                    "จากนั้นให้ข้อเสนอแนะเกี่ยวกับความเสี่ยง ข้อที่ขาดหายไป และความคลุมเครือ "
                    "และสุดท้ายให้ระบุ RiskScore: 1–10 ซึ่ง 10 หมายถึงความเสี่ยงสูงสุด"
                )
            elif output_language == "Italian":
                system_prompt = (
                    "Sei un assistente legale. Analizza questo contratto iniziando con l’estrazione dei dati principali "
                    "come durata, prezzo e località. Poi fornisci un’analisi sui rischi, clausole mancanti e ambiguità. "
                    "Infine, scrivi una riga: RiskScore: 1–10, dove 10 è il rischio massimo."
                )
            else:
                system_prompt = (
                    "You are a legal assistant. First, extract key contract metadata such as term, price, and location. "
                    "Then analyze the contract and provide feedback on risks, missing clauses, and ambiguities. "
                    "At the end, include a line like: RiskScore: 1–10, where 10 is highest risk."
                )

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": contract_text}
                ]
            )

            feedback = response.choices[0].message.content
            match = re.search(r"RiskScore[:\-]?\s*(\d{1,2})", feedback)
            score = int(match.group(1)) if match else None

            if score is None:
                st.session_state.risk_label = "🚨 Risk Score: Not specified ⚪ Unknown (1 = Low, 10 = High)"
            elif score <= 3:
                st.session_state.risk_label = f"🚨 Risk Score: {score}/10 🟢 Very Low (1 = Low, 10 = High)"
            elif score <= 6:
                st.session_state.risk_label = f"🚨 Risk Score: {score}/10 🟡 Moderate (1 = Low, 10 = High)"
            else:
                st.session_state.risk_label = f"🚨 Risk Score: {score}/10 🔴 High (1 = Low, 10 = High)"

            st.session_state.feedback = feedback

if st.session_state.feedback:

    def extract_metadata(text):
        def match(pattern):
            m = re.search(pattern, text, re.IGNORECASE)
            return m.group(1).strip("* ").strip() if m else "Not specified"
        term = match(r"(?:term|duration)[^\n:]*[:\-]\s*(.+)")
        price = match(r"(?:price|amount|rent)[^\n:]*[:\-]\s*(.+)")
        location = match(r"(?:location|address)[^\n:]*[:\-]\s*(.+)")
        return term, price, location

    term, price, location = extract_metadata(st.session_state.feedback)

    risk_display = st.session_state.get("risk_label", "🚨 Risk Score: Not specified ⚪ Unknown (1 = Low, 10 = High)")
    summary = f"""{risk_display}

### 📊 Key Contract Metadata:

- **Term:** {term}
- **Price:** {price}
- **Location:** {location}

---

### 🧠 AI Feedback:
{st.session_state.feedback}
"""
    st.markdown(summary)

    st.download_button(
        label="💾 Download Analysis as Text",
        data=summary,
        file_name="contract_analysis.txt",
        mime="text/plain"
    )
