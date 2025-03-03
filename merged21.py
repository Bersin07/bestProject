from flask import Flask, render_template_string, jsonify
import os
import pygame
import time
import random
import google.generativeai as genAI
import speech_recognition as spchRcg
from googletrans import Translator
import gtts
import threading
import re
from pydub import AudioSegment
from pydub.playback import play
from dotenv import load_dotenv
import RPi.GPIO as GPIO
import yt_dlp
import subprocess
import simpleaudio as sa
import shutil
import stat
import uuid
import logging
from io import StringIO
import pickle
import whisper
import cv2
import signal
import torch
import soundfile as sf
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
from deep_translator import GoogleTranslator
from google.cloud import texttospeech
import socket
from flask_cors import CORS
import numpy as np
import requests



os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/admin/Downloads/voce-interaction-chatbot-ff61efef1cdb.json"

# Initialize the client
client = texttospeech.TextToSpeechClient()

translated_text = GoogleTranslator(source='auto', target='en').translate('Bonjour le monde')
print(translated_text)


app = Flask(__name__)
CORS(app)  # Enable CORS for the entire app



# Control variables
exit_condition = False
skip_response = False
listening = False
listening_thread = None
head_moving = False
head_thread = None
walking = False
stop_response = False  # Global flag to control response stopping
audio_process = None   # Global variable to track the audio process


# Create a StringIO buffer to capture logging output
log_buffer = StringIO()

# Set up logging to use our buffer
logging.basicConfig(level=logging.INFO, stream=log_buffer, format='%(message)s')

def translate_response(ans, target_language):
    # Step 1: Replace the company name with a placeholder
    company_name = "iSpark Learning Solutions"
    placeholder = "{iSpark Learning Solutions}"
    ans_with_placeholder = ans.replace(company_name, placeholder)

    # Step 2: Translate the text (excluding the placeholder)
    translation = translator.translate(ans_with_placeholder, dest=target_language)
    translated_text = translation.text

    # Step 3: Replace the placeholder back with the company name
    final_translated_text = translated_text.replace(placeholder, company_name)

    return final_translated_text



# Custom log filter to exclude HTTP logs and include only relevant logs
class CustomLogFilter(logging.Filter):
    def filter(self, record):
        # Exclude HTTP logs
        if any(x in record.msg for x in ['GET /', 'POST /', 'GET /get_output']):
            return False
        
        # Include only relevant logs
        relevant_keywords = ['Listening', 'Identifying question', 'Recognized', 'Chat Response', 'Answer']
        return any(keyword in record.msg for keyword in relevant_keywords)
        
# Apply the combined filter to the root logger
for handler in logging.getLogger().handlers:
    handler.addFilter(CustomLogFilter())

# Function to get log contents
def get_logs():
    logs = log_buffer.getvalue()
    return logs

# Route to retrieve terminal output/logs
@app.route('/get_output')
def get_output():
    logs = get_logs()
    logging.info("Fetching terminal output")  # Log when fetching terminal output
    return logs

#multilanguage

@app.route('/stopit', methods=['POST'])
def stop_response_action():
    global stop_response
    global audio_process
    stop_response = True  # Set the stop flag to True
    if audio_process:  # Stop the audio if it's playing
        os.killpg(os.getpgid(audio_process.pid), signal.SIGTERM)
        audio_process = None
    return jsonify({'status': 'stopped'})  # Send a response back to the front-end


def listen_for_stop_key():
    global stop_response
    global audio_process
    while True:
        key = input("Press 'e' to stop the response: ")  # Wait for input
        if key.lower() == 'e':  # Check if the input is 'e'
            print("Stopping response...")
            stop_response = True
            if audio_process:  # If audio is playing, stop it
                os.killpg(os.getpgid(audio_process.pid), signal.SIGTERM)  # Terminate the audio process
            break
            
# Configure Google Gemini AI
GOOGLE_API_KEY = ""  # Replace with your actual API key
genAI.configure(api_key=GOOGLE_API_KEY)
gemini_model = genAI.GenerativeModel('gemini-1.5-flash')

# Constants for Google Custom Search (if needed)
CSE_ID = ''  # Replace with your actual CSE ID

# Load Encodings and Class Names (if applicable for context-based responses)
with open('encodings.pkl', 'rb') as f:
    all_encodings, classNames = pickle.load(f)

encodeListKnown = list(all_encodings.values())
known = [f"{i[0]}_{i[1]}" for i in classNames]
peoples = known + ["Unknown_00_N/A", "step_by_step", "evaluator", "poet", "ispark", "allemin", "ismart"]
chats = {}

# Load or Initialize Chat Histories
if os.path.exists('historyBook.pkl'):
    with open('historyBook.pkl', 'rb') as f:
        historyBook = pickle.load(f)
    for page in historyBook.keys():
        chats[page] = gemini_model.start_chat(history=historyBook[page])
    for page in peoples:
        if page not in historyBook.keys():
            chats[page] = gemini_model.start_chat(history=[])
else:
    historyBook = {}
    for page in peoples:
        chats[page] = gemini_model.start_chat(history=[])

welcomed = {i: False for i in known}

# Initialize Translator and Whisper Model
translator = Translator()
whisper_model = whisper.load_model("small")

