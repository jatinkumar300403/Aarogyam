import streamlit as st
from pathlib import Path
import google.generativeai as genai

from api_key import api_key

#configure genai with api key
genai.configure(api_key=api_key)

# Create the model
generation_config = {
  "temperature": 0.4,
  "top_p": 1,
  "top_k":32,
  "max_output_tokens": 4096,
}
system_prompt = """

As a highly skilled medical practitioner specializing in image analysis, you are tasked with examining medical images for a renowned hospital. Your expertise is crucial in identifying any anomalies, diseases, or health issues that may be present in the image.

Your Responsibility:

1.Detailed analysis: Thoroughly analyze each image, focusing on identifying any abnormal findings.
2.Findings Report: Document all observed anomalies or signs of disease. Clearly articulate these findings in a structured format.
3.Recommendations and Next Steps: Based on your analysis, suggest potential next steps, steps including further tests or treatments as applicable.
4.Treatment Suggestions: If appropriate, recommend possible treatment options or interventions.

Important Notes:

1.Scope of Response: Only respond if the image pertains to human health issues.
2.Clarity of Images: In cases where the image quality impedes clear analysis note that certain aspects are 'Unable to be determined based on provided image'.
3.Disclaimer: Accompany your analysis with a disclaimer: "Consult with a doctor before making any decisions."
4.Your insights are valuable in guiding clinical decisions. Please proceed with the analysis, adhering to the structured approach outlined above.

Please provide me an output response with these four headings Detailed Analysis, Findings Report, Recommendations and Next Steps, Treatment Suggestions
"""

#model config
model = genai.GenerativeModel(
  model_name="gemini-1.5-pro",
  generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)

#page confirmation
st.set_page_config(page_title="Aarogyam",page_icon=":robot:")

#set logo
st.image("health-logo.png",width=200)

#set title
st.title("Aarogyam")

#set subheading
st.subheader("An AI application that help people to get an about the disease by just using it's images!")
uploaded_file = st.file_uploader("Upload the medical image for analysis", type=["png", "jpg", "jpeg"])
if uploaded_file:
    st.image(uploaded_file, width=200, caption="Uploaded image")
submit_button = st.button("Analyze!")

if submit_button:
    #process the image
    image_data = uploaded_file.getvalue()

    #for image
    image_parts = [
        {
            "mime_type": "image/jpeg",
            "data": image_data
        },
    ]

    #for prompt
    prompt_parts = [
        image_parts[0],
        system_prompt,
    ]
    #generate response based on prompt and image
    st.title("Analysis on the basis of the provided image: ")
    response = model.generate_content(prompt_parts)
    st.write(response.text)