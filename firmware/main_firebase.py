UNIX_EPOCH_OFFSET = 946684800

def build_fb_url(path):
    url = f"{config.FIREBASE_URL}/smart_clothesline/{path}.json"
    if config.FIREBASE_AUTH:
        url += f"?auth={config.FIREBASE_AUTH}"
    return url

def restore_sun_stats(today):
    """Khôi phục bộ đếm phơi hôm nay từ telemetry để không mất khi board khởi động lại."""
    if not firebase_enabled:
        system_state["sun_minutes_date"] = today
        return True

    res = None
    data = None
    try:
        gc.collect()
        print("[Firebase] RAM trống trước khi khôi phục:", gc.mem_free(), "bytes")
        res = urequests.get(build_fb_url("telemetry"))
        if res.status_code != 200:
            print("[!] Firebase trả về HTTP", res.status_code, "khi khôi phục thống kê")
            return False

        data = res.json()
        if isinstance(data, dict) and data.get("sun_minutes_date") == today:
            system_state["sun_minutes_today"] = max(0, int(data.get("sun_minutes_today", 0)))
            remainder = float(data.get("sun_seconds_remainder", 0))
            system_state["sun_seconds_remainder"] = max(0.0, min(remainder, 59.999))
        else:
            system_state["sun_minutes_today"] = 0
            system_state["sun_seconds_remainder"] = 0.0
        system_state["sun_minutes_date"] = today
        print("[*] Đã khôi phục thống kê phơi hôm nay:", system_state["sun_minutes_today"], "phút")
        return True
    except Exception as e:
        print("[!] Không thể khôi phục thống kê phơi:", e)
        return False
    finally:
        if res:
            res.close()
        res = None
        data = None
        gc.collect()

def push_telemetry(temp, hum, water_a2, is_raining, ldr_a1, is_sunny, is_humid):
    """Đẩy telemetry thời gian thực lên Firebase"""
    if not firebase_enabled:
        return
    gc.collect()
    url = build_fb_url("telemetry")
    payload = {
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "water_a0": water_a2,
        "is_raining": is_raining,
        "ldr_a1": ldr_a1,
        "is_sunny": is_sunny,
        "is_humid": is_humid,
        "clothesline_state": system_state["clothesline_state"],
        "firmware_version": config.CURRENT_VERSION,
        "last_updated": time.time()
    }
    if system_state["sun_stats_loaded"]:
        payload["sun_minutes_today"] = system_state["sun_minutes_today"]
        payload["sun_seconds_remainder"] = system_state["sun_seconds_remainder"]
        payload["sun_minutes_date"] = system_state["sun_minutes_date"]
    res = None
    try:
        res = urequests.patch(url, json=payload)
    except Exception as e:
        print("[!] Lỗi đẩy telemetry lên Firebase:", e)
    finally:
        if res:
            res.close()
        res = None
        payload = None
        url = None
        gc.collect()

def push_history_record(temp, hum, water_a2, ldr_a1, timestamp):
    """Đẩy bản ghi lịch sử định kỳ lên /smart_clothesline/history/<timestamp>"""
    if not firebase_enabled:
        return
    gc.collect()
    url = build_fb_url(f"history/{int(timestamp)}")
    payload = {
        "temp": round(temp, 1),
        "hum": round(hum, 1),
        "water_a0": water_a2,
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
        res = None
        payload = None
        url = None
        gc.collect()

def fetch_firebase_section(section):
    """Đọc riêng một nhánh cần thiết, không tải nhánh history lớn."""
    if not firebase_enabled:
        return None

    res = None
    data = None
    try:
        gc.collect()
        res = urequests.get(build_fb_url(section))
        if res.status_code == 200:
            data = res.json()
        else:
            print("[!] Firebase trả về HTTP", res.status_code, "khi đọc", section)
    except Exception as e:
        print("[!] Lỗi đọc Firebase", section + ":", e)
    finally:
        if res:
            res.close()
        res = None
        gc.collect()
    return data

def reset_control_mode_on_boot():
    if not firebase_enabled:
        return

    res = None
    try:
        gc.collect()
        res = urequests.patch(build_fb_url("control"), json={
            "mode": "AUTO",
            "manual_command": "NONE"
        })
        if res.status_code != 200:
            print("[!] Firebase trả về HTTP", res.status_code, "khi đặt lại chế độ AUTO")
    except Exception as e:
        print("[!] Không thể đặt chế độ AUTO trên Firebase khi khởi động:", e)
    finally:
        if res:
            res.close()
        res = None
        gc.collect()

def update_firebase_maintenance_flag(key, val):
    """Cập nhật cờ bảo trì trên Firebase"""
    if not firebase_enabled:
        return
    gc.collect()
    url = build_fb_url("maintenance")
    payload = {key: val}
    res = None
    try:
        res = urequests.patch(url, json=payload)
    except Exception as e:
        pass
    finally:
        if res:
            res.close()
        res = None
        payload = None
        url = None
        gc.collect()

# ------------------------------------------------------------------------------
