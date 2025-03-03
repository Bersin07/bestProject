import detect

if __name__ == "__main__":
    # Start the Flask application from the compiled .so file
    detect.app.run(host="0.0.0.0", port=5002)
