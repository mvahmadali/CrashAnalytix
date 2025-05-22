from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import os
from ultralytics import YOLO
import uuid
from datetime import datetime
# Import your db functions
from db import save_accident, get_all_accidents, get_accident_by_id

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

        detected_classes = [int(cls) for cls in predictions.cls.tolist()]
        print(f" Detected Classes in Frame {frame_count}: {detected_classes}")  

        if 0 in detected_classes:
            print(" Accident Detected in Frame", frame_count)
            accident_detected = True
            break
    
    cap.release()
    os.remove(temp_video_path)  
    
    if accident_detected:
        response = {
            "result": "Accident Detected",
            "severity": "Moderate",
            "entities": [
                {
                    "type": "truck",
                    "license_plate": "NWFP-893"
                },
                {
                    "type": "car",
                    "license_plate": "ABC-5678"
                },
                {
                    "type": "pedestrian"
                }
                ]
        }
        
        # Save to MongoDB if accident detected
        accident_id = str(uuid.uuid4())
        accident_record = {
            "_id": accident_id,
            "timestamp": datetime.now().isoformat(),
            "result": response["result"],
            "severity": response["severity"],
            "entities": response["entities"],
            "processingTime": frame_count * (1/30)  # Approximate processing time in seconds
        }
        
        try:
            # Use the save_accident function from db.py
            saved_id = save_accident(accident_record)
            if saved_id:
                print(f"Accident record saved with ID: {saved_id}")
                response["_id"] = accident_id  # Include the ID in the response
            else:
                print("Failed to save accident record")
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")
    else:
        response = {
            "result": "No Accident Detected"
        }

    print(" Final Response:", response)
    return jsonify(response)

@app.route('/accidents', methods=['GET'])
def get_accidents():
    try:
        sort_by_severity = request.args.get('sortBySeverity', 'false').lower() == 'true'
        
        # Use the get_all_accidents function from db.py
        accidents = get_all_accidents(sort_by_severity)
        
        return jsonify(accidents)
    except Exception as e:
        print(f"Error fetching accidents: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/accidents/<accident_id>', methods=['GET'])
def get_accident(accident_id):
    try:
        # Use the get_accident_by_id function from db.py
        accident = get_accident_by_id(accident_id)
        
        if not accident:
            return jsonify({"error": "Accident not found"}), 404
        
        return jsonify(accident)
    except Exception as e:
        print(f"Error fetching accident: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)