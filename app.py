from openai import OpenAI
import streamlit as st
import fitz  # PyMuPDF

# Set up OpenAI client
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Streamlit page settings
st.set_page_config(page_title="ProDocs - AI Contract Analyser", layout="centered")
st.title("📄 ProDocs - AI Contract Analyser")

# File uploader
uploaded_file = st.file_uploader("Upload a contract (PDF or TXT)", type=["pdf", "txt"])
contract_text = ""

# Extract text from uploaded file
if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1].lower()

    if file_type == "pdf":
        pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        contract_text = ""
        for page in pdf_doc:
            contract_text += page.get_text()
    elif file_type == "txt":
        contract_text = uploaded_file.read().decode("utf-8")

# If text was extracted, show preview and language options
if contract_text:
    st.subheader("📃 Contract Preview")
    st.text_area("Text Extracted", contract_text, height=300)

    # Language radio boxes in the main body
    contract_language = st.radio("📄 Contract Language (Input)", ["Thai", "English", "Italian"], index=0)
    output_language = st.radio("🗣️ Analysis Output Language", ["Thai", "English", "Italian"], index=0)

    # Analyse button
    if st.button("🔍 Analyse contract"):
        with st.spinner("🐟🐟🐟 eeelllooo little fishies..."):

            # Language-specific prompts
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
            else:  # English
                system_prompt = (
                    "You are a legal assistant. First, extract key contract metadata such as term, price, and location. "
                    "Then analyze the contract and provide feedback on risks, missing clauses, and ambiguities. "
                    "Respond in English."
                )

            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": contract_text}
                ]
            )

            # Display AI feedback
            feedback = response.choices[0].message.content
            st.subheader("🧠 AI Feedback")
            st.markdown(feedback)
