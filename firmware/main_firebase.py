def build_fb_url(path):
    url = f"{config.FIREBASE_URL}/smart_clothesline/{path}.json"
    if config.FIREBASE_AUTH:
        url += f"?auth={config.FIREBASE_AUTH}"
    return url

def push_telemetry(temp, hum, water_a0, is_raining, ldr_a1, is_sunny, is_humid):
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
        "is_humid": is_humid,
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
