import os

# Getting params from the .env file

# GCP
PROJECT_ID = os.environ.get('PROJECT_ID')
BUCKET_NAME = os.environ.get("BUCKET_NAME")
BQ_DS = os.environ.get('BQ_DS')
BQ_USERT = os.environ.get('BQ_USERT')
BQ_AUDT = os.environ.get('BQ_AUDT')

# Hugging Face
SM_TOKEN = os.environ.get("SM_TOKEN")

# Flask
SUPER_SECRET = os.environ.get('SUPER_SECRET')
