# ==============================================================================
# main.py - Firmware Giàn Phơi Thông Minh (ESP8266 - MicroPython)
# WeMos D1 R2 | Cảm biến ADS1115, DHT22 | Servo SG90 | Firebase | GitHub OTA
# ==============================================================================
import gc
import time
import machine
import dht
import urequests

import config
from ads1x15 import ADS1115
import ota

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

# Cảm biến nhiệt độ & độ ẩm DHT22 (D4: GPIO2)
sensor_dht = dht.DHT22(machine.Pin(config.PIN_DHT22))

# Động cơ Servo SG90 (D7: GPIO13, PWM 50Hz)
servo_pin = machine.Pin(config.PIN_SERVO)
servo_pwm = machine.PWM(servo_pin, freq=50)

def set_servo_angle(angle):
    """
    Điều khiển Servo SG90 quay đến góc đích (0 - 180 độ).
    Sau khi quay xong, ngắt xung PWM (duty 0) để chống rung (jitter) và chống sụt áp.
    """
    angle = max(0, min(180, int(angle)))
    # Ánh xạ 0-180 độ sang duty cycle 26-128 (đối với 10-bit PWM 50Hz trên ESP8266)
    duty = int(26 + (angle / 180.0) * (128 - 26))
    servo_pwm.duty(duty)
    time.sleep_ms(500)   # Chờ động cơ quay đến vị trí
    servo_pwm.duty(0)    # Ngắt xung giữ để tiết kiệm điện & chống rung lắc

# Khởi tạo trạng thái ban đầu của Servo (Thu vào)
set_servo_angle(config.SERVO_ANGLE_IN)

# ------------------------------------------------------------------------------
# 2. KHỞI TẠO NÚT NHẤN CƠ HỌC SW1 (D6: GPIO 12)
# Hỗ trợ 2 thao tác:
#   - Nhấn nhả (< 3 giây): Đảo trạng thái giàn phơi (Thu vào / Đưa ra) & chuyển MANUAL
#   - Nhấn giữ (>= 3 giây): Kích hoạt Cập nhật OTA trực tiếp từ GitHub (Không cần Firebase)
# ------------------------------------------------------------------------------
button_pin = machine.Pin(config.PIN_BUTTON, machine.Pin.IN)

# ------------------------------------------------------------------------------
# 3. TRẠNG THÁI HỆ THỐNG
# ------------------------------------------------------------------------------
system_state = {
    "mode": "AUTO",                 # "AUTO" hoặc "MANUAL"
    "clothesline_out": False,       # True = Đang phơi ngoài, False = Thu vào
    "target_angle": config.SERVO_ANGLE_IN,
    "rain_threshold": config.DEFAULT_RAIN_THRESHOLD,
    "light_threshold": config.DEFAULT_LIGHT_THRESHOLD
}

# Kiểm tra xem Firebase đã được cấu hình hay chưa
firebase_enabled = bool(config.FIREBASE_URL and "your-project-id" not in config.FIREBASE_URL)
if firebase_enabled:
    print("[+] Chế độ hoạt động: Đồng bộ Firebase Realtime Database")
else:
    print("[*] Chế độ hoạt động: Độc lập (Không dùng Firebase, tự động theo cảm biến & nút nhấn)")

# ------------------------------------------------------------------------------
# 4. CÁC HÀM GIAO TIẾP FIREBASE (REST API)
# ------------------------------------------------------------------------------
def build_fb_url(path):
    url = f"{config.FIREBASE_URL}/smart_clothesline/{path}.json"
    if config.FIREBASE_AUTH:
        url += f"?auth={config.FIREBASE_AUTH}"
    return url

def push_telemetry(temp, hum, rain_adc, ldr_adc):
    """Gửi dữ liệu cảm biến định kỳ lên Firebase (PATCH)"""
    if not firebase_enabled:
        return
    url = build_fb_url("telemetry")
    payload = {
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "rain_adc": rain_adc,
        "ldr_adc": ldr_adc,
        "last_updated": time.time()
    }
    res = None
    try:
        res = urequests.patch(url, json=payload)
    except Exception as e:
        print("[!] Lỗi đẩy telemetry lên Firebase:", e)
    finally:
        if res:
            res.close()
        gc.collect()

