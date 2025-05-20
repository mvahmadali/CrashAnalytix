# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from PIL import Image
# import io
# from ultralytics import YOLO

# app = Flask(__name__)
# CORS(app)

# # Load YOLO model
# model = YOLO('best.pt')

# @app.route('/predict', methods=['POST'])
# def predict():
#     print("Received request!")  
#     print("Request Content-Type:", request.content_type)  
#     print("Request files keys:", request.files.keys())  

#     # Ensure a file is uploaded
#     if 'file' not in request.files:
#         print("No file found in request!")  
#         return jsonify({'error': 'No file uploaded'}), 400

#     file = request.files['file']
#     print(f"Received file: {file.filename}")  

#     # Read the image
#     image = Image.open(io.BytesIO(file.read()))

#     # Get prediction from model
#     results = model(image)  
#     predictions = results[0].boxes  

#     # Check if accident detected (class ID 0)
#     accident_detected = any(predictions.cls.tolist()) and 0 in predictions.cls.tolist()

#     result = 'Accident Detected' if accident_detected else 'No Accident Detected'
#     return jsonify({'result': result})

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)



from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import os
from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

model = YOLO('best.pt')  

@app.route('/predict', methods=['POST'])
def predict():
    print(" Received request!")  
    print(" Request Content-Type:", request.content_type)  
    print(" Request files keys:", request.files.keys())  

    if 'file' not in request.files:
        print(" No file found in request!")  
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    print(f" Received file: {file.filename}")  
    
    temp_video_path = "temp_video.mp4"
    file.save(temp_video_path)
    
    cap = cv2.VideoCapture(temp_video_path)
    if not cap.isOpened():
        print(" Error opening video file")  
        return jsonify({'error': 'Error opening video file'}), 400
    
    frame_skip = 1
    frame_count = 0
    accident_detected = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        if frame_count % frame_skip != 0:
            continue
        
        results = model(frame, device='cpu')
        predictions = results[0].boxes  

        # Convert float class labels to int
        detected_classes = [int(cls) for cls in predictions.cls.tolist()]
        print(f" Detected Classes in Frame {frame_count}: {detected_classes}")  

        # Check if class '0' (accident) is detected
        if 0 in detected_classes:
            print(" Accident Detected in Frame", frame_count)
            accident_detected = True
            break  # Stop checking further if accident is detected
    
    cap.release()
    os.remove(temp_video_path)  
    
    result = 'Accident Detected' if accident_detected else 'No Accident Detected'
    print(" Final Response:", result)
    return jsonify({'result': result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

