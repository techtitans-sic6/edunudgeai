🧠 EduNudge AI – Smart Classroom Monitoring

Sistem kelas pintar berbasis **ESP32 dan AI** untuk memantau lingkungan dan ekspresi siswa secara real-time, serta memberikan **rekomendasi pembelajaran otomatis** menggunakan **Google Gemini AI**.
-----------------------------------

🚀 Fitur Utama

- 📡 Monitoring suhu, kelembaban, cahaya, suara, dan gerakan (PIR)
- 📷 Analisis wajah & emosi siswa dengan **ESP32-CAM + DeepFace**
- 🧠 Rekomendasi AI berbasis kondisi kelas dan emosi siswa (Gemini AI)
- 📊 Dashboard interaktif berbasis **Streamlit**
- 🔐 Pengamanan API dengan API Key
- 💾 Manajemen penyimpanan otomatis (gambar dihapus saat storage penuh)
-----------------------------------

🧩 Teknologi yang Digunakan

| Komponen     | Teknologi                          |
|--------------|-------------------------------------|
| Microcontroller | ESP32, ESP32-CAM                 |
| Backend         | Flask REST API + MongoDB         |
| Frontend        | Streamlit Dashboard              |
| AI/ML           | DeepFace, Google Gemini Pro      |
| Komunikasi      | HTTP (REST API), MQTT (opsional) |
| Gambar          | OpenCV, PIL                      |
-----------------------------------

🖼️ Arsitektur Sistem

- ESP32/ESP32-CAM → Flask API (MongoDB + Uploads) ↓ Streamlit UI (Realtime + AI Insight)
-----------------------------------

⚙️ Cara Menjalankan

1. Jalankan Flask API
python flask_app.py
Port default: http://localhost:5001

2. Jalankan Dashboard Streamlit
streamlit run streamlit_app.py

3. Siapkan ESP32 & ESP32-CAM
    - Flash file esp32.py ke ESP32
    - Upload esp32cam.ino ke ESP32-CAM
    - Pastikan file config.json dan wifi_config.json tersedia

4. Akses Dashboard
Buka browser dan akses: http://localhost:8501
-----------------------------------

🔐 API Endpoint (Flask)
Endpoint	Fungsi
/api/sensor	POST data sensor
/api/sensor/latest	Ambil 10 data sensor terbaru
/api/camera/upload	Upload gambar dari ESP32-CAM
/api/camera/latest	Gambar terbaru (JSON path)

Gunakan header:
X-API-KEY: [your_api_key]
-----------------------------------

🧪 Contoh Rekomendasi AI

Gemini AI akan memberikan saran seperti:
### 1. Tambah Aktivitas Fisik
- 🎯 Tujuan: Mengatasi kejenuhan siswa
- ⚡ Aksi: Lakukan ice-breaking 3 menit
- 📚 Alasan: Membantu reset suasana belajar

### 2. Atur Pencahayaan
- 🎯 Tujuan: Cegah mata lelah
- ⚡ Aksi: Nyalakan lampu tambahan
- 📚 Alasan: Cahaya terdeteksi <40%
-----------------------------------

📦 Kebutuhan Hardware
    - ESP32 + Sensor Kit
    - ESP32-CAM
    - Breadboard, jumper
    - Laptop/server lokal/VPS
    - Koneksi WiFi stabil
-----------------------------------

🏁 Roadmap & Pengembangan

- Notifikasi ke WhatsApp guru
- Penghitungan jumlah siswa otomatis
- Integrasi ke cloud (Firebase / GCP)
- Rekam historis per kelas
-----------------------------------

🤝 Kontribusi
Pull request dan ide sangat kami hargai!
-----------------------------------

📄 Lisensi

Proyek ini bersifat open-source untuk keperluan edukasi dan pengembangan lebih lanjut. Silakan gunakan dengan menyebutkan kredit.
© 2025 – Tim Tech Titans | Samsung Innovation Campus Batch 6
