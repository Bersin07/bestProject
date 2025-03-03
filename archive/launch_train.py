import train

if __name__ == "__main__":
    # Start the Flask application from the compiled .so file
    train.app.run(host="0.0.0.0", port=5004)
