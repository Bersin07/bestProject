import datetime
import time
import cv2
import face_recognition
import numpy as np
import os
import csv
import pickle
import subprocess
from gtts import gTTS

def say(mytext, language='en', accent="com"):
    myobj = gTTS(text=mytext, lang=language, tld=accent, slow=False)
    myobj.save("welcome.mp3")
    os.system("paplay welcome.mp3")  # For Linux systems  ###playsound("welcome.mp3") supports for all os need to import! os.system("start welcome.mp3") for windows OS.

# Load encodings
with open('encodings.pkl', 'rb') as f:
    all_encodings, classNames = pickle.load(f)

encodeListKnown = list(all_encodings.values())

def add_attendance(person, group_name):
    file_path = f'./facial_recognition_attendance/{group_name}_attendance.csv'
    person_id, person_name = person
    date_today = datetime.date.today().strftime('%d/%m/%Y')
    current_time = datetime.datetime.now().strftime('%H:%M:%S')

    # Read the existing data
    if os.path.exists(file_path):
        with open(file_path, 'r', newline='') as file:
            reader = csv.DictReader(file)
            data = list(reader)
    else:
        data = []

    # Ensure all rows have today's date column if it doesn't already exist
    if data and date_today not in data[0]:
        for row in data:
            row[date_today] = ''  # Initialize with an empty string

    # Check for the person's row and update if not already marked today
    found = False
    for row in data:
        if row['ID'] == person_id and row['Name'] == person_name:
            if row[date_today] == '':  # Only update if empty
                row[date_today] = current_time
            found = True
            break

    # If not found, add a new entry
    if not found:
        new_entry = {'ID': person_id, 'Name': person_name, date_today: current_time}
        data.append(new_entry)

    # Determine fieldnames - ensure 'id' and 'name' are first, followed by dates
    fieldnames = ['ID', 'Name'] + sorted([key for key in data[0].keys() if key not in ['ID', 'Name']])

    # Write back to the CSV file
    with open(file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    print(f"Successfully added attendance to {person_name} {person_id}")
    say(f"Successfully added attendance to {person_name} {person_id}")

# Function to list available webcams
def list_webcams():
    result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True)
    output = result.stdout.split('\n')

    devices = []
    device_name = None
    for line in output:
        if line.endswith(':'):
            device_name = line.strip()[:-1]
        elif line.strip().startswith('/dev/'):
            device_path = line.strip()
            devices.append((device_name, device_path))

    return devices

# Check if selected_webcam.txt exists
if os.path.exists("selected_webcam.txt"):
    with open("selected_webcam.txt", "r") as f:
        selected_webcam_path = f.read().strip()
else:
    webcams = list_webcams()
    print("Available webcams:")
    for i, (name, path) in enumerate(webcams):
        print(f"{i}: {name} ({path})")

    selected_webcam = int(input("Select a webcam by entering the corresponding number: "))
    if selected_webcam >= len(webcams):
        print("Invalid selection. Exiting.")
        exit(1)

    selected_webcam_path = webcams[selected_webcam][1]

def splitstr(text, delimiter):
    split_text = []
    current_word = ""
    for char in text:
        if char == delimiter:
            split_text.append(current_word)
            current_word = ""  # Start a new word
        else:
            current_word += char

    # Add the last word if it wasn't empty
    if current_word:
        split_text.append(current_word)
    return split_text

def draw_rectangle_with_text(img, faceLoc, text, color):
    y1, x2, y2, x1 = faceLoc
    y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    cv2.rectangle(img, (x1, y2), (x2, y2), color, cv2.FILLED)
    cv2.putText(img, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

# Start capturing image frame by frame
cap = cv2.VideoCapture(selected_webcam_path)

countName = ''
count = 1

# Define the threshold for recognizing a face
threshold = 0.4  # Adjust this value as needed

while True:
    success, img = cap.read()
    if not success:
        print("Failed to capture image")
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

            draw_rectangle_with_text(img, faceLoc, f"{name}: {group_name}", (0, 255, 0))

            if count > 6:
                person = splitstr(name, '_')[::-1]
                add_attendance(person, group_name)
                # Clear the buffer by reading all available frames
                while cap.isOpened() and cap.grab():
                    pass

        else:
            countName = 'Unknown'
            print('Unknown [', count, ']')
            draw_rectangle_with_text(img, faceLoc, 'Unknown', (0, 0, 255))

    # Show the result window and exit the loop on pressing 'x'
    cv2.imshow('Webcam, Scanning...', img)
    if cv2.waitKey(1) & 0xFF == ord('x'):
        break

# Release video capture
cap.release()
cv2.destroyAllWindows()
print('--Project Runs Smoothly!--')
