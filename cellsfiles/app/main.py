from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from google.cloud import storage
import requests
from pydub import AudioSegment
from cellsfiles.params import *

# The API endpoint
url = "http://34.147.230.220:5000/speech"


app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(os.path.join(basedir, 'audio_files.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

class AudioFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)

@app.route('/')
def home():
    return render_template('trial.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/transcript')
def transcript():
    return render_template('transcript.html')


# def index():
#     with app.app_context():
#         audio_files = AudioFile.query.all()
#     return render_template('index.html', audio_files=audio_files)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        if file:
            # Create the 'uploads' folder if it doesn't exist
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            # Save the file to the uploads folder
            filename = basedir+'/uploads/'+file.filename
            file.save(filename)

            # Define the input and output files
            input_filename = file.filename
            output_filename = ''.join(input_filename.split('.')[:-1])+'.wav'

            # Get the format of the input file
            file_format = input_filename.split('.')[-1]

            if file_format != 'wav':
                # Converting the file and exporting the output file
                sound = AudioSegment.from_file(filename, format=file_format)
                sound.export(basedir+'/uploads/'+output_filename, format='wav')

            client = storage.Client()
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob(file.filename.split('.')[0])
            blob.upload_from_filename(basedir+'/uploads/'+output_filename)

            # with app.app_context():
            #     new_audio_file = AudioFile(filename=filename)
            #     db.session.add(new_audio_file)
            #     db.session.commit()

            # A GET request to the API
            response = requests.get(url)

            # Print the response
            response_json = response.json()

            # return render_template('index.html',response = response_json['text'])
            return render_template('dashboard.html', response = response_json['text'])

    return render_template('dashboard.html')


@app.route('/upload30seg', methods=['GET', 'POST'])
def upload30seg():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        if file:
            # Create the 'uploads' folder if it doesn't exist
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            # Save the file to the uploads folder
            filename = basedir+'/uploads/'+file.filename
            file.save(filename)

            # Define the input and output files
            input_filename = file.filename
            output_filename = ''.join(input_filename.split('.')[:-1])+'.wav'

            # Get the format of the input file
            file_format = input_filename.split('.')[-1]

            if file_format != 'wav':
                # Converting the file and exporting the output file
                sound = AudioSegment.from_file(filename, format=file_format)
                sound.export(basedir+'/uploads/'+output_filename, format='wav')

            API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
            headers = {"Authorization": f"Bearer {SM_TOKEN}"}

            def query(filename):
                with open(filename, "rb") as f:
                    data = f.read()
                response = requests.post(API_URL, headers=headers, data=data)
                return response.json()

            output = query(basedir+'/uploads/'+output_filename)

            os.remove(basedir+'/uploads/'+output_filename)
            os.remove(basedir+'/uploads/'+input_filename)

            if 'error' in output.keys():
                return render_template('trial.html', response = 'Format of file is incorrect.')
            else:
                return render_template('trial.html', response = output['text'])

    return render_template('trial.html')



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port = 5000)
