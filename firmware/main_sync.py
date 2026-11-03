def sync_firebase_commands():
    # --- C. ĐỒNG BỘ CẤU HÌNH & LỆNH TỪ FIREBASE ---
    if firebase_enabled:
        # 1. Cấu hình ngưỡng & điều khiển thủ công
        ctrl = fetch_firebase_section("control")
        if ctrl and isinstance(ctrl, dict):
            if "rain_threshold" in ctrl and ctrl["rain_threshold"] is not None:
                system_state["rain_threshold"] = int(ctrl["rain_threshold"])
            if "sun_threshold" in ctrl and ctrl["sun_threshold"] is not None:
                system_state["sun_threshold"] = int(ctrl["sun_threshold"])
            if "humidity_threshold" in ctrl and ctrl["humidity_threshold"] is not None:
                system_state["humidity_threshold"] = float(ctrl["humidity_threshold"])

            cmd = ctrl.get("manual_command")
            if cmd in ("OPEN", "CLOSE") and cmd != system_state["manual_command"]:
                print(f"[*] Nhận lệnh thủ công từ Firebase: {cmd}")
                system_state["manual_command"] = cmd
        ctrl = None
        gc.collect()

        # 2. Cấu hình lịch hẹn giờ
        sch = fetch_firebase_section("schedule")
        if sch and isinstance(sch, dict):
            if "auto_schedule_enabled" in sch:
                system_state["auto_schedule_enabled"] = bool(sch["auto_schedule_enabled"])
            if "open_time" in sch and sch["open_time"]:
                system_state["open_time"] = sch["open_time"]
            if "close_time" in sch and sch["close_time"]:
                system_state["close_time"] = sch["close_time"]
            if "rain_priority_override" in sch:
                system_state["rain_priority_override"] = bool(sch["rain_priority_override"])
        sch = None
        gc.collect()

        # 3. Cơ chế bảo trì (Reset & OTA)
        maint = fetch_firebase_section("maintenance")
        if maint and isinstance(maint, dict):
            if maint.get("trigger_reset") is True:
                print("[*] Nhận lệnh khởi động lại (Reset) từ Web!")
                update_firebase_maintenance_flag("trigger_reset", False)
                time.sleep(1)
                machine.reset()

            if maint.get("trigger_ota") is True:
                print("[*] Nhận lệnh cập nhật OTA Firmware từ Web!")
                import ota
                ota.perform_ota(maint)
        maint = None
        gc.collect()

