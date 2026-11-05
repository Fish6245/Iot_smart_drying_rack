# ==============================================================================
# main.py - Firmware Giàn Phơi Thông Minh V2.0 (ESP8266 - MicroPython)
# WeMos D1 R2 | ADS1115 (A1/A2), DHT11 (D4) | Servo SG90 (D7) | Firebase | GitHub OTA
# ==============================================================================
import gc
import time
import machine
import dht

try:
    import ntptime
except ImportError:
    ntptime = None

import config
from ads1x15 import ADS1115

print("[+] Khởi động Firmware Giàn phơi thông minh v" + config.CURRENT_VERSION)

# ------------------------------------------------------------------------------
# 1. KHỞI TẠO NGOẠI VI VÀ CẢM BIẾN
# ------------------------------------------------------------------------------

# I2C cho ADS1115 (D1: SCL=GPIO5, D2: SDA=GPIO4)
i2c = machine.I2C(scl=machine.Pin(config.PIN_I2C_SCL), sda=machine.Pin(config.PIN_I2C_SDA))

try:
    ads = ADS1115(i2c, address=0x48, gain=1)
    print("[+] Đã kết nối module ADS1115 (0x48)")
except Exception as e:
    ads = None
    print("[!] Lỗi khởi tạo ADS1115:", e)

# Cảm biến nhiệt độ & độ ẩm DHT11 (D4: GPIO2)
sensor_dht = dht.DHT11(machine.Pin(config.PIN_DHT11))

# Động cơ Servo SG90 (D7: GPIO13, PWM 50Hz)
servo_pin = machine.Pin(config.PIN_SERVO)
servo_pwm = machine.PWM(servo_pin, freq=50)

def set_servo_angle(angle):
    """
    Điều khiển Servo SG90 quay đến góc đích (0 - 180 độ).
    Sau khi quay xong, ngắt xung PWM (duty 0) để chống rung (jitter) và chống sụt áp.
    """
    angle = max(0, min(180, int(angle)))
    duty = int(26 + (angle / 180.0) * (128 - 26))
    servo_pwm.duty(duty)
    time.sleep_ms(500)
    servo_pwm.duty(0)

# Khởi tạo trạng thái ban đầu của Servo (Thu vào)
set_servo_angle(config.SERVO_ANGLE_IN)

# Nút nhấn cơ học SW1 (D6: GPIO 12)
button_pin = machine.Pin(config.PIN_BUTTON, machine.Pin.IN)
button_pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=button_irq_handler)

# ------------------------------------------------------------------------------
# 2. ĐỒNG BỘ THỜI GIAN THỰC QUA NTP (UTC+7)
# ------------------------------------------------------------------------------
NTP_SYNCED = False
UTC_OFFSET_SEC = 7 * 3600  # Múi giờ Việt Nam UTC+7 (+25200 giây)

def sync_ntp_time():
    global NTP_SYNCED
    if not ntptime:
        return False
    try:
        ntptime.host = "pool.ntp.org"
        ntptime.settime()
        NTP_SYNCED = True
        print("[+] Đã đồng bộ thời gian NTP thành công.")
        return True
    except Exception as e:
        print("[!] Chưa thể đồng bộ NTP:", e)
        return False

# Thử đồng bộ NTP ngay khi khởi động

def get_current_local_time():
    """Lấy thời gian địa phương theo UTC+7: (year, month, day, hour, min, sec, time_str, epoch)"""
    epoch = time.time()
    local_epoch = epoch + UTC_OFFSET_SEC
    tm = time.localtime(local_epoch)
    time_str = f"{tm[3]:02d}:{tm[4]:02d}"
    return tm, time_str, epoch

# ------------------------------------------------------------------------------
# 3. TRẠNG THÁI HỆ THỐNG V2.0
# ------------------------------------------------------------------------------
system_state = {
    # Telemetry
    "clothesline_state": "CLOSED",      # "OPEN" hoặc "CLOSED"
    "sun_minutes_today": 0,
    "sun_seconds_remainder": 0.0,
    "sun_minutes_date": None,
    "sun_stats_loaded": False,

    # Control
    "manual_command": "NONE",           # "OPEN", "CLOSE", "NONE"
    "servo_angle": config.SERVO_ANGLE_IN,
    "rain_threshold": config.DEFAULT_RAIN_THRESHOLD,
    "sun_threshold": config.DEFAULT_SUN_THRESHOLD,
    "humidity_threshold": config.DEFAULT_HUMIDITY_THRESHOLD,

    # Schedule
    "auto_schedule_enabled": True,
    "open_time": "07:00",
    "close_time": "18:00",
    "rain_priority_override": True
}

firebase_enabled = bool(config.FIREBASE_URL and "your-project-id" not in config.FIREBASE_URL)
if firebase_enabled:
    print("[+] Chế độ hoạt động: Đồng bộ Firebase Realtime Database V2.0")
else:
    print("[*] Chế độ hoạt động: Độc lập (Không dùng Firebase, tự động theo cảm biến & nút nhấn)")

# ------------------------------------------------------------------------------
# 4. GIAO TIẾP FIREBASE REST API
# ------------------------------------------------------------------------------
