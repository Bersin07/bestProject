from flask import Flask, render_template, request, send_file
import pandas as pd
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire Flask app

# Path where your CSV files are stored
CSV_FOLDER = '/home/admin/Downloads/archive/facial_recognition_attendance'

@app.route('/')
def home():
    # List all CSV files in the directory
    files = [f for f in os.listdir(CSV_FOLDER) if f.endswith('.csv')]
    return render_template('index.html', files=files)

@app.route('/view/<filename>')
def view_csv(filename):
    file_path = os.path.join(CSV_FOLDER, filename)
    if os.path.exists(file_path):
        # Read the CSV file
        df = pd.read_csv(file_path)
        # Convert the DataFrame to HTML
        table_html = df.to_html(classes='table table-striped', index=False)
        return render_template('view.html', table=table_html, filename=filename)
    else:
        return "File not found!", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5008)
