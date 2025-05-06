#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include <Arduino.h>
#include "FS.h"
#include "SD_MMC.h"
#include <time.h>

// Konfigurasi WiFi
const char* ssid = "SSID-HD";
const char* password = "123123123";
const char* serverUrl = "https://edunudgeai.mantigamedan.sch.id/upload";

// Konfigurasi NTP
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 7 * 3600; // GMT+7 (WIB)
const int daylightOffset_sec = 0;     // Tidak ada daylight saving time

// Interval sinkronisasi waktu (6 jam)
#define NTP_SYNC_INTERVAL 6 * 3600 * 1000
unsigned long lastNTPSync = 0;

// Konfigurasi Kamera (AI Thinker ESP32-CAM)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Interval pengambilan gambar (15 detik)
const int captureInterval = 15000;
unsigned long lastCaptureTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.printf("Memori awal: %d bytes\n", ESP.getFreeHeap());

  // Antena internal
  pinMode(12, OUTPUT);
  digitalWrite(12, LOW);

  // Inisialisasi MicroSD Card
  if (!initSDCard()) {
    Serial.println("❌ Gagal menginisialisasi SD Card");
    ESP.restart();
  }

  // Hubungkan ke WiFi
  connectToWiFi();

  // Konfigurasi waktu dengan NTP
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  printLocalTime(); // Uji waktu pertama kali

  // Konfigurasi kamera dengan resolusi tinggi
  setupCamera();
}

bool initSDCard() {
  Serial.println("Memulai SD Card...");
  if (!SD_MMC.begin("/sdcard", true)) {
    Serial.println("Gagal memulai SD_MMC");
    return false;
  }

  uint8_t cardType = SD_MMC.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("Tidak terdeteksi SD Card");
    return false;
  }

  Serial.print("Tipe SD Card: ");
  if (cardType == CARD_MMC) {
    Serial.println("MMC");
  } else if (cardType == CARD_SD) {
    Serial.println("SDSC");
  } else if (cardType == CARD_SDHC) {
    Serial.println("SDHC");
  } else {
    Serial.println("Tidak dikenali");
  }

  uint64_t cardSize = SD_MMC.cardSize() / (1024 * 1024);
  Serial.printf("Kapasitas SD Card: %lluMB\n", cardSize);
  
  return true;
}

void connectToWiFi() {
  WiFi.begin(ssid, password);
  Serial.println("Menghubungkan ke WiFi...");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n❌ Gagal terhubung ke WiFi!");
    ESP.restart();
  }
  
  Serial.println("\n✅ Terhubung ke WiFi!");
  Serial.print("Alamat IP: ");
  Serial.println(WiFi.localIP());
}

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_UXGA;  // 1600x1200
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;  // 800x600
    config.jpeg_quality = 10;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Kamera gagal diinisialisasi: 0x%x\n", err);
    ESP.restart();
  }
}

// Tambahkan di bagian global
bool timeSynced = false;

void syncNTP() {
  if (millis() - lastNTPSync > NTP_SYNC_INTERVAL || !timeSynced) {
    Serial.println("Menyinkronkan waktu dengan NTP server...");
    
    // Pastikan WiFi terhubung
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi tidak terhubung, tidak bisa sinkronisasi waktu");
      return;
    }

    // Hentikan WiFi sementara untuk menghindari konflik
    WiFi.disconnect(true);
    delay(100);
    
    // Inisialisasi configTime dengan heap yang cukup
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    
    // Tunggu maksimal 5 detik untuk sinkronisasi
    struct tm timeinfo;
    int attempts = 0;
    while (!getLocalTime(&timeinfo, 5000) && attempts < 3) {
      Serial.print(".");
      attempts++;
      delay(100);
    }
    
    // Kembalikan WiFi
    WiFi.disconnect(false);
    WiFi.begin(ssid, password);
    
    if (attempts < 3) {
      lastNTPSync = millis();
      timeSynced = true;
      printLocalTime();
    } else {
      Serial.println("\nGagal sinkronisasi waktu!");
    }
  }
}

void printLocalTime() {
  static struct tm timeinfo; // Gunakan static untuk menghindari alokasi stack besar
  
  if (!getLocalTime(&timeinfo, 1000)) {
    Serial.println("Gagal mendapatkan waktu lokal");
    return;
  }
  
  char timeStr[64];
  strftime(timeStr, sizeof(timeStr), "%A, %d %B %Y %H:%M:%S", &timeinfo);
  Serial.printf("Waktu terkini: %s (GMT+7)\n", timeStr);
}

void manageStorage() {
  uint64_t usedBytes = SD_MMC.usedBytes();
  uint64_t totalBytes = SD_MMC.totalBytes();
  float usedPercentage = (float)usedBytes / totalBytes * 100;

  if (usedPercentage > 90) {
    Serial.println("Penyimpanan hampir penuh, menghapus file tertua...");
    deleteOldestFile();
  }
}

