import datetime
import time
import re
import cv2
import face_recognition
import numpy as np
import os
import csv
import pickle
import subprocess
from gtts import gTTS
from flask import Flask, render_template, Response
from flask_cors import CORS
from google.cloud import texttospeech


os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/home/admin/Downloads/voce-interaction-chatbot-ff61efef1cdb.json"
client = texttospeech.TextToSpeechClient()


# Initialize Flask
app = Flask(__name__)
CORS(app)  # Enable CORS for the entire Flask app


#def say(mytext, language='en', accent="com"):
 #  myobj = gTTS(text=mytext, lang=language, tld=accent, slow=False)
  # myobj.save("welcome.mp3")
   #os.system("paplay welcome.mp3")
   
def say(mytext, language_code='en-US', voice_gender=texttospeech.SsmlVoiceGender.FEMALE):
    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=mytext)

    # Build the voice request with male gender
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        ssml_gender=voice_gender
    )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # Perform the text-to-speech request
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    # Save the output to an MP3 file
    with open('output.mp3', 'wb') as out:
        out.write(response.audio_content)
        print('Audio content written to file "output.mp3"')

    # Play the audio using a command-line tool
    os.system("paplay output.mp3")

# Example usage
#say("Hello, this is a male voice.")

# Load encodings
with open('encodings.pkl', 'rb') as f:
    all_encodings, classNames = pickle.load(f)

encodeListKnown = list(all_encodings.values())

def add_attendance(person, group_name):
    file_path = f'./facial_recognition_attendance/{group_name}_attendance.csv'
    
    # Check if the person tuple contains two elements
    if len(person) != 2:
        print(f"Error: Expected 2 elements in 'person' but got {len(person)}. Value: {person}")
        return  # Skip adding attendance if the data is incorrect

    person_id, person_name = person
    date_today = datetime.date.today().strftime('%d/%m/%Y')
    current_time = datetime.datetime.now().strftime('%H:%M:%S')

    if os.path.exists(file_path):
        with open(file_path, 'r', newline='') as file:
            reader = csv.DictReader(file)
            data = list(reader)
    else:
        data = []

    if data and date_today not in data[0]:
        for row in data:
            row[date_today] = ''

    found = False
    for row in data:
        if row['ID'] == person_id and row['Name'] == person_name:
            if row[date_today] == '':
                row[date_today] = current_time
            found = True
            break

    if not found:
        new_entry = {'ID': person_id, 'Name': person_name, date_today: current_time}
        data.append(new_entry)

    fieldnames = ['ID', 'Name'] + sorted([key for key in data[0].keys() if key not in ['ID', 'Name']])

    with open(file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"Successfully added attendance to {person_name}")
    say(f"Successfully added attendance to {person_name}")


def splitstr(text, delimiter):
    split_text = []
    current_word = ""
    for char in text:
        if char == delimiter:
            split_text.append(current_word)
            current_word = ""
        else:
            current_word += char

    if current_word:
        split_text.append(current_word)
    return split_text

# Directly set the camera to /dev/video0
selected_webcam_path = "/dev/video0"
cap = cv2.VideoCapture(selected_webcam_path)

countName = ''
count = 1
max_wipe_frames = 10
threshold = 0.4

def generate_frames():
    global countName, count, max_wipe_frames

    while True:
        success, img = cap.read()
        if not success:
            break

        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        facesCurFrame = face_recognition.face_locations(imgS)
        encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

        if not facesCurFrame:
            print("No faces detected")

        for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            matchIndex = np.argmin(faceDis)

            if matches[matchIndex] and faceDis[matchIndex] < threshold:
                name, group_name = classNames[matchIndex]
                if name == countName:
                    count += 1
                else:
                    count = 1
                countName = name
                print(name, ' [', count, ']')

                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.rectangle(img, (x1, y2), (x2, y2), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, name+': '+group_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                if count > 6:
                    person = splitstr(name, '_')[::-1]
                    add_attendance(person, group_name)
                    while max_wipe_frames and cap.isOpened() and cap.grab():
                        max_wipe_frames -= 1
                        pass
            else:
                countName = 'Unknown'
                print('Unknown [', count, ']')

                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.rectangle(img, (x1, y2), (x2, y2), (0, 0, 255), cv2.FILLED)
                cv2.putText(img, 'Unknown', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