def fetch_control_and_ota():
    """Đọc lệnh điều khiển và cờ OTA từ Firebase (GET)"""
    if not firebase_enabled:
        return None
    url = f"{config.FIREBASE_URL}/smart_clothesline.json"
    if config.FIREBASE_AUTH:
        url += f"?auth={config.FIREBASE_AUTH}"

    res = None
    data = None
    try:
        res = urequests.get(url)
        if res.status_code == 200:
            data = res.json()
    except Exception as e:
        print("[!] Lỗi đọc lệnh từ Firebase:", e)
    finally:
        if res:
            res.close()
        gc.collect()
    return data

def sync_control_to_firebase():
    """Đồng bộ trạng thái điều khiển lên Firebase"""
    if not firebase_enabled:
        return
    url = build_fb_url("control")
    payload = {
        "mode": system_state["mode"],
        "clothesline_out": system_state["clothesline_out"],
        "target_angle": system_state["target_angle"]
    }
    res = None
    try:
        res = urequests.patch(url, json=payload)
    except Exception as e:
        print("[!] Lỗi đồng bộ control lên Firebase:", e)
    finally:
        if res:
            res.close()
        gc.collect()

# ------------------------------------------------------------------------------
# 5. KIỂM TRA CẬP NHẬT GITHUB OTA KHI KHỞI ĐỘNG (TỰ ĐỘNG)
# ------------------------------------------------------------------------------
try:
    print("[*] Tự động kiểm tra phiên bản mới từ GitHub...")
    ota.check_and_update_github(force=False)
except Exception as e:
    print("[!] Không thể kiểm tra OTA lúc khởi động:", e)

# Khởi tạo trạng thái OTA trên Firebase nếu có
if firebase_enabled:
    try:
        init_res = urequests.patch(build_fb_url("ota"), json={
            "current_version": config.CURRENT_VERSION,
            "status": "IDLE",
            "trigger_update": False
        })
        init_res.close()
    except:
        pass

# ------------------------------------------------------------------------------
# 6. VÒNG LẶP CHÍNH (MAIN LOOP)
# ------------------------------------------------------------------------------
print("[+] Hệ thống giàn phơi thông minh sẵn sàng hoạt động!")

