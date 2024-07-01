from flask import Flask, request, render_template_string, redirect, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from werkzeug.utils import secure_filename
import boto3
import io
import os
import base64
import json
from PIL import Image
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

# Initialize Boto3 clients and resources
s3 = boto3.resource('s3')
rekognition = boto3.client('rekognition', region_name='us-east-1')
dynamodb = boto3.client('dynamodb', region_name='us-east-1')

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads/'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Flask-WTF forms for photo upload and new person form
class PhotoForm(FlaskForm):
    photo = FileField('Upload Image', validators=[FileRequired()])

class NewPersonForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    photo = FileField('Upload Image', validators=[FileRequired()])
    submit = SubmitField('Upload')
    
# Flask-WTF form for image upload
class UploadForm(FlaskForm):
    photo = FileField('Upload Image', validators=[FileRequired()])
    
    

# Route for uploading images to S3
@app.route("/registration", methods=['GET', 'POST'])
def registration():
    form = UploadForm()
    message = None

    if form.validate_on_submit():
        photo = form.photo.data
        filename = secure_filename(photo.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(filepath)

        # Upload the file to S3
        object = s3.Object('persons-20240629', 'index/' + filename)
        object.put(Body=open(filepath, 'rb'), Metadata={'FullName': request.form['fullname']})

        message = f"Image {filename} uploaded successfully!"

    return render_template_string('''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
        <title>AWS Rekognition: Real-Time Face ID</title>
        <style>
        body {
    margin: 0;
    font-family: Arial, sans-serif;
    background-color: #f0f0f0;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}
    .container2{
    display: flex;
    flex-direction: column;
    width: 90%;
    height: 90%;
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    overflow: hidden;
}
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #4CAF50;
    color: white;
    padding: 20px;
    font-size: 24px;
}
.header .title {
    flex: 1;
}
.header button {
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    background-color: white;
    color: #4CAF50;
    font-size: 16px;
    cursor: pointer;
    margin-left: 10px;
}
        </style>
    </head>
    <body>
    
     <div class="container2">
    <div class="header">
        <div class="title">AWS Rekognition: Real-Time Face ID</div>
        <button id="registerBtn">back</button>
      
        <form method="POST" enctype="multipart/form-data" class="mt-4">
            {{ form.csrf_token }}           
        </form>
    </div>
        <div class="container">
            <div class="row">
                <div class="col-md-6 offset-md-3">
                    <h1 class="text-center">Upload Image to S3</h1>
                    <form method="POST" enctype="multipart/form-data" class="mt-4">
                        {{ form.csrf_token }}
                        <div class="form-group">
                            <label for="fullname" class="form-label">Full Name</label>
                            <input type="text" name="fullname" id="fullname" class="form-control" required>
                        </div>
                        <div class="form-group">
                            {{ form.photo.label(class="form-label") }}
                            {{ form.photo(class="form-control-file") }}
                        </div>
                        <button type="submit" class="btn btn-primary btn-block">Upload</button>
                    </form>
                    {% if message %}
                    <div class="alert alert-success mt-4" role="alert">
                        {{ message }}
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
        <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.4/dist/umd/popper.min.js"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
        <script>
          document.getElementById('registerBtn').addEventListener('click', function() {
        window.location.href = "{{ url_for('upload_image') }}";
    });
        </script>
    </body>
    </html>
    ''', form=form, message=message)
    
    
    # Route for uploading image and recognizing faces
@app.route("/", methods=['GET', 'POST'])
def upload_image():
    form = PhotoForm()
    new_person_form = NewPersonForm()
    message = None

    if request.method == 'POST':
        if form.validate_on_submit():
            photo = form.photo.data
            filename = secure_filename(photo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(filepath)

            # Process the image
            with Image.open(filepath) as image:
                stream = io.BytesIO()
                image.save(stream, format="JPEG")
                image_binary = stream.getvalue()

        elif 'webcam_image' in request.form:
            data_url = request.form['webcam_image']
            # Decoding the base64 image data
            header, encoded = data_url.split(",", 1)
            image_binary = base64.b64decode(encoded)

        else:
            return redirect(url_for('upload_image'))

        # Call Rekognition to search for faces
        response = rekognition.search_faces_by_image(
            CollectionId='famouspersons',
            Image={'Bytes': image_binary}
        )
        
         # Log the entire response
        # print("Response from Rekognition:", response) 
        


        found = False
        messages = []
        for match in response['FaceMatches']:
            face_id = match['Face']['FaceId']
            confidence = match['Face']['Confidence']
            
            face = dynamodb.get_item(
                TableName='facerecognition',
                Key={'RekognitionId': {'S': face_id}}
            )
            
           
            if 'Item' in face:
                fullname = face['Item']['FullName']['S']
                messages.append(f"<h2>Name: {fullname}</h2>")
                messages.append(f"<small>Confidence={confidence}%</small>")
                found = True

        if not found:
            messages.append("Person cannot be recognized")

        message = "<br>".join(messages)

    return render_template_string('''
 <!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>AWS Rekognition: Real-Time Face ID</title>
    <style>
        body {
    margin: 0;
    font-family: Arial, sans-serif;
    background-color: #f0f0f0;
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
}
.container {
    display: flex;
    flex-direction: column;
    width: 90%;
    height: 90%;
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    overflow: hidden;
}
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #4CAF50;
    color: white;
    padding: 20px;
    font-size: 24px;
}
.header .title {
    flex: 1;
}
.header button {
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    background-color: white;
    color: #4CAF50;
    font-size: 16px;
    cursor: pointer;
    margin-left: 10px;
}
.content {
    display: flex;
    flex: 1;
}
.left-side, .right-side {
    flex: 1;
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.left-side {
    background-color: #f9f9f9;
}

.left-side .button-group { 
    display: flex;
    gap: 10px;
    margin-top: 10px
}
.left-side button {
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    background-color: #4CAF50;
    color: white;
    font-size: 16px;
    cursor: pointer;
}
.right-side {
    background-color: #e3e3ff;
}
.profile {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    background-color: white;
    padding: 20px;
    border-radius: 10px;
    width: 100%;
    max-width: 400px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}
.profile img.profile-pic {
    border-radius: 10px;
    margin-bottom: 20px;
    width: 100%;
    max-width: 200px;
}
.profile .info h2 {
    margin: 0;
    color: #4CAF50;
    font-size: 24px;
}
.profile .info p {
    margin: 10px 0;
    color: #666;
    font-size: 18px;
}
.profile .info .icons {
    display: flex;
    justify-content: space-around;
    margin-top: 20px;
}
.profile .info .icons img {
    width: 30px;
    height: 30px;
}
@media (max-width: 1200px) {
         .container {
                width: 100%;
                height: 100%;
            }
            .content {
                flex-direction: column;
            }
            .right-side, .left-side {
                width: 100%;
                max-width: none;
            }
            .profile {
                width: 90%;
                max-width: 400px; /* Ensure max width doesn't exceed 400px */
                margin: 20px auto; /* Center align the profile section */
            }
            .left-side .button-group { 
                flex-direction: column;
                width: 100%;
            }
        }

    </style>
</head>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="title">AWS Rekognition: Real-Time Face ID</div>
        <button id="registerBtn">Register</button>
      
        <form method="POST" enctype="multipart/form-data" class="mt-4">
            {{ form.csrf_token }}           
        </form>
    </div>
    <div class="content">
        <div class="left-side">
            <div class="video-container">
                <video id="video" width="640" height="480" autoplay></video>
                <canvas id="canvas" width="640" height="480" style="display:none;"></canvas>
            </div>
            <div class="button-group">
                <form id="webcamForm" method="POST">
                    <input type="hidden" name="webcam_image" id="webcam_image">
                    <button id="snap">Capture Photo</button>
                    <button type="submit" id="snap">Upload Photo</button>
                </form>
            </div>
        </div>
        <div class="right-side">
            <div class="profile">
              
                <div class="info">
                 <h2 class="text-center">User Details</h2>
                    {% if message %}
                    <div class="results">
                        <p>{{ message|safe }}</p>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
<script>
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const snap = document.getElementById('snap');
    const webcamForm = document.getElementById('webcamForm');
    const webcamImage = document.getElementById('webcam_image');
    
    // Get access to the camera
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true }).then(function(stream) {
            video.srcObject = stream;
            video.play();
        });
    }

    // Capture the image
    snap.addEventListener('click', function() {
        const context = canvas.getContext('2d');
        context.drawImage(video, 0, 0, 640, 480);
        const dataURL = canvas.toDataURL('image/jpeg');
        webcamImage.value = dataURL;
        
        // Hide the video and show the canvas
        video.style.display = 'none';
        canvas.style.display = 'block';
        
        // After 3 seconds, hide the canvas and show the video
        setTimeout(function() {
            canvas.style.display = 'none';
            video.style.display = 'block';
        }, 3000);
    });
    
    
     document.getElementById('registerBtn').addEventListener('click', function() {
        window.location.href = "{{ url_for('registration') }}";
    });
    
</script>
</body>
</html>

    ''', form=form, new_person_form=new_person_form, message=message)

if __name__ == "__main__":
    app.run(debug=True)