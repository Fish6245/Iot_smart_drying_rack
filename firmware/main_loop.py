def run_loop():
    last_minute_tick = time.time()
    last_history_tick = time.time()
    last_ntp_sync_tick = time.time()
    print("[+] Hệ thống sào phơi thông minh V2.0 sẵn sàng hoạt động!")

    while True:
        current_time_sec = time.time()
        if not NTP_SYNCED or (current_time_sec - last_ntp_sync_tick > 600):
            last_ntp_sync_tick = current_time_sec
            sync_ntp_time()

        local_tm, current_time_str, epoch_now = get_current_local_time()
        hour, minute, day = local_tm[3], local_tm[4], local_tm[2]
        if hour == 0 and minute == 0 and system_state["last_reset_day"] != day:
            system_state["sun_minutes_today"] = 0
            system_state["last_reset_day"] = day
            print("[*] 00:00 -> Đặt lại số phút phơi trong ngày về 0")

        handle_button()
        temp, hum, water_a0, is_raining, ldr_a1, is_sunny, is_humid = read_sensors()
        sync_firebase_commands()
        apply_target_state(current_time_str, is_raining, is_humid)
        last_minute_tick, last_history_tick = periodic_updates(
            last_minute_tick, last_history_tick, current_time_sec,
            temp, hum, water_a0, ldr_a1, is_raining, is_sunny, is_humid, epoch_now
        )
        gc.collect()
        time.sleep(config.LOOP_INTERVAL_SEC)