lang_names = ['english', 'tamil', 'telugu', 'kannada', 'malayalam', 'bengali', 'gujarati', 'punjabi', 'hindi', 'arabic']
lang_codes = ["en-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "bn-IN", "gu-IN", "pa-guru-IN", "hi-IN", "ar-SA"]



def listen_for_wakeup_word(wakeup_word="smart"):
    r = spchRcg.Recognizer()
    with spchRcg.Microphone() as source:
        # Adjust for ambient noise to improve speech recognition accuracy
        logging.info("Adjusting for ambient noise...")
        r.adjust_for_ambient_noise(source, duration=2.0)

        logging.info("Listening continuously for the wake-up word...")
        
        while True:  # Infinite loop for continuous listening
            try:
                # Continuously listen without a timeout or phrase time limit
                audio = r.listen(source)
                logging.info("Processing audio for wake-up word...")
                
                # Recognize the speech using Google Speech Recognition API
                transcript = r.recognize_google(audio)
                logging.info(f"Transcript: {transcript}")
                
                # Check if the wake-up word is in the transcript
                if wakeup_word.lower() in transcript.lower():
                    logging.info(f"Wake-up word '{wakeup_word}' detected.")
                    return True  # Exit the loop when the wake-up word is detected
                else:
                    logging.info(f"Wake-up word '{wakeup_word}' not detected. Heard: {transcript}")
            except spchRcg.UnknownValueError:
                logging.info("Could not understand the audio.")
                continue  # Continue listening if there was an error in recognizing speech
            except spchRcg.RequestError as e:
                logging.error(f"Could not request results from Google Speech Recognition service; {e}")
                continue  # Continue listening if there was a request error
            except Exception as e:
                logging.error(f"Error during wake-up word detection: {e}")
                continue  # Continue listening on any other error

def say(mytext, language='en-IN', gender='FEMALE'):
    global stop_response
    global audio_process
    global head_thread
    global head_moving
    company_name = "iSpark Learning Solutions"

    stop_response = False  # Reset the stop_response flag

    # Start head movement
    head_moving = True
    head_thread = threading.Thread(target=move_head_servo)
    head_thread.start()

    # Map gender to the correct enum
    gender_enum = texttospeech.SsmlVoiceGender.FEMALE  # Always use MALE voice

    # Synthesize speech using Google Cloud Text-to-Speech API
    synthesis_input = texttospeech.SynthesisInput(text=mytext)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=language,
        ssml_gender=gender_enum
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    # Generate the speech
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config
    )

    # Save the audio file
    with open("response2.mp3", "wb") as out:
        out.write(response.audio_content)

    # Check if stop has been requested before playing the audio
    if stop_response:
        return

    # Play the audio file and track the process
    audio_process = subprocess.Popen(['paplay', 'response2.mp3'], preexec_fn=os.setsid)

    # Wait for the audio process to complete
    audio_process.wait()

    # Stop head movement when the audio completes
    head_moving = False
    audio_process = None


def say_hi_indian_female():
    mytext = "Hi, do you have any question?"
    language = 'en-IN'  # Set the language to Indian English
    gender_enum = texttospeech.SsmlVoiceGender.FEMALE  # Use MALE voice

    # Synthesize speech using Google Cloud Text-to-Speech API
    synthesis_input = texttospeech.SynthesisInput(text=mytext)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=language,
        ssml_gender=gender_enum
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    # Generate the speech
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config
    )

    # Save the audio file
    audio_file = "/home/admin/Downloads/myTeacher/response1.mp3"
    with open(audio_file, "wb") as out:
        out.write(response.audio_content)
    
    # Play the audio file
    #play_audio_file(audio_file)

    print(f"Using default female voice for Indian English (language: {voice_params.language_code})")


def hear_for_language(lang_code):
    # First listen for the wake-up word "smart"
    #if not listen_for_wakeup_word("smart"):
     #   logging.info("Wake-up word not detected, stopping the function.")
      #  return None, None
        
    # Play the audio after detecting the wake-up word
    #os.system("paplay ./audio/anyques.mp3")  # Play a prompt asking for a question
    #say_hi_indian_female()
    os.system("paplay ./audio/anyques1.mp3")  # Play a prompt asking for a question


    
    logging.info(f"Listening for language: {lang_code}")
    r = spchRcg.Recognizer()
    with spchRcg.Microphone() as source:
        logging.info(f"Adjusting for ambient noise for language: {lang_code}")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)
        logging.info(f"Audio captured for {lang_code}")
    try:
        # Handle languages supported by Google Speech Recognition
        if lang_code in lang_codes[:10]:
            logging.info(f"Using Google recognition for {lang_code}")
            qn = r.recognize_google(audio, language=lang_code)
            logging.info(f"Recognized question: {qn}")
            if not qn:
                logging.warning(f"No question recognized, retrying for {lang_code}")
                return hear_for_language(lang_code)
            
            # Translate non-English languages
            if lang_code != "en-IN":  # Assuming 'english' is "en-IN"
                logging.info(f"Translating question from {lang_code} to English")
                translation = translator.translate(qn, src=lang_code[:2], dest='en')
                qn = translation.text
                logging.info(f"Translated question: {qn}")
            return qn, lang_code[:2]
        else:
            # Whisper recognition for unsupported languages
            logging.info(f"Using Whisper model for recognition")
            audio_data = np.frombuffer(audio.get_raw_data(), np.int16)
            sample_rate = 16000  # Whisper typically uses 16 kHz
            if audio.sample_rate != sample_rate:
                logging.info(f"Resampling audio from {audio.sample_rate} to {sample_rate}")
                audio_data = sf.resample(audio_data, audio.sample_rate, sample_rate)
            
            qn = whisper_model.transcribe(audio_data)
            logging.info(f"Whisper transcription: {qn}")
            
            if not qn:
                logging.warning(f"No question recognized by Whisper, retrying")
                return hear_for_language(lang_code)
            
            if qn["language"] != 'en':
                logging.info(f"Translating Whisper transcription from {qn['language']} to English")
                translation = translator.translate(qn["text"], src=qn["language"], dest='en')
                return translation.text, qn["language"]
            return qn["text"], qn["language"]
    except Exception as e:
        logging.error(f"Error during recognition for {lang_code}: {e}")
        os.system("paplay ./audio/pardon.mp3")  # Play a pardon audio prompt
        return hear_for_language(lang_code)




def deliver(page, qn):
    try:
        response = chats[page].send_message(qn, stream=False)
        response.resolve()
        ans = to_markdown(response.text)
        return ans
    except Exception as e:
        os.system("paplay ./audio/again.mp3")  # Play an error audio prompt
        print(e)
        return None

def to_markdown(txt):
    txt = txt.replace('*','    ')
    return txt.replace('#','    ')

