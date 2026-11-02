# ==============================================================================
# main.py - Firmware Giàn Phơi Thông Minh V2.0 (ESP8266 - MicroPython)
# WeMos D1 R2 | ADS1115 (A0/A1), DHT22 (D4) | Servo SG90 (D7) | Firebase | GitHub OTA
# ==============================================================================
import gc
import time
import machine
import dht
import urequests

try:
    import ntptime
except ImportError:
    ntptime = None

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
    duty = int(26 + (angle / 180.0) * (128 - 26))
    servo_pwm.duty(duty)
    time.sleep_ms(500)
    servo_pwm.duty(0)

# Khởi tạo trạng thái ban đầu của Servo (Thu vào)
set_servo_angle(config.SERVO_ANGLE_IN)

# Nút nhấn cơ học SW1 (D6: GPIO 12)
button_pin = machine.Pin(config.PIN_BUTTON, machine.Pin.IN)

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
sync_ntp_time()

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
    "last_reset_day": -1,

    # Control
    "manual_command": "NONE",           # "OPEN", "CLOSE", "NONE"
    "servo_angle": config.SERVO_ANGLE_IN,
    "rain_threshold": config.DEFAULT_RAIN_THRESHOLD,
    "sun_threshold": config.DEFAULT_SUN_THRESHOLD,

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
def build_fb_url(path):
    url = f"{config.FIREBASE_URL}/smart_clothesline/{path}.json"
    if config.FIREBASE_AUTH:
        url += f"?auth={config.FIREBASE_AUTH}"
    return url

