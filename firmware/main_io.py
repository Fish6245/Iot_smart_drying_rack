button_press_pending = False

def button_irq_handler(_pin):
    global button_press_pending
    button_press_pending = True

def handle_button():
    global button_press_pending

    # --- A. XỬ LÝ NÚT NHẤN CƠ SW1 (GPIO 12) - ĐÓNG / MỞ SÀO THỦ CÔNG TẠI CHỖ ---
    if not button_press_pending:
        return
    button_press_pending = False
    time.sleep_ms(50)  # Chống dội phím (debounce)
    button_press_pending = False
    new_state = "CLOSED" if system_state["clothesline_state"] == "OPEN" else "OPEN"
    manual_command = "CLOSE" if new_state == "CLOSED" else "OPEN"
    print(f"[*] Bấm nút SW1: Chuyển sào sang {new_state}")
    system_state["manual_command"] = manual_command
    system_state["clothesline_state"] = new_state
    system_state["servo_angle"] = config.SERVO_ANGLE_OUT if new_state == "OPEN" else config.SERVO_ANGLE_IN
    set_servo_angle(system_state["servo_angle"])

    if firebase_enabled:
        try:
            res_m = urequests.patch(build_fb_url("control"), json={
                "manual_command": manual_command,
                "servo_angle": system_state["servo_angle"]
            })
            res_m.close()
        except Exception as e:
            print("[!] Lỗi gửi lệnh nút SW1 lên Firebase:", e)


def read_sensors():
    # --- B. ĐỌC DỮ LIỆU CẢM BIẾN ---
    temp, hum = 0.0, 0.0
    try:
        sensor_dht.measure()
        temp = sensor_dht.temperature()
        hum = sensor_dht.humidity()
    except Exception as e:
        pass

    # Keep the rack closed if the ADC cannot be read; treat it as a wet-sensor fail-safe.
    water_a2 = 26400
    ldr_a1 = 0
    if ads:
        try:
            water_a2 = ads.read_raw(config.ADC_CHANNEL_RAIN)
            ldr_a1 = ads.read_raw(config.ADC_CHANNEL_LDR)
        except Exception as e:
            pass

    # Phân tích điều kiện thời tiết thực tế
    is_raining = water_a2 > system_state["rain_threshold"]
    is_sunny = ldr_a1 > system_state["sun_threshold"]
    is_humid = hum > system_state["humidity_threshold"]

    return temp, hum, water_a2, is_raining, ldr_a1, is_sunny, is_humid
