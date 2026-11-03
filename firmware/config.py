# ==============================================================================
# CẤU HÌNH HỆ THỐNG GIÀN PHƠI THÔNG MINH V2.0 (WEMOS D1 R2 - ESP8266)
# MicroPython - Firebase Realtime Database - GitHub OTA
# ==============================================================================


def _load_env():
    """Đọc cấu hình config.ini, hỗ trợ nhiều kiểu xuống dòng."""
    env = {}

    try:
        with open("/config.ini", "r") as f:
            content = f.read()

        # Chuẩn hóa kiểu xuống dòng
        content = content.replace("\r\n", "\n")
        content = content.replace("\r", "\n")

        for line in content.split("\n"):
            line = line.strip()

            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")

    except OSError as e:
        print("[!] Loi doc config.ini:", e)

    return env


_env = _load_env()

# 1. Cấu hình WiFi
WIFI_SSID = _env.get("WIFI_SSID", "YOUR_WIFI_SSID")
WIFI_PASSWORD = _env.get("WIFI_PASSWORD", "YOUR_WIFI_PASSWORD")

# 2. Cấu hình Firebase Realtime Database
# Định dạng: https://<your-project-id>-default-rtdb.firebaseio.com
FIREBASE_URL = _env.get("FIREBASE_URL", "https://your-project-id-default-rtdb.firebaseio.com")
FIREBASE_AUTH = _env.get("FIREBASE_AUTH", "")  # Để trống nếu Database ở chế độ test rules

# 3. Cấu hình GitHub OTA & Local OTA
GITHUB_USER = _env.get("GITHUB_USER", "chuvitvang")
GITHUB_REPO = _env.get("GITHUB_REPO", "Iot_smart_drying_rack")
GITHUB_BRANCH = _env.get("GITHUB_BRANCH", "main")
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
OTA_VERSION_URL = f"{GITHUB_RAW_BASE}/version.json"

# Cập nhật qua máy tính trong mạng LAN (ví dụ: http://192.168.1.100:8000/main.py)
LOCAL_OTA_URL = _env.get("LOCAL_OTA_URL", "")
CHECK_GITHUB_OTA_ON_BOOT = _env.get("CHECK_GITHUB_OTA_ON_BOOT", "0") == "1"

# Phiên bản hiện hành của Firmware
CURRENT_VERSION = "2.0.0"

# 4. Sơ đồ chân GPIO (WeMos D1 R2)
PIN_I2C_SCL = 5   # D1 (GPIO 5) -> SCL ADS1115
PIN_I2C_SDA = 4   # D2 (GPIO 4) -> SDA ADS1115
PIN_DHT22   = 2   # D4 (GPIO 2) -> DATA DHT22
PIN_BUTTON  = 12  # D6 (GPIO 12) -> Nút nhấn SW1 (External Pull-up 10k)
PIN_SERVO   = 13  # D7 (GPIO 13) -> PWM Động cơ Servo SG90

# Kênh trên module ADS1115 (0x48)
ADC_CHANNEL_RAIN = 0  # A0: Cảm biến mưa (WATER_A0)
ADC_CHANNEL_LDR  = 1  # A1: Cảm biến quang trở (LDR_A1)

# 5. Ngưỡng mặc định điều khiển tự động
DEFAULT_RAIN_THRESHOLD     = 15000  # ADC < 15000: Có mưa (cần thu sào)
DEFAULT_SUN_THRESHOLD      = 16000  # ADC > 16000: Có nắng
DEFAULT_HUMIDITY_THRESHOLD = 80.0   # Độ ẩm (%) > 80.0%: Quá ẩm (không đạt chuẩn phơi, thu sào)

# Góc quay Servo SG90 (Độ)
SERVO_ANGLE_OUT = 90  # Đưa sào phơi ra ngoài (OPEN)
SERVO_ANGLE_IN  = 0   # Thu sào phơi vào nhà (CLOSED)

# Chu kỳ lặp vòng quét chính (giây)
LOOP_INTERVAL_SEC = 2.0