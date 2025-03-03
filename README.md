# Humanoid Robot

## Project Overview
The iSmart Humanoid Robot is an advanced AI-powered robot developed using a **Raspberry Pi 5**, designed to interact with users through speech, facial recognition, and movement. The robot integrates **Google Cloud TTS**, **Gemini API**, and multiple AI-based features to enhance user experience.

## Features
- **Conversational AI** using the **Gemini API**
- **Multilingual Support** (10 languages)
- **Facial Recognition** for identifying users
- **Text-to-Speech (TTS)** powered by **Google Cloud**
- **Head & Hand Movement** for expressive interactions
- **Directional Movement** with motorized wheels
- **Speech Recognition** for real-time responses
- **Custom Static Responses** for predefined interactions

## Project Complexity
This is a **complex multi-routing project** developed using **Flask** and **Python**, integrating various **AI-based functionalities**. The project consists of multiple interconnected modules, including:
- **Advanced Flask Backend** with multiple API endpoints
- **Real-time Speech Processing** using advanced NLP models
- **Facial Recognition System** requiring dedicated GPU acceleration
- **Embedded System Integration** with Raspberry Pi GPIO controls
- **AI-powered chatbot** requiring cloud-based API services
- **Custom Linux Packages & Dependencies**, including:
  - OpenCV (for image processing)
  - Deep Learning libraries (TensorFlow/PyTorch)
  - Flask & REST API frameworks
  - Google Cloud SDK
  - SpeechRecognition & Text-to-Speech APIs
  - Hardware-specific drivers & modules

Due to its complexity and deep integration with **specialized hardware and cloud services**, this project cannot be simply installed and requires extensive configuration and system dependencies.

## Dependencies
- Python 3.x
- OpenCV (for facial recognition)
- SpeechRecognition
- Google Cloud Text-to-Speech API
- Raspberry Pi GPIO Library
- Deep Learning Frameworks (TensorFlow/PyTorch)
- Flask for API communication
- Custom Linux system configurations

## Usage
- Start the robot using `python app.py` in aidesktopmode
- It will listen for voice commands and respond accordingly
- Facial recognition will be triggered when a user is detected

## Contribution
If you wish to contribute, feel free to submit a pull request. Ensure your code follows proper formatting and includes comments where necessary.

## License
This project is licensed under the MIT License.

---

🚀 **Developed by Bersin B**
