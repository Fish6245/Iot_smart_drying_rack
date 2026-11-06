# ==============================================================================
# CẤU HÌNH HỆ THỐNG GIÀN PHƠI THÔNG MINH V2.0 (WEMOS D1 R2 - ESP8266)
# MicroPython - Firebase Realtime Database - GitHub OTA
# ==============================================================================


def _load_env():
    """Đọc file cấu hình config.ini hoặc .env từ bộ nhớ Flash ESP8266."""
    paths = (
        "/config.ini",
        "config.ini",
        "/firmware/config.ini",
        "firmware/config.ini",
        "../config.ini",
        "../firmware/config.ini",
        "/.env",
        ".env",
        "/firmware/.env",
        "firmware/.env",
        "../.env",
    )

    for path in paths:
        try:
            with open(path, "r") as f:
                content = f.read()

            # Chuan hoa xuong dong
            content = content.replace("\r\n", "\n")
            content = content.replace("\r", "\n")

            env = {}

            for line in content.split("\n"):
                line = line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                env[key] = value

            if env:
                ssid = env.get("WIFI_SSID", "")
                password = env.get("WIFI_PASSWORD", "")

                if ssid and password:
                    print("[+] Da doc config:", path)
                    print("SSID:", ssid)
                    print("Password:", 'Da doc' if password != "YOUR_WIFI_PASSWORD" else "Chua doc")
                    return env

                print("[!] File co cau hinh nhung thieu WiFi:", path)

        except OSError:
            continue
        except Exception as e:
            print("[!] Loi doc", path, ":", repr(e))

    print("[!] Khong doc duoc cau hinh WiFi!")
    return {}

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
ENABLE_WEBREPL = _env.get("ENABLE_WEBREPL", "0") == "1"

# Phiên bản hiện hành của Firmware
CURRENT_VERSION = "3.1.0"

# 4. Sơ đồ chân GPIO (WeMos D1 R2)
PIN_I2C_SCL = 5   # D1 (GPIO 5) -> SCL ADS1115
PIN_I2C_SDA = 4   # D2 (GPIO 4) -> SDA ADS1115
PIN_DHT11   = 2   # D4 (GPIO 2) -> DATA DHT11
PIN_DHT22   = PIN_DHT11 # Alias tương thích ngược
PIN_BUTTON  = 12  # D6 (GPIO 12) -> Nút nhấn SW1 (External Pull-up 10k)
PIN_SERVO   = 13  # D7 (GPIO 13) -> PWM Động cơ Servo SG90

# Kênh trên module ADS1115 (0x48)
ADC_CHANNEL_RAIN = 2  # A2: Cảm biến mưa (WATER_A2)
ADC_CHANNEL_LDR  = 1  # A1: Cảm biến quang trở (LDR_A1)

# 5. Ngưỡng mặc định điều khiển tự động
DEFAULT_RAIN_THRESHOLD     = 2000   # ADC > 2000: Có mưa (cần thu sào)
DEFAULT_SUN_THRESHOLD      = 2000  # ADC > 2000: Có ánh sáng
DEFAULT_HUMIDITY_THRESHOLD = 80.0   # Độ ẩm (%) > 80.0%: Quá ẩm (không đạt chuẩn phơi, thu sào)

# Góc quay Servo SG90 (Độ)
SERVO_ANGLE_OUT = 0  
SERVO_ANGLE_IN = 90 # SERVO_ANGLE_IN  = 90   # Thu sào phơi vào nhà (CLOSED)

# Chu kỳ lặp vòng quét chính (giây)
LOOP_INTERVAL_SEC = 2.0

del _env
del _load_env

