import streamlit as st
from pathlib import Path
import google.generativeai as genai
from deep_translator import GoogleTranslator
from opencage.geocoder import OpenCageGeocode
import requests
import speech_recognition as sr
from gtts import gTTS
import re
import docx
import fitz

api_key = st.secrets["GEMINI_API_KEY"]
OPENCAGE_API_KEY = st.secrets["OPENCAGE_API_KEY"]
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

genai.configure(api_key=api_key)
generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 4096,
}

system_prompt_image = """
As a highly skilled medical practitioner specializing in image analysis, you are tasked with examining medical images for a renowned hospital. Your expertise is crucial in identifying any anomalies, diseases, or health issues that may be present in the image.

Your Responsibility:

1. **Give the name of the disease as the heading in bold letters.**
2. **Detailed Analysis:** Thoroughly analyze each image, focusing on identifying any abnormal findings.
3. **Findings Report:** Document all observed anomalies or signs of disease. Clearly articulate these findings in a structured format.
4. **Recommendations and Next Steps:** Based on your analysis, suggest potential next steps, including further tests or treatments as applicable.
5. **Treatment Suggestions:** If appropriate, recommend possible treatment options or interventions.

Important Notes:
- Scope of Response: Only respond if the image pertains to human health issues.
- Clarity of Images: In cases where the image quality impedes clear analysis, note that certain aspects are 'Unable to be determined based on the provided image'.
- Disclaimer: Accompany your analysis with a disclaimer: "Consult with a doctor before making any decisions."

Please provide me an output response with these four headings: **Detailed Analysis**, **Findings Report**, **Recommendations and Next Steps**, **Treatment Suggestions**.
"""

system_prompt_report = """
You are a highly experienced medical doctor. Please thoroughly analyze the patient's uploaded health report. Focus on identifying key medical conditions, abnormalities, or issues.

Your Responsibility:

1. **Give the name of the condition or disease as the heading in bold letters.**
2. **Detailed Analysis:** Explain relevant test values and what they imply medically.
3. **Findings Report:** Highlight any abnormal or significant findings.
4. **Recommendations and Next Steps:** Suggest further investigations, lifestyle changes, or specialist referrals.
5. **Treatment Suggestions:** Include any applicable treatments or therapies.

End with: "Consult with a doctor before making any decisions."
"""

model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

# Utilities
def get_user_location():
    try:
        data = requests.get("https://ipinfo.io").json()
        return data.get("city", "Unknown")
    except:
        return "Unknown"

def get_default_language(location):
    mapping = {
        "Delhi": "Hindi", "Mumbai": "Hindi", "Chennai": "Tamil", "Kolkata": "Bengali",
        "Hyderabad": "Telugu", "Bangalore": "Kannada", "Ahmedabad": "Gujarati",
        "Pune": "Marathi", "Thiruvananthapuram": "Malayalam", "Amritsar": "Punjabi",
    }
    return mapping.get(location, "English")

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
        results = geocoder.reverse_geocode(lat, lon)
        if results:
            components = results[0]['components']
            area = components.get('city') or components.get('county') or "Unknown Area"
            return {
                "name": "City Medical Center", "area": area, "phone": "+1-234-567-8901",
                "latitude": lat, "longitude": lon
            }
        return None
    except:
        return None

def extract_disease_name(text):
    match = re.search(r"\*\*(.*?)\*\*", text)
    return match.group(1) if match else "Unknown"

def give_speech_dictation(disease_name, urgency, hospital_details):
    msg = f"Disease: {disease_name}, Urgency of treatment: {urgency}."
    speak(msg)
    st.write(msg)
st.set_page_config(page_title="Aarogyam", page_icon=":robot:")
st.image("health-logo.png", width=200)
st.title("Aarogyam")
st.subheader("AI tool to analyze medical images or health reports.")

if "generated_text" not in st.session_state:
    st.session_state["generated_text"] = ""

user_location = get_user_location()
default_language = get_default_language(user_location)
st.markdown("### 📷 Upload Medical Image")
image_file = st.file_uploader("Upload an image (JPG, PNG, JPEG)", type=["png", "jpg", "jpeg"], key="image_uploader")

st.markdown("### 📄 Upload Health Report (PDF or DOCX)")
report_file = st.file_uploader("Upload a health report", type=["pdf", "docx"], key="report_uploader")
if image_file and not report_file:
    if image_file.type not in ["image/jpeg", "image/png", "image/jpg"]:
        st.error("❌ Please upload only image files (JPG, JPEG, PNG).")
    else:
        if st.button("Analyze Image"):
            with st.spinner("🔍 Analyzing the medical image... Please wait."):
                image_data = image_file.getvalue()
                prompt_parts = [{"mime_type": image_file.type, "data": image_data}, system_prompt_image]
                response = model.generate_content(prompt_parts)
                st.session_state["generated_text"] = response.text
                st.markdown(st.session_state["generated_text"])

                disease_name = extract_disease_name(response.text)
                hospital = get_nearest_hospital()
                if hospital:
                    give_speech_dictation(disease_name, "High", hospital)
                else:
                    st.warning("Unable to find nearby hospitals.")


elif report_file and not image_file:
    if report_file.type == "application/pdf":
        pdf = fitz.open(stream=report_file.read(), filetype="pdf")
        report_text = "\n".join(page.get_text() for page in pdf)
    elif report_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(report_file)
        report_text = "\n".join(p.text for p in doc.paragraphs)
    else:
        st.error("❌ Invalid health report file.")
        report_text = ""

    if report_text and st.button("Analyze Report"):
        with st.spinner("📄 Analyzing the health report... Please wait."):
            prompt = f"{system_prompt_report}\n\n{report_text}"
            response = model.generate_content(prompt)
            st.session_state["generated_text"] = response.text
            st.markdown(st.session_state["generated_text"])

            disease_name = extract_disease_name(response.text)
            hospital = get_nearest_hospital()
            if hospital:
                give_speech_dictation(disease_name, "Medium", hospital)
            else:
                st.warning("Unable to find nearby hospitals.")


elif image_file and report_file:
    st.error("❌ Please upload either a medical image or a health report, not both.")

def split_text(text, max_chars=5000):
    chunks = []
    while len(text) > max_chars:
        split_at = text.rfind("\n", 0, max_chars)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_chars)
        if split_at == -1:
            split_at = max_chars
        chunks.append(text[:split_at])
        text = text[split_at:]
    chunks.append(text)
    return chunks

if st.session_state["generated_text"]:
    st.markdown("### 🌐 Translate the Analysis")
    languages = {
        "English": "en", "Hindi": "hi", "Bengali": "bn", "Tamil": "ta", "Telugu": "te",
        "Marathi": "mr", "Gujarati": "gu", "Kannada": "kn", "Malayalam": "ml", "Punjabi": "pa",
    }
    selected_language = st.selectbox("Select language", list(languages.keys()),
                                     index=list(languages.keys()).index(default_language))

    if st.button("Translate"):
        full_text = st.session_state["generated_text"]
        chunks = split_text(full_text)
        translated_parts = []
        for chunk in chunks:
            translated_chunk = GoogleTranslator(source='auto', target=languages[selected_language]).translate(chunk)
            translated_parts.append(translated_chunk)
        translated_text = "\n".join(translated_parts)

        st.markdown(f"**Translated in {selected_language}:**")
        st.write(translated_text)
