from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import os
import tempfile
import re
import numpy as np
import easyocr
from ultralytics import YOLO
import uuid
from datetime import datetime
from db import save_accident, get_all_accidents, get_accident_by_id

app = Flask(__name__)
CORS(app)

# Load models
accident_model = YOLO('best.pt')
lpr_model = YOLO('lpr.pt')

class SimpleLPR:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.reader = easyocr.Reader(['en'], gpu=False)
        
        # Common license plate patterns
        self.plate_patterns = [
            r'^[A-Z]{2,3}[0-9]{3,4}$',
            r'^[0-9]{3,4}[A-Z]{2,3}$',
            r'^[A-Z]{1}[0-9]{3}[A-Z]{3}$',
            r'^[0-9]{2}[A-Z]{2}[0-9]{2,3}$',
            r'^[A-Z]{2}[0-9]{2}[A-Z]{2}$'
        ]

    def clean_text(self, text):
        """Clean and correct OCR text"""
        if not text:
            return ""
        
        text = text.upper().strip()
        text = re.sub(r'[^A-Z0-9]', '', text)
        
        # Basic OCR corrections
        corrections = {'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8', 'G': '6'}
        for old, new in corrections.items():
            text = text.replace(old, new)
            
        return text

    def is_valid_plate(self, text):
        """Check if text matches license plate patterns"""
        if not text or len(text) < 4 or len(text) > 10:
            return False
            
        for pattern in self.plate_patterns:
            if re.match(pattern, text):
                return True
                
        # Basic validation: mix of letters and numbers
        letters = sum(1 for c in text if c.isalpha())
        numbers = sum(1 for c in text if c.isdigit())
        return 2 <= letters <= 6 and 2 <= numbers <= 6

    def process_video(self, video_path):
        """Process video and return best detected license plate"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        detected_plates = {}
        frame_count = 0
        frame_skip = 15  # Process every 15th frame for speed

        print("🔍 Processing video for license plates...")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % frame_skip != 0:
                continue

            # YOLO detection
            results = self.model(frame, conf=0.3, device='cpu')
            
            if results[0].boxes is not None:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                    
                    # Extract and enhance crop
                    crop = frame[y1:y2, x1:x2]
                    if crop.size == 0:
                        continue
                        
                    # Convert to grayscale and resize if too small
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    if gray.shape[0] < 40:
                        scale = 40 / gray.shape[0]
                        new_width = int(gray.shape[1] * scale)
                        gray = cv2.resize(gray, (new_width, 40))
                    
                    # OCR
                    try:
                        results = self.reader.readtext(gray, detail=1)
                        for detection in results:
                            if len(detection) >= 3:
                                text = detection[1]
                                confidence = detection[2]
                                
                                if confidence > 0.4:
                                    cleaned_text = self.clean_text(text)
                                    if self.is_valid_plate(cleaned_text):
                                        if cleaned_text not in detected_plates or confidence > detected_plates[cleaned_text]:
                                            detected_plates[cleaned_text] = confidence
                                            print(f"🎯 Found plate: {cleaned_text}")
                    except:
                        continue

        cap.release()
        
        # Return plate with highest confidence
        if detected_plates:
            best_plate = max(detected_plates.items(), key=lambda x: x[1])[0]
            print(f"✅ Best plate: {best_plate}")
            return best_plate
        
        return None

# Initialize LPR system
lpr_system = SimpleLPR('lpr.pt')

@app.route('/predict', methods=['POST'])
def predict():
    print("🚗 Received request!")  
    print("🚗 Request Content-Type:", request.content_type)  
    print("🚗 Request files keys:", request.files.keys())  

    if 'file' not in request.files:
        print("❌ No file found in request!")  
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    print(f"📁 Received file: {file.filename}")  
    
    temp_video_path = "temp_video.mp4"
    file.save(temp_video_path)
    
    cap = cv2.VideoCapture(temp_video_path)
    if not cap.isOpened():
        print("❌ Error opening video file")  
        os.remove(temp_video_path)
        return jsonify({'error': 'Error opening video file'}), 400
    
    frame_skip = 5
    frame_count = 0
    accident_detected = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        if frame_count % frame_skip != 0:
            continue
        
        results = accident_model(frame, device='cpu')
        predictions = results[0].boxes  

        detected_classes = [int(cls) for cls in predictions.cls.tolist()]
        print(f"🚗 Detected Classes in Frame {frame_count}: {detected_classes}")  

        if 0 in detected_classes:
            print("🚨 Accident Detected in Frame", frame_count)
            accident_detected = True
            break
    
    cap.release()
    os.remove(temp_video_path)  
    
    if accident_detected:
        response = {
            "result": "Accident Detected",
            "severity": "Minor",
            "entities": [
                {
                    "type": "truck",
                    "license_plate": "NWFP-893"
                },
                {
                    "type": "car",
                    "license_plate": ""
                },
                {
                    "type": "pedestrian"
                }
                ],
            "filename": "accident_snapshot_collage"
        }
        
        # Save to MongoDB if accident detected
        accident_id = str(uuid.uuid4())
        accident_record = {
            "_id": accident_id,
            "timestamp": datetime.now().isoformat(),
            "result": response["result"],
            "severity": response["severity"],
            "entities": response["entities"],
            "filename": response["filename"],
            "processingTime": frame_count * (1/30)
        }
        
        try:
            saved_id = save_accident(accident_record)
            if saved_id:
                print(f"💾 Accident record saved with ID: {saved_id}")
                response["_id"] = accident_id
            else:
                print("❌ Failed to save accident record")
        except Exception as e:
            print(f"❌ Error saving to MongoDB: {e}")
    else:
        response = {
            "result": "No Accident Detected"
        }

    print("📤 Final Response:", response)
    return jsonify(response)

@app.route('/collages/<path:filename>', methods=['GET'])
def get_collage(filename):
    print(f"📂 Fetching collage: {filename}")  
    base_dir = os.path.dirname(os.path.abspath(__file__))
    collage_path = os.path.join(base_dir, 'collages', filename)
    
    if not os.path.exists(collage_path):
        print("❌ Collage not found!")  
        return jsonify({'error': 'Collage not found'}), 404
    
    with open(collage_path, 'rb') as f:
        content = f.read()
    
    print("📤 Collage fetched successfully!")  
    return content, 200, {'Content-Type': 'image/jpeg'}

@app.route('/detect-license-plate', methods=['POST'])
def detect_license_plate():
    print("🔍 License Plate Detection - Received request!")  
    print("🔍 Request Content-Type:", request.content_type)  
    print("🔍 Request files keys:", request.files.keys())  

    if 'file' not in request.files:
        print("❌ No file found in request!")  
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    print(f"📁 Received file: {file.filename}")  
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
        temp_video_path = temp_file.name
        file.save(temp_video_path)
    
    try:
        detected_plate = lpr_system.process_video(temp_video_path)
        
        if detected_plate:
            response = {
                "license_plates": [detected_plate],
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "frames_processed": "variable",
                "detection_method": "YOLO + EasyOCR"
            }
            print(f"✅ License Plate Detection Success: {detected_plate}")
        else:
            response = {
                "license_plates": [],
                "timestamp": datetime.now().isoformat(),
                "status": "no_detection",
                "frames_processed": "variable",
                "detection_method": "YOLO + EasyOCR"
            }
            print("❌ No license plates detected")
        
    except Exception as e:
        print(f"❌ Error during license plate detection: {e}")
        response = {
            "license_plates": [],
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
            "detection_method": "YOLO + EasyOCR"
        }
    
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
    
    print("📤 Final License Plate Response:", response)
    return jsonify(response)

@app.route('/accidents', methods=['GET'])
def get_accidents():
    try:
        sort_by_severity = request.args.get('sortBySeverity', 'false').lower() == 'true'
        accidents = get_all_accidents(sort_by_severity)
        return jsonify(accidents)
    except Exception as e:
        print(f"❌ Error fetching accidents: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/accidents/<accident_id>', methods=['GET'])
def get_accident(accident_id):
    try:
        accident = get_accident_by_id(accident_id)
        if not accident:
            return jsonify({"error": "Accident not found"}), 404
        return jsonify(accident)
    except Exception as e:
        print(f"❌ Error fetching accident: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)