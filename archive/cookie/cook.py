from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import os
import csv
import cv2
from PIL import Image
import subprocess

app = Flask(__name__)

# Define the poses and emotions
poses_emotions = [
    'close eyes', 'look straight', 'open mouth', 'raise eyebrow', 
    'smile', 'turn left for 45 degree', 'turn right for 45 degree', 'wear glass'
]

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

# Webcam listing for dropdown
webcams = list_webcams()
webcam_names = [name for name, path in webcams]
webcam_paths = [path for name, path in webcams]

selected_webcam_path = webcam_paths[0] if webcam_paths else None

# Function to read and write attendance files
def read_attendance_file(file_path):
    data = []
    if os.path.exists(file_path):
        with open(file_path, 'r', newline='') as file:
            reader = csv.DictReader(file)
            data = list(reader)
    return data

def write_attendance_file(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', newline='') as file:
        fieldnames = data[0].keys() if data else ['ID', 'Name']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

# Function to insert new name in sorted order
def insert_new_name(data, new_name, emp_id):
    insert_index = 0
    for i, row in enumerate(data):
        if row['Name'] < new_name:
            insert_index = i + 1
    data.insert(insert_index, {'ID': emp_id, 'Name': new_name})
    return new_name

# Routes for the web application
@app.route('/')
def index():
    return render_template('index.html', webcams=webcam_names)

@app.route('/start', methods=['POST'])
def start():
    person_name = request.form['name']
    emp_id = request.form['emp_id']
    team_name = request.form['team_name']
    selected_webcam = request.form['webcam']

    if not person_name or not emp_id or not team_name:
        return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400

    # Prepare file paths
    file_path = f'./static/{team_name}_attendance.csv'
    folder_name = f"./static/images/{team_name}/{person_name}_{emp_id}"

    # Read existing data from the file
    attendance_data = read_attendance_file(file_path)

    # Insert the new name into the data
    person_full_name = insert_new_name(attendance_data, person_name, emp_id)

    # Write the updated data back to the file
    write_attendance_file(file_path, attendance_data)

    # Create a folder with the person's name if it doesn't exist
    os.makedirs(folder_name, exist_ok=True)

    # Save selected webcam
    global selected_webcam_path
    selected_webcam_path = webcam_paths[int(selected_webcam)]

    return redirect(url_for('capture', index=0))

@app.route('/capture/<int:index>')
def capture(index):
    if index < len(poses_emotions):
        return render_template('capture.html', pose=poses_emotions[index], index=index)
    return jsonify({'status': 'complete', 'message': 'All images captured successfully.'})

def gen_frames():
    # Video capture loop for streaming
    cap = cv2.VideoCapture(0)  # Default camera
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Encode the frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            # Stream in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()
    
@app.route('/capture_image', methods=['POST'])
def capture_image():
    global selected_webcam_path
    data = request.get_json()
    index = int(data['index'])
    person_name = data['person_name']
    emp_id = data['emp_id']
    team_name = data['team_name']

    folder_name = f"./static/images/{team_name}/{person_name}_{emp_id}"
    pose = poses_emotions[index]

    # Debugging: print received data
    print(f"Received data: index={index}, person_name={person_name}, emp_id={emp_id}, team_name={team_name}")
    print(f"Saving image for pose: {pose}")

    # Access the webcam and capture an image
    try:
        cap = cv2.VideoCapture(0)  # Using camera index 0 for consistency
        if not cap.isOpened():
            print("Error: Could not open the webcam.")
            return jsonify({'status': 'error', 'message': 'Could not open the webcam.'})

        # Attempt to read a frame from the camera
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("Error: Failed to read a frame from the webcam.")
            return jsonify({'status': 'error', 'message': 'Failed to read a frame from the webcam.'})

        # Save the captured image to the appropriate directory
        os.makedirs(folder_name, exist_ok=True)
        image_path = os.path.join(folder_name, f'{pose}.jpg')
        cv2.imwrite(image_path, frame)
        print(f"Image saved successfully at {image_path}")

        return jsonify({'status': 'success', 'message': f'Image for {pose} captured successfully.', 'next_index': index + 1})
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Error occurred: {str(e)}'})

    

@app.route('/video_feed')
def video_feed():
    # Return the response generated by gen_frames() as multipart
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
