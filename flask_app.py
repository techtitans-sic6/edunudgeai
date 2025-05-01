from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from datetime import datetime
import os
import cv2
import numpy as np
import logging
from logging.handlers import RotatingFileHandler
import shutil
import base64

# ========== KONFIGURASI APLIKASI ==========
app = Flask(__name__)
CORS(app)

# ========== KONFIGURASI MONGODB ==========
MONGO_URI = "mongodb://tech_titans:edunudgeai@localhost:27017/edunudge_db?authSource=admin"
client = MongoClient(MONGO_URI)
db = client['edunudge_db']
sensor_collection = db['sensor_data']

# ========== KONFIGURASI UPLOAD GAMBAR ==========
UPLOAD_FOLDER = 'static/uploads'
MAX_STORAGE_MB = 100  # Batas maksimal penyimpanan
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== KONFIGURASI KEAMANAN ==========
VALID_API_KEYS = {
    "EduNudgeAI": "sensor_device",  # Untuk data sensor
    "edunudgeai": "ESP32-CAM"       # Untuk gambar
}

# ========== KONFIGURASI RATE LIMITING ==========
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# ========== KONFIGURASI LOGGING ==========
log_handler = RotatingFileHandler('flask.log', maxBytes=10000, backupCount=3)
log_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.INFO)

# ========== FUNGSI BANTUAN ==========
def validate_api_key(headers, device_type="sensor"):
    """Validasi API key berdasarkan jenis perangkat"""
    api_key = headers.get('X-API-KEY')
    if device_type == "sensor":
        return api_key in [k for k, v in VALID_API_KEYS.items() if v == "sensor_device"]
    else:  # camera
        return api_key in [k for k, v in VALID_API_KEYS.items() if v == "ESP32-CAM"]

def initialize_database():
    """Fungsi untuk inisialisasi database"""
    try:
        # Cek apakah koleksi sudah ada
        if 'sensor_data' not in db.list_collection_names():
            db.create_collection('sensor_data')
            app.logger.info("Created sensor_data collection")
        
        # Buat index jika belum ada
        if "timestamp_-1" not in sensor_collection.index_information():
            sensor_collection.create_index([("timestamp", -1)], name="timestamp_-1")
            app.logger.info("Created timestamp index")
    except Exception as e:
        app.logger.error(f"Error initializing database: {str(e)}")
        raise e

def manage_storage():
    """Kelola penyimpanan otomatis untuk gambar"""
    total_size = 0
    files = []
    
    # Hitung total ukuran penyimpanan
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            files.append((filepath, os.path.getctime(filepath)))
            total_size += os.path.getsize(filepath)
    
    # Konversi ke MB
    total_size_mb = total_size / (1024 * 1024)
    
    # Jika melebihi batas, hapus file tertua
    if total_size_mb > MAX_STORAGE_MB:
        app.logger.warning(f"Penyimpanan hampir penuh: {total_size_mb:.2f}MB")
        files.sort(key=lambda x: x[1])  # Sort by creation time
        
        while total_size_mb > MAX_STORAGE_MB * 0.8:  # Hapus sampai 80% kapasitas
            if not files:
                break
            oldest_file = files.pop(0)
            try:
                os.remove(oldest_file[0])
                total_size_mb -= os.path.getsize(oldest_file[0]) / (1024 * 1024)
                app.logger.info(f"Menghapus file lama: {oldest_file[0]}")
            except Exception as e:
                app.logger.error(f"Gagal menghapus {oldest_file[0]}: {str(e)}")

