import streamlit as st
from pathlib import Path
import google.genai as genai
from deep_translator import GoogleTranslator
from opencage.geocoder import OpenCageGeocode
import requests, re, os, docx, fitz
from gtts import gTTS

api_key = st.secrets["GEMINI_API_KEY"]
OPENCAGE_API_KEY = st.secrets["OPENCAGE_API_KEY"]
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

client = genai.Client(api_key=api_key)

generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 4096,
}

MODEL_NAME = "models/gemini-2.5-flash"

system_prompt_image = """
As a highly skilled medical practitioner specializing in image analysis, analyze this medical image.

Responsibilities:
1. **Give the disease name as a bold heading.**
2. **Detailed Analysis:** Explain visual indicators or abnormalities.
3. **Findings Report:** Summarize significant observations.
4. **Recommendations and Next Steps:** Suggest further tests or referrals.
5. **Treatment Suggestions:** Mention possible interventions.
Add disclaimer: "Consult with a doctor before making any decisions."
"""

system_prompt_report = """
You are a highly experienced medical doctor analyzing a patient’s health report.

Responsibilities:
1. **Give the condition/disease as a bold heading.**
2. **Detailed Analysis:** Explain test values and implications.
3. **Findings Report:** Highlight abnormal or critical findings.
4. **Recommendations and Next Steps:** Suggest follow-ups or tests.
5. **Treatment Suggestions:** Mention therapies or lifestyle advice.
End with: "Consult with a doctor before making any decisions."
"""

def get_user_location():
    try:
        return requests.get("https://ipinfo.io").json().get("city", "Unknown")
    except:
        return "Unknown"

def get_default_language(city):
    mapping = {
        "Delhi": "Hindi", "Mumbai": "Hindi", "Chennai": "Tamil", "Kolkata": "Bengali",
        "Hyderabad": "Telugu", "Bangalore": "Kannada", "Ahmedabad": "Gujarati",
        "Pune": "Marathi", "Thiruvananthapuram": "Malayalam", "Amritsar": "Punjabi",
    }
    return mapping.get(city, "English")

def speak(text):
    tts = gTTS(text=text, lang="en")
    tts.save("output.mp3")
    st.audio("output.mp3", format="audio/mp3")

def get_nearest_hospital():
    try:
        loc = requests.get("https://ipinfo.io").json().get("loc")
        if not loc:
            return None
        lat, lon = map(float, loc.split(","))
        res = geocoder.reverse_geocode(lat, lon)
        if res:
            area = res[0]["components"].get("city") or res[0]["components"].get("county") or "Unknown Area"
            return {"name": "City Medical Center", "area": area, "phone": "+1-234-567-8901"}
        return None
    except:
        return None

def extract_disease_name(text):
    if not isinstance(text, str): return "Unknown"
    m = re.search(r"\*\*(.*?)\*\*", text)
    return m.group(1) if m else "Unknown"

def give_speech_dictation(disease, urgency, hospital):
    msg = f"Disease: {disease}, Urgency of treatment: {urgency}."
    speak(msg); st.write(msg)

def split_text(text, max_chars=5000):
    chunks = []
    while len(text) > max_chars:
        i = text.rfind("\n", 0, max_chars)
        if i == -1: i = text.rfind(" ", 0, max_chars)
        if i == -1: i = max_chars
        chunks.append(text[:i]); text = text[i:]
    chunks.append(text)
    return chunks

st.set_page_config(page_title="Aarogyam", page_icon=":robot_face:")
st.image("health-logo.png", width=200)
st.title("Aarogyam")
st.subheader("AI tool to analyze medical images or health reports")

if "generated_text" not in st.session_state:
    st.session_state["generated_text"] = ""

city = get_user_location()
default_lang = get_default_language(city)

st.markdown("### 📷 Upload Medical Image")
image_file = st.file_uploader("Upload an image (JPG, PNG, JPEG)", type=["png","jpg","jpeg"], key="img")

