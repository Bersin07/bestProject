from flask import Flask, render_template, redirect
import subprocess
import socket
from flask_cors import CORS
import time
import psutil
import os
import signal

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire Flask app

# Store the process globally to manage it
ai_teacher_process = None

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

@app.route('/')
def home():
    # Get the current IP address to pass to the HTML template
    current_ip = get_ip_address()
    return render_template('index.html', ip=current_ip)

@app.route('/run_ai_teacher')
def run_ai_teacher():
    # Run the first Python script for AI Teacher in a separate LXTerminal
    subprocess.Popen(['bash', '/home/admin/Downloads/myTeacher/merged21.sh'])
    # Redirect to the loading page while waiting for the AI Teacher to be ready
    current_ip = get_ip_address()
    return render_template('loading.html', ip=current_ip)

# Route to stop the AI Teacher
@app.route('/stop_ai_teacher', methods=['POST'])
def stop_ai_teacher():
    # Use pkill to terminate the terminal running the AI Teacher
    subprocess.call(['pkill', '-f', 'launch_merged21.py'])
    
    # Redirect back to the home page
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5001/')

@app.route('/stop_attendance', methods=['POST'])
def stop_attendance():
    # Use pkill to terminate the terminal running the Attendance
    subprocess.call(['pkill', '-f', 'launch_detect.py'])
    
    # Redirect back to the home page
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5001/')

@app.route('/run_attendance')
def run_attendance():
    # Run the Attendance script without opening a new terminal
    subprocess.Popen(['bash', '/home/admin/Downloads/archive/detect.sh'])
    # Redirect to the current IP after starting the script
    current_ip = get_ip_address()
    return render_template('loading1.html', ip=current_ip)
    
    
@app.route('/ai_chat')
def ai_chat():
    # Run the Attendance script without opening a new terminal
    subprocess.Popen(['bash', '/home/admin/Downloads/myTeacher/chat2voice/chat2voice.sh'])
    # Redirect to the current IP after starting the script
    current_ip = get_ip_address()
    return render_template('loading_ai_chat.html', ip=current_ip)
    
@app.route('/stop_ai_chat', methods=['POST'])
def stop_ai_chat():
    # Use pkill to terminate the terminal running the Attendance
    subprocess.call(['pkill', '-f', 'launch_chat2voice.py'])
    
    # Redirect back to the home page
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5001/')
    
    
@app.route('/stop_audio_play', methods=['POST'])
def stop_audio_play():
    print("Attempting to stop audioplay.py")
    subprocess.call(['pkill', '-9', '-f', 'python.*launch_audioplay.py'])
    print("pkill executed")
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5001/')

    
    
# Route for add data    
@app.route('/add_data')
def add_data():
    # Adjust the command below to your actual script path and command
    subprocess.Popen(['bash', '/home/admin/Downloads/archive/cook.sh'])
    
    # Redirect back to home after starting the script
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5001/')
    
    
    
# Route
@app.route('/audio_play')
def audio_play():
    # Adjust the command below to your actual script path and command
    subprocess.Popen(['bash', '/home/admin/Downloads/myTeacher/audioplay/audioplay.sh'])
    
    # Redirect back to home after starting the script
    current_ip = get_ip_address()
    return render_template('loading_audio_play.html', ip=current_ip)
    
# Route for train
@app.route('/train_data')
def train_data():
    # Run the script to train data
    # Adjust the command below to your actual script path and command
    subprocess.Popen(['bash', '/home/admin/Downloads/archive/train.sh'])
    
    # Redirect back to home after starting the script
    current_ip = get_ip_address()
    return render_template('loading_train.html', ip=current_ip)
    
    
    
#route for the basecontroller
@app.route('/base_controll')
def base_controll():
    # Run the script to train data
    # Adjust the command below to your actual script path and command
    subprocess.Popen(['bash', '/home/admin/fxd.sh'])
    
    # Redirect back to home after starting the script
    current_ip = get_ip_address()
    return render_template('loading_base.html', ip=current_ip)
    
@app.route('/excel')
def excel():
    # Run the script to train data
    # Adjust the command below to your actual script path and command
    subprocess.Popen(['bash', '/home/admin/Downloads/myTeacher/excelfiles_display/excel.sh'])
    
    # Redirect back to home after starting the script
    current_ip = get_ip_address()
    return render_template('loading_excel.html', ip=current_ip)
    
    

@app.route('/stop_excel', methods=['POST'])
def stop_excel():
    subprocess.call(['pkill', '-f', 'launch_excel.py'])
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5001/')

#stop base controller
@app.route('/stop_base_controll', methods=['POST'])
def stop_base_controll():
    subprocess.call(['pkill', '-f', 'launch_Basecontrol.py'])
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5001/')

@app.route('/stop_train', methods=['POST'])
def stop_train():
    subprocess.call(['pkill', '-f', 'stop_train.py'])
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5001/')
    
    
#for shuutting down
@app.route('/shutdown', methods=['POST'])
def shutdown():
    os.system("sudo shutdown -h now")
    return 'Shutting down...', 200
    
    
#for rebooting down
@app.route('/reboot', methods=['POST'])
def reboot():
    os.system("sudo reboot")
    return 'Rebooting...', 200
    
    
#checking the status panel

    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
