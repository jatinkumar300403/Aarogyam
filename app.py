import streamlit as st
from pathlib import Path
import google.generativeai as genai
from api_key import api_key
from googletrans import Translator
from geopy.geocoders import Nominatim
import requests
import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import re  # For regular expression matching

# Configure genai with API key
genai.configure(api_key=api_key)

# Initialize the translator
translator = Translator()

# Create the model
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

# Model config
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
)

# Function to fetch user's approximate location
def get_user_location():
    try:
        # Using IP-based geolocation
        response = requests.get("https://ipinfo.io")
        data = response.json()
        location = data["city"]
        return location
    except Exception as e:
        return "Unknown"

# Map location to default language
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
    return location_language_map.get(location, "English")  # Default to English

# Function to recognize speech and process input
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

# Function to convert text to speech
def speak(text):
    # Generate speech using gTTS
    tts = gTTS(text=text, lang="en")
    tts.save("output.mp3")

    # Streamlit can play the audio
    st.audio("output.mp3", format="audio/mp3")

# Function to fetch nearest hospital and area details
def get_nearest_hospital(location):
    geolocator = Nominatim(user_agent="myApp")
    location_obj = geolocator.geocode(location)

    if location_obj:
        lat, lon = location_obj.latitude, location_obj.longitude
        # Reverse geocode to get the area or address
        reverse = geolocator.reverse((lat, lon), language='en')
        area = reverse.raw.get('address', {}).get('suburb', 'Unknown Area')  # Get the area or suburb
        
        # Mock hospital details (you would integrate with a real hospital API here)
        hospital_details = {
            "name": "City Medical Center",
            "area": area,
            "phone": "+1-234-567-8901"
        }
        return hospital_details
    else:
        return None

# Function to give speech dictation for analysis
def give_speech_dictation(disease_name, urgency, hospital_details):
    # Generate the dictation response
    response = f"Disease: {disease_name}, Urgency of treatment: {urgency}. " \
            #    f"For emergency services, call: {hospital_details['phone']}. " \
            #    f"The nearest hospital is located in: {hospital_details['area']}."
    
    # Speak the response
    speak(response)
    st.write(response)  # Also display the text

# Function to extract the disease name from the response
def extract_disease_name(text):
    # Regex pattern to capture bold text (disease name) based on the system prompt structure
    pattern = r"\*\*(.*?)\*\*"
    match = re.search(pattern, text)
    if match:
        return match.group(1)  # Return the first match (the disease name)
    return None

# Page configuration
st.set_page_config(page_title="Aarogyam", page_icon=":robot:")

# Set logo and title
st.image("health-logo.png", width=200)
st.title("Aarogyam")
st.subheader("An AI application that helps people understand diseases by analyzing medical images.")

# File uploader
uploaded_file = st.file_uploader("Upload the image for analysis", type=["png", "jpg", "jpeg"])

# Initialize session state for generated text
if "generated_text" not in st.session_state:
    st.session_state["generated_text"] = ""

# Get user location (this example uses a hardcoded location for simplicity)
user_location = get_user_location()
default_language = get_default_language(user_location)

if uploaded_file:
    st.image(uploaded_file, width=200, caption="Uploaded image")
    analyze_button = st.button("Analyze!")

    if analyze_button:
        # Process the image (existing code)
        image_data = uploaded_file.getvalue()
        image_parts = [{"mime_type": "image/jpeg", "data": image_data}]
        prompt_parts = [image_parts[0], system_prompt]
        
        st.header("Analysis on the basis of the provided image:")
        response = model.generate_content(prompt_parts)
        st.session_state["generated_text"] = response.text
        st.write(st.session_state["generated_text"])

        # Extract disease name from the generated response
        disease_name = extract_disease_name(st.session_state["generated_text"])
        # if disease_name:
        #     st.write(f"Disease Name Extracted: {disease_name}")
        
        # Extract urgency and hospital details (this can be dynamically modified based on response)
        urgency = "High"  # Replace with dynamic analysis output
        hospital_details = get_nearest_hospital(user_location)
        
        if hospital_details:
            give_speech_dictation(disease_name, urgency, hospital_details)
        else:
            st.write("Unable to find nearby hospitals.")

# Translation options
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

    st.write(f"Detected Location: **{user_location}** ")

    # Use default language or allow override
    selected_language = st.selectbox(
        "Select a language to translate",
        list(languages.keys()),
        index=list(languages.keys()).index(default_language)
    )

    translate_button = st.button("Translate")

    if translate_button:
        # Translate the text
        translated_text = translator.translate(
            st.session_state["generated_text"], src="en", dest=languages[selected_language]
        ).text
        st.write(f"Translated Text in {selected_language}:")
        st.write(translated_text)
