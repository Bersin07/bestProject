import csv
import os
import cv2
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from PIL import Image, ImageTk
import subprocess

# Initialize global variable to track last active entry widget
last_active_entry = None

# Define poses and emotions
poses_emotions = [
    'close eyes', 'look straight', 'open mouth', 'raise eyebrow', 'smile', 'turn left for 45 degrees', 
    'turn right for 45 degrees', 'wear glasses'
]

# Function to list available webcams
# def list_webcams():
    # result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True)
    # output = result.stdout.split('\n')
    # devices = []
    # device_name = None
    # for line in output:
        # if line.endswith(':'):
            # device_name = line.strip()[:-1]
        # elif line.strip().startswith('/dev/'):
            # device_path = line.strip()
            # devices.append((device_name, device_path))
    # return devices

# def write_selected_webcam():
    # selected_webcam_path = webcam_paths[webcam_dropdown.current()]
    # with open("selected_webcam.txt", "w") as f:
        # f.write(selected_webcam_path)

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

def insert_new_name(data, new_name, emp_id):
    insert_index = 0
    for i, row in enumerate(data):
        if row['Name'] < new_name:
            insert_index = i + 1
    data.insert(insert_index, {'ID': emp_id, 'Name': new_name})
    return new_name

def detect_bounding_box(vid):
    gray_image = cv2.cvtColor(vid, cv2.COLOR_BGR2GRAY)
    faces = face_classifier.detectMultiScale(gray_image, 1.1, 5, minSize=(40, 40))
    for (x, y, w, h) in faces:
        faces = vid[y - 50:y + h + 50, x - 50:x + w + 50]
    return faces

def save_cropped_image(folder_name, pose_emotion, img):
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
        if captured_image is not None:
            frame = cv2.cvtColor(captured_image, cv2.COLOR_BGR2RGB)
        else:
            messagebox.showerror("Error", "No captured image available.")
            return
    else:
        result, frame = video_capture.read()
        if not result or frame is None:
            messagebox.showerror("Error", "Failed to capture frame from camera.")
            return
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
    attendance_data = read_attendance_file(file_path)
    person_full_name = insert_new_name(attendance_data, person_name, emp_id)
    write_attendance_file(file_path, attendance_data)
    messagebox.showinfo("Info", f"Name '{person_full_name}' has been added to the attendance file.")
    os.makedirs(folder_name, exist_ok=True)
    global face_classifier
    face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    global video_capture
    # Set the camera directly to /dev/video0
    video_capture = cv2.VideoCapture("/dev/video0")
    current_pose_emotion_index = 0
    update_pose_emotion()
    update_camera_feed()
    show_capture_button()
    

def show_capture_button():
    capture_button.grid(row=0, column=0, padx=5, pady=5)
    confirm_button.grid_forget()
    retake_button.grid_forget()

def show_confirm_retake_buttons():
    capture_button.grid_forget()
    confirm_button.grid(row=0, column=0, padx=5, pady=5)
    retake_button.grid(row=0, column=1, padx=5, pady=5)

def hide_all_buttons():
    capture_button.grid_forget()
    confirm_button.grid_forget()
    retake_button.grid_forget()

def show_train_button():
    train_button.grid(row=0, column=0, padx=5, pady=5)

def train_model():
    subprocess.run(["python3", "train.py"])
    hide_all_buttons()
    show_recognition_button()

def show_recognition_button():
    recognition_button.grid(row=0, column=0, padx=5, pady=5)

def start_recognition():
    subprocess.run(["python3", "detect.py"])

def on_closing():
    if os.path.exists("selected_webcam.txt"):
        os.remove("selected_webcam.txt")
    root.destroy()

# Function to insert character into the last active entry
def insert_char(char):
    if last_active_entry:
        last_active_entry.insert(tk.END, char)
        last_active_entry.focus_set()  # Refocus on the entry after inserting

# Function to delete the last character in the last active entry
def delete_char():
    if last_active_entry:
        current_text = last_active_entry.get()
        last_active_entry.delete(len(current_text) - 1, tk.END)
        last_active_entry.focus_set()  # Refocus on the entry after deleting

# Function to handle focus event and store last active entry
def on_entry_focus(event):
    global last_active_entry
    last_active_entry = event.widget

# Function to create an on-screen keyboard layout
def create_keyboard():
    global keyboard_frame
    # Check if keyboard already exists to avoid creating multiple keyboards
    if keyboard_frame:
        return
    keyboard_frame = ttk.Frame(root)
    keyboard_frame.grid(row=3, column=0, columnspan=2, pady=10)

    keys = [
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
        'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p',
        'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l',
        'z', 'x', 'c', 'v', 'b', 'n', 'm', '.', '@', '_'
    ]

    row = 0
    col = 0
    for key in keys:
        button = ttk.Button(keyboard_frame, text=key, command=lambda k=key: insert_char(k))
        button.grid(row=row, column=col, ipadx=10, ipady=5, padx=2, pady=2)
        col += 1
        if col > 9:
            col = 0
            row += 1

    # Special keys for space, delete, and done
    space_button = ttk.Button(keyboard_frame, text="Space", command=lambda: insert_char(' '))
    space_button.grid(row=row + 1, column=0, columnspan=3, ipadx=20, ipady=5, padx=2, pady=2)

    delete_button = ttk.Button(keyboard_frame, text="Delete", command=delete_char)
    delete_button.grid(row=row + 1, column=3, columnspan=3, ipadx=10, ipady=5, padx=2, pady=2)

    done_button = ttk.Button(keyboard_frame, text="Done", command=close_keyboard)
    done_button.grid(row=row + 1, column=6, columnspan=3, ipadx=20, ipady=5, padx=2, pady=2)

