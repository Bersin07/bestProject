from flask import Flask, render_template_string
import RPi.GPIO as GPIO
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire Flask app


# Define motor control pins
motor_pins = {
    'motorA1': 5,
    'motorA2': 6,
    'motorB1': 13,
    'motorB2': 19,
    'motorC1': 26,
    'motorC2': 21,
    'motorD1': 20,
    'motorD2': 16
}

# Setup GPIO
GPIO.setmode(GPIO.BCM)
for pin in motor_pins.values():
    GPIO.setup(pin, GPIO.OUT)

@app.route('/')
def index():
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iSpark's iSMART Robot Base Controller</title>
    <!-- Font Awesome for Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: 
            linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), /* Black shadow overlay */
            url('https://img.freepik.com/free-photo/close-up-anthropomorphic-robot-working-company_23-2150865913.jpg?t=st=1730187158~exp=1730190758~hmac=a260224c004deb9a8ba73e1242ee5f5c3592ef152ebda8485a4f0c83a356f7c6&w=826') 
            no-repeat center center fixed;
            background-size: cover;
            position: relative;
            color: #333333; /* Standard Dark Text */
        }

        .logo {
            position: absolute;
            top: 15px;
            left: 15px;
            max-width: 100px;
        }
        .controller {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            background: rgba(8, 8, 8, 0.1); /* Semi-transparent for glassmorphism */
            backdrop-filter: blur(5px); /* Frosted glass effect */
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3); /* Border for glass effect */
            margin: 20px;
            max-width: 90%;
            width: 600px;
        }
        ::selection {
            background-color: darkorange;
            color: white;
        }
        .controller h1 {
            margin-bottom: 50px;
            color: #EF7C00; /* Vibrant Blue for Heading */
            font-size: 2em;
            text-shadow: rgba(0, 0, 0, 1.9);
        }
        .controls {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }
        .controls button {
            width: 100%;
            padding: 15px 30px;
            margin: 10px 0;
            font-size: 1em;
            border: none;
            border-radius: 10px;
            background-color: #0073B6; /* Vibrant Blue Buttons */
            color: #ffffff;
            cursor: pointer;
            transition: background-color 0.3s, transform 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .controls button:hover {
            background-color: #EF7C00; /* Darker Blue on Hover */
            transform: scale(1.05);
        }
        .controls button:active {
            transform: scale(0.95);
        }
        .direction-buttons {
            display: flex;
            justify-content: space-between;
            width: 100%;
        }
        .direction-buttons button {
            width: 30%;
        }
        /* Back button styling */
        .back-button {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            padding: 10px 20px;
            font-size: 1em;
            color: #ffffff;
            background-color: #EF7C00; /* Bright Orange for Back Button */
            border: none;
            border-radius: 10px;
            cursor: pointer;
            text-decoration: none;
            overflow: hidden;
            transition: background-color 0.3s ease;
        }
        .back-button i {
            margin-right: 5px;
        }
        .back-button::before {
            content: "";
            position: absolute;
            top: 0;
            left: -50px;
            width: 50px;
            height: 100%;
            background: rgba(255, 255, 255, 0.2);
            transition: left 0.3s ease;
        }
        .back-button:hover::before {
            left: 100%;
        }
        .back-button:hover {
            background-color: #d46900; /* Darker Orange on Hover */
        }
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .controller {
                padding: 30px;
                width: 90%;
            }
            .controls button {
                padding: 12px 20px;
                margin: 8px 0;
                font-size: 0.9em;
            }
            .controller h1 {
                font-size: 1.6em;
            }
            .back-button {
                font-size: 0.9em;
                padding: 8px 16px;
            }
        }
        @media (max-width: 480px) {
            .direction-buttons {
                flex-direction: column;
            }
            .direction-buttons button {
                width: 100%;
                margin: 5px 0;
            }
            .controller h1 {
                font-size: 1.3em;
            }
            .back-button {
                font-size: 0.8em;
                padding: 6px 14px;
            }
        }
    </style>
