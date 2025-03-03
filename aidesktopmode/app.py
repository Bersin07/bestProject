from flask import Flask, render_template, redirect, jsonify
import subprocess
import socket
from flask_cors import CORS
import time
import psutil
import os
import signal


app = Flask(__name__)
CORS(app)  # Enable CORS for the entire Flask app
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
# Home route to render the page
@app.route('/')
def home():
    return render_template('index.html')

# Route for AI Mode
@app.route('/ai_mode')
def ai_mode():
    # Run the script to train data
    # Adjust the command below to your actual script path and command
    subprocess.Popen(['bash', '/home/admin/Downloads/myTeacher/kiosk.sh'])
    
    # Redirect back to home after starting the script
    current_ip = get_ip_address()
    return render_template('loading_ai_mode.html', ip=current_ip)
    
    
@app.route('/stop_ai_mode', methods=['POST'])
def stop_excel():
    subprocess.call(['pkill', '-f', 'kiosk.py'])
    current_ip = get_ip_address()
    return redirect(f'http://{current_ip}:5010/')
        
        
# Route for Desktop Mode
@app.route('/desktop_mode')
def desktop_mode():
    try:
		
        # Kill Chrome (Linux example)
        subprocess.run(['pkill', 'chromium'], check=True)  # Use 'chrome' for Chrome on Linux
        subprocess.call(['pkill', '-f', 'lxterminal'])
        subprocess.call(['pkill', '-f', 'app.py'])
        
        # Or, for Windows, you can use:
        # subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], check=True)
        
        return jsonify({'success': True, 'message': 'Chrome has been closed.'})
    except subprocess.CalledProcessError:
        return jsonify({'success': False, 'message': 'Failed to close Chrome'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010)
