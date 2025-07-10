from openai import OpenAI
import streamlit as st
import fitz  # PyMuPDF
import re
import tiktoken

MAX_TOKENS = 16385

client = OpenAI(api_key=st.secrets["openai_api_key"])

st.markdown("""
<div style="text-align:center">
    <h1 style="margin-bottom:0.2rem;">📄 PropDocs 📄</h1>
    <h3 style="margin-top:0; color:#666; font-weight:normal;">AI Contract Analyser</h3>
    <hr style="border: none; height: 1px; background-color: #ccc; margin: 1rem auto; width: 100%;">
</div>
""", unsafe_allow_html=True)

def count_tokens(text, model="gpt-4-turbo"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

st.markdown("""
<div style='color: #666; font-size: 0.9rem; margin-bottom: 0.5rem; text-align: center;'>
    💡 <strong>Tip:</strong> For best results, upload contracts under <strong>10 pages</strong> 
    or <strong>80 KB</strong> to stay within AI token limits (16,385 tokens max).
</div>
""", unsafe_allow_html=True)

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
    st.session_state.translated_text = ""
    st.session_state.feedback = ""
    st.session_state.risk_label = ""

if contract_text:
    st.subheader("📃 Contract Preview")
    st.text_area("Text Extracted", contract_text, height=300)

    token_count = count_tokens(contract_text)
    st.markdown(f"**Token count:** {token_count} / {MAX_TOKENS}")
    st.progress(min(token_count / MAX_TOKENS, 1.0))

    if token_count > MAX_TOKENS:
        st.error(f"❌ Document too long to process: {token_count} tokens (max is {MAX_TOKENS}). Please shorten the document.")
        st.stop()

    st.markdown("### 📄 Contract Language (Input)")
    contract_language = st.radio("", ["Thai", "English", "Italian"], index=0, key="contract_language")

    st.markdown("### 🗣️ Analysis Output Language")
    output_language = st.radio("", ["Thai", "English", "Italian"], index=0, key="output_language")

    if st.button("🔍 Analyse contract"):
        with st.spinner("Deploying AI-powered contract lawyer..."):
            st.markdown("⏳ Step 1: Analysing contract...")

            system_prompts = {
                "Thai": "คุณเป็นผู้ช่วยด้านกฎหมาย วิเคราะห์เอกสารสัญญาฉบับนี้ โดยเริ่มจากการระบุข้อมูลสำคัญ เช่น ระยะเวลาสัญญา จำนวนเงิน และสถานที่ จากนั้นให้ข้อเสนอแนะเกี่ยวกับความเสี่ยง ข้อที่ขาดหายไป และความคลุมเครือ และสุดท้ายให้ระบุ RiskScore: 1–10 ซึ่ง 10 หมายถึงความเสี่ยงสูงสุด",
                "Italian": "Sei un assistente legale. Analizza questo contratto iniziando con l’estrazione dei dati principali come durata, prezzo e località. Poi fornisci un’analisi sui rischi, clausole mancanti e ambiguità. Infine, scrivi una riga: RiskScore: 1–10, dove 10 è il rischio massimo.",
                "English": "You are a legal assistant. First, extract key contract metadata such as term, price, and location. Then analyze the contract and provide feedback on risks, missing clauses, and ambiguities. At the end, include a line like: RiskScore: 1–10, where 10 is highest risk."
            }

            system_prompt = system_prompts.get(output_language, system_prompts["English"])

            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": contract_text}
                ]
            )

            feedback = response.choices[0].message.content
            match = re.search(r"Risk[\s_]*Score[:=\-]?\s*(\d{1,2})", feedback, re.IGNORECASE)
            score = int(match.group(1)) if match else None

            if score is None:
                st.session_state.risk_label = "🚨 Risk Score: Not specified ⚪ Unknown (1 = Low, 10 = High)"
            elif score <= 3:
                st.session_state.risk_label = f"🚨 Risk Score: {score}/10 🟢 Very Low (1 = Low, 10 = High)"
            elif score <= 6:
                st.session_state.risk_label = f"🚨 Risk Score: {score}/10 🟡 Moderate (1 = Low, 10 = High)"
            else:
                st.session_state.risk_label = f"🚨 Risk Score: {score}/10 🔴 High (1 = Low, 10 = High)"

            if score:
                feedback = re.sub(r"Risk[\s_]*Score[:=\-]?\s*\d{1,2}", "", feedback, flags=re.IGNORECASE)
            st.session_state.feedback = feedback.strip()
            st.markdown("✅ 📑 Contract analysis complete.")

            if contract_language != output_language:
                st.markdown("⏳ Step 2: Translating contract...")
                translation_prompt = f"Translate the following contract from {contract_language} to {output_language}:\n\n{contract_text}"
                translation_response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": f"You are a legal translator. Translate only the contract text below into {output_language}."},
                        {"role": "user", "content": translation_prompt}
                    ]
                )
                st.session_state.translated_text = translation_response.choices[0].message.content
                st.markdown("✅ 🌐 Contract translation complete.")

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
    translated_text = st.session_state.get("translated_text", "")
    translation_section = f"\n\n---\n\n### 🌐 Translated Contract:\n\n{translated_text}" if translated_text else ""

    risk_display = st.session_state.get("risk_label", "🚨 Risk Score: Not specified ⚪ Unknown (1 = Low, 10 = High)")
    summary = f"""{risk_display}{translation_section}

### 📊 Key Contract Metadata:

- **Term:** {term}
- **Price:** {price}
- **Location:** {location}

---

### 🧠 AI Feedback:
{st.session_state.feedback}
"""

    st.markdown(summary)
    st.download_button("💾 Download Analysis as Text", summary, "contract_analysis.txt", "text/plain")