# ========== ROUTE UNTUK DATA SENSOR ==========
@app.route('/api/sensor', methods=['POST'])
def receive_sensor_data():
    if not validate_api_key(request.headers, "sensor"):
        app.logger.warning("Unauthorized access attempt to sensor endpoint")
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    try:
        data = request.json
        required_fields = ['temp', 'hum', 'light', 'motion', 'sound']
        
        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing fields"}), 400
        
        # Tambahkan metadata
        sensor_data = {
            **data,
            "timestamp": datetime.now(),
            "device_type": "ESP32-Sensor"
        }
        
        # Simpan ke MongoDB
        result = sensor_collection.insert_one(sensor_data)
        
        app.logger.info(f"Data sensor saved: {result.inserted_id}")
        return jsonify({
            "status": "success",
            "message": "Data saved",
            "id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        app.logger.error(f"Error saving sensor data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sensor/latest', methods=['GET'])
def get_latest_sensor_data():
    try:
        # Ambil 10 data terbaru
        data = list(sensor_collection.find().sort("timestamp", -1).limit(10))
        
        # Format data untuk response
        formatted_data = []
        for item in data:
            item['_id'] = str(item['_id'])
            item['timestamp'] = item['timestamp'].isoformat()
            formatted_data.append(item)
        
        return jsonify({
            "status": "success",
            "count": len(formatted_data),
            "data": formatted_data
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sensor/aggregate', methods=['GET'])
def get_aggregated_sensor_data():
    try:
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avgTemp": {"$avg": "$temp"},
                    "avgHum": {"$avg": "$hum"},
                    "avgLight": {"$avg": "$light"},
                    "avgSound": {"$avg": "$sound"},
                    "motionCount": {"$sum": "$motion"}
                }
            }
        ]
        
        result = list(sensor_collection.aggregate(pipeline))[0]
        del result['_id']
        
        return jsonify({
            "status": "success",
            "data": result
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ========== ROUTE UNTUK GAMBAR ==========
# @app.route('/api/camera/upload', methods=['POST'])
@app.route('/upload', methods=['POST'])
@limiter.limit("5 per minute")  # Limit upload rate
def upload_image():
    # Validasi API Key
    if not validate_api_key(request.headers, "camera"):
        app.logger.warning("Unauthorized access attempt to camera endpoint")
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    # Validasi data gambar
    if 'image' not in request.files and not request.data:
        app.logger.error("Tidak ada data gambar diterima")
        return jsonify({"status": "error", "message": "No image data received"}), 400
    
    try:
        # Baca data gambar
        img_data = request.files['image'].read() if 'image' in request.files else request.data
        
        # Validasi ukuran gambar (max 5MB)
        if len(img_data) > 5 * 1024 * 1024:
            raise ValueError("Ukuran gambar melebihi 5MB")
        
        # Decode gambar
        img_array = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Data gambar tidak valid")
        
        # Kelola penyimpanan sebelum menyimpan yang baru
        manage_storage()
        
        # Simpan gambar
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"esp32cam_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        cv2.imwrite(filepath, img)
        
        app.logger.info(f"Gambar berhasil disimpan: {filename}")
        return jsonify({
            "status": "success",
            "filename": filename,
            "size": f"{os.path.getsize(filepath) / 1024:.2f}KB",
            "message": "Image received and saved"
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error processing image: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/camera/latest', methods=['GET'])
def get_latest_image():
    try:
        files = [f for f in os.listdir(UPLOAD_FOLDER) 
                if f.endswith('.jpg') and f.startswith('esp32cam_')]
        
        if not files:
            return jsonify({"status": "error", "message": "No images found"}), 404
        
        # Dapatkan file terbaru berdasarkan timestamp nama file
        latest_file = max(files)
        filepath = os.path.join(UPLOAD_FOLDER, latest_file)
        
        # Baca gambar sebagai base64
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        return jsonify({
            "status": "success",
            "filename": latest_file,
            "image_data": encoded_string,
            "timestamp": latest_file.split('_')[1].split('.')[0]
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error getting latest image: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/camera/cleanup', methods=['POST'])
def cleanup_files():
    """Endpoint untuk pembersihan manual"""
    if not validate_api_key(request.headers, "camera"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    try:
        deleted_files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            try:
                os.remove(filepath)
                deleted_files.append(filename)
            except Exception as e:
                app.logger.error(f"Gagal menghapus {filename}: {str(e)}")
        
        return jsonify({
            "status": "success",
            "deleted": deleted_files,
            "count": len(deleted_files)
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Initialize database before first request
    try:
        initialize_database()
    except Exception as e:
        app.logger.error(f"Failed to initialize database: {str(e)}")
        raise e

    # ====== BACKUP FOLDER ======
    if not app.debug:  # Backup hanya kalau debug=False (mode produksi)
        try:
            # Pastikan folder backup tersedia
            BACKUP_ROOT = 'static/backups'
            os.makedirs(BACKUP_ROOT, exist_ok=True)

            # Nama backup berdasarkan waktu yang sangat unik
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            backup_dir = os.path.join(BACKUP_ROOT, f"backup_{timestamp_str}")

            if os.path.exists(UPLOAD_FOLDER):
                shutil.copytree(UPLOAD_FOLDER, backup_dir)
                app.logger.info(f"Backup berhasil dibuat di: {backup_dir}")
            else:
                app.logger.warning(f"Folder upload {UPLOAD_FOLDER} tidak ditemukan. Lewati backup.")

        except Exception as e:
            app.logger.error(f"Gagal membuat backup: {str(e)}")
    else:
        app.logger.info("Debug mode aktif. Lewati proses backup.")

    # Jalankan server Flask
    app.run(host='0.0.0.0', port=5001, debug=True)
