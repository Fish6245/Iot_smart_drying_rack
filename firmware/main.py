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
    with open(_part, "r") as _source:
        exec(_source.read(), globals())
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

if firebase_enabled:
    try:
        init_res = urequests.patch(build_fb_url("maintenance"), json={
            "current_version": config.CURRENT_VERSION,
            "target_version": config.CURRENT_VERSION,
            "trigger_ota": False,
            "trigger_reset": False,
            "ota_status": "IDLE"
        })
        init_res.close()
    except:
        pass

# Bộ đếm thời gian

gc.collect()
run_loop()
