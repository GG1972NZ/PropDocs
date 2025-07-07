
from openai import OpenAI
import streamlit as st
import fitz  # PyMuPDF
import re

# Set up OpenAI client
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Streamlit page settings
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

# File uploader
uploaded_file = st.file_uploader("Upload a contract (PDF, DOCX, or TXT)", type=["pdf", "txt", "docx"])
contract_text = ""

# Extract text from uploaded file
if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1].lower()
    if file_type == "pdf":
        pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        contract_text = ""
        for page in pdf_doc:
            contract_text += page.get_text()
    elif file_type == "docx":
        from docx import Document
        doc = Document(uploaded_file)
        contract_text = "\n".join([para.text for para in doc.paragraphs])
    elif file_type == "txt":
        contract_text = uploaded_file.read().decode("utf-8")

if "feedback" not in st.session_state:
    st.session_state.feedback = ""

# Display UI and process contract
if contract_text:
    st.subheader("📃 Contract Preview")
    st.text_area("Text Extracted", contract_text, height=300)

    st.markdown("### 📄 **Contract Language (Input)**")
    contract_language = st.radio("", ["Thai", "English", "Italian"], index=0, key="contract_language")

    st.markdown("### 🗣️ **Analysis Output Language**")
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

            # Extract feedback and prepend a numeric risk score
            raw_feedback = response.choices[0].message.content

            def extract_risk_score(text):
                match = re.search(r"RiskScore[:\-]?\s*(\d{1,2})", text)
                return int(match.group(1)) if match else None

            score = extract_risk_score(raw_feedback)
            if score is None:
                rating = "⚪ Unknown"
                label = "Not specified"
            elif score <= 3:
                rating = "🟢 Very Low"
                label = f"{score}/10"
            elif score <= 6:
                rating = "🟡 Moderate"
                label = f"{score}/10"
            else:
                rating = "🔴 High"
                label = f"{score}/10"

            header = f"### 🚨 Risk Score: **{label}** {rating} _(1 = Low, 10 = High)_\\n\\n"
            st.session_state.feedback = header + raw_feedback

# Show feedback with metadata table
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

    metadata_md = f"""

### 📊 Extracted Metadata

| Term         | Price        | Location     |
|--------------|--------------|--------------|
| {term} | {price} | {location} |
"""

    full_output = st.session_state.feedback + metadata_md
    st.markdown(full_output)

    st.download_button(
        label="💾 Download Analysis as Text",
        data=st.session_state.feedback,
        file_name="contract_analysis.txt",
        mime="text/plain"
    )
