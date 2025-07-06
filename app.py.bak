from openai import OpenAI
import streamlit as st
import fitz  # PyMuPDF

import streamlit as st
client = OpenAI(api_key=st.secrets["openai_api_key"])


st.set_page_config(page_title="ProDocs - AI Contract Analyser", layout="centered")
st.title("📄 ProDocs - AI Contract Analyser")

uploaded_file = st.file_uploader("Upload a contract (PDF or TXT)", type=["pdf", "txt"])
contract_text = ""

if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1].lower()

    if file_type == "pdf":
        pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        contract_text = ""
        for page in pdf_doc:
            contract_text += page.get_text()
    elif file_type == "txt":
        contract_text = uploaded_file.read().decode("utf-8")

if contract_text:
    st.subheader("📃 Contract Preview")
    st.text_area("Text Extracted", contract_text, height=300)

    if st.button("🔍 Analyse contract"):
        with st.spinner("Heeelllooo little fishies..."):
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a legal assistant. Analyze the contract and give feedback on risks, missing clauses, and ambiguities."},
                    {"role": "user", "content": contract_text}
                ]
            )
            feedback = response.choices[0].message.content
            st.subheader("🧠 AI Feedback")
            st.markdown(feedback)