def start_verbal_teaching(lang_code, page="step_by_step"):
    global skip_response
    skip_response = False  # Reset this flag at the start of each session
    logging.info(f"Starting verbal teaching session in {lang_code}")
    
    #os.system("paplay ./audio/anyques.mp3")  # Play a prompt asking for a question
    qn, lang = hear_for_language(lang_code)
    
    if qn is None:
        logging.error("No question recognized, stopping the function.")
        return  # Exit the function if no valid question is recognized

    logging.info(f"Question received: {qn}")  # Log the received question
    qn_lower = qn.lower()

    # Check for "play" or "sing" keyword
    if re.match(r"^\s*(play|sing)\b", qn_lower):  # Strictly check for 'play' or 'sing' at the beginning
        song_name_match = re.search(r'(play|sing) (.+)', qn_lower, re.IGNORECASE)
        if song_name_match:
            song_name = song_name_match.group(2)
            logging.info(f"Playing or singing requested: {song_name}")  # Log the song request
            handle_song_command(song_name)  # Call the song handler function
            return  # Exit the function after executing the song command
    
    # Check for static responses
    static_response = get_static_response(qn_lower)
    if static_response:
        ans = static_response
        logging.info(f"Static response: {ans}")  # Log the static response
    else:
        if "latest" in qn_lower:
            qn_lower = qn_lower.replace("latest ", "")
            search_results = google_custom_search(qn_lower, GOOGLE_API_KEY, CSE_ID)
            snippet = get_relevant_snippet(search_results)
            qn = f"my question: {qn}. Explain within 50 to 100 words."

            ans = deliver(page, qn + " Explain within 50 to 100 words.")
            logging.info(f"Latest response fetched: {ans}")  # Log the latest response
        else:
            # If no static response or "latest" keyword, proceed to dynamic response generation
            ans = deliver(page, qn + " explain within 50 to 100 words")
            logging.info(f"Dynamic response: {ans}")  # Log the dynamic response

    print(f"Answer: {ans}")
    logging.info(f"Answer delivered: {ans}")  # Log the final answer

    # Translation section
    if ans and lang:
        if lang != 'en':
            ans = translate_response(ans, lang)
            logging.info(f"Translated answer: {ans} in {lang}")  # Log the translation
        say(ans, language=lang)

        logging.info(f"Finished verbal teaching session in {lang_code}")



    # Optionally, continue the loop
    #loop = input("Do you want to continue? [y/N]: ")
    #if loop.lower() == 'y':
     #   start_verbal_teaching(page, 0, None)

# Optional: Functions for Google Custom Search (if you intend to use them)
def google_custom_search(query, api_key, cse_id):
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={cse_id}"
    response = requests.get(url)
    search_results = response.json()
    return search_results

def get_relevant_snippet(search_results):
    if 'items' in search_results:
        combined_snippet = ''
        for item in search_results['items']:
            snippet = item['snippet']
            combined_snippet += snippet + ' '
            if len(combined_snippet) > 200:  # Limit the combined snippet length
                combined_snippet = combined_snippet[:200] + '...'
                break
        return combined_snippet.strip()
    return "I couldn't find an answer to your question."



@app.route('/start/<language>', methods=['POST'])
def start_language(language):
    lang_code = {
        'english': 'en-IN',
        'tamil': 'ta-IN',
        'telugu': 'te-IN',
        'kannada': 'kn-IN',
        'malayalam': 'ml-IN',
        'bengali': 'bn-IN',
        'gujarati': 'gu-IN',
        'punjabi': 'pa-guru-IN',
        'hindi': 'hi-IN',
        'arabic': 'ar-SA'
    }.get(language.lower())
    
    if lang_code:
        threading.Thread(target=start_verbal_teaching, args=(lang_code,)).start()
        return jsonify({"message": f"{language.capitalize()} chatbot started!"})
    else:
        return jsonify({"message": "Invalid language selected."}), 400

#multi



# Load environment variables from .env file
geminiAPI = ''#replace your API

# Configure the generative AI with the API key
try:
    genAI.configure(api_key=geminiAPI)
except Exception as e:
    logging.error(f'API Key Error: {e}')
    exit(1)

# Initialize translator and speech recognizer
g_trans = Translator()
listener = spchRcg.Recognizer()

# Define GPIO pins for the servos and motors
motor_pins = {
    'motorA1': 5,
    'motorA2': 6,
    'motorB1': 13,
    'motorB2': 19,
    'motorC1': 26,
    'motorC2': 21,
    'motorD1': 20,
    'motorD2': 16
}

servo_pins = {
    'head': 18,
    'right_hand': 17,
    'left_hand': 27,
    'lips': 22,  # Define the pin for lips servo
    'eyes': 23   # Define the pin for eyes serv
}

# Initialize PWM for the servos
servo_pwm = {}

def initialize_gpio_and_pwm():
    global servo_pwm
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for pin in motor_pins.values():
        GPIO.setup(pin, GPIO.OUT)

    for pin in servo_pins.values():
        GPIO.setup(pin, GPIO.OUT)
    
    if not servo_pwm:
        servo_pwm = {name: GPIO.PWM(pin, 50) for name, pin in servo_pins.items()}
        for pwm in servo_pwm.values():
            pwm.start(0)  # Initialize with 0 duty cycle

def cleanup_gpio_and_pwm():
    global servo_pwm
    for pwm in servo_pwm.values():
        pwm.stop()
    GPIO.cleanup()
    servo_pwm.clear()  # Clear the dictionary after cleanup
    
    
    




# Restricted keywords
restricted_keywords = ['love', 'sex', 'inappropriate', 'violence', 'abuse', 'drugs', 'fuck', 'harassment', 'violent']

# Static response data and processing feedbacks
closing_note = ['thanks', 'thank', 'thank you', 'Thanks', 'Thank You', 'Thank']
developer_info = (
    "I'm an iSmart AI Teacher, developed by a team of software developers and engineers from i Spark Learning Solutions."
)
about_info = (
    "I'm the i-smart. version 1. Your AI Teacher. Created by Team I Spark."
)
processing_feedbacks = [
    "I'm working on the perfect answer for you.",
    "Just a moment, finding the best response.",
    "Hold on, generating the perfect reply.",
    "Please wait, preparing an accurate answer.",
    "One moment, I'm getting the right information."
]

# Conversation history
conversation_history = []

# Add Flask Route for Multilingual Feature
@app.route('/multilang_chatbot', methods=['POST'])
def multilang_chatbot():
    logging.info("Multilingual Chatbot route was triggered.")
    try:
        # Start the verbal teaching in a new thread
        start_verbal_teaching_threaded()
        return jsonify({"message": "Multilingual teaching session started."})
    except Exception as e:
        logging.error(f"Error in /multilang_chatbot route: {e}")
        return jsonify({"message": "Error occurred in multilingual chatbot"}), 500

def start_verbal_teaching_threaded():
    thread = threading.Thread(target=start_verbal_teaching)
    thread.start()



# New Route to start listening
@app.route('/send_s', methods=['POST'])
def send_s():
    global listening
    if not listening:
        listening = True
        threading.Thread(target=listen_for_speech).start()
        return create_json_response("Chatbot started listening.")
    return create_json_response("Chatbot is already listening.")

# New Route to stop listening
@app.route('/send_e', methods=['POST'])
def send_e():
    global skip_response, listening
    if listening:
        skip_response = True
        listening = False
        return create_json_response("Chatbot stopped listening.")
    return create_json_response("Chatbot is not listening.")
    
