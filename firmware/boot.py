# ==============================================================================
# boot.py - Khởi động hệ thống WeMos D1 (ESP8266) & Kết nối WiFi V2.0
# Tích hợp: Safe Boot, WiFi Captive Portal (SaoPhoi-Setup) & WebREPL
# ==============================================================================
import gc
import machine
import network
import sys
import time
import config

gc.enable()

# ------------------------------------------------------------------------------
# 1. XỬ LÝ NÚT NHẤN SW1 (D6 / GPIO 12) KHI BẬT NGUỒN
# ------------------------------------------------------------------------------
# - Nhấn giữ > 3 giây khi cắm nguồn: CƯỠNG BỨC MỞ WIFI CAPTIVE PORTAL (SaoPhoi-Setup)
# - Nhấn nhả (< 3 giây) khi cắm nguồn: CHẾ ĐỘ SAFE BOOT (Dừng code để nạp qua USB)
button_pin = machine.Pin(config.PIN_BUTTON, machine.Pin.IN)
if button_pin.value() == 0:
    t_press = time.ticks_ms()
    is_long = False
    print("[*] Phát hiện nút SW1 được bấm khi cấp nguồn...")
    while button_pin.value() == 0:
        time.sleep_ms(50)
        if time.ticks_diff(time.ticks_ms(), t_press) >= 3000:
            is_long = True
            break

    if is_long:
        print("\n" + "=" * 55)
        print("[*] NHẬN DIỆN NHẤN GIỮ > 3S LÚC KHỞI ĐỘNG -> MỞ CỔNG CẤU HÌNH WIFI!")
        print("=" * 55 + "\n")
        try:
            import wifi_manager
            wifi_manager.start_portal(timeout_sec=300)
        except Exception as e:
            print("[!] Lỗi WiFi Manager:", e)
    else:
        print("\n" + "!" * 55)
        print("[!] SAFE BOOT MODE ĐƯỢC KÍCH HOẠT!")
        print("[!] Tạm dừng nạp main.py để sửa code an toàn qua cáp USB.")
        print("!" * 55 + "\n")
        sys.exit()

# ------------------------------------------------------------------------------
# 2. KẾT NỐI WIFI VÀ TỰ ĐỘNG BẬT CAPTIVE PORTAL NẾU CHƯA CÓ MẠNG
# ------------------------------------------------------------------------------
def connect_wifi():
    """Kết nối vào mạng WiFi theo cấu hình trong .env / config.py"""
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)

    if ap_if.active():
        ap_if.active(False)

    ssid = config.WIFI_SSID
    password = config.WIFI_PASSWORD

    # Kiểm tra xem đã có cấu hình WiFi hợp lệ hay chưa
    has_valid_ssid = bool(ssid and ssid != "YOUR_WIFI_SSID")

    if has_valid_ssid:
        print(f"[*] Đang kết nối WiFi: {ssid}...")
        sta_if.active(True)
        sta_if.connect(ssid, password)

        timeout = 12  # Chờ tối đa 12 giây
        while not sta_if.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
        print()

    if sta_if.isconnected():
        print("[+] Kết nối WiFi thành công!")
        print("[+] Địa chỉ IP thiết bị:", sta_if.ifconfig()[0])

        # Kích hoạt WebREPL nội bộ (nếu có cấu hình)
        try:
            import webrepl
            webrepl.start()
            print("[+] WebREPL đã sẵn sàng cho cập nhật không dây nội bộ.")
        except Exception:
            pass
        return True
    else:
        print("\n" + "!" * 55)
        if not has_valid_ssid:
            print("[!] Chưa có cấu hình WiFi (hoặc đang để mặc định)!")
        else:
            print("[!] Không thể kết nối tới WiFi đã lưu (sai mật khẩu hoặc ngoài vùng phủ sóng)!")
        print("[*] TỰ ĐỘNG KHỞI CHẠY WIFI CAPTIVE PORTAL: 'SaoPhoi-Setup'...")
        print("!" * 55 + "\n")

        try:
            import wifi_manager
            # Khởi chạy cổng cấu hình trong 180 giây (3 phút)
            wifi_manager.start_portal(timeout_sec=180)
        except Exception as e:
            print("[!] Không thể chạy WiFi Manager:", e)

        print("[*] Tiếp tục khởi chạy chế độ Offline (Cảm biến hoạt động độc lập).")
        return False

# Thực hiện kết nối
connect_wifi()
gc.collect()
