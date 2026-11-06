def run_loop():
    last_minute_tick = time.time()
    last_history_tick = time.time()
    last_ntp_sync_tick = time.time()
    print("[+] Hệ thống sào phơi thông minh V2.0 sẵn sàng hoạt động!")

    while True:
        current_time_sec = time.time()
        if not NTP_SYNCED or (current_time_sec - last_ntp_sync_tick > 600):
            if sync_ntp_time():
                current_time_sec = time.time()
                last_minute_tick = current_time_sec
            last_ntp_sync_tick = current_time_sec

        local_tm, current_time_str, epoch_now = get_current_local_time()
        today = "{:04d}-{:02d}-{:02d}".format(local_tm[0], local_tm[1], local_tm[2])
        if NTP_SYNCED and not system_state["sun_stats_loaded"]:
            system_state["sun_stats_loaded"] = restore_sun_stats(today)
        elif system_state["sun_stats_loaded"] and system_state["sun_minutes_date"] != today:
            system_state["sun_minutes_today"] = 0
            system_state["sun_seconds_remainder"] = 0.0
            system_state["sun_minutes_date"] = today
            print("[*] Sang ngày mới -> Đặt lại số phút phơi về 0")

        handle_button()
        temp, hum, water_a2, is_raining, ldr_a1, is_sunny, is_humid = read_sensors()
        sync_firebase_commands()
        apply_target_state(current_time_str, is_raining, is_humid)
        last_minute_tick, last_history_tick = periodic_updates(
            last_minute_tick, last_history_tick, current_time_sec,
            temp, hum, water_a2, ldr_a1, is_raining, is_sunny, is_humid, epoch_now
        )
        gc.collect()
        time.sleep(config.LOOP_INTERVAL_SEC)
