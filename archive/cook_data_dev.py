import csv
import os
import cv2
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from tkinter import ttk
from PIL import Image, ImageTk
import subprocess

# Define the poses and emotions
poses_emotions = [
    'close eyes', 'look straight', 'open mouth', 'raise eyebrow', 'smile', 'turn left for 45 degree', 'turn right for 45 degree', 'wear glass'
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

def write_selected_webcam():
    selected_webcam_path = webcam_paths[webcam_dropdown.current()]
    with open("selected_webcam.txt", "w") as f:
        f.write(selected_webcam_path)

def read_attendance_file(file_path):
    """
    Read the attendance CSV file and return the data as a list of dictionaries.
    """
    data = []
    if os.path.exists(file_path):
        with open(file_path, 'r', newline='') as file:
            reader = csv.DictReader(file)
            data = list(reader)
    return data

def write_attendance_file(file_path, data):
    """
    Write the updated data back to the attendance CSV file.
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', newline='') as file:
        fieldnames = data[0].keys() if data else ['ID', 'Name']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def insert_new_name(data, new_name, emp_id):
    """
    Insert a new name with an employee ID into the attendance data.
    """
    insert_index = 0
    for i, row in enumerate(data):
        if row['Name'] < new_name:
            insert_index = i + 1

    # Insert the new name into the data list
    data.insert(insert_index, {'ID': emp_id, 'Name': new_name})
    return new_name

def detect_bounding_box(vid):
    # Convert the Image to Grayscale
    gray_image = cv2.cvtColor(vid, cv2.COLOR_BGR2GRAY)
    # Detect faces
    faces = face_classifier.detectMultiScale(gray_image, 1.1, 5, minSize=(40, 40))
    # Draw rectangle around the faces and crop the faces
    for (x, y, w, h) in faces:
        faces = vid[y -50:y + h +50, x -50:x + w +50] #-50 or +50 are additional spaces allows to covers adjacent pixels of face.
    return faces

def save_cropped_image(folder_name, pose_emotion, img):
    # Save the file into the person's folder
    file_path = os.path.join(folder_name, f'{pose_emotion}.jpg')
    cv2.imwrite(file_path, img)
    print(f"Image saved: {file_path}")

def capture_image():
    global captured_image, display_captured_image
    result, video_frame = video_capture.read()
    if not result:
        messagebox.showerror("Error", "Failed to capture image from camera.")
        return

    faces = detect_bounding_box(video_frame)

    if len(faces) == 0:
        messagebox.showerror("Error", "No face detected. Please retake the pose.")
    else:
        captured_image = faces
        display_captured_image = True
        show_confirm_retake_buttons()

def confirm_image():
    save_cropped_image(folder_name, poses_emotions[current_pose_emotion_index], captured_image)
    global display_captured_image
    display_captured_image = False
    next_image()

def retake_image():
    global display_captured_image
    display_captured_image = False
    show_capture_button()

def next_image():
    global current_pose_emotion_index
    current_pose_emotion_index += 1
    if current_pose_emotion_index >= len(poses_emotions):
        messagebox.showinfo("Info", "All images captured successfully.")
        hide_all_buttons()
        show_train_button()
        video_capture.release()
        cv2.destroyAllWindows()
        return

    update_pose_emotion()
    show_capture_button()

def update_pose_emotion():
    global current_pose_image
    pose_image_path = f'./pose_images/{poses_emotions[current_pose_emotion_index]}.jpg'
    pose_image = Image.open(pose_image_path)
    pose_image = ImageTk.PhotoImage(pose_image)
    pose_image_label.config(image=pose_image)
    pose_image_label.image = pose_image

    current_pose_emotion_label.config(text=f"Pose/Emotion: {poses_emotions[current_pose_emotion_index]}")

def update_camera_feed():
    if display_captured_image:
        frame = cv2.cvtColor(captured_image, cv2.COLOR_BGR2RGB)
    else:
        _, frame = video_capture.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame)
    imgtk = ImageTk.PhotoImage(image=img)
    camera_feed_label.imgtk = imgtk
    camera_feed_label.configure(image=imgtk)
    camera_feed_label.after(10, update_camera_feed)

def start_process():
    global person_name, emp_id, team_name, folder_name, video_capture, current_pose_emotion_index

    person_name = name_entry.get().strip()
    emp_id = emp_id_entry.get().strip()
    team_name = team_name_entry.get().strip()

    if not person_name or not emp_id or not team_name:
        messagebox.showerror("Error", "Please enter name, employee ID, and team name.")
        return

    file_path = f'./facial_recognition_attendance/{team_name}_attendance.csv'
    folder_name = f"./facial_recognition_attendance/{team_name}/{person_name}_{emp_id}"

    # Read existing data from the file
    attendance_data = read_attendance_file(file_path)

    # Insert the new name into the data & get the modified name (if 2 persons have the same name)
    person_full_name = insert_new_name(attendance_data, person_name, emp_id)

    # Write the updated data back to the file
    write_attendance_file(file_path, attendance_data)
    messagebox.showinfo("Info", f"Name '{person_full_name}' has been added to the attendance file.")

    # Create a folder with the person's name if it doesn't exist
    os.makedirs(folder_name, exist_ok=True)

    # Load the cascade
    global face_classifier
    face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    # Access the Webcam
    global video_capture
    selected_webcam_path = webcam_paths[webcam_dropdown.current()]
    write_selected_webcam()
    video_capture = cv2.VideoCapture(selected_webcam_path)

    current_pose_emotion_index = 0
    update_pose_emotion()
    update_camera_feed()
    show_capture_button()

def show_capture_button():
    capture_button.pack(pady=10)
    confirm_button.pack_forget()
    retake_button.pack_forget()

def show_confirm_retake_buttons():
    capture_button.pack_forget()
    confirm_button.pack(pady=10)
    retake_button.pack(pady=10)

def hide_all_buttons():
    capture_button.pack_forget()
    confirm_button.pack_forget()
    retake_button.pack_forget()

def show_train_button():
    train_button.pack(pady=10)

def train_model():
    subprocess.run(["python3", "train.py"])
    hide_all_buttons()
    show_recognition_button()

def show_recognition_button():
    recognition_button.pack(pady=10)

def start_recognition():
    subprocess.run(["python3", "detect.py"])

def on_closing():
    if os.path.exists("selected_webcam.txt"):
        os.remove("selected_webcam.txt")
    root.destroy()

# Create the main window
root = tk.Tk()
root.title("Face Data Collector")
root.geometry("1400x1000")  # Set a fixed size for the window
root.resizable(False, False)  # Disable resizing

# Create GUI elements
name_label = ttk.Label(root, text="Enter the name of the person:")
name_label.pack(pady=10)

name_entry = ttk.Entry(root, width=30)
name_entry.pack(pady=10)

emp_id_label = ttk.Label(root, text="Enter the employee ID:")
emp_id_label.pack(pady=10)

emp_id_entry = ttk.Entry(root, width=30)
emp_id_entry.pack(pady=10)

team_name_label = ttk.Label(root, text="Enter the team name:")
team_name_label.pack(pady=10)

team_name_entry = ttk.Entry(root, width=30)
team_name_entry.pack(pady=10)

start_button = ttk.Button(root, text="Start", command=start_process)
start_button.pack(pady=20)

# Webcam dropdown menu
webcam_label = ttk.Label(root, text="Select Webcam:")
webcam_label.pack(pady=10)

webcams = list_webcams()
webcam_names = [name for name, path in webcams]
webcam_paths = [path for name, path in webcams]

webcam_dropdown = ttk.Combobox(root, values=webcam_names)
webcam_dropdown.pack(pady=10)
webcam_dropdown.current(0)

# Write selected webcam on change
webcam_dropdown.bind("<<ComboboxSelected>>", lambda e: write_selected_webcam())
"""
# Image and pose/emotion display
pose_image_label = ttk.Label(root)
pose_image_label.pack(side=tk.LEFT, padx=20, pady=20)

current_pose_emotion_label = ttk.Label(root, text="", font=("Helvetica", 16))
"""
# Frame for pose image and label
pose_frame = ttk.Frame(root)
pose_frame.pack(side=tk.LEFT, padx=20, pady=20)

pose_image_label = ttk.Label(pose_frame)
pose_image_label.pack()

current_pose_emotion_label = ttk.Label(pose_frame, text="", font=("Helvetica", 16))
current_pose_emotion_label.pack(pady=10)

# Camera feed display
camera_feed_label = ttk.Label(root)
camera_feed_label.pack(side=tk.RIGHT, padx=20, pady=20)

# Capture, Confirm, Retake, Train, and Recognition buttons
capture_button = ttk.Button(root, text="Capture", command=capture_image)
confirm_button = ttk.Button(root, text="Confirm", command=confirm_image)
retake_button = ttk.Button(root, text="Retake", command=retake_image)
train_button = ttk.Button(root, text="Train the Model", command=train_model)
recognition_button = ttk.Button(root, text="Start Recognition", command=start_recognition)

# Initialize variables
current_pose_emotion_index = 0
video_capture = None
captured_image = None
display_captured_image = False

# Set up the on_closing event
root.protocol("WM_DELETE_WINDOW", on_closing)

# Start the GUI event loop
root.mainloop()
