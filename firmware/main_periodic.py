def periodic_updates(last_minute_tick, last_history_tick, current_time_sec, temp, hum, water_a2, ldr_a1, is_raining, is_sunny, is_humid, epoch_now):
    # --- E. THỐNG KÊ THỜI GIAN PHƠI (CỘNG ĐỦ CÁC PHÚT ĐÃ TRÔI QUA) ---
    elapsed_seconds = current_time_sec - last_minute_tick
    last_minute_tick = current_time_sec
    if elapsed_seconds < 0:
        elapsed_seconds = 0
    if system_state["sun_stats_loaded"] and system_state["clothesline_state"] == "OPEN":
        total_seconds = system_state["sun_seconds_remainder"] + elapsed_seconds
        added_minutes = int(total_seconds // 60)
        system_state["sun_minutes_today"] += added_minutes
        system_state["sun_seconds_remainder"] = total_seconds - added_minutes * 60

    # --- F. GHI BẢN GHI LỊCH SỬ (MỖI 5 PHÚT) ---
    if current_time_sec - last_history_tick >= 300:
        last_history_tick = current_time_sec
        push_history_record(temp, hum, water_a2, ldr_a1, epoch_now)

    # --- G. ĐẨY DỮ LIỆU TELEMETRY LÊN FIREBASE ĐỊNH KỲ ---
    push_telemetry(temp, hum, water_a2, is_raining, ldr_a1, is_sunny, is_humid)

    return last_minute_tick, last_history_tick