# Function definitions from both chatbotservo.py and Controller.py

def move_servo_smoothly(servo, start_duty_cycle, end_duty_cycle, steps=20, delay=0.02):
    step_size = (end_duty_cycle - start_duty_cycle) / steps
    for step in range(steps):
        current_duty_cycle = start_duty_cycle + step * step_size
        servo.ChangeDutyCycle(current_duty_cycle)
        time.sleep(delay)
    servo.ChangeDutyCycle(end_duty_cycle)
    time.sleep(0.1)  # Small delay to ensure the final position is reached
    servo.ChangeDutyCycle(0)  # Turn off the signal to prevent vibrations

def move_hand_servo():
    move_servo_smoothly(servo_pwm['right_hand'], 7.5, 10, steps=50, delay=0.02)
    time.sleep(3)
    servo_pwm['right_hand'].ChangeDutyCycle(0)

def move_head_servo():
    global head_moving
    while head_moving:
        time.sleep(0.5)
        move_servo_smoothly(servo_pwm['head'], 5, 7.5)    # Move to center
        time.sleep(0.5)
        move_servo_smoothly(servo_pwm['head'], 7.5, 10)    # Move back to right
        time.sleep(0.5)
        move_servo_smoothly(servo_pwm['head'], 10, 7.5)    # Move back to center
        time.sleep(0.5)
    servo_pwm['head'].ChangeDutyCycle(0)  # Stop the servo

def change_playback_speed(sound, speed=1.0):
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    })
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)

