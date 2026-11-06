# ==============================================================================
# ota.py - Module Quản lý Cập nhật Firmware từ xa qua GitHub (OTA) V2.0
# Hỗ trợ 2 chế độ:
#   1. Có Firebase: Nhận lệnh cập nhật từ xa từ WebApp qua nhánh maintenance
#   2. KHÔNG có Firebase: Tự động đối chiếu version.json trực tiếp từ GitHub
# ==============================================================================
import gc
import os
import machine
import urequests
import config

def has_firebase():
    """Kiểm tra xem Firebase URL đã được cấu hình hợp lệ hay chưa"""
    return bool(config.FIREBASE_URL and "your-project-id" not in config.FIREBASE_URL)

def update_firebase_maint_status(ota_status, trigger_ota=None, current_version=None):
    """Cập nhật trạng thái tiến trình OTA lên Firebase /smart_clothesline/maintenance (nếu có cấu hình)"""
    if not has_firebase():
        return

    try:
        url = f"{config.FIREBASE_URL}/smart_clothesline/maintenance.json"
        if config.FIREBASE_AUTH:
            url += f"?auth={config.FIREBASE_AUTH}"

        payload = {"ota_status": ota_status}
        if trigger_ota is not None:
            payload["trigger_ota"] = trigger_ota
        if current_version is not None:
            payload["current_version"] = current_version

        res = urequests.patch(url, json=payload)
        res.close()
    except Exception as e:
        print("[OTA] Không thể cập nhật trạng thái lên Firebase:", e)
    finally:
        gc.collect()

def download_file(file_url, target_path):
    """Tải một file từ GitHub Raw và lưu vào hệ thống tệp Flash của ESP8266"""
    print(f"[OTA] Đang tải từ: {file_url} -> {target_path}...")
    temp_path = target_path + ".tmp"

    res = None
    try:
        res = urequests.get(file_url)
        if res.status_code != 200:
            print(f"[OTA] HTTP Error {res.status_code}")
            return False

        # Ghi nội dung vào file tạm
        with open(temp_path, "wb") as f:
            f.write(res.content)

        res.close()
        res = None
        gc.collect()

        # Kiểm tra kích thước file tải về
        stat = os.stat(temp_path)
        if stat[6] == 0:
            print("[OTA] File rỗng! Hủy bỏ.")
            try:
                os.remove(temp_path)
            except:
                pass
            return False

        # Thay thế file cũ an toàn (lưu giữ file config.py và .env)
        try:
            os.remove(target_path)
        except OSError:
            pass

        os.rename(temp_path, target_path)
        print(f"[OTA] Đã cập nhật thành công: {target_path} ({stat[6]} bytes)")
        return True

    except Exception as e:
        print(f"[OTA] Lỗi trong quá trình tải {target_path}:", e)
        try:
            os.remove(temp_path)
        except:
            pass
        return False
    finally:
        if res:
            res.close()
        gc.collect()

def perform_ota(maint_data):
    """
    Thực hiện quy trình nạp Firmware mới:
    1. Đổi ota_status thành DOWNLOADING (nếu có Firebase)
    2. Tải các module firmware và main.py từ GitHub
    3. Cập nhật version và ota_status thành SUCCESS, trigger_ota = False
    4. Reset vi điều khiển để chạy mã nguồn mới
    """
    target_version = maint_data.get("target_version", config.CURRENT_VERSION)
    download_url = maint_data.get("download_url") or f"{config.GITHUB_RAW_BASE}/firmware/main.py"

    print(f"[*] Bắt đầu tiến trình OTA lên phiên bản {target_version}...")
    update_firebase_maint_status(ota_status="DOWNLOADING")

    module_base_url = download_url.rsplit("/", 1)[0]
    core_modules = (
        "main_loop.py",
        "main_io.py",
        "main_sync.py",
        "main_control.py",
        "main_periodic.py",
        "main_setup.py",
        "main_firebase.py",
        "wifi_manager.py"
    )
    for module_name in core_modules:
        if not download_file(module_base_url + "/" + module_name, module_name):
            print("[-] OTA thất bại khi tải module:", module_name)
            update_firebase_maint_status(
                ota_status="FAILED",
                trigger_ota=False
            )
            return False

    success = download_file(download_url, "main.py")

    if success:
        print(f"[+] Cập nhật thành công lên phiên bản v{target_version}! Đang khởi động lại...")
        update_firebase_maint_status(
            ota_status="SUCCESS",
            trigger_ota=False,
            current_version=target_version
        )
        import time
        time.sleep(1)
        machine.reset()
        return True
    else:
        print("[-] Cập nhật OTA thất bại!")
        update_firebase_maint_status(
            ota_status="FAILED",
            trigger_ota=False
        )
        return False

def check_and_update_github(force=False):
    """
    Kiểm tra và cập nhật OTA TRỰC TIẾP (Không cần Firebase)
    Hỗ trợ 2 nguồn tải:
      1. Từ máy tính nội bộ trong mạng LAN (nếu có config.LOCAL_OTA_URL)
      2. Từ GitHub Repository
    """
    if config.LOCAL_OTA_URL:
        print(f"[OTA] Đang cập nhật từ máy tính nội bộ (LAN): {config.LOCAL_OTA_URL}")
        return perform_ota({
            "target_version": "local",
            "download_url": config.LOCAL_OTA_URL
        })

    print("[OTA] Kiểm tra phiên bản trực tiếp từ GitHub...")
    res = None
    try:
        res = urequests.get(config.OTA_VERSION_URL)
        if res.status_code != 200:
            print(f"[OTA] Không thể đọc version.json từ GitHub (Mã lỗi: {res.status_code})")
            return False

        git_data = res.json()
        res.close()
        res = None
        gc.collect()

        remote_ver = git_data.get("version", "").strip()
        print(f"[OTA] Phiên bản trên thiết bị: v{config.CURRENT_VERSION} | Phiên bản trên GitHub: v{remote_ver}")

        if force or (remote_ver and remote_ver != config.CURRENT_VERSION):
            print(f"[OTA] Phát hiện phiên bản mới (v{remote_ver})! Tiến hành cập nhật ngay...")
            return perform_ota({
                "target_version": remote_ver,
                "download_url": f"{config.GITHUB_RAW_BASE}/firmware/main.py"
            })
        else:
            print("[OTA] Thiết bị đang ở phiên bản mới nhất.")
            return False

    except Exception as e:
        print("[OTA] Lỗi khi kiểm tra GitHub OTA:", e)
        return False
    finally:
        if res:
            res.close()
        gc.collect()
