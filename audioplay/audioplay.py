from flask import Flask, render_template
import pygame
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire Flask app

# Initialize pygame mixer
pygame.mixer.init()

# Path to your audio file
audio_file = '/home/admin/Downloads/myTeacher/audioplay/Dr_JS_A_Badruddin_4Mins_Audio_copy.mp3'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/play')
def play_audio():
    if not pygame.mixer.music.get_busy():  # Check if audio is already playing
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
    return "Audio is playing"

@app.route('/stop')
def stop_audio():
    pygame.mixer.music.stop()
    return "Audio stopped"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5007)
