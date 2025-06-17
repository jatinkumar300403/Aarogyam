import streamlit as st
from pathlib import Path
import google.generativeai as genai
from deep_translator import GoogleTranslator
from opencage.geocoder import OpenCageGeocode
import requests
import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import re

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
system_prompt = """
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
- Your insights are valuable in guiding clinical decisions. Please proceed with the analysis, adhering to the structured approach outlined above.

Please provide me an output response with these four headings: **Detailed Analysis**, **Findings Report**, **Recommendations and Next Steps**, **Treatment Suggestions**.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

#location
def get_user_location():
    try:
        response = requests.get("https://ipinfo.io")
        data = response.json()
        location = data["city"]
        return location
    except Exception as e:
        return "Unknown"

def get_default_language(location):
    location_language_map = {
        "Delhi": "Hindi",
        "Mumbai": "Hindi",
        "Chennai": "Tamil",
        "Kolkata": "Bengali",
        "Hyderabad": "Telugu",
        "Bangalore": "Kannada",
        "Ahmedabad": "Gujarati",
        "Pune": "Marathi",
        "Thiruvananthapuram": "Malayalam",
        "Amritsar": "Punjabi",
    }
    return location_language_map.get(location, "English")

def recognize_speech():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        st.write("Listening for your input... Speak now!")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        speech = recognizer.recognize_google(audio)
        st.write(f"You said: {speech}")
        return speech
    except sr.UnknownValueError:
        st.write("Sorry, I could not understand the audio.")
        return None
    except sr.RequestError:
        st.write("Could not request results from Google Speech Recognition service.")
        return None

def speak(text):
    tts = gTTS(text=text, lang="en")
    tts.save("output.mp3")
    st.audio("output.mp3", format="audio/mp3")

def get_nearest_hospital():
    try:
        ipinfo_data = requests.get("https://ipinfo.io").json()
        loc = ipinfo_data.get("loc")
        if not loc:
            return None

        lat, lon = map(float, loc.split(","))

        results = geocoder.reverse_geocode(lat, lon)

        if results and len(results):
            components = results[0]['components']
            area = (
                components.get('suburb') or
                components.get('neighbourhood') or
                components.get('city') or
                components.get('county') or
                "Unknown Area"
            )

            hospital_details = {
                "name": "City Medical Center",
                "area": area,
                "phone": "+1-234-567-8901",
                "latitude": lat,
                "longitude": lon
            }

            return hospital_details
        else:
            return None
    except Exception as e:
        st.error("Failed to determine your location or nearby hospital area.")
        return None

def give_speech_dictation(disease_name, urgency, hospital_details):
    response = f"Disease: {disease_name}, Urgency of treatment: {urgency}. " 
    speak(response)
    st.write(response)

def extract_disease_name(text):
    pattern = r"\*\*(.*?)\*\*"
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None

st.set_page_config(page_title="Aarogyam", page_icon=":robot:")

st.image("health-logo.png", width=200)
st.title("Aarogyam")
st.subheader("An AI application that helps people understand diseases by analyzing medical images.")

uploaded_file = st.file_uploader("Upload the image for analysis", type=["png", "jpg", "jpeg"])

if "generated_text" not in st.session_state:
    st.session_state["generated_text"] = ""

user_location = get_user_location()
default_language = get_default_language(user_location)

if uploaded_file:
    st.image(uploaded_file, width=200, caption="Uploaded image")
    analyze_button = st.button("Analyze!")

    if analyze_button:
        image_data = uploaded_file.getvalue()
        image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
        prompt_parts = [image_parts[0], system_prompt]
        
        st.header("Analysis on the basis of the provided image:")
        response = model.generate_content(prompt_parts)
        st.session_state["generated_text"] = response.text
        st.write(st.session_state["generated_text"])

        disease_name = extract_disease_name(st.session_state["generated_text"])
        
        urgency = "High" 
        hospital_details = get_nearest_hospital()
        
        if hospital_details:
            with st.sidebar:
                st.subheader("Nearest Hospital Info 🏥")
                st.write(f"**Name:** {hospital_details['name']}")
                st.write(f"**Area:** {hospital_details['area']}")
                st.write(f"**Phone:** {hospital_details['phone']}")
        else:
            with st.sidebar:
                st.subheader("Nearest Hospital Info 🏥")
                st.write("Unable to determine hospital details based on your location.")

        if hospital_details:
            give_speech_dictation(disease_name, urgency, hospital_details)
        else:
            st.write("Unable to find nearby hospitals.")

if st.session_state["generated_text"]:
    st.header("Translate the Analysis:")
    languages = {
        "English": "en",
        "Hindi": "hi",
        "Bengali": "bn",
        "Tamil": "ta",
        "Telugu": "te",
        "Marathi": "mr",
        "Gujarati": "gu",
        "Kannada": "kn",
        "Malayalam": "ml",
        "Punjabi": "pa",
    }

    selected_language = st.selectbox(
        "Select a language to translate",
        list(languages.keys()),
        index=list(languages.keys()).index(default_language)
    )

    translate_button = st.button("Translate")

    if translate_button:
        translated_text = GoogleTranslator(source='auto', target=languages[selected_language]).translate(st.session_state["generated_text"])
        st.write(f"Translated Text in {selected_language}:")
        st.write(translated_text)
