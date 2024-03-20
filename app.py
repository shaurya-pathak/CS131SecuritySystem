from flask import Flask, request, jsonify, Response
from google.cloud import storage
import face_recognition
import numpy as np
import cv2
import pickle
import base64
from werkzeug.utils import secure_filename
import os
from Crypto.Cipher import AES
from imwatermark import WatermarkDecoder
import io
import time

app = Flask(__name__)

# Initialize Google Cloud Storage client
storage_client = storage.Client()
bucket_name = 'facial-recognition-cs131'  # Replace with your bucket name
blob_name = 'face_encodings.pkl'  # The name of your pickled file

# Load encodings and names from GCS
def load_encodings_from_gcs():
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    pickle_data = blob.download_as_bytes()
    data = pickle.loads(pickle_data)
    return data

def unpad(data):
    return data.rstrip(b"\0")

def decrypt_image_in_memory(encrypted_data, key):
    # Extract the initialization vector from the encrypted data
    iv = encrypted_data[:AES.block_size]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    # Decrypt the data and remove the padding
    decrypted_data = cipher.decrypt(encrypted_data[AES.block_size:])
    unpadded_data = unpad(decrypted_data)
    
    return unpadded_data

@app.route('/')
def index():
    return "Welcome to my Flask app!"

@app.route('/api/recognize', methods=['POST'])
def recognize_faces():
    timings = {}  # Dictionary to store timings
    try:
        start_time = time.time()
        # if 'file' not in request.files:
        #     return jsonify({"message": "No file part"}), 400
        # file = request.files['file']
        # if file.filename == '':
        #     return jsonify({"message": "No selected file"}), 400
        
        # # Read the AES key from the file
        # with open('aes_key.bin', 'rb') as key_file:
        #     aes_key = key_file.read()
        
        # # Read the encrypted file data
        # encrypted_data = file.read()
        
        # # Decrypt the image data in memory
        # decrypted_data = decrypt_image_in_memory(encrypted_data, aes_key)
        
        # # Convert the decrypted data to a format that face_recognition can work with
        # decrypted_image = face_recognition.load_image_file(io.BytesIO(decrypted_data))
        # decrypted_image = face_recognition.load_image_file(file)
        # preprocessing_time = time.time() - start_time
        # timings['loading'] = preprocessing_time
        
        # start_time = time.time()
        # bgr_image = cv2.cvtColor(decrypted_image, cv2.COLOR_RGB2BGR)

        # # Initialize the WatermarkDecoder
        # decoder = WatermarkDecoder('bytes', 32)

        # # Decode the watermark from the BGR image
        # watermark = decoder.decode(bgr_image, 'dwtDct')
        # decoded_watermark = watermark.decode('utf-8')
        
        # Find all the faces and face encodings in the unknown image
        # face_locations = face_recognition.face_locations(decrypted_image)
        # face_encodings = face_recognition.face_encodings(decrypted_image, face_locations)
        
        # if not request.is_json:
        #     return jsonify({"message": "Request body must be JSON"}), 400
        
        # data = request.get_json()
        
        # # Assuming `data` contains a list of face encodings (which are lists of floats)
        # face_encodings = data.get('face_encodings')
        # if face_encodings is None:
        #     return jsonify({"message": "No face_encodings in request"}), 400
        
        # # Convert the list of lists back to numpy arrays for processing
        # face_encodings = [np.array(encoding) for encoding in face_encodings]
        face_encodings = request.get_json()
        face_encodings = [np.array(encoding) for encoding in face_encodings]
        processing_time = time.time() - start_time
        timings['read encodings'] = processing_time
        start_time = time.time()

        # Load known face encodings and names
        data = load_encodings_from_gcs()
        known_face_encodings = data['encodings']
        known_face_names = data['names']

        names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = ""
            if True in matches:
                first_match_index = matches.index(True)
                name = known_face_names[first_match_index]
            if len(name) != 0:
                names.append(name)
        processing_time = time.time() - start_time
        timings['matching_face'] = processing_time
        start_time = time.time()
        return jsonify({"faces": names, "timings": timings}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