</head>
<body>
    <img src="https://isparkinnovators.com/logos/iSpark%20logo_final.png" alt="Company Logo" class="logo">
    
    <!-- Main Controller -->
    <div class="controller">
        <h1>iSpark's iSMART AI Teacher</h1>
        <div class="controls">
            <button onclick="sendCommand('forward')"><i class="fas fa-arrow-up"></i> Forward</button>
            <div class="direction-buttons">
                <button onclick="sendCommand('left')"><i class="fas fa-arrow-left"></i> Left</button>
                <button onclick="sendCommand('stop')"><i class="fas fa-stop"></i> Stop</button>
                <button onclick="sendCommand('right')"><i class="fas fa-arrow-right"></i> Right</button>
            </div>
            <button onclick="sendCommand('backward')"><i class="fas fa-arrow-down"></i> Backward</button>
        </div>
    </div>

    <!-- Back Button at Bottom Center -->
 <button class = "back-button" onclick="stop_base_controll()"><i class="fas fa-arrow-left"></i>Back</button>

    <script>
        function stop_base_controll() {
            fetch('http://' + window.location.hostname + ':5001/stop_base_controll', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                if (response.ok) {
                    window.location.href = 'http://' + window.location.hostname + ':5001/';
                } else {
                    console.error('Failed to stop attendance:', response.statusText);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }

        function sendCommand(command) {
            fetch('/' + command)
            .then(response => {
                if (!response.ok) {
                    console.error('Command failed:', response.statusText);
                }
            })
            .catch(error => {
                console.error('Error sending command:', error);
            });
        }
    </script>
</body>
</html>
    '''
    return render_template_string(html)

@app.route('/forward')
def forward():
    print("Moving Forward")
    GPIO.output(motor_pins['motorA1'], GPIO.HIGH)
    GPIO.output(motor_pins['motorA2'], GPIO.LOW)
    GPIO.output(motor_pins['motorB1'], GPIO.HIGH)
    GPIO.output(motor_pins['motorB2'], GPIO.LOW)
    GPIO.output(motor_pins['motorC1'], GPIO.HIGH)
    GPIO.output(motor_pins['motorC2'], GPIO.LOW)
    GPIO.output(motor_pins['motorD1'], GPIO.HIGH)
    GPIO.output(motor_pins['motorD2'], GPIO.LOW)
    return "Moving Forward"

@app.route('/backward')
def backward():
    print("Moving Backward")
    GPIO.output(motor_pins['motorA1'], GPIO.LOW)
    GPIO.output(motor_pins['motorA2'], GPIO.HIGH)
    GPIO.output(motor_pins['motorB1'], GPIO.LOW)
    GPIO.output(motor_pins['motorB2'], GPIO.HIGH)
    GPIO.output(motor_pins['motorC1'], GPIO.LOW)
    GPIO.output(motor_pins['motorC2'], GPIO.HIGH)
    GPIO.output(motor_pins['motorD1'], GPIO.LOW)
    GPIO.output(motor_pins['motorD2'], GPIO.HIGH)
    return "Moving Backward"

@app.route('/left')
def left():
    print("Turning Left")
    GPIO.output(motor_pins['motorA1'], GPIO.LOW)
    GPIO.output(motor_pins['motorA2'], GPIO.HIGH)
    GPIO.output(motor_pins['motorB1'], GPIO.HIGH)
    GPIO.output(motor_pins['motorB2'], GPIO.LOW)
    GPIO.output(motor_pins['motorC1'], GPIO.LOW)
    GPIO.output(motor_pins['motorC2'], GPIO.HIGH)
    GPIO.output(motor_pins['motorD1'], GPIO.HIGH)
    GPIO.output(motor_pins['motorD2'], GPIO.LOW)
    return "Turning Left"

@app.route('/right')
def right():
    print("Turning Right")
    GPIO.output(motor_pins['motorA1'], GPIO.HIGH)
    GPIO.output(motor_pins['motorA2'], GPIO.LOW)
    GPIO.output(motor_pins['motorB1'], GPIO.LOW)
    GPIO.output(motor_pins['motorB2'], GPIO.HIGH)
    GPIO.output(motor_pins['motorC1'], GPIO.HIGH)
    GPIO.output(motor_pins['motorC2'], GPIO.LOW)
    GPIO.output(motor_pins['motorD1'], GPIO.LOW)
    GPIO.output(motor_pins['motorD2'], GPIO.HIGH)
    return "Turning Right"

@app.route('/stop')
def stop():
    print("Stopping")
    for pin in motor_pins.values():
        GPIO.output(pin, GPIO.LOW)
    return "Stopping"

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5005)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