# Function to close/hide the keyboard
def close_keyboard():
    global keyboard_frame
    if keyboard_frame:
        keyboard_frame.destroy()  # Remove the keyboard frame
        keyboard_frame = None  # Reset the frame variable
    start_process()


# Create the main window
root = tk.Tk()
root.title("Face Data Collector")
root.geometry("1200x800")
root.resizable(False, False)

# Adding custom theme
style = ttk.Style(root)
root.tk.call("source", "/home/admin/Downloads/archive/Azure/azure.tcl")  # Assume the modern theme file azure.tcl is available
root.tk.call("set_theme", "dark") 


# Frames for layout organization
# Create input_frame within root for styled input fields
input_frame = ttk.Frame(root, padding="10")
input_frame.grid(row=0, column=0, padx=10, pady=10)

camera_frame = ttk.Frame(root)
camera_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nw")

pose_frame = ttk.Frame(root)
pose_frame.grid(row=0, column=2, padx=10, pady=10, sticky="ne")

button_frame = ttk.Frame(root)
button_frame.grid(row=1, column=0, columnspan=3, pady=10)

# Inputs
# Styled input fields within input_frame
name_label = ttk.Label(input_frame, text="Name:")
name_label.grid(row=0, column=0, sticky="w", pady=5)

name_entry = ttk.Entry(input_frame, width=30)
name_entry.grid(row=0, column=1, pady=5)
name_entry.bind("<FocusIn>", on_entry_focus)  # Bind focus event to store active entry

emp_id_label = ttk.Label(input_frame, text="Section:")
emp_id_label.grid(row=1, column=0, sticky="w", pady=5)

emp_id_entry = ttk.Entry(input_frame, width=30)
emp_id_entry.grid(row=1, column=1, pady=5)
emp_id_entry.bind("<FocusIn>", on_entry_focus)  # Bind focus event to store active entry

team_name_label = ttk.Label(input_frame, text="Grade:")
team_name_label.grid(row=2, column=0, sticky="w", pady=5)

team_name_entry = ttk.Entry(input_frame, width=30)
team_name_entry.grid(row=2, column=1, pady=5)
team_name_entry.bind("<FocusIn>", on_entry_focus)  # Bind focus event to store active entry


start_button = ttk.Button(input_frame, text="Start", command=close_keyboard)
start_button.grid(row=3, column=0, columnspan=2, pady=10)

# webcam_label = ttk.Label(input_frame, text="Webcam:")
# webcam_label.grid(row=4, column=0, sticky="w", pady=5)

# # Webcam dropdown
# webcams = list_webcams()
# webcam_names = [name for name, path in webcams]
# webcam_paths = [path for name, path in webcams]

# webcam_dropdown = ttk.Combobox(input_frame, values=webcam_names, width=18)
# webcam_dropdown.grid(row=4, column=1, pady=5)
# webcam_dropdown.current(0)
# webcam_dropdown.bind("<<ComboboxSelected>>", lambda e: write_selected_webcam())

# Pose image and label
pose_image_label = ttk.Label(pose_frame)
pose_image_label.grid(row=0, column=0, padx=10, pady=10)

current_pose_emotion_label = ttk.Label(pose_frame, text="", font=("Helvetica", 12))
current_pose_emotion_label.grid(row=1, column=0, pady=5)

# Camera feed display
camera_feed_label = ttk.Label(camera_frame)
camera_feed_label.pack()

# Control buttons
capture_button = ttk.Button(button_frame, text="Capture", command=capture_image)
confirm_button = ttk.Button(button_frame, text="Confirm", command=confirm_image)
retake_button = ttk.Button(button_frame, text="Retake", command=retake_image)
train_button = ttk.Button(button_frame, text="Train", command=train_model)
recognition_button = ttk.Button(button_frame, text="Recognize", command=start_recognition)

# Initialize variables
current_pose_emotion_index = 0
video_capture = None
captured_image = None
display_captured_image = False

# Handle window close event
root.protocol("WM_DELETE_WINDOW", on_closing)

# Button to manually open the keyboard
open_keyboard_button = ttk.Button(root, text="Open Keyboard", command=create_keyboard)
open_keyboard_button.grid(row=2, column=0, pady=10)

# Initialize keyboard frame as None
keyboard_frame = None

# Start the GUI
root.mainloop()