void deleteOldestFile() {
  File root = SD_MMC.open("/");
  File file = root.openNextFile();
  
  String oldestFileName;
  time_t oldestTime = 0;

  while (file) {
    if (!file.isDirectory()) {
      time_t fileTime = file.getLastWrite();
      if (oldestTime == 0 || fileTime < oldestTime) {
        oldestTime = fileTime;
        oldestFileName = String(file.name());
      }
    }
    file = root.openNextFile();
  }

  if (oldestFileName.length() > 0) {
    Serial.printf("Menghapus file tertua: %s\n", oldestFileName.c_str());
    SD_MMC.remove(oldestFileName.c_str());
    
    // Cetak waktu file yang dihapus
    struct tm *timeinfo = localtime(&oldestTime);
    char timeStr[20];
    strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", timeinfo);
    Serial.printf("Waktu file: %s\n", timeStr);
  }
}

String generateFilename() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Gagal mendapatkan waktu, menggunakan timestamp millis");
    return "/image_" + String(millis()) + ".jpg";
  }
  
  char timeStr[20];
  strftime(timeStr, sizeof(timeStr), "%Y%m%d_%H%M%S", &timeinfo);
  return "/" + String(timeStr) + ".jpg";
}

bool saveImageToSD(camera_fb_t *fb) {
  String filename = generateFilename();
  
  File file = SD_MMC.open(filename.c_str(), FILE_WRITE);
  if (!file) {
    Serial.println("Gagal membuka file untuk ditulis");
    return false;
  }
  
  if (file.write(fb->buf, fb->len) != fb->len) {
    Serial.println("Gagal menulis file");
    file.close();
    return false;
  }

  file.flush();
  file.close();
  
  // Dapatkan waktu file untuk verifikasi
  struct tm timeinfo;
  if (getLocalTime(&timeinfo)) {
    char timeStr[64];
    strftime(timeStr, sizeof(timeStr), "%Y-%m-%d %H:%M:%S", &timeinfo);
    Serial.printf("Gambar disimpan: %s (%d bytes) [%s]\n", 
                 filename.c_str(), fb->len, timeStr);
  } else {
    Serial.printf("Gambar disimpan: %s (%d bytes)\n", filename.c_str(), fb->len);
  }
  
  return true;
}

void sendImageToServer(camera_fb_t* fb) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Koneksi WiFi terputus, gambar hanya disimpan ke SD Card");
    return;
  }

  HTTPClient http;
  WiFiClientSecure client;
  
  client.setInsecure();
  
  String boundary = "----WebKitFormBoundary" + String(millis());
  String header = "--" + boundary + "\r\n";
  header += "Content-Disposition: form-data; name=\"image\"; filename=\"";
  
  // Tambahkan timestamp ke nama file yang dikirim
  struct tm timeinfo;
  if (getLocalTime(&timeinfo)) {
    char timeStr[20];
    strftime(timeStr, sizeof(timeStr), "%Y%m%d_%H%M%S", &timeinfo);
    header += String(timeStr) + ".jpg";
  } else {
    header += "image.jpg";
  }
  
  header += "\"\r\nContent-Type: image/jpeg\r\n\r\n";
  
  String footer = "\r\n--" + boundary + "--\r\n";
  
  size_t totalLength = header.length() + fb->len + footer.length();
  
  if (!http.begin(client, serverUrl)) {
    Serial.println("❌ Gagal memulai koneksi HTTP");
    return;
  }
  
  // API KEY
  http.addHeader("X-API-KEY", "edunudgeai");
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  http.addHeader("Content-Length", String(totalLength));
  
  uint8_t* payload = (uint8_t*)malloc(totalLength);
  if (!payload) {
    Serial.println("❌ Gagal alokasi memori untuk payload");
    return;
  }
  
  memcpy(payload, header.c_str(), header.length());
  memcpy(payload + header.length(), fb->buf, fb->len);
  memcpy(payload + header.length() + fb->len, footer.c_str(), footer.length());
  
  int httpResponseCode = http.POST(payload, totalLength);
  free(payload);
  
  if (httpResponseCode == HTTP_CODE_OK) {
    Serial.println("✅ Gambar berhasil dikirim ke server!");
  } else {
    Serial.printf("❌ Gagal kirim gambar. Kode: %d\n", httpResponseCode);
    Serial.printf("Pesan error: %s\n", http.errorToString(httpResponseCode).c_str());
  }
  
  http.end();
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Sinkronisasi waktu secara berkala
  syncNTP();
  
  if (currentMillis - lastCaptureTime >= captureInterval) {
    lastCaptureTime = currentMillis;
    
    // Ambil gambar dari kamera
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("❌ Gagal mengambil gambar");
      return;
    }
    
    // Simpan ke SD Card
    if (saveImageToSD(fb)) {
      // Kelola penyimpanan
      manageStorage();
      
      // Coba kirim ke server
      sendImageToServer(fb);
    }
    
    // Kembalikan frame buffer
    esp_camera_fb_return(fb);
    
    // Cetak info memori
    Serial.printf("Memori bebas: %d bytes\n", ESP.getFreeHeap());
  }
  
  // Jika WiFi terputus, coba sambungkan kembali
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Koneksi WiFi terputus. Mencoba menghubungkan kembali...");
    connectToWiFi();
  }
  
  delay(1000);
}