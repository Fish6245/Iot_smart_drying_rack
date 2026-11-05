button_press_active = False
button_high_since = None
button_low_since = None
BUTTON_SHORT_PRESS_MAX_MS = 1000
BUTTON_RESET_HOLD_MS = 3000
BUTTON_DEBOUNCE_MS = 80

def button_irq_handler(_pin):
    global button_press_active, button_high_since, button_low_since
    now = time.ticks_ms()
    if _pin.value() == 1:
        if button_press_active:
            button_low_since = None
        else:
            button_high_since = now
            button_press_active = True
    elif button_press_active:
        button_low_since = now

def handle_button():
    global button_press_active, button_high_since, button_low_since

    now = time.ticks_ms()
    if not button_press_active:
        return

    if button_pin.value() == 1:
        button_low_since = None
        if time.ticks_diff(now, button_high_since) >= BUTTON_RESET_HOLD_MS:
            print("[*] Giữ nút D6 mức HIGH đủ 3 giây. Đang khởi động lại...")
            machine.reset()
        return

    if button_low_since is None:
        return

    if time.ticks_diff(now, button_low_since) < BUTTON_DEBOUNCE_MS:
        return

    held_ms = time.ticks_diff(button_low_since, button_high_since)
    button_press_active = False
    button_high_since = None
    button_low_since = None
    if held_ms >= BUTTON_RESET_HOLD_MS:
        print("[*] Giữ nút D6 mức HIGH đủ 3 giây. Đang khởi động lại...")
        machine.reset()
    if held_ms > BUTTON_SHORT_PRESS_MAX_MS:
        print("[*] Đã bỏ qua lần nhấn D6 dài hơn 1 giây; giữ đủ 3 giây để reset.")
        return
    # --- A. XỬ LÝ NÚT NHẤN CƠ SW1 (GPIO 12) - ĐÓNG / MỞ SÀO THỦ CÔNG TẠI CHỖ ---
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