def play_response(respo_file, speed=1.0):
    global skip_response, head_moving, head_thread
    head_moving = True
    head_thread = threading.Thread(target=move_head_servo)
    head_thread.start()

    sound = AudioSegment.from_file(respo_file)
    sound = change_playback_speed(sound, speed)
    sound.export("adjusted_response.mp3", format="mp3")

    pygame.mixer.init()
    pygame.mixer.music.load("adjusted_response.mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if skip_response:
            pygame.mixer.music.stop()
            skip_response = False
            break
        time.sleep(0.1)
    pygame.mixer.quit()
    head_moving = False
    head_thread.join()

def eng_talk(word_to_talk, speed=1.0):
    try:
        response = gtts.gTTS(text=word_to_talk, lang='en')
        response.save('response.mp3')
        play_response('response.mp3', speed=speed)
        os.remove('response.mp3')
    except Exception as e:
        logging.error(f'Error in eng_talk: {e}')

def clean_text(text):
    return re.sub(r'[^A-Za-z0-9\s]', '', text)

def get_static_response(question):
    question = question.lower()
    static_responses = {
        # Common responses
    }

    for key, response in static_responses.items():
        if key in question:
            return response
    return None

def handle_greeting(name=None):
    move_hand_servo()
    if name:
        eng_talk(f"Hello, {name}! Nice to meet you.", speed=1.0)
    else:
        eng_talk("Hello! Nice to meet you.", speed=1.0)

def is_greeting(message):
    greetings = ["hello", "hi", "hey", "greetings"]
    excluded_start_words = ["debate","adequate","nowadays","now a days","do","i am","I","i","am","I'am","i'am","play","which", "when", "how", "what", "why", "where", "who","tell","tell me","can","How far","How long","Whose","Whom","In what way","Please","please tell","Please Tell","please","speak","Speak","fashion","as","an","explain","Explain","there","this","that","them","she","he","yeah"]
    if any(message.lower().startswith(word) for word in excluded_start_words):
        return False, None
    for greeting in greetings:
        if greeting in message.lower():
            name_match = re.search(rf'{greeting} my name is (\w+)', message, re.IGNORECASE)
            if name_match:
                return True, name_match.group(1)
            return True, None
    return False, None

def is_restricted(message):
    for keyword in restricted_keywords:
        if keyword in message.lower():
            return True
    return False

def search_and_download_audio(query, output_path="audio.mp3"):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch:{query}", download=True)
        if 'entries' in result:
            downloaded_file = output_path if os.path.exists(output_path) else output_path + ".mp3"
            return result['entries'][0]['title'], downloaded_file
        return None, None

def convert_to_wav(input_audio, output_audio):
    audio = AudioSegment.from_file(input_audio)
    audio.export(output_audio, format="wav")

def set_permissions(path):
    for root, dirs, files in os.walk(path):
        for dir_ in dirs:
            try:
                os.chown(os.path.join(root, dir_), os.getuid(), os.getgid())
                os.chmod(os.path.join(root, dir_), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                logging.info(f"Changed ownership and permissions for directory: {os.path.join(root, dir_)}")
            except PermissionError as e:
                logging.error(f"PermissionError changing permissions for directory {dir_}: {e}")
        for file_ in files:
            try:
                os.chown(os.path.join(root, file_), os.getuid(), os.getgid())
                os.chmod(os.path.join(root, file_), stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                logging.info(f"Changed ownership and permissions for file: {os.path.join(root, file_)}")
            except PermissionError as e:
                logging.error(f"PermissionError changing permissions for file {file_}: {e}")

def separate_vocals(input_audio, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    pretrained_models_dir = os.path.join(os.getcwd(), "pretrained_models")
    os.makedirs(pretrained_models_dir, exist_ok=True)
    set_permissions(pretrained_models_dir)

    uid = os.getuid()
    gid = os.getgid()
    command = (
        f"docker run --rm --user {uid}:{gid} "
        f"-e NUMBA_CACHE_DIR=/tmp/numba_cache "
        f"-e NUMBA_DISABLE_CACHING=1 "
        f"-v $(pwd)/{os.path.dirname(input_audio)}:/input "
        f"-v $(pwd)/{output_dir}:/output "
        f"-v $(pwd)/pretrained_models:/pretrained_models "
        f"spleeter-arm separate -p spleeter:2stems -o /output /input/{os.path.basename(input_audio)}"
    )
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"An error occurred while running Spleeter: {e}")
        return None

    vocal_path = os.path.join(output_dir, 'audio', 'vocals.wav')
    if not os.path.exists(vocal_path):
        logging.error(f"Vocal file not found in expected path: {vocal_path}")
        return None
    return vocal_path

def play_audio(audio_path):
    wave_obj = sa.WaveObject.from_wave_file(audio_path)
    play_obj = wave_obj.play()
    play_obj.wait_done()

def handle_song_command(query):
    audio_file = "audio.mp3"
    wav_file = "audio.wav"
    output_dir = f"separated_{uuid.uuid4().hex}"  # Generate a unique output directory

    if os.path.exists(audio_file):
        os.remove(audio_file)

    song_title, downloaded_file = search_and_download_audio(query, audio_file)

    if not song_title:
        eng_talk("No results found for the song.", speed=1.0)
        return

    convert_to_wav(downloaded_file, wav_file)
    vocal_file = separate_vocals(wav_file, output_dir)

    if vocal_file and os.path.exists(vocal_file):
        play_audio(vocal_file)
        shutil.rmtree(output_dir)  # Clean up after playing
    else:
        eng_talk("Vocal file not found.", speed=1.0)

def listen_for_action():
    global skip_response
    while True:
        user_input = input()
        if user_input == 's':
            return 'start'
        elif user_input == 'n':
            return 'next'
        elif user_input == 'e':
            skip_response = True

def action_listener():
    global exit_condition, skip_response, listening
    while not exit_condition:
        action = listen_for_action()
        if action == 'start' and not listening:
            eng_talk("Please ask  after 5 seconds", speed=1.0)
            time.sleep(0.1)  # Wait for 5 seconds before starting to listen
            return 'start'
        elif action == 'next' and not listening:
            return 'next'
        elif action == 'e' and listening:
            skip_response = True

def listen_for_speech():
    global listening
    try:
        with spchRcg.Microphone() as source:
            listener.adjust_for_ambient_noise(source)
            logging.info('Listening...')
            voice = listener.listen(source)
            logging.info('Identifying question...')
            try:
                voice_msg = listener.recognize_google(voice)
                logging.info(f'Recognized: {voice_msg}')
                conversation_history.append(f'User: {voice_msg}')

                if is_restricted(voice_msg):
                    eng_talk("Sorry, I cannot discuss this topic.", speed=1.0)
                    return

                is_greeting_message, name = is_greeting(voice_msg)
                if is_greeting_message:
                    handle_greeting(name)
                elif re.match(r"^\s*(play|sing)\b", voice_msg.lower()):  # Strictly check for 'play' or 'sing' at the beginning
                    song_name_match = re.search(r'(play|sing) (.+)', voice_msg, re.IGNORECASE)
                    if song_name_match:
                        song_name = song_name_match.group(2)
                        handle_song_command(song_name)
                else:
                    static_response = get_static_response(voice_msg)
                    if static_response:
                        chat_respo = static_response
                    else:
                        feedback = random.choice(processing_feedbacks)
                        eng_talk(feedback, speed=1.0)
                        time.sleep(0.5)  # Simulate processing time

                        try:
                            response = genAI.generate_text(prompt=f'Explain in a short paragraph: {voice_msg}')
                            logging.info(f'Raw response: {response}')  # Log raw response for debugging
                            if hasattr(response, 'candidates') and response.candidates:
                                chat_respo = response.candidates[0]['output']
                            elif hasattr(response, 'result'):
                                chat_respo = response.result
                            else:
                                chat_respo = 'I am sorry, I cannot generate a response right now.'
                            logging.info(f'Chat Response: {chat_respo}')
                        except Exception as e:
                            logging.error(f'Error generating text: {e}')
                            chat_respo = "I am sorry, I cannot generate a response right now."

                    conversation_history.append(f'iSmart AI Teacher: {chat_respo}')

                    if not skip_response:
                        try:
                            clean_respo = clean_text(chat_respo)
                            spoken = gtts.gTTS(text=clean_respo, lang='en')
                            spoken.save('gen_respo.mp3')
                            play_response('gen_respo.mp3', speed=1.0)
                            os.remove('gen_respo.mp3')
                        except Exception as e:
                            logging.error(f'Error with text-to-speech: {e}')
                            err_msg = "Sorry, I am not trained with this language - can you please ask me with my trained language!"
                            eng_talk(err_msg, speed=1.0)
            except spchRcg.UnknownValueError:
                eng_talk("Sorry, I did not catch that.", speed=1.0)
            except spchRcg.RequestError as e:
                eng_talk(f"Could not request results; {e}", speed=1.0)
    except Exception as e:
        logging.error(f'General error: {e}')
        eng_talk("Sorry, an error happened... Please excuse me.", speed=1.0)
    finally:
        listening = False

# Functions for Controller.py

def smooth_transition(pwm, start, end, steps=100, delay=0.03):
    step_size = (end - start) / steps
    duty_cycle = start
    for _ in range(steps):
        pwm.ChangeDutyCycle(duty_cycle)
        duty_cycle += step_size
        time.sleep(delay)
    pwm.ChangeDutyCycle(end)  # Ensure it ends at the exact end position
    time.sleep(0.5)  # Wait for the movement to complete
    pwm.ChangeDutyCycle(0)  # Stop the servo to prevent jittering

def walking_movement():
    global walking
    while walking:
        smooth_transition(servo_pwm['left_hand'], 7.5, 5, steps=50, delay=0.05)
        smooth_transition(servo_pwm['right_hand'], 7.5, 10, steps=50, delay=0.05)
        time.sleep(0.5)
        smooth_transition(servo_pwm['left_hand'], 5, 10, steps=50, delay=0.05)
        smooth_transition(servo_pwm['right_hand'], 10, 5, steps=50, delay=0.05)
        time.sleep(0.5)
    smooth_transition(servo_pwm['left_hand'], 5, 7.5, steps=50, delay=0.05)
    smooth_transition(servo_pwm['right_hand'], 5, 7.5, steps=50, delay=0.05)

@app.route('/')
def index():
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iSpark's iSMART Robot Base Controller</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            padding: 0;
            background: url('https://wallpapercat.com/w/full/e/4/1/1143047-3840x2160-desktop-4k-robot-background-photo.jpg') no-repeat center center fixed;
            background-size: cover;
            box-sizing: border-box;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 2fr 1fr;
            grid-template-rows: auto auto auto;
            gap: 20px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.85);
            border-radius: 20px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
            width: 90%;
            max-width: 800px;
            box-sizing: border-box;
            text-align: center;
        }

        .title {
            grid-column: span 3;
            color: #FF8C00;
            font-size: 1.8em;
            font-weight: bold;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px;
            border-radius: 10px;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
            box-sizing: border-box;
        }

        /* Control Sections */
        .controls {
            background: rgba(255, 255, 255, 0.9);
            padding: 15px;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            display: flex;
            flex-direction: column;
            align-items: center;
            max-width: 100%;
            box-sizing: border-box;
        }

        .controls h2 {
            font-size: 1.1em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .base-controls {
            grid-column: 2 / span 1;
            display: grid;
            grid-template-rows: auto 1fr auto;
            gap: 10px;
            align-items: center;
        }

        .base-controls button {
            font-size: 14px;
            padding: 10px 15px;
            background: linear-gradient(135deg, #007bff, #0056b3);
            border-radius: 8px;
            border: none;
            color: white;
            cursor: pointer;
            transition: background 0.3s, transform 0.3s;
        }

        /* Button Layout and Styles */
        .control-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
            align-items: center;
        }

        .control-group button {
            font-size: 14px;
            padding: 8px 12px;
            background: linear-gradient(135deg, #007bff, #0056b3);
            border-radius: 8px;
            border: none;
            color: white;
            cursor: pointer;
            transition: background 0.3s, transform 0.3s;
        }

        .control-group button:hover,
        .back-button:hover {
            background: linear-gradient(135deg, #0056b3, #007bff);
            transform: scale(1.05);
        }

        .control-group button:active,
        .back-button:active {
            transform: scale(0.95);
        }

        /* Icons */
        .icon {
            color: #FF8C00;
        }

        /* Back Button */
        .back-button {
            grid-column: 1 / span 3;
            font-size: 16px;
            padding: 10px 20px;
            margin-top: 20px;
            background: linear-gradient(135deg, #007bff, #0056b3);
            border-radius: 8px;
            border: none;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: background 0.3s, transform 0.3s;
        }

        /* Responsive Adjustments */
        @media (max-width: 768px) {
            .title {
                font-size: 1.5em;
            }
            .controls h2 {
                font-size: 1em;
            }
            .control-group button,
            .base-controls button,
            .back-button {
                font-size: 12px;
                padding: 8px 12px;
            }
        }

        @media (max-width: 480px) {
            .title {
                font-size: 1.3em;
            }
            .controls h2 {
                font-size: 0.9em;
            }
            .control-group button,
            .base-controls button,
            .back-button {
                font-size: 11px;
                padding: 6px 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Title -->
        <div class="title"><i class="fas fa-robot"></i> iSpark's iSMART Robot Base Controller</div>

        <!-- Left Hand Control -->
        <div class="controls">
            <h2><i class="fas fa-hand-paper icon"></i> Left Hand Control</h2>
            <div class="control-group">
                <button onclick="sendCommand('left_hand_up')"><i class="fas fa-hand-point-up"></i> Up</button>
                <button onclick="sendCommand('left_hand_down')"><i class="fas fa-hand-point-down"></i> Down</button>
            </div>
        </div>

        <!-- Base Control -->
        <div class="base-controls">
            <button onclick="sendCommand('forward')"><i class="fas fa-arrow-up"></i> Forward</button>
            <div style="display: flex; gap: 10px; justify-content: center;">
                <button onclick="sendCommand('left')"><i class="fas fa-arrow-left"></i> Left</button>
                <button onclick="sendCommand('stop')"><i class="fas fa-stop"></i> Stop</button>
                <button onclick="sendCommand('right')"><i class="fas fa-arrow-right"></i> Right</button>
            </div>
            <button onclick="sendCommand('backward')"><i class="fas fa-arrow-down"></i> Backward</button>
        </div>

        <!-- Right Hand Control -->
        <div class="controls">
            <h2><i class="fas fa-hand-paper icon"></i> Right Hand Control</h2>
            <div class="control-group">
                <button onclick="sendCommand('right_hand_up')"><i class="fas fa-hand-point-up"></i> Up</button>
                <button onclick="sendCommand('right_hand_down')"><i class="fas fa-hand-point-down"></i> Down</button>
            </div>
        </div>

        <!-- Head Control -->
        <div class="controls" style="grid-column: 1 / span 3;">
            <h2><i class="fas fa-head-side icon"></i> Head Control</h2>
            <div class="control-group" style="flex-direction: row; gap: 20px;">
                <button onclick="sendCommand('head_left')"><i class="fas fa-arrow-left"></i> Left</button>
                <button onclick="sendCommand('head_center')"><i class="fas fa-circle"></i> Center</button>
                <button onclick="sendCommand('head_right')"><i class="fas fa-arrow-right"></i> Right</button>
            </div>
        </div>

        <!-- Back Button -->
        <button class="back-button" onclick="goToTerminal()"><i class="fas fa-arrow-left"></i> Back</button>
    </div>

    <script>
        function goToTerminal() {
            window.location.href = '/terminal';  // Redirects to the index route
        }
    
        function sendCommand(command) {
            fetch('/' + command)
                .then(response => response.json())
                .then(data => console.log(data.message))
                .catch(error => console.error('Error:', error));
        }
    </script>
</body>
</html>




    '''
    return render_template_string(html)

@app.route('/terminal')
def terminal():
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terminal Output</title>
    <style>
        body {
            background-color: #f0f4f8;
            color: #333333;
            font-family: 'Courier New', Courier, monospace;
            padding: 20px;
            margin: 0;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
            min-height: 100vh;
        }

        .logo-container {
            position: absolute;
            top: 20px;
            left: 20px;
        }

        .logo-container img {
            max-width: 80px;
            height: auto;
        }

        .layout-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            max-width: 1200px;
            margin-bottom: 20px;
        }

        .button-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 12px;
            align-self: flex-start;
            margin-top: 125px; /* Add margin to drop the buttons down */
        }

        .button-container button {
            padding: 10px 16px;
            font-size: 14px;
            border: none;
            border-radius: 6px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
            width: 150px;
            transition: background-color 0.3s ease;
        }

        .buttonb button:hover {
            background-color: #0056b3;
        }
        
                .button-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 12px;
            align-self: flex-start;
            margin-top: 125px; /* Add margin to drop the buttons down */
        }

        .buttonb button {
            padding: 10px 16px;
            font-size: 14px;
            border: none;
            border-radius: 6px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
            width: 150px;
            transition: background-color 0.3s ease;
        }

        .buttonb button:hover {
            background-color: #0056b3;
        }


        .terminal {
            flex: 1;
            padding: 20px;
            border-radius: 12px;
            background-color: #ffffff;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 700px;
            margin: 0 20px;
        }

        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            border-bottom: 2px solid #00aaff;
            padding-bottom: 12px;
        }

        .terminal-header .logo {
            font-size: 28px;
            font-weight: bold;
            color: #00aaff;
        }

        .terminal-header .heading {
            font-size: 18px;
            color: #555555;
            font-weight: bold;
        }

        .terminal-output {
            white-space: pre-wrap;
            overflow-y: auto;
            height: 400px;
            font-size: 16px;
            line-height: 1.5;
            color: #333333;
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 10px;
            box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.1);
        }

        .blinking-cursor {
            font-weight: bold;
            font-size: 18px;
            color: #00aaff;
            animation: blink 0.7s infinite;
        }

        @keyframes blink {
            50% { opacity: 0; }
        }

        .controls {
            width: 100%;
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            text-align: center;
            margin-top: 20px;
        }

        .controls h2 {
            font-size: 20px;
            margin-bottom: 20px;
        }

        .controls button {
            padding: 12px 24px;
            margin: 10px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
            transition: background 0.3s, transform 0.3s;
            min-width: 160px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .controls button:hover {
            background-color: #0056b3;
            transform: scale(1.05);
        }

        .controls button:active {
            transform: scale(0.95);
        }

    </style>
</head>
<body>
    <div class="logo-container">
        <!--<img src="https://isparkinnovators.com/logos/iSpark%20logo_final.png" alt="Company Logo">-->
    </div>

    <div class="layout-container">
        <!-- Left Button Group -->
        <div class="button-container">
            <button onclick="sendLanguage('english')">English</button>
            <button onclick="sendLanguage('tamil')">Tamil</button>
            <button onclick="sendLanguage('hindi')">Hindi</button>
            <button onclick="sendLanguage('telugu')">Telugu</button>
            <button onclick="sendLanguage('kannada')">Kannada</button>
        </div>

        <!-- Terminal -->
        <div class="terminal">
            <div class="terminal-header">
                <div class="logo">iCUBE</div>
                <div class="heading"></div>
            </div>
            <div class="terminal-output" id="output">
                <p>No output yet...</p>
                <span class="blinking-cursor">|</span>
            </div>
        </div>

        <!-- Right Button Group -->
        <div class="button-container">
            <button onclick="sendLanguage('malayalam')">Malayalam</button>
            <button onclick="sendLanguage('gujarati')">Gujarati</button>
            <button onclick="sendLanguage('bengali')">Bengali</button>
            <button onclick="sendLanguage('punjabi')">Punjabi</button>
            <button onclick="sendLanguage('arabic')">Arabic</button>
        </div>
    </div>

    <!-- Chatbot Control Section 
    <div class="controls">
        <h2>Chatbot Control</h2>
        <button onclick="SendCommand('send_s')">Start Listening</button>
        <button onclick="SendCommand('send_e')">Stop Listening</button>
        

    </div>
-->
<div class="buttonb">
<button onclick="stopit()">Stop Response</button>
<button onclick="stopMergedProcess()">Stop AI Teacher</button>
<!--<button onclick="goToHome()">AI Teacher Control</button>-->
</div>
    <script>
        let autoScroll = true;
        const outputDiv = document.getElementById('output');

        // Event listener to detect manual scrolling and disable auto-scroll if not at the bottom
        outputDiv.addEventListener('scroll', () => {
            const isScrolledToBottom = outputDiv.scrollHeight - outputDiv.clientHeight <= outputDiv.scrollTop + 10;
            autoScroll = isScrolledToBottom;  // Enable auto-scroll only when at the bottom
        });
        
        
    
   // Function to get the current IP address from the server
        function getCurrentIP() {
            return fetch('/get_ip')
                .then(response => response.json())
                .then(data => data.ip)  // Assuming the server returns { "ip": "your-ip-address" }
                .catch((error) => {
                    console.error('Error fetching IP address:', error);
                    return null;  // Return null if there's an error
                });
        }

        // Function to stop the AI Teacher and redirect
        function stopMergedProcess() {
            getCurrentIP().then(currentIP => {
                if (currentIP) {
                    fetch(`http://${currentIP}:5001/stop_ai_teacher`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                    })
                    .then(response => {
                        if (response.ok) {
                            window.location.href = `http://${currentIP}:5001/`;  // Redirect to kiosk home
                        } else {
                            console.error('Failed to stop AI Teacher:', response.statusText);
                        }
                    })
                    .catch((error) => {
                        console.error('Error:', error);
                    });
                } else {
                    console.error('Failed to get current IP address');
                }
            });
        }

        
        
        
        
        function stopit() {
            fetch('/stopit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
            })
            .catch((error) => {
                console.error('Error:', error);
            });
        }
        
        


        // Function to update the output and optionally auto-scroll
        function updateOutput() {
            fetch('/get_output')
                .then(response => response.text())
                .then(data => {
                    const outputDiv = document.getElementById('output');
                    const wasScrolledToBottom = autoScroll;

                    // Update the terminal output with new data
                    outputDiv.innerHTML = data + '<span class="blinking-cursor">|</span>';

                    // Auto-scroll to the bottom if autoScroll is true (user didn't scroll up)
                    if (wasScrolledToBottom) {
                        outputDiv.scrollTop = outputDiv.scrollHeight;
                    }
                });
        }

        function sendLanguage(language) {
            fetch('/start/' + language, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    // You can handle the success case here without an alert
                    console.log(data.message); // Logs the success message in the console
                })
                .catch(error => {
                    // Handle errors here without an alert
                    console.error('Error:', error); // Logs the error in the console
                });
        }

        function SendCommand(command) {
            fetch('/' + command, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    const outputDiv = document.getElementById('output');
                    outputDiv.innerHTML += '<p>' + data.message + '</p>';
                    outputDiv.scrollTop = outputDiv.scrollHeight;
                });
        }
        
         function goToHome() {
            window.location.href = '/';  // Redirects to the index route
        }

        setInterval(updateOutput, 1000);
    </script>
</body>
</html>


    '''
    return render_template_string(html)


def create_json_response(message):
    return jsonify({"message": message})
    
    

def get_ip_address():
    """Get the current IP address of the device."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't have to be reachable
        s.connect(('10.254.254.254', 1))
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = '127.0.0.1'
    finally:
        s.close()
    return ip_address

@app.route('/get_ip')
def get_ip():
    # Get the current IP address and return it as JSON
    current_ip = get_ip_address()
    return {'ip': current_ip}

@app.route('/forward')
def forward():
    try:
        logging.info("Moving Forward")
        GPIO.output(motor_pins['motorA1'], GPIO.HIGH)
        GPIO.output(motor_pins['motorA2'], GPIO.LOW)
        GPIO.output(motor_pins['motorB1'], GPIO.HIGH)
        GPIO.output(motor_pins['motorB2'], GPIO.LOW)
        GPIO.output(motor_pins['motorC1'], GPIO.HIGH)
        GPIO.output(motor_pins['motorC2'], GPIO.LOW)
        GPIO.output(motor_pins['motorD1'], GPIO.HIGH)
        GPIO.output(motor_pins['motorD2'], GPIO.LOW)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Moving Forward")

@app.route('/backward')
def backward():
    try:
        logging.info("Moving Backward")
        GPIO.output(motor_pins['motorA1'], GPIO.LOW)
        GPIO.output(motor_pins['motorA2'], GPIO.HIGH)
        GPIO.output(motor_pins['motorB1'], GPIO.LOW)
        GPIO.output(motor_pins['motorB2'], GPIO.HIGH)
        GPIO.output(motor_pins['motorC1'], GPIO.LOW)
        GPIO.output(motor_pins['motorC2'], GPIO.HIGH)
        GPIO.output(motor_pins['motorD1'], GPIO.LOW)
        GPIO.output(motor_pins['motorD2'], GPIO.HIGH)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Moving Backward")

@app.route('/left')
def left():
    try:
        logging.info("Turning Left")
        GPIO.output(motor_pins['motorA1'], GPIO.LOW)
        GPIO.output(motor_pins['motorA2'], GPIO.HIGH)
        GPIO.output(motor_pins['motorB1'], GPIO.LOW)
        GPIO.output(motor_pins['motorB2'], GPIO.HIGH)
        GPIO.output(motor_pins['motorC1'], GPIO.HIGH)
        GPIO.output(motor_pins['motorC2'], GPIO.LOW)
        GPIO.output(motor_pins['motorD1'], GPIO.HIGH)
        GPIO.output(motor_pins['motorD2'], GPIO.LOW)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Turning Left")

@app.route('/right')
def right():
    try:
        logging.info("Turning Right")
        GPIO.output(motor_pins['motorA1'], GPIO.HIGH)
        GPIO.output(motor_pins['motorA2'], GPIO.LOW)
        GPIO.output(motor_pins['motorB1'], GPIO.HIGH)
        GPIO.output(motor_pins['motorB2'], GPIO.LOW)
        GPIO.output(motor_pins['motorC1'], GPIO.LOW)
        GPIO.output(motor_pins['motorC2'], GPIO.HIGH)
        GPIO.output(motor_pins['motorD1'], GPIO.LOW)
        GPIO.output(motor_pins['motorD2'], GPIO.HIGH)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Turning Right")
    
    
@app.route('/stop_audio', methods=['POST'])
def stop_audio():
    global skip_response
    skip_response = True  # This will stop the chatbot's current response
    return jsonify({"message": "Chatbot response stopped."})


@app.route('/stop')
def stop():
    try:
        logging.info("Stopping")
        for pin in motor_pins.values():
            GPIO.output(pin, GPIO.LOW)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Stopping")

@app.route('/head_left')
def head_left():
    try:
        logging.info("Moving Head Left")
        smooth_transition(servo_pwm['head'], 8, 10, steps=20, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Head Left")

@app.route('/head_center')
def head_center():
    try:
        logging.info("Centering Head")
        smooth_transition(servo_pwm['head'], 8, 8, steps=20, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Head Center")

@app.route('/head_right')
def head_right():
    try:
        logging.info("Moving Head Right")
        smooth_transition(servo_pwm['head'], 8, 5, steps=20, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Head Right")

@app.route('/right_hand_up')
def right_hand_up():
    try:
        logging.info("Moving Right Hand Up")
        smooth_transition(servo_pwm['right_hand'], 7.5, 10, steps=50, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Right Hand Up")

@app.route('/right_hand_down')
def right_hand_down():
    try:
        logging.info("Moving Right Hand Down")
        smooth_transition(servo_pwm['right_hand'], 10, 7.5, steps=50, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Right Hand Down")

@app.route('/left_hand_up')
def left_hand_up():
    try:
        logging.info("Moving Left Hand Up")
        smooth_transition(servo_pwm['left_hand'], 7.5, 5, steps=50, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Left Hand Up")

@app.route('/left_hand_down')
def left_hand_down():
    try:
        logging.info("Moving Left Hand Down")
        smooth_transition(servo_pwm['left_hand'], 5, 7.5, steps=50, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Left Hand Down")

@app.route('/toggle_walking')
def toggle_walking():
    global walking
    if walking:
        logging.info("Stopping Walking Movement")
        walking = False
        return create_json_response("Stopped Walking Movement")
    else:
        logging.info("Starting Walking Movement")
        walking = True
        thread = threading.Thread(target=walking_movement)
        thread.start()
        return create_json_response("Started Walking Movement")
        
#lips and eyes 
@app.route('/lips_up')
def lips_up():
    try:
        logging.info("Moving Lips Up")
        smooth_transition(servo_pwm['lips'], 8, 5, steps=25, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Lips Up")

@app.route('/lips_down')
def lips_down():
    try:
        logging.info("Moving Lips Down")
        smooth_transition(servo_pwm['lips'], 5, 8, steps=25, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Lips Down")

@app.route('/eyes_left')
def eyes_left():
    try:
        logging.info("Moving Eyes Left")
        smooth_transition(servo_pwm['eyes'], 7.5, 5, steps=50, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Eyes Left")

@app.route('/eyes_right')
def eyes_right():
    try:
        logging.info("Moving Eyes Right")
        smooth_transition(servo_pwm['eyes'], 7.5, 10, steps=50, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Eyes Right")
    
    
@app.route('/eyes_center')
def eyes_center():
    try:
        logging.info("Moving Eyes Right")
        smooth_transition(servo_pwm['eyes'], 5, 7.5, steps=50, delay=0.03)
    except Exception as e:
        return create_json_response(f"Error: {e}")
    return create_json_response("Eyes center")



@app.route('/start_chatbot')
def start_chatbot():
    global exit_condition
    exit_condition = False
    chatbot_thread = threading.Thread(target=chatbot_main_loop)
    chatbot_thread.start()
    return create_json_response("Started Chatbot")

@app.route('/stop_chatbot')
def stop_chatbot():
    global exit_condition
    exit_condition = True
    return create_json_response("Stopped Chatbot")

def chatbot_main_loop():
    while not exit_condition:
        action = action_listener()
        if action == 'start':
            listening = True
            listening_thread = threading.Thread(target=listen_for_speech)
            listening_thread.start()
        elif action == 'next':
            continue


if __name__ == '__main__':
    logging.info("Flask app is starting")
    try:
        initialize_gpio_and_pwm()
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_gpio_and_pwm()
