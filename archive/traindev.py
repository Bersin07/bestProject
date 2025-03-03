import os
import cv2
import face_recognition
import pickle
import numpy as np

#### Defining Paths and Declaring Lists
base_path = 'facial_recognition_attendance'
group_paths = [os.path.join(base_path, group) for group in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, group))]

all_encodings = {}
classNames = []

print('Retrieving Image Dataset...')

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
                print(f"No face found in an image. Skipping this image.")
        except Exception as e:
            print(f"Error processing an image. Skipping this image. Error: {e}")
            continue
    if encodings:
        return np.mean(encodings, axis=0)
    else:
        raise ValueError("No encodings found for this person.")

#### Traversing the dataset structure and calculating average encodings
for group_path in group_paths:
    group_name = os.path.basename(group_path)
    for person in os.listdir(group_path):
        person_path = os.path.join(group_path, person)
        if os.path.isdir(person_path):
            images = []
            for img_name in os.listdir(person_path):
                img_path = os.path.join(person_path, img_name)
                curImg = cv2.imread(img_path)
                if curImg is None:
                    print(f"Failed to read image {img_path}. Skipping this image.")
                    continue
                images.append(curImg)
            if images:
                try:
                    avg_encoding = calculate_average_encoding(images)
                    all_encodings[(person, group_name)] = avg_encoding
                    classNames.append((person, group_name))
                except ValueError as e:
                    print(f"Error processing images for {person}. Skipping this person. Error: {e}")
                    continue

print('Encoding Complete')

#### Saving Encodings and Class Names to a .pkl file
try:
    with open('encodings.pkl', 'wb') as f:
        pickle.dump((all_encodings, classNames), f)
    print("Encodings saved to 'encodings.pkl'")
except Exception as e:
    print(f"Failed to save encodings to file. Error: {e}")
