# Audio to Text Coverter Using GCP and Flask ([Echoscript](http://34.147.158.180:5000/))
### System Architecture
![Apllication Architecture](https://github.com/elsebasmar/cloud-mini-project/assets/148969526/c92439b9-87ba-4daa-b3d1-037ee432afd5)

### Prerequisites

- Python: Familiarity with Python is needed and and also working knowledge of libraries within is important.
- Python should be installed in either the personal system or on the cloud
- Basic Understanding of the Flask framework as mojor work is done this light weight framework. 
- Usage of Git and GitHub

Post the Prerequisites the following packages are to be mandatorily installed in the system(as we can see in the [requirements.txt](https://github.com/elsebasmar/cloud-mini-project/blob/main/requirements.txt)):
1. **Flask**: Flask is a micro web framework written in Python. It is classified as a microframework because it does not require particular tools or libraries.
    **Installation**:
    ~~~sh
    $ pip install Flask
    ~~~
2. **Flask-SQLAlchemy**: Flask-SQLAlchemy is an extension for Flask that adds support for SQLAlchemy to your application. It simplifies using SQLAlchemy with Flask by setting up common objects and patterns for using those objects, such as a session tied to each web request, models, and engines.
    **Installation**:
    ~~~sh
    pip install -U Flask-SQLAlchemy
    ~~~
3. **Flask-GoogleStorage**: Flask extension for adding storage capabilities using Google Cloud Storage.
    **Installation**:
    ~~~sh
    $ pip install flask-googlestorage
    ~~~
4. **pydub**: It is a simple Python library to manipulate audio with an simple and easy high level interface. 
    **Installation**:
    ~~~sh
    $ pip install pydub
    ~~~
5. **ffprobe-python**: Also a Python Library to put wrapper around the ffprobe command to extract metadata from media files.
    **Installation**:
    ~~~sh
    $ pip install ffprobe
    ~~~
6. **ffmpeg-python**: A complete, cross-platform solution to record, convert and stream audio and video. There are a variety of ways to install FFmpeg, such as the [official download links](https://ffmpeg.org/download.html), or using your package manager of choice (e.g. sudo apt install ffmpeg on Debian/Ubuntu, brew install ffmpeg on OS X, etc.)
    **Installation**:
    ~~~sh
    $ pip install ffmpeg-python
    ~~~

The project Directory:

<img width="420" alt="Project Directory" src="https://github.com/elsebasmar/cloud-mini-project/assets/148969526/280af553-fd3d-4e0d-81fb-bbfeea8aa075">

## Program Flow

<img width="1427" alt="Screenshot 2023-12-12 at 1 41 25 PM" src="https://github.com/elsebasmar/cloud-mini-project/assets/148969526/d6e8e9eb-e49e-4020-ba7d-bdc418f6e39e">

The Programflow is approximately shown throught the flow chart below describing each and every page.

## Operations in the App
The URL we would be using for the application is [http://34.147.158.180:5000/](http://34.147.158.180:5000/)

Once you open the URL you can see the Dashboard which is the home page of the app with the menu bar with options: Login, Signup and About Us

1. **Sign up page**: The Sign up option will lead to the new page where you will be given an option to register to start using the app. In the backend part in the Flask we will be recording the values for the input and will the hashing the the password so that the password is secured. Now this is stored in a table(**user_table**) in big query.

user_table:
<img width="1061" alt="User ID table BQ" src="https://github.com/elsebasmar/cloud-mini-project/assets/148969526/812452ee-3ae0-4c7a-bc7b-3422cef2959a">

The code the below is shown:
```py
def register():
    form = RegisterUserForm()
    if form.validate_on_submit():

        username = form.username
        email = form.email
        password = form.password

        # confirm_password = form.confirm_password
        # if password != confirm_password:
        #     return "Passwords do not match please try again."

        user_id = str(uuid.uuid4())

        dataset_ref = client.dataset(dataset_id)
        user_table_ref = dataset_ref.table(user_table_id)

        # You may need to define your table schema based on your requirements
        schema = [
            bigquery.SchemaField("username", "STRING"),
            bigquery.SchemaField("email", "STRING"),
            bigquery.SchemaField("password", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
        ]
        job_config = bigquery.LoadJobConfig(schema=schema)

        row_to_insert = {
            "username": username,
            "email": email,
            "password": md5(password),
            "user_id": user_id
        }

        job = client.load_table_from_json([row_to_insert], user_table_ref, job_config=job_config)
        job.result()  # Wait for the job to complete

        return "Registerd user successfully."

    return render_template('signup.html', form=form)

```
2. Login Page: This page gives the user to login into the application using their Email and Password and if the details input by the user is in accordance with any row in the table: **user_table** in the Big query, then the user is logged into the app and the UI changes where he can upload the audio file.

~~~py
def login():
    form = LoginUserForm()
    if form.validate_on_submit():

        # username = form.username
        email = form.email
        password = form.password

        # Make an API request to get the data from the table
        query = f"SELECT * FROM `{project_id}.{dataset_id}.{user_table_id}` WHERE `{email_column_id}` = '{email}' AND `{password_column_id}` = '{md5(password)}' LIMIT 1"

        query_job = client.query(query)

        # Wait for the job to complete
        results = query_job.result()

        if len(results) == 0:
            # invalid credentials and return back to login page
            return "Invalid Credentials"
        else:
            # create the session
            # set the user_id, email and username
            # redirect to listing page

             # Assuming 'user_id', 'email', and 'username' are columns in the user_table
            user_data = results[0]  # Assuming the first row contains user data
            user_id = user_data['user_id']
            email = user_data['email']
            username = user_data['username']

            # Create a session and set user data
            session['user_id'] = user_id
            session['email'] = email
            session['username'] = username
            return render_template('index.html', form=form)

    return render_template('login.html', form=form)
~~~
3. **Upload Page**: Once in the upload page you have option to selct a file  from the local system and upload it. In the backend process the audio is processed by two python libraries Python-ffmpeg and Python-ffprobe.The ffmpeg function is used to convert the audio file to the required format in this case which is .wav file. The ffprobe wraps around the .wav file and extracts the meta data from the audio and stores this data corresponding the the unique user_id in the Big Query table(**audio_meta**).

audio_meta table:
<img width="1066" alt="Audio table BQ" src="https://github.com/elsebasmar/cloud-mini-project/assets/148969526/a25d419b-5140-4050-a742-223f74c0f835">

The code is:
~~~py
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

            if 'error' in output.keys():
                return render_template('trial.html', response = 'Format of file is incorrect.')
            else:
                return render_template('trial.html', response = output['text'])

    return render_template('trial.html')
~~~

In the operations done on the Audio files we do the CRUD operation through REST services. Mainly for creating the transcript for an audio file we uploading an audio file through the POST which can be seen in the upload function of the code in the **main.py** file. For the GET functionality we are using **curl -X "GET" 34.147.158.180:5000/get_all_files_ids** which would give the output of all the audio files details which have been uploaded by different User IDs. Lastly for the DELETE we are using **curl -X "DELETE" 34.147.158.180:5000/deletefile/<file_id>** which would give us the functionality to delete any audio file though the audio file ID number. 

## HTML Templates

We are using a total of 9 HTML templates for each page to be as UI friendly as possible and attractive.
1. [index.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/index.html)
2. [dashboard.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/dashboard.html)
3. [login.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/login.html)
4. [signup.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/signup.html)
5. [thankyou.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/thankyou.html)
6. [transcript.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/transcript.html)
7. [trial.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/trial.html)
8. [upload.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/upload.html)
9. [welcome_page.html](https://github.com/elsebasmar/cloud-mini-project/blob/main/cellsfiles/app/templates/welcome_page.html)

The Templates in the Project:

<img width="305" alt="Templates" src="https://github.com/elsebasmar/cloud-mini-project/assets/148969526/6b68c478-6011-4da1-9fbb-e23b38c0d647">


## Database

### Big Query

BigQuery is a fully managed enterprise data warehouse that helps you manage and analyze your data with built-in features like machine learning, geospatial analysis, and business intelligence. BigQuery's serverless architecture lets you use SQL queries to answer your organization's biggest questions with zero infrastructure management. BigQuery's scalable, distributed analysis engine lets you query terabytes in seconds and petabytes in minutes.

BigQuery maximizes flexibility by separating the compute engine that analyzes your data from your storage choices. You can store and analyze your data within BigQuery or use BigQuery to assess your data where it lives. Federated queries let you read data from external sources while streaming supports continuous data updates. Powerful tools like BigQuery ML and BI Engine let you analyze and understand that data.

## External API
### Hugging Face API(Whisper)

Whisper is a pre-trained model for automatic speech recognition (ASR) and speech translation. Trained on 680k hours of labelled data, Whisper models demonstrate a strong ability to generalise to many datasets and domains without the need for fine-tuning.

Whisper was proposed in the paper [Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356) by Alec Radford et al. from OpenAI. The original code repository can be found [here](https://github.com/openai/whisper).

Whisper large-v3 has the same architecture as the previous large models except the following minor differences:

1. The input uses 128 Mel frequency bins instead of 80
2. A new language token for Cantonese

The Whisper large-v3 model is trained on 1 million hours of weakly labeled audio and 4 million hours of pseudolabeled audio collected using Whisper large-v2. The model was trained for 2.0 epochs over this mixture dataset. The large-v3 model shows improved performance over a wide variety of languages.

## Application Running
Dashboard: This is the main page of the Application it has options on the menu bar and if you scroll down we can see the option to upload the audio file. But it only works if we are logged in with the application.

Signup: This page is for the registering as the new user so that you can access the functionality.
<img width="560" alt="Sign up" src="https://github.com/elsebasmar/cloud-mini-project/assets/148969526/eb96dd12-b56c-4406-8572-5325657f2a49">


Login: This page is to login into the application.
<img width="1440" alt="Login" src="https://github.com/elsebasmar/cloud-mini-project/assets/148969526/a4e4a6f7-ee3f-4c0b-986c-dd83a488832c">

Upload: This page comes once you the user is logged and the authentication is done.
<img width="1440" alt="Upload" src="https://github.com/elsebasmar/cloud-mini-project/assets/148969526/832f82fa-8327-4a9a-939d-41f20a7480ba">

Transcript: This page gives the transcript of the processed audio file in the form of text.


## Conclusion

We buit an Application which can take take input of an audio file convert into an .wav file and can annotate the text file from the audio in the file, With that we are also able to apply the authentication system in the application where the user is able to access the application only after logging into the application through an Email and password.


