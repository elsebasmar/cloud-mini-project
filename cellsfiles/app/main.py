# All flask modules
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired

# All modules related with login interface
from wtforms import FileField, SubmitField, StringField, PasswordField, EmailField
from wtforms.validators import InputRequired, Length, Regexp

# Module for hashing inputs
import hashlib
import uuid

import os
import datetime
from pytz import timezone
from google.cloud import storage, bigquery
import requests
from pydub import AudioSegment
from cellsfiles.params import *

# Creating the app with Flask
app = Flask(__name__)
# Setting up the app config
app.config['SECRET_KEY'] = SUPER_SECRET

# Hashing function
def md5(ip):
    return hashlib.md5(ip.encode('utf-8')).hexdigest()

# Defined base directory for easy handling
basedir = os.path.abspath(os.path.dirname(__file__))

# Home Page Elements
@app.route('/', methods=['GET'])
def home():
    return render_template('trial.html')

# Login Page Elements

# Define the class for the loginuserform
class LoginUserForm(FlaskForm):
    email = EmailField("email", validators=[InputRequired()])
    password = PasswordField("password", validators=[
        InputRequired(),
        Length(min=8),
    ])
    submit = SubmitField("submit", render_kw={'class': 'button'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Validate if the user in logged in
    if session.get('uid'):
        return redirect(url_for('dashboard', username=session.get('username')))

    # Create the form for the method GET
    if request.method == 'GET':
        form = LoginUserForm()
        return render_template('login.html', form=form)

    # The form is retrived from the request
    form = LoginUserForm(request.form)

    try:
        # Validation of the elements of the login
        if not form.validate_on_submit():
            flash('Invalid Form Input Please try again', 'error')
            return render_template('login.html', form=form)

        # TEMP
        email_column_id = 'email'
        password_column_id = 'password'

        # Create the query to the dataset in GBQ
        query = f"SELECT * FROM `{PROJECT_ID}.{BQ_DS}.{BQ_USERT}` WHERE `{email_column_id}` = '{form.email.data}' AND `{password_column_id}` = '{md5(form.password.data)}' LIMIT 1"
        # Create the client to generate the query
        client = bigquery.Client(project=PROJECT_ID)
        query_job = client.query(query)

        # Get the result from the query
        results = query_job.result()

        # Validation of results from query
        if results.total_rows == 0:
            flash('Invalid username/password.', 'error')
            return render_template('login.html', form=form)

        for row in results:
            session['username'] = row['username']
            session['uid'] = row['uid']
            session['email'] = row['email']
            break

        # Display message of success
        flash('Login successful! Welcome to your personal transcriber.', 'success')
        return redirect(url_for('dashboard', username=session.get('username')))

    except Exception as e:
        flash(f'Signup failed due to an error: {str(e)}', 'error')
        return render_template('login.html', form=form)


# Signup Page Elements

# Define the class registration
class RegisterUserForm(FlaskForm):
    username = StringField("username", validators=[
        InputRequired(),
        Length(min=8),
        Regexp('^[a-zA-Z0-9]*$',
               message='Username must be alphanumeric and 8 atleast characters long.')
    ])
    email = EmailField("email", validators=[InputRequired()])
    password = PasswordField("password", validators=[
        InputRequired(),
        Length(min=8),
        Regexp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,}$',
               message='Password must have at least 1 lowercase, 1 uppercase, 1 special character, 1 number')
    ])
    submit = SubmitField("submit", render_kw={'class': 'button'})

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    # Validate the session
    if session.get('uid'):
        return redirect(url_for('dashboard', username=session.get('username')))

    # Create the registration form
    if request.method == 'GET':
        form = RegisterUserForm()
        return render_template('signup.html', form=form)

    # Get the registration form
    form = RegisterUserForm(request.form)

    username_column_id = 'username'
    email_column_id = 'email'


    try:
        # Validation of the elements of the login
        if not form.validate_on_submit():
            flash('Invalid Form Input Please try again', 'error')
            return render_template('signup.html', form=form)

        # Create the query to the dataset in GBQ
        query = f"SELECT * FROM `{PROJECT_ID}.{BQ_DS}.{BQ_USERT}` WHERE `{username_column_id}` = '{form.username.data}' OR `{email_column_id}` = '{form.email.data}' LIMIT 1"
        # Create the client to generate the query
        client = bigquery.Client(project=PROJECT_ID)
        query_job = client.query(query)

        # Get the result from the query
        results = query_job.result()
        # Validating if the user is already in the dataset
        if results.total_rows != 0:
            flash('Try Signing up with different username/password.', 'error')
            return render_template('signup.html', form=form)

        # Locating the dataset and table to where the user will be saved
        dataset_ref = client.dataset(BQ_DS)
        user_table_ref = dataset_ref.table(BQ_USERT)

        # Define the squema of the query
        schema = [
            bigquery.SchemaField("username", "STRING"),
            bigquery.SchemaField("email", "STRING"),
            bigquery.SchemaField("password", "STRING"),
            bigquery.SchemaField("uid", "STRING"),
        ]

        # Configure the job config of the query
        job_config = bigquery.LoadJobConfig(schema=schema)

        # Define the row to be inserted
        row_to_insert = {
            "username": form.username.data,
            "email": form.email.data,
            "password": md5(form.password.data),
            "uid": str(uuid.uuid4())
        }

        # Load the user to the big query
        job = client.load_table_from_json(
            [row_to_insert],
            user_table_ref,
            job_config=job_config
        )

        job.result()

        flash('Signup successful! Please Login to continue.', 'success')
        return redirect(url_for('login'))

    except Exception as e:
        flash(f'Signup failed due to an error: {str(e)}', 'error')
        return render_template('signup.html', form=form)


