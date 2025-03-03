import os
import threading
import subprocess
import pickle
import google.generativeai as genAI
from flask import Flask, jsonify, request, render_template
from google.cloud import texttospeech
from googletrans import Translator
import markdown
from flask_cors import CORS


os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/admin/Downloads/voce-interaction-chatbot-ff61efef1cdb.json"

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for the entire Flask app


# Google Gemini AI Configuration
GOOGLE_API_KEY = "AIzaSyANsCXLLMosM1qdpp_7Rf4gJmwqPlqPLXQ"  # Replace with your actual API key
genAI.configure(api_key=GOOGLE_API_KEY)
gemini_model = genAI.GenerativeModel('gemini-1.5-flash')

# Load Encodings and Chat History
chats = {}
historyBook = {}
peoples = ["step_by_step"]  # Add any other relevant pages as needed
for page in peoples:
    chats[page] = gemini_model.start_chat(history=[])

# Initialize Translator
translator = Translator()

# Static questions and answers dictionary
static_responses = {
    "What is iSpark?": "iSpark is an innovative education platform offering advanced robotics and STEM learning solutions.",
    "What is the capital of France?": "The capital of France is Paris.",
    "Who is the CEO of iSpark?": "The CEO of iSpark is Mohan.",
    # Add more static question-answer pairs as needed
}

# Text-to-Speech Function
def say(mytext, language='en-IN'):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=mytext)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language,
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open("response.mp3", "wb") as out:
        out.write(response.audio_content)
    subprocess.Popen(['paplay', 'response.mp3'], preexec_fn=os.setsid).wait()

def deliver(page, qn):
    # Check if the question is in the static responses
    if qn in static_responses:
        response_text = static_responses[qn]
    else:
        try:
            response = chats[page].send_message(qn, stream=False)
            response.resolve()
            response_text = response.text
        except Exception as e:
            print(f"Error in Gemini response delivery: {e}")
            return "Sorry, there was an error processing your request."

    # Convert Markdown to HTML with code block formatting
    response_text = markdown.markdown(response_text, extensions=['fenced_code', 'nl2br'])
    return response_text

# Home Route
@app.route('/')
def home():
    return render_template('index.html')

# API Endpoint for Chatbot Interaction
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get('message')
    if not user_input:
        return jsonify({'response': "Please enter a message."})

    response_text = deliver("step_by_step", user_input)
    return jsonify({'response': response_text})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5006)
