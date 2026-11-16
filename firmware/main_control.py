def apply_target_state(current_time_str, is_raining, is_humid):
    # --- D. QUY TẮC ƯU TIÊN ĐIỀU KHIỂN SÀO PHƠI ---
    # Mục tiêu dự kiến cho sào phơi: "OPEN" hoặc "CLOSED"
    target_state = system_state["clothesline_state"]

    if system_state["mode"] == "MANUAL":
        if system_state["manual_command"] in ("OPEN", "CLOSE"):
            target_state = "OPEN" if system_state["manual_command"] == "OPEN" else "CLOSED"
    elif system_state["auto_schedule_enabled"]:
        op_time = system_state["open_time"]
        cl_time = system_state["close_time"]

        # Also support schedules that continue past midnight.
        if op_time <= cl_time:
            in_schedule = op_time <= current_time_str < cl_time
        else:
            in_schedule = current_time_str >= op_time or current_time_str < cl_time
        if not in_schedule or (
            system_state["rain_priority_override"] and (is_raining or is_humid)
        ):
            target_state = "CLOSED"
        else:
            target_state = "OPEN"
    else:
        target_state = "CLOSED" if is_raining or is_humid else "OPEN"

    # Thực thi điều khiển Servo nếu trạng thái thay đổi
    if target_state != system_state["clothesline_state"]:
        system_state["clothesline_state"] = target_state
        system_state["servo_angle"] = config.SERVO_ANGLE_OUT if target_state == "OPEN" else config.SERVO_ANGLE_IN
        print(f"[POLE] Cập nhật vị trí sào phơi: {target_state} (Góc: {system_state['servo_angle']}°)")
        set_servo_angle(system_state["servo_angle"])

        if firebase_enabled:
            try:
                gc.collect()
                res_u = urequests.patch(build_fb_url("control"), json={
                    "servo_angle": system_state["servo_angle"]
                })
                res_u.close()
                res_u = None
                gc.collect()
            except:
                pass