# Dashboard Page Elements

# Define the class to upload the from from the user
class UploadFileForm(FlaskForm):
    file = FileField(
        'file',
        validators=[
            FileRequired(message='Please choose a file'),
            FileAllowed(['wav','m4a'], message='Only audio files are allowed')
        ]
    )
    submit = SubmitField("submit", render_kw={'class': 'button'})

@app.route('/dashboard', methods = ['GET'])
def dashboard():
    # Validating the session
    if not session.get('uid'):
        flash('Please Login to continue.', 'error')
        return redirect(url_for('login'))

    # Get all information of user from Big Query
    if request.method == 'GET':

        form = UploadFileForm()
        user_id = session.get('uid')

        #TEMP
        creation_timestamp_column_id = 'creation_timestamp'
        user_id_column_id = 'user_id'

        # Query to get the information of the user.
        query = f"SELECT * FROM `{PROJECT_ID}.{BQ_DS}.{BQ_AUDT}` WHERE `{user_id_column_id}` = '{user_id}' ORDER BY `{creation_timestamp_column_id}` DESC"
        # Create the client to generate the query
        client = bigquery.Client(project=PROJECT_ID)
        query_job = client.query(query)

        # Wait for the job to complete
        results = query_job.result()

        # Process and print the results
        records = [dict(row) for row in results]
        print (str(session.get('username')).capitalize())
        return render_template('dashboard.html', form=form, records=records, username=str(session.get('username')).capitalize())

# Upload Trial form

@app.route('/upload30seg', methods=['GET', 'POST'])
def upload30seg():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        if file:

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

            # return output
            if 'error' in output.keys():
                return render_template('trial.html', response = 'Format of file is incorrect.')
            else:
                return render_template('trial.html', response = output['text'])

    return render_template('trial.html')


# Upload format page

# Get the audio duration
def get_audio_duration(file_path):
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        audio = AudioSegment.from_file(file_path)
        duration_seconds = len(audio)
        return duration_seconds
    except Exception as e:
        print(f"Error: {e}")
        return 0

# Get the upload time
def get_upload_timestamp():
    # Get the current timestamp
    return datetime.datetime.utcnow()

@app.route('/upload', methods=['POST'])
def upload():

    # Define the input form
    form = UploadFileForm()

    try:
        # Create the audio id
        audio_id = str(uuid.uuid4())
        # Create the user id
        user_id = session.get('uid')

        # Get the file
        file = request.files['file']

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

        # Connecting to GCS to upload the file
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(audio_id)

        # Upload the audio file to Google Cloud Storage
        blob.upload_from_filename(basedir+'/uploads/'+output_filename)

        # Get the URL of the file
        expiration_time = datetime.datetime.now(timezone('UTC')) + datetime.timedelta(days=3650)
        file_url = blob.generate_signed_url(expiration=expiration_time)

        url = 'http://34.89.80.52:5000/speech/'+audio_id

        # A GET request to the API
        response = requests.get(url)

        # Same the response
        response_json = response.json()

        if 'error' in response_json.keys():
            flash(f'Failed uploading the file. Please try again later', 'error')
            return redirect(url_for('dashboard', username=session.get('username')))

        blob = bucket.blob(audio_id + '_transcript')
        blob.upload_from_string(response_json['text'], content_type='text/plain')
        transcript_url = blob.generate_signed_url(expiration=expiration_time)

        # get the size of file in bytes
        input_fileduration = get_audio_duration(filename)

        # when the file was uploaded by the user
        creation_timestamp = get_upload_timestamp().isoformat()

        # Record the reference and metadata of the audio file in BigQuery
        client = bigquery.Client(project=PROJECT_ID)
        dataset_ref = client.dataset(BQ_DS)
        audio_table_ref = dataset_ref.table(BQ_AUDT)

        # Define the table schema based on the requirements
        schema = [
            bigquery.SchemaField("audio_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("file_name", "STRING"),
            bigquery.SchemaField("file_url", "STRING"),
            bigquery.SchemaField("file_size", "INTEGER"),
            bigquery.SchemaField("audio_duration", "INTEGER"),
            bigquery.SchemaField("creation_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("processed_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("transcript_url", "STRING")
        ]
        job_config = bigquery.LoadJobConfig(schema=schema)

        # Create the row to insert
        row_to_insert = {
            "audio_id": audio_id,
            "user_id": user_id,
            "file_name": input_filename,
            "file_url": file_url,
            "file_size": 0,
            "audio_duration": input_fileduration,
            "creation_timestamp": creation_timestamp,
            "processed_timestamp": creation_timestamp,
            "transcript_url": transcript_url
        }

        # Load the job to the table
        job = client.load_table_from_json(
            [row_to_insert],
            audio_table_ref,
            job_config=job_config
        )

        # Produce the call
        job.result()

        flash(f'Successfully uploaded the file.', 'success')
        return redirect(url_for('dashboard',username=session.get('username')))

    except Exception as e:
        flash(f'Upload failed due to an error: {str(e)}', 'error')
        return redirect(url_for('dashboard',username=session.get('username')))

# Log out page

@app.route('/logout', methods=['GET'])
def logout():
    if 'uid' in session:
        # Destroy the session data related to the user
        session.pop('uid')
        session.pop('email')
        session.pop('username')
        flash(f'Logged out successfully.', 'success')

    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 5000)