def push_telemetry(temp, hum, water_a0, is_raining, ldr_a1, is_sunny):
    """Đẩy telemetry thời gian thực lên Firebase"""
    if not firebase_enabled:
        return
    url = build_fb_url("telemetry")
    payload = {
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "water_a0": water_a0,
        "is_raining": is_raining,
        "ldr_a1": ldr_a1,
        "is_sunny": is_sunny,
        "clothesline_state": system_state["clothesline_state"],
        "sun_minutes_today": system_state["sun_minutes_today"],
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

def push_history_record(temp, hum, water_a0, ldr_a1, timestamp):
    """Đẩy bản ghi lịch sử định kỳ lên /smart_clothesline/history/<timestamp>"""
    if not firebase_enabled:
        return
    url = build_fb_url(f"history/{int(timestamp)}")
    payload = {
        "temp": round(temp, 1),
        "hum": round(hum, 1),
        "water_a0": water_a0,
        "ldr_a1": ldr_a1
    }
    res = None
    try:
        res = urequests.put(url, json=payload)
    except Exception as e:
        print("[!] Lỗi lưu lịch sử:", e)
    finally:
        if res:
            res.close()
        gc.collect()

def fetch_firebase_all():
    """Đọc toàn bộ cây dữ liệu smart_clothesline từ Firebase (GET)"""
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
        print("[!] Lỗi đọc Firebase:", e)
    finally:
        if res:
            res.close()
        gc.collect()
    return data

def update_firebase_maintenance_flag(key, val):
    """Cập nhật cờ bảo trì trên Firebase"""
    if not firebase_enabled:
        return
    url = build_fb_url("maintenance")
    res = None
    try:
        res = urequests.patch(url, json={key: val})
    except Exception as e:
        pass
    finally:
        if res:
            res.close()
        gc.collect()

# ------------------------------------------------------------------------------
# 5. KHỞI TẠO BAN ĐẦU TRÊN FIREBASE
# ------------------------------------------------------------------------------
try:
    print("[*] Kiểm tra phiên bản mới từ GitHub...")
    ota.check_and_update_github(force=False)
except Exception as e:
    print("[!] Không thể kiểm tra OTA lúc khởi động:", e)

if firebase_enabled:
    try:
        init_res = urequests.patch(build_fb_url("maintenance"), json={
            "current_version": config.CURRENT_VERSION,
            "target_version": config.CURRENT_VERSION,
            "trigger_ota": False,
            "trigger_reset": False,
            "ota_status": "IDLE"
        })
        init_res.close()
    except:
        pass

# Bộ đếm thời gian
last_minute_tick = time.time()
last_history_tick = time.time()
last_ntp_sync_tick = time.time()

# ------------------------------------------------------------------------------
# 6. VÒNG LẶP CHÍNH (MAIN LOOP)
# ------------------------------------------------------------------------------
print("[+] Hệ thống sào phơi thông minh V2.0 sẵn sàng hoạt động!")

while True:
    current_time_sec = time.time()

    # Định kỳ thử đồng bộ lại NTP nếu chưa thành công (mỗi 10 phút)
    if not NTP_SYNCED or (current_time_sec - last_ntp_sync_tick > 600):
        last_ntp_sync_tick = current_time_sec
        sync_ntp_time()

    # Lấy thời gian thực
    local_tm, current_time_str, epoch_now = get_current_local_time()
    hour, minute, day = local_tm[3], local_tm[4], local_tm[2]

    # Đặt lại bộ đếm phơi nắng lúc 00:00 hàng ngày
    if hour == 0 and minute == 0 and system_state["last_reset_day"] != day:
        system_state["sun_minutes_today"] = 0
        system_state["last_reset_day"] = day
        print("[*] 00:00 -> Đặt lại số phút phơi trong ngày về 0")

    # --- A. XỬ LÝ NÚT NHẤN CƠ SW1 (GPIO 12) - ĐÓNG / MỞ SÀO THỦ CÔNG TẠI CHỖ ---
    if button_pin.value() == 0:
        time.sleep_ms(50)  # Chống dội phím (debounce)
        if button_pin.value() == 0:
            # Đảo trạng thái sào phơi thủ công ngay lập tức (không cần chờ nhấn giữ)
            new_target = "CLOSED" if system_state["clothesline_state"] == "OPEN" else "OPEN"
            print(f"[*] Bấm nút SW1: Chuyển sào sang {new_target}")
            system_state["manual_command"] = new_target
            system_state["clothesline_state"] = new_target
            system_state["servo_angle"] = config.SERVO_ANGLE_OUT if new_target == "OPEN" else config.SERVO_ANGLE_IN
            set_servo_angle(system_state["servo_angle"])

            if firebase_enabled:
                try:
                    res_m = urequests.patch(build_fb_url("control"), json={
                        "manual_command": new_target,
                        "servo_angle": system_state["servo_angle"]
                    })
                    res_m.close()
                except:
                    pass

            # Đợi nhả nút để tránh kích hoạt liên tục
            while button_pin.value() == 0:
                time.sleep_ms(20)

    # --- B. ĐỌC DỮ LIỆU CẢM BIẾN ---
    temp, hum = 0.0, 0.0
    try:
        sensor_dht.measure()
        temp = sensor_dht.temperature()
        hum = sensor_dht.humidity()
    except Exception as e:
        pass

    water_a0 = 26400
    ldr_a1 = 0
    if ads:
        try:
            water_a0 = ads.read_raw(config.ADC_CHANNEL_RAIN)
            ldr_a1 = ads.read_raw(config.ADC_CHANNEL_LDR)
        except Exception as e:
            pass

    # Phân tích điều kiện thời tiết thực tế
    is_raining = water_a0 < system_state["rain_threshold"]
    is_sunny = ldr_a1 > system_state["sun_threshold"]

    # --- C. ĐỒNG BỘ CẤU HÌNH & LỆNH TỪ FIREBASE ---
    if firebase_enabled:
        fb_root = fetch_firebase_all()
        if fb_root and isinstance(fb_root, dict):
            # 1. Cấu hình ngưỡng & điều khiển thủ công
            ctrl = fb_root.get("control")
            if ctrl and isinstance(ctrl, dict):
                if "rain_threshold" in ctrl and ctrl["rain_threshold"] is not None:
                    system_state["rain_threshold"] = int(ctrl["rain_threshold"])
                if "sun_threshold" in ctrl and ctrl["sun_threshold"] is not None:
                    system_state["sun_threshold"] = int(ctrl["sun_threshold"])

                cmd = ctrl.get("manual_command")
                if cmd in ("OPEN", "CLOSE") and cmd != system_state["manual_command"]:
                    print(f"[*] Nhận lệnh thủ công từ Firebase: {cmd}")
                    system_state["manual_command"] = cmd

            # 2. Cấu hình lịch hẹn giờ
            sch = fb_root.get("schedule")
            if sch and isinstance(sch, dict):
                if "auto_schedule_enabled" in sch:
                    system_state["auto_schedule_enabled"] = bool(sch["auto_schedule_enabled"])
                if "open_time" in sch and sch["open_time"]:
                    system_state["open_time"] = sch["open_time"]
                if "close_time" in sch and sch["close_time"]:
                    system_state["close_time"] = sch["close_time"]
                if "rain_priority_override" in sch:
                    system_state["rain_priority_override"] = bool(sch["rain_priority_override"])

            # 3. Cơ chế bảo trì (Reset & OTA)
            maint = fb_root.get("maintenance")
            if maint and isinstance(maint, dict):
                if maint.get("trigger_reset") is True:
                    print("[*] Nhận lệnh khởi động lại (Reset) từ Web!")
                    update_firebase_maintenance_flag("trigger_reset", False)
                    time.sleep(1)
                    machine.reset()

                if maint.get("trigger_ota") is True:
                    print("[*] Nhận lệnh cập nhật OTA Firmware từ Web!")
                    ota.perform_ota(maint)

    # --- D. QUY TẮC ƯU TIÊN ĐIỀU KHIỂN SÀO PHƠI ---
    # Mục tiêu dự kiến cho sào phơi: "OPEN" hoặc "CLOSED"
    target_state = system_state["clothesline_state"]

    # Mức ưu tiên 1: Chế độ ưu tiên chống mưa (Rain Priority Override)
    if system_state["rain_priority_override"] and is_raining:
        target_state = "CLOSED"

    # Mức ưu tiên 2: Điều khiển thủ công (Manual Command)
    elif system_state["manual_command"] in ("OPEN", "CLOSE"):
        target_state = system_state["manual_command"]

    # Mức ưu tiên 3: Lịch hẹn giờ tự động (Auto Schedule)
    elif system_state["auto_schedule_enabled"]:
        op_time = system_state["open_time"]
        cl_time = system_state["close_time"]

        # So sánh thời gian trong ngày
        in_schedule = (op_time <= current_time_str < cl_time)
        if in_schedule and not is_raining:
            target_state = "OPEN"
        else:
            target_state = "CLOSED"

    # Thực thi điều khiển Servo nếu trạng thái thay đổi
    if target_state != system_state["clothesline_state"]:
        system_state["clothesline_state"] = target_state
        system_state["servo_angle"] = config.SERVO_ANGLE_OUT if target_state == "OPEN" else config.SERVO_ANGLE_IN
        print(f"[POLE] Cập nhật vị trí sào phơi: {target_state} (Góc: {system_state['servo_angle']}°)")
        set_servo_angle(system_state["servo_angle"])

        if firebase_enabled:
            try:
                res_u = urequests.patch(build_fb_url("control"), {
                    "servo_angle": system_state["servo_angle"]
                })
                res_u.close()
            except:
                pass

    # --- E. THỐNG KÊ THỜI GIAN PHƠI NẮNG (MỖI 1 PHÚT) ---
    if current_time_sec - last_minute_tick >= 60:
        last_minute_tick = current_time_sec
        if system_state["clothesline_state"] == "OPEN":
            system_state["sun_minutes_today"] += 1

    # --- F. GHI BẢN GHI LỊCH SỬ (MỖI 5 PHÚT) ---
    if current_time_sec - last_history_tick >= 300:
        last_history_tick = current_time_sec
        push_history_record(temp, hum, water_a0, ldr_a1, epoch_now)

    # --- G. ĐẨY DỮ LIỆU TELEMETRY LÊN FIREBASE ĐỊNH KỲ ---
    push_telemetry(temp, hum, water_a0, is_raining, ldr_a1, is_sunny)

    # Quản lý giải phóng RAM cho ESP8266
    gc.collect()

    time.sleep(config.LOOP_INTERVAL_SEC)
