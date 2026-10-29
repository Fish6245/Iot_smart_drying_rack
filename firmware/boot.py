# ==============================================================================
# boot.py - Khởi động hệ thống WeMos D1 (ESP8266) & Kết nối WiFi
# Tích hợp chế độ Safe Boot (Chống Brick) và WebREPL (OTA nội bộ)
# ==============================================================================
import gc
import machine
import network
import sys
import time
import config

gc.enable()

# ------------------------------------------------------------------------------
# 1. CHẾ ĐỘ SAFE BOOT (CHỐNG BRICK PHẦN CỨNG)
# ------------------------------------------------------------------------------
# Nếu người dùng nhấn giữ nút SW1 (D6 / GPIO 12) trong lúc cắm nguồn hoặc bấm RST:
# Hệ thống sẽ KHÔNG chạy main.py, giúp tránh vòng lặp khởi động vô tận (bootloop)
# và cho phép nạp lại firmware an toàn qua cáp USB hoặc WebREPL.
button_pin = machine.Pin(config.PIN_BUTTON, machine.Pin.IN)
if button_pin.value() == 0:
    print("\n" + "!" * 55)
    print("[!] SAFE BOOT MODE ĐƯỢC KÍCH HOẠT!")
    print("[!] Phát hiện nút SW1 được nhấn giữ trong khi khởi động.")
    print("[!] Tạm dừng nạp main.py để đảm bảo an toàn.")
    print("[!] Bạn có thể sửa file hoặc nạp lại code qua USB (Thonny/uPyCraft).")
    print("!" * 55 + "\n")
    sys.exit()

# ------------------------------------------------------------------------------
# 2. KẾT NỐI WIFI
# ------------------------------------------------------------------------------
def connect_wifi():
    """Kết nối vào mạng WiFi theo cấu hình trong config.py / .env"""
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    
    # Tắt Access Point để tiết kiệm RAM & tránh xung đột
    if ap_if.active():
        ap_if.active(False)
        
    if not sta_if.isconnected():
        print(f"[*] Đang kết nối WiFi: {config.WIFI_SSID}...")
        sta_if.active(True)
        sta_if.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        
        timeout = 15  # Tối đa 15 giây
        while not sta_if.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
        print()

    if sta_if.isconnected():
        print("[+] Kết nối WiFi thành công!")
        print("[+] Địa chỉ IP thiết bị:", sta_if.ifconfig()[0])
        
        # 3. KÍCH HOẠT WEBREPL (NẾU CÓ CẤU HÌNH TRONG MICROPYTHON)
        # Cho phép kéo thả nạp file qua mạng WiFi nội bộ không cần Internet
        try:
            import webrepl
            webrepl.start()
            print("[+] WebREPL đã sẵn sàng cho cập nhật không dây nội bộ.")
        except Exception:
            pass
    else:
        print("[!] Không thể kết nối WiFi. Thiết bị sẽ chạy offline với cảm biến.")

# Thực hiện kết nối
connect_wifi()
gc.collect()
