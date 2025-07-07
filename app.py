
from openai import OpenAI
import streamlit as st
import fitz  # PyMuPDF

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

# Display contract input and language selection
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
                    "ทั้งหมดให้แสดงผลเป็นภาษาไทย"
                )
            elif output_language == "Italian":
                system_prompt = (
                    "Sei un assistente legale. Analizza questo contratto iniziando con l’estrazione dei dati principali "
                    "come durata, prezzo e località. Poi fornisci un’analisi sui rischi, clausole mancanti e ambiguità. "
                    "Scrivi tutto in italiano."
                )
            else:
                system_prompt = (
                    "You are a legal assistant. First, extract key contract metadata such as term, price, and location. "
                    "Then analyze the contract and provide feedback on risks, missing clauses, and ambiguities. "
                    "Respond in English."
                )

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": contract_text}
                ]
            )
            st.session_state.feedback = response.choices[0].message.content

# Show AI feedback with extracted metadata
if st.session_state.feedback:

    # Extract metadata using simple regex matching
    import re
    def extract_metadata(text):
        def match(pattern):
            m = re.search(pattern, text, re.IGNORECASE)
            return m.group(1).strip() if m else "Not specified"

        term = match(r"(?:term|duration)[^\n:]*[:\-]\s*(.+)")
        price = match(r"(?:price|amount|rent)[^\n:]*[:\-]\s*(.+)")
        location = match(r"(?:location|address)[^\n:]*[:\-]\s*(.+)")
        return term.strip("*").strip(), price.strip("*").strip(), location.strip("*").strip()

    term, price, location = extract_metadata(st.session_state.feedback)

    metadata_md = f"""

### 📊 Extracted Metadata

| Term         | Price        | Location     |
|--------------|--------------|--------------|
| {term.strip("*")} | {price.strip("*")} | {location.strip("*")} |
"""

    feedback_with_metadata = st.session_state.feedback + metadata_md
    st.markdown(feedback_with_metadata)

    st.download_button(
        label="💾 Download Analysis as Text",
        data=st.session_state.feedback,
        file_name="contract_analysis.txt",
        mime="text/plain"
    )
