Face Recognition Project with AWS Rekognition
Overview
This project utilizes AWS Rekognition for real-time face identification by allowing users to upload images to an S3 bucket. The uploaded images are processed to recognize faces, which are then indexed and stored in DynamoDB for future reference.

Features
Upload images to an S3 bucket.
Use AWS Rekognition to recognize and index faces.
Store metadata in DynamoDB.
Capture images from a webcam.
User-friendly web interface with Bootstrap.
Prerequisites
Before running the project, ensure you have the following:

Python 3.x installed.
AWS account with IAM permissions for S3, Rekognition, and DynamoDB.
Flask and required libraries installed. You can install them using pip:

/face_recognition_project
    /uploads            # Folder for temporarily storing uploaded images
    app.py              # Main Flask application
    lambda_function.py   # AWS Lambda function for face indexing

    Configure AWS Credentials: Make sure your AWS credentials are configured. You can set them up in ~/.aws/credentials:
    aws_access_key_id = YOUR_ACCESS_KEY
    aws_secret_access_key = YOUR_SECRET_KEY

Run the Flask application:
python app.py

Visit http://127.0.0.1:5000 in your web browser to access the application.
