import requests
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import cv2
from threading import Thread
import io
import time
from imwatermark import WatermarkEncoder
from datetime import datetime


def intruder_detector():
    # Initialize the camera
    cap = cv2.VideoCapture(1)  # Adjust the camera index as needed

    framecount = 0
    strt_time = time.time()
    comparison_frame = None
    movement_detected = False
    contours = []

    while True:
        framecount += 1
        movement_detected = False

        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Convert BGR to RGB (for displaying with correct colors)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process the frame
        processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        processed_frame = cv2.GaussianBlur(processed_frame, (5, 5), 0)

        if comparison_frame is None or time.time() - strt_time > 3:
            comparison_frame = processed_frame
            strt_time = time.time()

        # Calculate difference
        diff_frame = cv2.absdiff(src1=comparison_frame, src2=processed_frame)

        # Apply threshold to get frame with white regions for moving objects
        thresh_frame = cv2.threshold(src=diff_frame, thresh=20, maxval=255, type=cv2.THRESH_BINARY)[1]

        # Find contours of moving objects
        contours, _ = cv2.findContours(image=thresh_frame, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

        # Draw green rectangles around each contour on the original frame
        for contour in contours:
            if cv2.contourArea(contour) < 10000:
                continue  # too small: skip!
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(img_rgb, (x, y), (x + w, y + h), (0, 255, 0), 3)
            movement_detected = True

        if movement_detected:
            if is_locked:
                # If the system is locked and movement is detected, display "ALARM!!"
                cv2.putText(img=img_rgb, text="ALARM!!", org=(75, 20), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.7, color=(0, 0, 255), thickness=2)
                # Play alarm sound here
            else:
                # If the system is unlocked and movement is detected, display "Authorized movement"
                cv2.putText(img=img_rgb, text="Authorized movement", org=(75, 20), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.7, color=(0, 255, 0), thickness=2)
        else:
            # If no movement is detected, display "Secure" or "Unlocked" based on the lock status
            status_text = "Secure" if is_locked else "Unlocked"
            status_color = (0, 0, 255) if is_locked else (0, 255, 0)
            cv2.putText(img=img_rgb, text=status_text, org=(75, 20), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.7, color=status_color, thickness=2)

        # Display the result
        cv2.imshow('Result', img_rgb)

        # Press ESCAPE to exit
        if cv2.waitKey(30) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

# Global variable to track the lock status
is_locked = True  # Start with the system in a 'Secure' state

def update_gui_status(face_count):
    global is_locked  # Use the global variable within this function
    
    # If faces are detected, toggle the lock status
    if face_count > 0:
        is_locked = not is_locked  # Toggle the status
        
        # Update the label text and background color based on the new lock status
        if is_locked:
            status_label.config(text="Secure", bg="red")
        else:
            status_label.config(text="Unlocked", bg="green")

def pad(data):
    return data + b"\0" * (AES.block_size - len(data) % AES.block_size)

def encrypt_image_in_memory(image_data, key):
    padded_data = pad(image_data)
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = iv + cipher.encrypt(padded_data)
    return encrypted_data

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import requests
import cv2
import io

def pad(data):
    return data + b"\0" * (AES.block_size - len(data) % AES.block_size)

def encrypt_image_in_memory(image_data, key):
    padded_data = pad(image_data)
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = iv + cipher.encrypt(padded_data)
    return encrypted_data

def read_aes_key_from_file(key_file_path='aes_key.bin'):
    with open(key_file_path, 'rb') as key_file:
        key = key_file.read()
    return key

def send_image_to_api(image_buffer):
    api_url = 'https://smooth-era-414321.ue.r.appspot.com/api/recognize'
    resized_image = cv2.resize(image_buffer, (640, 480))
    # Generate a watermark with the current datetime
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wm = current_datetime
    
    # Initialize the WatermarkEncoder
    encoder = WatermarkEncoder()
    encoder.set_watermark('bytes', wm.encode('utf-8'))
    
    # Apply the watermark to the resized image
    bgr_encoded = encoder.encode(resized_image, 'dwtDct')
    
    # If you need the watermarked image as bytes (for example, to send it in a response), use cv2.imencode
    _, image_bytes = cv2.imencode('.jpg', bgr_encoded)
    image_bytes = image_bytes.tobytes()
    
    # Read the AES key from the file
    aes_key = read_aes_key_from_file()
    
    # Encrypt the image data in memory
    encrypted_image_data = encrypt_image_in_memory(image_bytes, aes_key)
    
    # Create an in-memory bytes buffer from the encrypted image data
    in_memory_file = io.BytesIO(encrypted_image_data)
    files = {'file': ('image.jpg', image_bytes, 'application/octet-stream')}
    
    # Send the POST request to the API endpoint with the encrypted image data
    response = requests.post(api_url, files=files)
    
    # Check the response
    if response.status_code == 200:
        print("Response from server:", response.json())
        update_gui_status(len(response.json()['faces']))
    else:
        print("Error:", response.status_code, response.text)

def capture_and_send_image():
    # Start video capture from the webcam
    cap = cv2.VideoCapture(1) # Keep at 1

    # Check if the webcam is opened correctly
    if not cap.isOpened():
        raise IOError("Cannot open webcam")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Display the resulting frame in a window called 'Camera'
        cv2.imshow('Camera', frame)
        
        # Press 'c' to capture the image or ESC to quit
        key = cv2.waitKey(1)
        if key == ord('c'):
            # Run the send image to API function in a thread to avoid freezing the GUI
            Thread(target=send_image_to_api, args=(frame,)).start()
            break
        elif key == 27:  # ESC key
            break

    # Release the capture and close any OpenCV windows
    cap.release()
    cv2.destroyAllWindows()


# Replace the existing lock_unlock_action function with this
def lock_unlock_action():
    capture_and_send_image()


# Function for "Security Cam 1" button
def security_cam_action():
    intruder_detector()

# Function to exit the application
def exit_app():
    root.destroy()

# Create the main window
root = tk.Tk()
root.title("Face Recognition Client")
# Initialize as "Secure" and red background
status_label = tk.Label(root, text="Secure", bg="red", font=("Helvetica", 24))
status_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

# Add "Lock/Unlock" button
lock_unlock_button = tk.Button(root, text="Lock/Unlock", command=lock_unlock_action)
lock_unlock_button.pack(pady=10)

# Add "Security Cam 1" button
security_cam_button = tk.Button(root, text="Security Cam 1", command=security_cam_action)
security_cam_button.pack(pady=10)

# Add "Exit" button
exit_button = tk.Button(root, text="Exit", command=exit_app)
exit_button.pack(pady=10)

# Start the GUI loop
root.mainloop()