while True:
    # --- A. XỬ LÝ NÚT NHẤN CƠ SW1 (Kèm nhận diện nhấn giữ để kích hoạt OTA) ---
    if button_pin.value() == 0:  # Nút được nhấn (kéo xuống GND)
        press_start = time.ticks_ms()
        is_long_press = False

        # Đo thời gian giữ nút
        while button_pin.value() == 0:
            time.sleep_ms(50)
            if time.ticks_diff(time.ticks_ms(), press_start) >= 3000:
                is_long_press = True
                break

        if is_long_press:
            # Nhấn giữ > 3 giây: Kích hoạt OTA trực tiếp từ GitHub!
            print("\n" + "="*50)
            print("[*] NHẬN DIỆN NHẤN GIỮ > 3 GIÂY!")
            print("[*] Đang kích hoạt cập nhật OTA trực tiếp từ GitHub...")
            print("="*50)
            # Chờ người dùng thả nút ra trước khi tải
            while button_pin.value() == 0:
                time.sleep_ms(50)
            ota.check_and_update_github(force=True)
        else:
            # Nhấn nhả thông thường (< 3 giây): Đảo trạng thái giàn phơi
            print("[*] Bấm nút SW1: Chuyển sang MANUAL & Đảo vị trí xào phơi")
            system_state["mode"] = "MANUAL"
            system_state["clothesline_out"] = not system_state["clothesline_out"]
            system_state["target_angle"] = config.SERVO_ANGLE_OUT if system_state["clothesline_out"] else config.SERVO_ANGLE_IN
            
            set_servo_angle(system_state["target_angle"])
            sync_control_to_firebase()

    # --- B. ĐỌC DỮ LIỆU CẢM BIẾN ---
    temp, hum = 0.0, 0.0
    try:
        sensor_dht.measure()
        temp = sensor_dht.temperature()
        hum = sensor_dht.humidity()
    except Exception as e:
        pass

    rain_adc = 0
    ldr_adc = 0
    if ads:
        try:
            rain_adc = ads.read_raw(config.ADC_CHANNEL_RAIN)
            ldr_adc = ads.read_raw(config.ADC_CHANNEL_LDR)
        except Exception as e:
            pass

    # --- C. ĐIỀU KHIỂN TỰ ĐỘNG (KHI Ở CHẾ ĐỘ AUTO) ---
    if system_state["mode"] == "AUTO":
        # Điều kiện mưa: ADC mưa < rain_threshold (nước làm dẫn điện, áp giảm)
        is_raining = rain_adc < system_state["rain_threshold"]
        # Điều kiện đủ nắng: ADC ánh sáng > light_threshold
        is_sunny = ldr_adc > system_state["light_threshold"]

        # Nếu mưa hoặc trời tối/râm -> Thu giàn phơi vào
        # Nếu không mưa và có nắng -> Đưa giàn phơi ra
        target_out = (not is_raining) and is_sunny

        if target_out != system_state["clothesline_out"]:
            system_state["clothesline_out"] = target_out
            system_state["target_angle"] = config.SERVO_ANGLE_OUT if target_out else config.SERVO_ANGLE_IN
            print(f"[AUTO] Chuyển đổi trạng thái: Out={target_out} (Mưa={is_raining}, Nắng={is_sunny})")
            set_servo_angle(system_state["target_angle"])
            sync_control_to_firebase()

    # --- D. ĐỒNG BỘ VÀ LẮNG NGHE LỆNH TỪ FIREBASE (NẾU CÓ CẤU HÌNH) ---
    if firebase_enabled:
        fb_root = fetch_control_and_ota()
        if fb_root and isinstance(fb_root, dict):
            # 1. Cập nhật lệnh Control
            ctrl = fb_root.get("control")
            if ctrl and isinstance(ctrl, dict):
                if "rain_threshold" in ctrl:
                    system_state["rain_threshold"] = ctrl["rain_threshold"]
                if "light_threshold" in ctrl:
                    system_state["light_threshold"] = ctrl["light_threshold"]

                web_mode = ctrl.get("mode")
                if web_mode in ("AUTO", "MANUAL") and web_mode != system_state["mode"]:
                    system_state["mode"] = web_mode
                    print(f"[*] Cập nhật Mode từ Web: {web_mode}")

                if system_state["mode"] == "MANUAL":
                    web_out = ctrl.get("clothesline_out")
                    if web_out is not None and web_out != system_state["clothesline_out"]:
                        system_state["clothesline_out"] = web_out
                        system_state["target_angle"] = ctrl.get("target_angle", config.SERVO_ANGLE_OUT if web_out else config.SERVO_ANGLE_IN)
                        print(f"[*] Điều khiển Servo từ Web: Out={web_out}, Angle={system_state['target_angle']}")
                        set_servo_angle(system_state["target_angle"])

            # 2. Kiểm tra cờ OTA Update
            ota_cfg = fb_root.get("ota")
            if ota_cfg and isinstance(ota_cfg, dict):
                if ota_cfg.get("trigger_update") is True:
                    print("[*] Phát hiện yêu cầu cập nhật OTA từ Firebase!")
                    ota.perform_ota(ota_cfg)

        # Đẩy dữ liệu Telemetry lên Firebase
        push_telemetry(temp, hum, rain_adc, ldr_adc)

    # Thu gom rác bộ nhớ (Memory Management cho ESP8266)
    gc.collect()

    # Chờ chu kỳ tiếp theo
    time.sleep(config.LOOP_INTERVAL_SEC)
