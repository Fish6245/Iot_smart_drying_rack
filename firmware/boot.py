# ==============================================================================
# boot.py - Khởi động hệ thống WeMos D1 (ESP8266) & Kết nối WiFi V2.0
# Tích hợp: WiFi Captive Portal (SaoPhoi-Setup) & WebREPL
# ==============================================================================
import gc
import machine
import sys
import time
import config

gc.enable()

# ------------------------------------------------------------------------------
# 1. XỬ LÝ NÚT NHẤN SW1 (D6 / GPIO 12) KHI BẬT NGUỒN
# ------------------------------------------------------------------------------
# - Nhấn SW1 (D6) trong lúc khởi động: MỞ WIFI CAPTIVE PORTAL (SaoPhoi-Setup)
button_pin = machine.Pin(config.PIN_BUTTON, machine.Pin.IN)
wifi_setup_requested = False
startup_check_start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), startup_check_start) < 3000:
    if button_pin.value() == 1:
        time.sleep_ms(100)
        if button_pin.value() == 1:
            wifi_setup_requested = True
            break
    time.sleep_ms(50)

if wifi_setup_requested:
    print("\n[*] Nhấn SW1 (D6) lúc khởi động -> mở WiFi cấu hình trong 3 phút.")
    try:
        gc.collect()
        import wifi_manager
        wifi_manager.start_portal(timeout_sec=180)
    except Exception as e:
        print("[!] Lỗi WiFi Manager:", e)
    finally:
        sys.modules.pop("wifi_manager", None)
        if "wifi_manager" in globals():
            del wifi_manager
        gc.collect()

# ------------------------------------------------------------------------------
# 2. KẾT NỐI WIFI VÀ TỰ ĐỘNG BẬT CAPTIVE PORTAL NẾU CHƯA CÓ MẠNG
# ------------------------------------------------------------------------------
def connect_wifi():
    """Kết nối WiFi theo cấu hình đã hợp nhất từ config.ini / .env."""
    gc.collect()
    import network
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)

    if ap_if.active():
        ap_if.active(False)

    ssid = config.WIFI_SSID
    password = config.WIFI_PASSWORD
    has_valid_ssid = bool(ssid and ssid != "YOUR_WIFI_SSID")

    if has_valid_ssid:
        print(f"[*] Đang kết nối WiFi: {ssid}...")
        sta_if.active(True)
        sta_if.disconnect()
        time.sleep(1)
        sta_if.connect(ssid, password)

        timeout = 20
        while not sta_if.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
        print()

    if sta_if.isconnected():
        print("[+] Kết nối WiFi thành công!")
        print("[+] Địa chỉ IP thiết bị:", sta_if.ifconfig()[0])

        if config.ENABLE_WEBREPL:
            try:
                import webrepl
                webrepl.start()
                print("[+] WebREPL đã sẵn sàng cho cập nhật không dây nội bộ.")
            except Exception as e:
                print("[!] Không thể khởi động WebREPL:", e)
        return True
    else:
        print("\n" + "!" * 55)
        if not has_valid_ssid:
            print("[!] Chưa có cấu hình WiFi (hoặc đang để mặc định)!")
        else:
            print("[!] Không thể kết nối WiFi. Mã trạng thái:", sta_if.status())
            print("[!] (Sai mật khẩu hoặc ngoài vùng phủ sóng)!")
        if wifi_setup_requested:
            print("[*] Đã chạy cổng cấu hình trong lần khởi động này; không mở lại.")
            print("[*] Tiếp tục khởi chạy chế độ Offline (Cảm biến hoạt động độc lập).")
            return False

        print("[*] TỰ ĐỘNG KHỞI CHẠY WIFI CAPTIVE PORTAL: 'SaoPhoi-Setup'...")
        print("!" * 55 + "\n")

        try:
            import wifi_manager
            # Khởi chạy cổng cấu hình trong 180 giây (3 phút)
            wifi_manager.start_portal(timeout_sec=180)
        except Exception as e:
            print("[!] Không thể chạy WiFi Manager:", e)
        finally:
            sys.modules.pop("wifi_manager", None)
            if "wifi_manager" in locals():
                del wifi_manager
            gc.collect()

        print("[*] Tiếp tục khởi chạy chế độ Offline (Cảm biến hoạt động độc lập).")
        return False

# Thực hiện kết nối
connect_wifi()
del connect_wifi, button_pin, startup_check_start, wifi_setup_requested, sys
gc.collect()
