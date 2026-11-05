# ==============================================================================
# main.py - Firmware Giàn Phơi Thông Minh V2.0 (ESP8266 - MicroPython)
# WeMos D1 R2 | ADS1115 (A1/A2), DHT11 (D4) | Servo SG90 (D7) | Firebase | GitHub OTA
# ==============================================================================
import gc

gc.collect()
for _part in (
    "main_loop.py",
    "main_io.py",
    "main_sync.py",
    "main_control.py",
    "main_periodic.py",
    "main_setup.py",
    "main_firebase.py",
):
    gc.collect()
    with open(_part, "r") as _source:
        _code = _source.read()
    exec(_code, globals())
    del _code
    gc.collect()
del _part, _source

import urequests
sync_ntp_time()
if config.CHECK_GITHUB_OTA_ON_BOOT:
    try:
        import ota
        print("[*] Kiểm tra phiên bản mới từ GitHub...")
        ota.check_and_update_github(force=False)
    except Exception as e:
        print("[!] Không thể kiểm tra OTA lúc khởi động:", e)

# Bộ đếm thời gian

gc.collect()
run_loop()