st.markdown("### 📄 Upload Health Report (PDF or DOCX)")
report_file = st.file_uploader("Upload a health report", type=["pdf","docx"], key="rep")

if image_file and not report_file:
    if st.button("Analyze Image"):
        with st.spinner("🔍 Analyzing image..."):
            tmp = Path(image_file.name)
            with open(tmp, "wb") as f: f.write(image_file.getvalue())
            uploaded = client.files.upload(file=tmp)
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[{"role": "user","parts":[
                    {"file_data":{"file_uri": uploaded.uri}},
                    {"text": system_prompt_image}
                ]}],
                config=generation_config,
            )
            text = getattr(response, "text", None) or "⚠️ No analysis result returned by Gemini."
            st.session_state["generated_text"] = text
            st.markdown(text)
            if "⚠️" not in text:
                disease = extract_disease_name(text)
                hosp = get_nearest_hospital()
                if hosp: give_speech_dictation(disease,"High",hosp)
            if os.path.exists(tmp): os.remove(tmp)

elif report_file and not image_file:
    report_text = ""
    if report_file.type == "application/pdf":
        pdf = fitz.open(stream=report_file.read(), filetype="pdf")
        report_text = "\n".join(page.get_text("text") for page in pdf)
    elif report_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(report_file)
        report_text = "\n".join(p.text for p in doc.paragraphs)

    report_text = re.sub(r"\s+", " ", report_text).strip()
    if report_text:
        st.text_area("Extracted Report Text (preview):", report_text[:1500], height=200)
        if st.button("Analyze Report"):
            with st.spinner("📄 Analyzing large report..."):

                max_chunk_size = 6000
                chunks = [report_text[i:i+max_chunk_size] for i in range(0,len(report_text),max_chunk_size)]
                analyses = []

                for i, chunk in enumerate(chunks,1):
                    st.write(f"🔹 Processing section {i}/{len(chunks)}...")
                    res = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[{"role":"user","parts":[
                            {"text": f"{system_prompt_report}\n\n---\nSection {i} of {len(chunks)}:\n{chunk}"}
                        ]}],
                        config=generation_config,
                    )
                    analyses.append(getattr(res,"text",f"⚠️ No output for section {i}"))

                combined = "\n\n".join(analyses)

                summary_prompt = f"""
                Combine and summarize the following medical analyses into one structured report.
                Use headings: **Detailed Analysis**, **Findings Report**, **Recommendations and Next Steps**, **Treatment Suggestions**.
                Stay under 4000 tokens.

                Analyses:
                {combined}
                """
                final = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[{"role":"user","parts":[{"text": summary_prompt}]}],
                    config=generation_config,
                )

                text = getattr(final,"text",None) or "⚠️ No final summary returned by Gemini."
                st.session_state["generated_text"] = text
                st.markdown(text)

                if "⚠️" not in text:
                    disease = extract_disease_name(text)
                    hosp = get_nearest_hospital()
                    if hosp: give_speech_dictation(disease,"Medium",hosp)
    else:
        st.warning("No readable text found in uploaded file.")

elif image_file and report_file:
    st.error("❌ Please upload either a medical image or a health report, not both.")

if st.session_state["generated_text"]:
    st.markdown("### 🌐 Translate the Analysis")
    langs = {
        "English":"en","Hindi":"hi","Bengali":"bn","Tamil":"ta","Telugu":"te",
        "Marathi":"mr","Gujarati":"gu","Kannada":"kn","Malayalam":"ml","Punjabi":"pa",
    }
    lang = st.selectbox("Select language", list(langs.keys()),
                        index=list(langs.keys()).index(default_lang))
    if st.button("Translate"):
        txt = st.session_state["generated_text"]
        parts = split_text(txt)
        translated = "\n".join(GoogleTranslator(source='auto', target=langs[lang]).translate(p) for p in parts)
        st.markdown(f"**Translated in {lang}:**")
        st.write(translated)
