from flask import Flask, request, jsonify
import subprocess
import os
import threading
import requests
import uuid
from dotenv import load_dotenv

app = Flask(__name__)
progress = {}
config_path = 'rclone.conf'

# Load environment variables from .env file
load_dotenv()

def download_config(config_url):
    response = requests.get(config_url)
    if response.status_code == 200:
        with open(config_path, 'w') as config_file:
            config_file.write(response.text)
        return True
    return False

def run_rclone_copyurl(source_url, destination, job_id):
    command = [
        'rclone', 'copyurl', source_url, destination,
        '--config', config_path,
        '--progress'
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in process.stdout:
        progress[job_id] = line
    process.wait()

@app.route('/copyurl', methods=['POST'])
def copyurl():
    data = request.json
    source_url = data.get('source_url')
    destination = data.get('destination')

    if not source_url or not destination:
        return jsonify({"error": "Source URL and destination are required"}), 400

    # Get the config URL from environment variables
    config_url = os.getenv('RCLONE_CONFIG_URL')
    if not config_url:
        return jsonify({"error": "RCLONE_CONFIG_URL environment variable not set"}), 500

    # Generate a unique job ID
    job_id = str(uuid.uuid4())

    if download_config(config_url):
        progress[job_id] = "Starting copyurl operation..."
        thread = threading.Thread(target=run_rclone_copyurl, args=(source_url, destination, job_id))
        thread.start()
        return jsonify({"message": "Copyurl operation started", "job_id": job_id})
    else:
        return jsonify({"error": "Failed to download rclone configuration"}), 500

@app.route('/progress/<job_id>', methods=['GET'])
def get_progress(job_id):
    return jsonify({"progress": progress.get(job_id, "No progress available")})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
