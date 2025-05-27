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
import pandas as pd
import shutil
import ast
import torch
from collage import create_collage_from_folder
from db import save_accident, get_all_accidents, get_accident_by_id

app = Flask(__name__)
CORS(app)

# Check for CUDA availability
if torch.cuda.is_available():
    print(f"CUDA device count: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"Device {i}: {torch.cuda.get_device_name(i)}")
        device = i
        break    
else:
    device = "cpu"
    print("No CUDA devices available.")

print(f"Selected device: {device}")

# Load models
accident_model = YOLO('accident.pt')
severity_model = YOLO('sev.pt')
object_model = YOLO('obj.pt')
lpr_model = YOLO('lpr.pt')

class AccidentDetectionPipeline:
    def __init__(self):
        self.accident_model = accident_model
        self.severity_model = severity_model
        self.object_model = object_model
        self.device = device
        
    def process_video_for_accident(self, video_path, unique_id):
        """Process video for accident detection and return comprehensive results"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print("Error: Could not open video.")
            return None, None, None, None
        
        frame_width = int(cap.get(3))
        frame_height = int(cap.get(4))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        # Create directories with unique ID
        crop_dir = f'snaps_{unique_id}'
        snapshot_dir = f'accident_snaps_{unique_id}'
        
        # Clean up existing directories
        for dir_path in [crop_dir, snapshot_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            os.makedirs(dir_path)
        
        frame_skip = 1
        frame_count = 0
        predictions = []
        
        print("🔍 Processing video for accident detection...")
        
        # Process video for accident detection
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            if frame_count % frame_skip != 0:
                continue
            
            # Run accident detection
            results = self.accident_model(frame, device=self.device)
            boxes = results[0].boxes
            
            frame_labels = []
            if boxes is not None and boxes.shape[0] > 0:
                for box in boxes:
                    cls_id = int(box.cls)
                    frame_labels.append(cls_id)
                
                # Save crops of detected accidents
                for i, box in enumerate(boxes.xyxy):
                    x1, y1, x2, y2 = map(int, box)
                    crop = frame[y1:y2, x1:x2]
                    crop_resized = cv2.resize(crop, (640, 640), interpolation=cv2.INTER_LINEAR)
                    crop_filename = f"{crop_dir}/frame{frame_count}_box{i}.jpg"
                    cv2.imwrite(crop_filename, crop_resized)
            
            predictions.append({'frame': frame_count, 'labels': frame_labels})
        
        cap.release()
        
        # Create snapshots for collage
        self._create_snapshots(video_path, snapshot_dir, fps, frame_count)
        
        # Analyze predictions for accident detection
        df = pd.DataFrame(predictions)
        df['labels'] = df['labels'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
        
        # Return 1 if any frame has label 0 (accident), else 0
        accident_result = 0 if any(0 in labels for labels in df['labels']) else 1
        
        if accident_result == 0:  # Accident detected
            # Process severity and objects
            severity_result = self._process_severity(crop_dir, unique_id)
            object_result = self._process_objects(crop_dir, unique_id)
            
            # Create collage from snapshots
            collage_path = create_collage_from_folder(
                folder_name=snapshot_dir,
                output_subfolder='collages',
                image_size=(320, 240),
                padding=10,
                bg_color=(255, 255, 255)
            )
            
            return [accident_result, snapshot_dir], object_result, severity_result, collage_path
        else:
            # Clean up directories if no accident
            for dir_path in [crop_dir, snapshot_dir]:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
            return [accident_result, None], None, None, None
    
    def _create_snapshots(self, video_path, snapshot_dir, fps, frame_count):
        """Create snapshots from video for collage creation"""
        start_frame = int(1 * fps)  # Start after the first second
        if frame_count - start_frame >= 8:
            snapshot_indices = [start_frame + int(i * (frame_count - start_frame) / 8) for i in range(8)]
        else:
            snapshot_indices = list(range(start_frame, frame_count))
        
        cap = cv2.VideoCapture(video_path)
        current_frame = 0
        snapshots_saved = 0
        
        while cap.isOpened() and snapshots_saved < len(snapshot_indices):
            ret, frame = cap.read()
            if not ret:
                break
            if current_frame == snapshot_indices[snapshots_saved]:
                snap_path = os.path.join(snapshot_dir, f'snapshot_{current_frame}.jpg')
                cv2.imwrite(snap_path, frame)
                snapshots_saved += 1
            current_frame += 1
        
        cap.release()
        print(f"Saved {snapshots_saved} snapshots to: {snapshot_dir}")
    
    def _process_severity(self, crop_dir, unique_id):
        """Process cropped images for severity detection"""
        output_annotated_dir = f'./sev_{unique_id}'
        if os.path.exists(output_annotated_dir):
            shutil.rmtree(output_annotated_dir)
        os.makedirs(output_annotated_dir)
        
        crop_images = [f for f in os.listdir(crop_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        print(f"🔍 Running severity model on {len(crop_images)} cropped images...")
        
        rows = []
        
        for image_file in crop_images:
            image_path = os.path.join(crop_dir, image_file)
            image = cv2.imread(image_path)
            
            if image is None:
                continue
            
            results = self.severity_model(image, device=self.device, conf=0.5)
            boxes = results[0].boxes
            
            if boxes is not None and boxes.shape[0] > 0:
                severities = []
                for box in boxes:
                    cls_id = int(box.cls)
                    severities.append(str(cls_id))
                severity_str = ";".join(severities)
                rows.append({'image_name': image_file, 'severity': severity_str})
        
        # Process severity results
        df = pd.DataFrame(rows)
        df['severity'] = df['severity'].fillna('').apply(
            lambda x: x.split(';') if isinstance(x, str) else (x if isinstance(x, list) else [])
        )
        
        # Flatten all severity labels
        all_severity_labels = [s for sublist in df['severity'] for s in sublist if s.strip() != '']
        
        # Count occurrences manually
        severity_label_counter = {}
        for label in all_severity_labels:
            if label in severity_label_counter:
                severity_label_counter[label] += 1
            else:
                severity_label_counter[label] = 1
        
        if severity_label_counter:
            max_severity_label = max(severity_label_counter, key=severity_label_counter.get)
            return int(max_severity_label)
        
        return 0  # Default to moderate if no severity detected
    
    def _process_objects(self, crop_dir, unique_id):
        """Process cropped images for object detection"""
        output_annotated_dir = f'./obj_{unique_id}'
        if os.path.exists(output_annotated_dir):
            shutil.rmtree(output_annotated_dir)
        os.makedirs(output_annotated_dir)
        
        crop_images = [f for f in os.listdir(crop_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        print(f"🔍 Running object model on {len(crop_images)} cropped images...")
        
        rows = []
        
        for image_file in crop_images:
            image_path = os.path.join(crop_dir, image_file)
            image = cv2.imread(image_path)
            
            if image is None:
                continue
            
            results = self.object_model(image, device=self.device, classes=[0,1,2,3,5,7], conf=0.4)
            boxes = results[0].boxes
            
            if boxes is not None and boxes.shape[0] > 0:
                objects = []
                for box in boxes:
                    cls_id = int(box.cls)
                    objects.append(str(cls_id))
                objects_str = ";".join(objects)
                rows.append({'image_name': image_file, 'objects': objects_str})
        
        # Process object results
        df = pd.DataFrame(rows)
        df['objects'] = df['objects'].fillna('').apply(
            lambda x: x.split(';') if isinstance(x, str) else (x if isinstance(x, list) else [])
        )
        
        # Count vehicles per frame
        df['vehicle_count'] = df['objects'].apply(lambda x: len([cls for cls in x if cls.strip() != '']))
        
        vehicle_frame_counts = df['vehicle_count'].value_counts().sort_index()
        vehicle_count_dict = vehicle_frame_counts.to_dict()
        total_frames = len(df)
        vehicle_percentage_dict = {}
        
        for num_vehicles, num_frames in vehicle_count_dict.items():
            percent = (num_frames / total_frames) * 100
            vehicle_percentage_dict[num_vehicles] = percent
        
        if vehicle_percentage_dict.get(1, 0) > 90:
            result = 1
        elif vehicle_percentage_dict.get(2, 0) > 2:
            result = 2
        else:
            result = max(vehicle_percentage_dict, key=vehicle_percentage_dict.get) if vehicle_percentage_dict else 1
        
        # Determine object types
        class_map = {
            0: "person",
            1: "bicycle", 
            2: "car",
            3: "motorcycle",
            5: "bus",
            7: "truck"
        }
        
        # Flatten all detected class IDs
        all_detections = [int(cls) for sublist in df['objects'] for cls in sublist if cls.strip().isdigit()]
        
        # Count occurrences for each class
        class_counts = {class_map[i]: all_detections.count(i) for i in class_map}
        total_detections = sum(class_counts.values())
        
        # Calculate frequency percentage
        class_percentage = {name: (count / total_detections) * 100 if total_detections > 0 else 0
                           for name, count in class_counts.items()}
        
        # Filter out classes below 20% (except car)
        filtered_class_percentage = {
            name: pct for name, pct in class_percentage.items()
            if name == "car" or pct >= 20
        }
        
        # Get remaining class IDs
        remaining_ids = [i for i, name in class_map.items() if name in filtered_class_percentage]
        
        # Final object list
        if len(remaining_ids) == 1:
            objs = [remaining_ids[0]] * result
        else:
            objs = remaining_ids
        
        return objs

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

def create_payload(accident_output, entities_result, severity_result, regnum_list, collage_path=None):
    """Create JSON payload for frontend"""
    entity_mapping = {
        0: 'pedestrian',   # person
        1: 'bicycle',
        2: 'car',
        3: 'motorcycle',
        5: 'bus',
        7: 'truck'
    }

    severity_mapping = {
        0: 'Moderate',
        1: 'Minor', 
        2: 'Severe'      # Changed from 'Critical' to 'Severe'
    }

    accident_result, file_path = accident_output

    if accident_result != 0:
        return {"result": "No Accident Detected"}

    # Extract filename from collage path if available and remove .jpg extension
    collage_filename = None
    if collage_path:
        collage_filename = os.path.basename(collage_path)
        # Remove .jpg extension if present to avoid double extension issue
        if collage_filename.endswith('.jpg'):
            collage_filename = collage_filename[:-4]

    result = {
        "result": "Accident Detected",
        "snapshot_path": file_path,
        "severity": severity_mapping.get(severity_result, "Unknown"),
        "entities": [],
        "filename": collage_filename
    }

    reg_index = 0

    for code in entities_result:
        entity_type = entity_mapping.get(code, "unknown")
        entity_obj = {"type": entity_type}

        if entity_type in ['car', 'motorcycle', 'bus', 'truck']:
            if reg_index < len(regnum_list):
                entity_obj["license_plate"] = regnum_list[reg_index]
                reg_index += 1
            else:
                entity_obj["license_plate"] = ""

        result["entities"].append(entity_obj)

    return result

# Initialize systems
accident_pipeline = AccidentDetectionPipeline()
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
    
    # Generate unique ID for this processing session
    unique_id = str(uuid.uuid4())[:8]
    temp_video_path = f"temp_video_{unique_id}.mp4"
    
    try:
        file.save(temp_video_path)
        
        # Process video through ML pipeline
        accident_output, entities_result, severity_result, collage_path = accident_pipeline.process_video_for_accident(
            temp_video_path, unique_id
        )
        
        if accident_output[0] == 0:  # Accident detected
            # Process license plates
            detected_plate = lpr_system.process_video(temp_video_path)
            regnum_list = [detected_plate] if detected_plate else [""]
            
            # Create payload
            response = create_payload(accident_output, entities_result, severity_result, regnum_list, collage_path)
            
            # Save to MongoDB if accident detected
            accident_id = str(uuid.uuid4())
            accident_record = {
                "_id": accident_id,
                "timestamp": datetime.now().isoformat(),
                "result": response["result"],
                "severity": response["severity"],
                "entities": response["entities"],
                "filename": response.get("filename", ""),
                "processingTime": 0  # You can calculate this if needed
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
            response = {"result": "No Accident Detected"}
        
        # Clean up GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
    except Exception as e:
        print(f"❌ Error processing video: {e}")
        response = {"error": f"Error processing video: {str(e)}"}
    
    finally:
        # Clean up temp video file
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

    print("📤 Final Response:", response)
    return jsonify(response)

@app.route('/collages/<path:filename>', methods=['GET'])
def get_collage(filename):
    print(f"📂 Fetching collage: {filename}")  
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add .jpg extension if not present to handle both cases
    if not filename.endswith('.jpg'):
        filename = filename + '.jpg'
    
    collage_path = os.path.join(base_dir, 'collages', filename)
    
    if not os.path.exists(collage_path):
        print(f"❌ Collage not found at: {collage_path}")  
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
