import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
import numpy as np
import requests
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import time
from datetime import datetime
from PIL import Image
import cv2
import google.generativeai as genai
from deepface import DeepFace
import re
import base64
import io

# ========== INISIALISASI STATE ==========
if "generating_recommendations" not in st.session_state:
    st.session_state.generating_recommendations = False
if "history" not in st.session_state:
    st.session_state.history = []
if "show_recommendations" not in st.session_state:
    st.session_state.show_recommendations = False
if "current_emotions" not in st.session_state:
    st.session_state.current_emotions = []
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ========== KONFIGURASI HALAMAN ==========
st.set_page_config(
    page_title="EduNudge AI - Smart Classroom Dashboard",
    layout="wide",
    page_icon="🏫",
    initial_sidebar_state="expanded"
)

# ========== GAYA CSS TAMBAHAN ==========
st.markdown("""
<style>
/* Main styling */
html, body, [class*="css"] {
    font-family: 'Segoe UI', sans-serif;
}
h1 {
    font-size: 1.8rem !important;
}
h2 {
    font-size: 1.6rem !important;
}
.st-emotion-cache-1r4qj8v {
    padding: 2rem !important;
}
.metric-box {
    border-radius: 15px;
    padding: 1rem;
    background-color: #f5f7fa;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.sidebar .css-1d391kg {
    padding-top: 2rem !important;
}
/* Custom colors */
.positive {
    color: #10b981;
}
.warning {
    color: #f59e0b;
}
.negative {
    color: #ef4444;
}
/* Face thumbnails */
.face-thumbnail {
    width: 100%;
    height: 120px;
    object-fit: cover;
    border-radius: 8px;
    border: 2px solid #e2e8f0;
}
/* Tab styling */
div[data-baseweb="tab-list"] {
    gap: 0.5rem;
}
div[data-baseweb="tab"] {
    padding: 0.5rem 1rem;
    border-radius: 8px !important;
    background-color: #f1f5f9 !important;
    margin-right: 0 !important;
}
div[data-baseweb="tab"][aria-selected="true"] {
    background-color: #3b82f6 !important;
    color: white !important;
}

/* REKOMENDASI STYLING */
.recommendation-container {
    margin-bottom: 2rem;
    padding: 1.5rem;
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.recommendation-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: #1e3a8a;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
}
.priority-high {
    background-color: #fee2e2;
    color: #b91c1c;
    padding: 0.25rem 0.5rem;
    border-radius: 0.5rem;
    font-size: 0.75rem;
    margin-left: 0.5rem;
    font-weight: 500;
}
.priority-medium {
    background-color: #fef3c7;
    color: #92400e;
    padding: 0.25rem 0.5rem;
    border-radius: 0.5rem;
    font-size: 0.75rem;
    margin-left: 0.5rem;
    font-weight: 500;
}
.priority-low {
    background-color: #dcfce7;
    color: #166534;
    padding: 0.25rem 0.5rem;
    border-radius: 0.5rem;
    font-size: 0.75rem;
    margin-left: 0.5rem;
    font-weight: 500;
}
.analysis-section {
    background-color: #f8fafc;
    border-left: 3px solid #3b82f6;
    padding: 1rem;
    border-radius: 0 0.5rem 0.5rem 0;
    margin: 0.5rem 0;
    font-size: 0.95rem;
}
.analysis-section strong {
    color: #1e40af;
}
.steps-section {
    margin: 1rem 0;
    padding-left: 1rem;
}
.step-item {
    margin-bottom: 0.5rem;
    display: flex;
    align-items: flex-start;
    position: relative;
    padding-left: 1.5rem;
}
.step-item:before {
    content: "";
    position: absolute;
    left: 0;
    top: 0.5rem;
    width: 8px;
    height: 8px;
    background-color: #3b82f6;
    border-radius: 50%;
}
.impact-section {
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-top: 1rem;
    font-size: 0.95rem;
}
.impact-section strong {
    color: #166534;
}
.section-icon {
    margin-right: 0.5rem;
}
.data-card {
    background-color: white;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.data-title {
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #374151;
}
.data-item {
    margin-bottom: 0.25rem;
    display: flex;
    align-items: center;
}
.data-icon {
    margin-right: 0.5rem;
    width: 20px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ========== GEMINI ENGINE ==========
class GeminiRecommendationEngine:
    def __init__(self):
        if 'GEMINI_API_KEY' not in st.secrets:
            st.error("API Key Gemini tidak ditemukan di secrets.toml")
            self.enabled = False
            return
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            available_models = [m.name for m in genai.list_models()]
            self.model_name = "models/gemini-1.5-pro-latest" if "models/gemini-1.5-pro-latest" in available_models else "models/gemini-pro"
            self.model = genai.GenerativeModel(self.model_name)
            self.enabled = True
        except Exception as e:
            st.error(f"Gagal inisialisasi Gemini: {str(e)}")
            self.enabled = False

    def _parse_recommendations(self, text):
        parts = [s.strip() for s in text.split("###") if s.strip()]
        return parts[:3] if parts else ["⚠️ Tidak ada data yang bisa ditampilkan"]
    
    def generate_recommendations(self, sensor_data, emotion_data):
        """
        Menghasilkan rekomendasi berdasarkan data sensor dan emosi siswa
        
        Parameters:
            sensor_data (list): Data sensor terbaru dari kelas
            emotion_data (list): Daftar emosi yang terdeteksi dari wajah siswa
            
        Returns:
            list: Daftar rekomendasi yang telah diparsing
        """
        if not self.enabled:
            return ["⚠️ Mesin rekomendasi tidak aktif"]
            
        if not sensor_data and not emotion_data:
            return ["⚠️ Tidak ada data sensor atau emosi yang tersedia"]
        
        try:
            # Persiapan data sensor
            latest_sensor = sensor_data[-1] if sensor_data else {}
            temp = latest_sensor.get('temp', 0)
            hum = latest_sensor.get('hum', 0)
            light = latest_sensor.get('light', 0)
            sound = latest_sensor.get('sound', 0)
            
            # Analisis distribusi emosi
            emotion_counts = {}
            if emotion_data:
                emotion_series = pd.Series(emotion_data)
                emotion_counts = emotion_series.value_counts().to_dict()
                dominant_emotion = emotion_series.mode()[0]
                negative_emotions = sum(count for emo, count in emotion_counts.items() 
                                      if emo in ['sad', 'angry', 'fear', 'disgust'])
                negative_ratio = negative_emotions / len(emotion_data) if emotion_data else 0
            else:
                dominant_emotion = "unknown"
                negative_ratio = 0
            
            # Buat prompt yang kontekstual
            prompt = f"""
            Anda adalah seorang ahli pendidikan dengan spesialisasi dalam teknologi pendidikan dan psikologi pembelajaran. 
            Berikan rekomendasi spesifik untuk meningkatkan pengalaman belajar di kelas berdasarkan data berikut:
            
            **Kondisi Lingkungan Kelas:**
            - Suhu: {temp}°C (ideal: 22-26°C)
            - Kelembaban: {hum}% (ideal: 40-60%)
            - Cahaya: {light}% (ideal: 40-70%)
            - Kebisingan: {sound}% (ideal: dibawah 45%)
            
            **Kondisi Emosi Siswa:**
            - Total siswa terdeteksi: {len(emotion_data) if emotion_data else 0}
            - Emosi dominan: {dominant_emotion}
            - Persentase emosi negatif: {negative_ratio:.0%}
            - Distribusi emosi: {emotion_counts}
            
            **Format Output:**
            Berikan 3 rekomendasi konkret dalam format berikut:
            
            ### Judul Rekomendasi (Prioritas: Tinggi/Medium/Rendah)
            - Analisis singkat: [analisis kondisi saat ini dan dampaknya pada pembelajaran]
            - Langkah-langkah spesifik untuk implementasi:
              1. [Langkah pertama]
              2. [Langkah kedua]
              3. [Langkah ketiga]
            - Dampak yang diharapkan pada pembelajaran: [penjelasan dampak positif yang diharapkan]
            
            Fokus pada:
            1. Penyesuaian lingkungan fisik jika diperlukan
            2. Strategi pengajaran berdasarkan emosi siswa
            3. Aktivitas kelas untuk meningkatkan keterlibatan
            """
            
            # Generate response
            response = self.model.generate_content(prompt)
            return self._parse_recommendations(response.text)
            
        except Exception as e:
            return [f"⚠️ Error dalam menghasilkan rekomendasi: {str(e)}"]

# ========== FUNGSI BANTUAN ==========
@st.cache_data(ttl=10)
def fetch_sensor_data(server_url):
    try:
        res = requests.get(f"{server_url}/api/sensor/latest", timeout=3)
        return res.json()["data"] if res.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=10)
def fetch_latest_image(server_url):
    try:
        response = requests.get(f"{server_url}/api/camera/latest", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('image_data'):
                img_data = base64.b64decode(data['image_data'])
                img_np = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                return img, data.get('timestamp', '')
        return None, None
    except Exception as e:
        st.sidebar.error(f"Koneksi ke server gagal: {str(e)}")
        return None, None

def analyze_faces(img_np, detection_model, min_confidence):
    try:
        # Konversi ke format yang kompatibel dengan DeepFace
        img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
        
        # Simpan ke buffer in-memory
        _, buffer = cv2.imencode(".jpg", img_rgb)
        io_buf = io.BytesIO(buffer)
        
        results = DeepFace.analyze(
            io_buf,
            actions=["emotion", "age", "gender"],
            detector_backend=detection_model,
            enforce_detection=False,
            silent=True  # Nonaktifkan logging internal DeepFace
        )
        
        if isinstance(results, dict):
            results = [results]

        processed_results = []
        for result in results:
            # Normalisasi region
            region = result.get("region", {})
            x = region.get("x", region.get("left", 0))
            y = region.get("y", region.get("top", 0))
            w = region.get("w", region.get("width", 0))
            h = region.get("h", region.get("height", 0))
            
            # Validasi ukuran wajah
            if w < 30 or h < 30:  # Skip wajah terlalu kecil
                continue
                
            # Update result
            result["region"] = {"x": x, "y": y, "w": w, "h": h}
            
            # Proses gender jika ada
            if isinstance(result.get("gender"), dict):
                dominant_gender = max(result["gender"].items(), key=lambda x: x[1])[0]
                result["dominant_gender"] = dominant_gender
                result["gender_percent"] = result["gender"][dominant_gender]
            
            # Filter berdasarkan confidence
            if result.get("face_confidence", 1) > min_confidence:
                processed_results.append(result)
        
        return processed_results
        
    except Exception as e:
        st.sidebar.error(f"Error analisis wajah: {str(e)}")
        return []

def visualize_detection(img_np, results):
    img_bboxes = img_np.copy()
    
    # Define colors and styles
    box_colors = {
        'happy': (0, 255, 0),       # Green
        'sad': (255, 0, 0),         # Blue
        'angry': (0, 0, 255),       # Red
        'surprise': (255, 255, 0),  # Cyan
        'fear': (255, 0, 255),      # Purple
        'disgust': (0, 255, 255),   # Yellow
        'neutral': (255, 165, 0)    # Orange
    }
    
    for result in results:
        region = result["region"]
        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
        emotion = result["dominant_emotion"]
        
        if w > 60 and h > 60:
            # Get color based on emotion
            color = box_colors.get(emotion, (0, 180, 0))  # Default to green
            
            # Draw thicker bounding box
            cv2.rectangle(img_bboxes, (x, y), (x+w, y+h), color, 3)
            
            # Draw emotion text with background for better visibility
            text = f"{emotion} ({result['age']:.0f}y)"
            (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            
            # Text background
            cv2.rectangle(img_bboxes, (x, y-30), (x+text_width+10, y), color, -1)
            
            # Text
            cv2.putText(img_bboxes, text, (x+5, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Confidence indicator
            confidence = result.get("face_confidence", 1)
            cv2.rectangle(img_bboxes, (x, y+h), (x+int(w*confidence), y+h+5), color, -1)
    
    return img_bboxes

def create_sensor_gauge(value, title, optimal_range):
    color = "#34a853" if optimal_range[0] <= value <= optimal_range[1] else "#ea4335"
    fig = px.bar(x=[value], title=f"{title} ({value:.1f})", color_discrete_sequence=[color])
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=40, b=20), height=150)
    fig.update_xaxes(range=[0, 100], visible=False)
    return fig

# ========== SIDEBAR ==========
with st.sidebar:
    st.title("🔐 Login Pengguna")
    
    if not st.session_state.logged_in:
        password = st.text_input("Masukkan password", type="password")
        if password == "edunudgeai":
            st.session_state.logged_in = True
            st.success("Login berhasil!")
            st.rerun()
        else:
            st.error("Password salah!")
            st.stop()

    st.title("⚙️ Konfigurasi")
    SERVER_URL = st.text_input("URL API Server", "https://edunudgeai.mantigamedan.sch.id")
    REFRESH_INTERVAL = st.slider("Interval Refresh (detik)", 5, 60, 30)
    
    st.markdown("### 🎯 Nilai Ideal Sensor")
    st.markdown("- 🌡️ Suhu: 22–26°C\n- 💧 Kelembaban: 40–60%\n- 💡 Cahaya: 40–70%\n- 🔊 Kebisingan: <45%")
    
    st.markdown("### 🎭 Konfigurasi Deteksi Wajah")
    detection_model = st.selectbox("Model Deteksi Wajah", ["retinaface", "mtcnn", "opencv"])
    min_confidence = st.slider("Confidence Minimal", 0.1, 0.9, 0.5, step=0.1)
    
    st.divider()
    st.caption(f"🔄 Terakhir diperbarui: {datetime.now().strftime('%H:%M:%S')}")

# ========== AUTO REFRESH ==========
if not st.session_state.generating_recommendations:
    st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="auto_refresh")

# ========== HALAMAN UTAMA ==========
st.title("🏫 EduNudge AI – Smart Classroom Dashboard - Tech Titans")
engine = GeminiRecommendationEngine()

# ========== TAB UTAMA ==========
tab1, tab2, tab3 = st.tabs(["📊 Dashboard Sensor", "🎭 Monitoring Emosi", "🧠 Rekomendasi"])

with tab1:
    # ===== DATA SENSOR =====
    sensor_data = fetch_sensor_data(SERVER_URL)
    if not sensor_data:
        st.warning("⏳ Menunggu data sensor...")
    else:
        df = pd.DataFrame(sensor_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        st.markdown("### 🔍 Data Sensor Terkini")
        col1, col2, col3, col4 = st.columns(4)
        metrics = [
            ("🌡️ Suhu", "temp", (22, 26), col1),
            ("💧 Kelembaban", "hum", (40, 60), col2),
            ("💡 Cahaya", "light", (40, 70), col3),
            ("🔊 Kebisingan", "sound", (0, 45), col4),
        ]

        for label, key, (low, high), col in metrics:
            val = df.iloc[-1][key]
            color = "#34a853" if low <= val <= high else "#ea4335"
            with col:
                st.markdown(f"<div class='metric-box'><strong>{label}</strong><br><span style='font-size: 1.5rem; color:{color}'>{val:.1f}</span></div>", unsafe_allow_html=True)

        st.markdown("## 📈 Tren Data Sensor (24 Jam Terakhir)")
        fig = px.line(df.tail(24), x='timestamp', y=['temp', 'hum', 'light', 'sound'],
                     markers=True, title="Trend Lingkungan Kelas")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("## 🎭 Monitoring Emosi Siswa")
    st.caption("Realtime monitoring ekspresi wajah menggunakan ESP32-CAM dan DeepFace")

    img_np, timestamp = fetch_latest_image(SERVER_URL)

    if img_np is not None:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        # Container untuk gambar utama
        with st.container():
            col1, col2 = st.columns(2)
            
            # Gambar asli
            with col1:
                st.image(
                    img_np, 
                    caption=f"Gambar Terkini - {timestamp}", 
                    use_container_width=True,
                    channels="BGR"  # Sesuaikan dengan format warna
                )

            # Analisis wajah
            with st.spinner("🔍 Menganalisis wajah..."):
                results = analyze_faces(img_np, detection_model, min_confidence)
            
            # Gambar dengan bounding box
            if results:
                img_bboxes = visualize_detection(img_np.copy(), results)
                with col2:
                    st.image(
                        img_bboxes, 
                        caption="Deteksi Wajah dengan Anotasi", 
                        use_container_width=True,
                        channels="BGR"
                    )
                
                st.success(f"✅ {len(results)} wajah siswa terdeteksi!")
                st.session_state.current_emotions = [r["dominant_emotion"] for r in results]
                
                # ===== Detail Per Wajah =====
                st.subheader("👥 Detail Emosi Siswa")
                
                # CSS untuk kartu wajah
                st.markdown("""
                <style>
                .face-card {
                    border: 1px solid #e2e8f0;
                    border-radius: 10px;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    background-color: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }
                .face-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 1rem;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Grid responsif untuk wajah
                st.markdown('<div class="face-grid">', unsafe_allow_html=True)
                for i, result in enumerate(results):
                    with st.container():
                        st.markdown('<div class="face-card">', unsafe_allow_html=True)
                        
                        # Crop wajah
                        region = result["region"]
                        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
                        face_crop = img_np[y:y+h, x:x+w]
                        
                        col_face, col_info = st.columns([1, 2])
                        with col_face:
                            st.image(
                                face_crop, 
                                use_container_width=True,
                                caption=f"Wajah {i+1}",
                                channels="BGR"
                            )
                        
                        with col_info:
                            st.markdown(f"""
                                <div style="font-size: 0.9rem; line-height: 1.5;">
                                    <div>😊 <b>Emosi:</b> {result['dominant_emotion'].capitalize()}</div>
                                    <div>🎂 <b>Usia:</b> {result['age']:.0f} tahun</div>
                                    <div>🚻 <b>Gender:</b> {result.get('dominant_gender', 'N/A')}</div>
                                    <div>📊 <b>Confidence:</b> {result.get('face_confidence', 1)*100:.1f}%</div>
                                </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # ===== Statistik Kelas =====
                st.subheader("📊 Statistik Kelas")
                
                # Tab untuk statistik
                tab_stat, tab_hist = st.tabs(["Statistik", "Riwayat"])
                
                with tab_stat:
                    # Container untuk metrik
                    with st.container():
                        col_met1, col_met2 = st.columns(2)
                        
                        with col_met1:
                            # Distribusi Emosi
                            emotion_counts = pd.Series([r["dominant_emotion"] for r in results]).value_counts()
                            fig_emo = px.pie(
                                names=emotion_counts.index,
                                values=emotion_counts.values,
                                title="Distribusi Emosi"
                            )
                            st.plotly_chart(fig_emo, use_container_width=True)
                        
                        with col_met2:
                            # Distribusi Gender
                            gender_data = [r.get("dominant_gender", "unknown") for r in results]
                            gender_counts = pd.Series(gender_data).value_counts()
                            
                            if len(gender_counts) > 0:
                                fig_gen = px.bar(
                                    x=gender_counts.index,
                                    y=gender_counts.values,
                                    labels={"x": "Gender", "y": "Jumlah"},
                                    title="Distribusi Gender"
                                )
                                st.plotly_chart(fig_gen, use_container_width=True)
                            else:
                                st.warning("Data gender tidak tersedia")
                
                with tab_hist:
                    # Riwayat emosi
                    st.session_state.history.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "total_students": len(results),
                        "emotions": [r["dominant_emotion"] for r in results],
                        "avg_age": np.mean([r["age"] for r in results])
                    })
                    
                    hist_df = pd.DataFrame(st.session_state.history)
                    st.dataframe(
                        hist_df,
                        column_config={
                            "timestamp": "Waktu",
                            "total_students": "Jumlah Siswa",
                            "avg_age": "Usia Rata-rata"
                        },
                        use_container_width=True
                    )
            
            else:
                st.warning("Tidak ada wajah yang terdeteksi dengan confidence yang memadai")
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Belum ada gambar tersedia dari server Flask")

with tab3:
    st.markdown("## 🧠 Rekomendasi untuk Kelas")
    st.caption("Rekomendasi berdasarkan kondisi lingkungan dan emosi siswa")
    
    sensor_data = fetch_sensor_data(SERVER_URL)
    emotion_data = st.session_state.get("current_emotions", [])
    
    if not sensor_data and not emotion_data:
        st.warning("⏳ Menunggu data sensor dan emosi...")
    else:
        if st.button("✨ Hasilkan Rekomendasi", key="generate_recommendations"):
            st.session_state.generating_recommendations = True
            try:
                with st.spinner("Menganalisis kondisi kelas dan emosi siswa..."):
                    st.session_state.recommendations = engine.generate_recommendations(
                        sensor_data, 
                        emotion_data
                    )
                    st.session_state.show_recommendations = True
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                st.session_state.generating_recommendations = False

        if st.session_state.get("show_recommendations", False):
            st.markdown("### 💡 Rekomendasi untuk Kelas")
            
            for rec in st.session_state.get("recommendations", []):
                if not rec.strip():
                    continue
                    
                # Parse recommendation parts
                lines = [line.strip() for line in rec.splitlines() if line.strip()]
                if not lines:
                    continue
                    
                # Extract priority
                priority_class = ""
                priority_text = ""
                if "Prioritas: Tinggi" in lines[0]:
                    priority_class = "priority-high"
                    priority_text = "Tinggi"
                elif "Prioritas: Medium" in lines[0]:
                    priority_class = "priority-medium"
                    priority_text = "Medium"
                elif "Prioritas: Rendah" in lines[0]:
                    priority_class = "priority-low"
                    priority_text = "Rendah"
                    
                # Get title without priority
                title = lines[0].split("(Prioritas:")[0].strip()
                
                # Find analysis, steps, and impact sections
                analysis = ""
                steps = []
                impact = ""
                
                current_section = None
                for line in lines[1:]:
                    line_lower = line.lower()
                    if "analisis singkat:" in line_lower:
                        current_section = "analysis"
                        analysis = line.split(":", 1)[1].strip()
                    elif "langkah-langkah spesifik untuk implementasi:" in line_lower:
                        current_section = "steps"
                    elif "dampak yang diharapkan pada pembelajaran:" in line_lower:
                        current_section = "impact"
                        impact = line.split(":", 1)[1].strip()
                    else:
                        if current_section == "steps" and line.strip().startswith(("-", "1.", "2.", "3.")):
                            # Remove bullet points or numbers
                            clean_step = re.sub(r'^[\-\d\.\s]+', '', line).strip()
                            steps.append(clean_step)
                
                # Render recommendation
                with st.container():
                    st.markdown(f"""
                    <div class="recommendation-container">
                        <div class="recommendation-title">
                            {title}
                            <span class="{priority_class}">{priority_text}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if analysis:
                        st.markdown(f"""
                        <div class="analysis-section">
                            <span class="section-icon">📊</span>
                            <strong>Analisis:</strong> {analysis}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    if steps:
                        st.markdown("<div class='steps-section'>", unsafe_allow_html=True)
                        for i, step in enumerate(steps, 1):
                            st.markdown(f"""
                            <div class="step-item">
                                {step}
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    if impact:
                        st.markdown(f"""
                        <div class="impact-section">
                            <span class="section-icon">✨</span>
                            <strong>Dampak yang diharapkan:</strong> {impact}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
            
            # Data yang digunakan
            st.markdown("### 📊 Data yang Digunakan")
            col1, col2 = st.columns(2)
            
            with col1:
                with st.container():
                    st.markdown('<div class="data-card">', unsafe_allow_html=True)
                    st.markdown('<div class="data-title">Kondisi Lingkungan Terkini</div>', unsafe_allow_html=True)
                    
                    if sensor_data:
                        latest = sensor_data[-1]
                        st.markdown(f"""
                        <div class="data-item">
                            <span class="data-icon">🌡️</span>
                            <span><strong>Suhu:</strong> {latest.get('temp', 'N/A')}°C (ideal: 22-26°C)</span>
                        </div>
                        <div class="data-item">
                            <span class="data-icon">💧</span>
                            <span><strong>Kelembaban:</strong> {latest.get('hum', 'N/A')}% (ideal: 40-60%)</span>
                        </div>
                        <div class="data-item">
                            <span class="data-icon">💡</span>
                            <span><strong>Cahaya:</strong> {latest.get('light', 'N/A')}% (ideal: 40-70%)</span>
                        </div>
                        <div class="data-item">
                            <span class="data-icon">🔊</span>
                            <span><strong>Kebisingan:</strong> {latest.get('sound', 'N/A')}% (ideal: <45%)</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning("Data sensor tidak tersedia")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                with st.container():
                    st.markdown('<div class="data-card">', unsafe_allow_html=True)
                    st.markdown('<div class="data-title">Distribusi Emosi Siswa</div>', unsafe_allow_html=True)
                    
                    if emotion_data:
                        emotion_counts = pd.Series(emotion_data).value_counts().to_dict()
                        total_students = len(emotion_data)
                        for emotion, count in emotion_counts.items():
                            percentage = (count / total_students) * 100
                            st.markdown(f"""
                            <div class="data-item">
                                <span class="data-icon">😊</span>
                                <span><strong>{emotion.capitalize()}:</strong> {count} siswa ({percentage:.1f}%)</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("Data emosi tidak tersedia")
                    st.markdown('</div>', unsafe_allow_html=True)

# if __name__ == "__main__":
    # Tambahkan ini untuk development
#    st.rerun() 
