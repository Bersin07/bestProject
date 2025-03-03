from flask import Flask, render_template, jsonify
import os
import cv2
import face_recognition
import pickle
import numpy as np
from threading import Thread
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire Flask app

# Paths and data structures
base_path = 'facial_recognition_attendance'
group_paths = [os.path.join(base_path, group) for group in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, group))]
all_encodings = {}
classNames = []

# Store progress status
progress_status = {
    "status": "Idle",
    "current": "",
    "total_groups": len(group_paths),
    "current_group": 0,
    "error_log": []
}

#### Function to calculate average encoding for a person
def calculate_average_encoding(images):
    encodings = []
    for img in images:
        try:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_encs = face_recognition.face_encodings(img, num_jitters=10)
            if face_encs:
                encodings.append(face_encs[0])
            else:
                progress_status['error_log'].append("No face found in an image. Skipping this image.")
        except Exception as e:
            progress_status['error_log'].append(f"Error processing an image. Skipping this image. Error: {e}")
            continue
    if encodings:
        return np.mean(encodings, axis=0)
    else:
        raise ValueError("No encodings found for this person.")

# Function to perform encoding in a separate thread
def encode_faces():
    global all_encodings, classNames
    progress_status["status"] = "Training in Progress"
    for idx, group_path in enumerate(group_paths):
        group_name = os.path.basename(group_path)
        progress_status["current_group"] = idx + 1
        for person in os.listdir(group_path):
            person_path = os.path.join(group_path, person)
            if os.path.isdir(person_path):
                images = []
                for img_name in os.listdir(person_path):
                    img_path = os.path.join(person_path, img_name)
                    curImg = cv2.imread(img_path)
                    if curImg is None:
                        progress_status['error_log'].append(f"Failed to read image {img_path}. Skipping this image.")
                        continue
                    images.append(curImg)
                
                if images:
                    try:
                        avg_encoding = calculate_average_encoding(images)
                        all_encodings[(person, group_name)] = avg_encoding
                        classNames.append((person, group_name))
                        progress_status["current"] = f"Encoded {person} in group {group_name}"
                    except ValueError as e:
                        progress_status['error_log'].append(f"Error processing images for {person}. Skipping this person. Error: {e}")
                        continue

    # Save Encodings
    try:
        with open('encodings.pkl', 'wb') as f:
            pickle.dump((all_encodings, classNames), f)
        progress_status["status"] = "Training Completed"
    except Exception as e:
        progress_status['error_log'].append(f"Failed to save encodings to file. Error: {e}")
        progress_status["status"] = "Training Failed"

@app.route('/')
def index():
    return render_template('train.html')

@app.route('/start_encoding', methods=['POST'])
def start_encoding():
    # Start the encoding in a new thread
    encoding_thread = Thread(target=encode_faces)
    encoding_thread.start()
    return jsonify({"message": "Training started."})

@app.route('/status', methods=['GET'])
def status():
    # Return the current encoding status
    return jsonify(progress_status)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5004)
