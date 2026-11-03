def periodic_updates(last_minute_tick, last_history_tick, current_time_sec, temp, hum, water_a0, ldr_a1, is_raining, is_sunny, is_humid, epoch_now):
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
    push_telemetry(temp, hum, water_a0, is_raining, ldr_a1, is_sunny, is_humid)

    return last_minute_tick, last_history_tick
