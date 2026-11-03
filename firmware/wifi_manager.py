# ==============================================================================
# wifi_manager.py - Trình Quản lý WiFi & Cổng Cấu hình Captive Portal V2.0
# WeMos D1 R2 / ESP8266 - MicroPython
#
# Chức năng:
#   1. Phát WiFi Access Point mở: 'SaoPhoi-Setup' (IP: 192.168.4.1)
#   2. Tiny DNS Server (Port 53) điều hướng mọi truy cập -> Trang cấu hình tự bật
#   3. Quét danh sách WiFi xung quanh (SSID + RSSI)
#   4. Web Server nhẹ (Port 80) nhận SSID/Password và lưu an toàn vào .env
#   5. Tự động khởi động lại thiết bị sau khi cấu hình thành công
# ==============================================================================
import gc
import os
import time
import network
import machine
import usocket as socket

AP_SSID = "SaoPhoi-Setup"
AP_IP = "192.168.4.1"
AP_SUBNET = "255.255.255.0"

def urldecode(s):
    """Giải mã chuỗi URL encoded (hỗ trợ tiếng Việt, dấu cách, ký tự đặc biệt)"""
    if not s:
        return ""
    s = s.replace("+", " ")
    parts = s.split("%")
    res = parts[0]
    for p in parts[1:]:
        if len(p) >= 2:
            try:
                code = int(p[:2], 16)
                res += chr(code) + p[2:]
            except Exception:
                res += "%" + p
        else:
            res += "%" + p
    return res

def save_wifi_to_env(ssid, password):
    """Lưu SSID và Password vào file .env, bảo toàn các cấu hình khác (Firebase, ...)"""
    lines = []
    # Đọc nội dung hiện có nếu có
    for path in (".env", "firmware/.env", ".evn"):
        try:
            with open(path, "r") as f:
                lines = f.readlines()
            break
        except OSError:
            pass

    new_lines = []
    ssid_written = False
    pass_written = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("WIFI_SSID="):
            new_lines.append('WIFI_SSID="{}"\n'.format(ssid))
            ssid_written = True
        elif stripped.startswith("WIFI_PASSWORD="):
            new_lines.append('WIFI_PASSWORD="{}"\n'.format(password))
            pass_written = True
        else:
            new_lines.append(line)

    if not ssid_written:
        new_lines.insert(0, 'WIFI_SSID="{}"\n'.format(ssid))
    if not pass_written:
        new_lines.insert(1, 'WIFI_PASSWORD="{}"\n'.format(password))

    # Ghi đè vào .env
    with open(".env", "w") as f:
        for l in new_lines:
            f.write(l)
    print("[WiFi] Đã lưu thông tin mạng mới vào .env thành công!")

def make_dns_reply(data, ip_str=AP_IP):
    """Tạo gói tin DNS Reply điều hướng mọi domain về IP 192.168.4.1"""
    try:
        tid = data[:2]
        flags = b'\x81\x80'
        counts = b'\x00\x01\x00\x01\x00\x00\x00\x00'
        idx = 12
        while idx < len(data) and data[idx] != 0:
            idx += data[idx] + 1
        idx += 5
        question = data[12:idx]
        ip_bytes = bytes([int(x) for x in ip_str.split('.')])
        answer = b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04' + ip_bytes
        return tid + flags + counts + question + answer
    except Exception:
        return None

def scan_networks(sta_if):
    """Quét các mạng WiFi 2.4GHz xung quanh"""
    networks = []
    try:
        was_active = sta_if.active()
        if not was_active:
            sta_if.active(True)
        raw_list = sta_if.scan()
        # raw_list: [(ssid, bssid, channel, RSSI, authmode, hidden), ...]
        seen = set()
        for item in raw_list:
            ssid = item[0].decode('utf-8', 'ignore').strip()
            rssi = item[3]
            if ssid and ssid not in seen:
                seen.add(ssid)
                networks.append((ssid, rssi))
        # Sắp xếp theo cường độ sóng mạnh nhất
        networks.sort(key=lambda x: x[1], reverse=True)
    except Exception as e:
        print("[WiFi] Lỗi quét mạng:", e)
    return networks

def render_html(networks, status_msg=""):
    """Tạo trang HTML cấu hình WiFi giao diện tiếng Việt thân thiện di động"""
    options_html = ""
    for ssid, rssi in networks[:15]:
        signal = "Mạnh" if rssi > -65 else ("Vừa" if rssi > -80 else "Yếu")
        options_html += '<button type="button" class="net-btn" onclick="selectSSID(\'{}\')">📡 {} <span class="badge">{} ({}dBm)</span></button>\n'.format(
            ssid, ssid, signal, rssi
        )

    if not options_html:
        options_html = '<p class="empty-note">Không tìm thấy mạng tự động. Bạn hãy nhập tên WiFi bên dưới.</p>'

    status_html = ""
    if status_msg:
        status_html = '<div class="alert">{}</div>'.format(status_msg)

    html = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cấu hình WiFi - Giàn Phơi Thông Minh</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f4f8; color: #1e293b; padding: 16px; }
.card { max-width: 440px; margin: 0 auto; background: #ffffff; border-radius: 14px; padding: 22px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.header { text-align: center; margin-bottom: 20px; }
.icon { font-size: 2.4rem; }
h1 { font-size: 1.3rem; margin-top: 6px; color: #0f172a; }
p.desc { font-size: 0.88rem; color: #64748b; margin-top: 4px; }
.alert { background: #fee2e2; color: #b91c1c; padding: 10px; border-radius: 8px; font-size: 0.88rem; margin-bottom: 14px; text-align: center; }
.section-title { font-size: 0.92rem; font-weight: 700; color: #334155; margin: 14px 0 8px; }
.net-list { max-height: 160px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; margin-bottom: 14px; background: #f8fafc; }
.net-btn { display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 8px 10px; margin-bottom: 4px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 0.88rem; cursor: pointer; text-align: left; }
.net-btn:hover { background: #eff6ff; border-color: #3b82f6; }
.badge { font-size: 0.75rem; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
.empty-note { font-size: 0.85rem; color: #94a3b8; text-align: center; padding: 12px; }
label { display: block; font-size: 0.86rem; font-weight: 600; color: #334155; margin-bottom: 4px; }
input[type="text"], input[type="password"] { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.95rem; margin-bottom: 12px; }
input:focus { outline: none; border-color: #2563eb; ring: 2px rgba(37,99,235,0.2); }
.btn-submit { width: 100%; padding: 12px; background: #2563eb; color: #ffffff; border: none; border-radius: 8px; font-size: 1rem; font-weight: 700; cursor: pointer; margin-top: 6px; transition: background 0.2s; }
.btn-submit:hover { background: #1d4ed8; }
.btn-skip { display: block; width: 100%; text-align: center; padding: 10px; margin-top: 10px; color: #64748b; text-decoration: none; font-size: 0.88rem; font-weight: 600; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; }
.footer { text-align: center; margin-top: 18px; font-size: 0.78rem; color: #94a3b8; }
</style>
<script>
function selectSSID(name) {
  document.getElementById('ssid').value = name;
  document.getElementById('password').focus();
}
</script>
</head>
<body>
<div class="card">
  <div class="header">
    <div class="icon">🌤️</div>
    <h1>Giàn Phơi Thông Minh V2.0</h1>
    <p class="desc">Cấu hình kết nối WiFi để sạc và đồng bộ dữ liệu</p>
  </div>
  """ + status_html + """
  <div class="section-title">Danh sách WiFi xung quanh (chọn để điền):</div>
  <div class="net-list">
    """ + options_html + """
  </div>

  <form method="POST" action="/save">
    <label for="ssid">Tên mạng WiFi (SSID):</label>
    <input type="text" id="ssid" name="ssid" placeholder="Nhập hoặc bấm chọn ở trên" required>

    <label for="password">Mật khẩu WiFi:</label>
    <input type="password" id="password" name="password" placeholder="Nhập mật khẩu WiFi">

    <button type="submit" class="btn-submit">💾 Lưu WiFi & Khởi Động Lại</button>
  </form>

  <a href="/skip" class="btn-skip">⏩ Bỏ qua (Chạy Chế độ Offline Cảm biến)</a>
  <div class="footer">IP Mặc định: 192.168.4.1 | WeMos D1 MicroPython</div>
</div>
</body>
</html>"""
    return html

def render_success_html(ssid):
    return """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Đã lưu WiFi</title>
<style>
body { font-family: sans-serif; background: #f0fdf4; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 16px; text-align: center; }
.card { background: white; border-radius: 12px; padding: 28px; max-width: 400px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
h1 { color: #166534; font-size: 1.3rem; margin-bottom: 10px; }
p { color: #334155; font-size: 0.95rem; line-height: 1.6; }
.loader { width: 40px; height: 40px; border: 4px solid #e2e8f0; border-top: 4px solid #16a34a; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="card">
  <h1>✓ Đã lưu cài đặt WiFi!</h1>
  <div class="loader"></div>
  <p>Đang kết nối vào mạng: <strong>""" + ssid + """</strong>.</p>
  <p>Mạch đang tự động khởi động lại... Bạn có thể kết nối điện thoại về mạng WiFi nhà bạn và mở Web Dashboard để điều khiển.</p>
</div>
</body>
</html>"""

def start_portal(timeout_sec=180):
    """
    Kích hoạt Cổng Cấu hình Captive Portal:
    - Bật Access Point 'SaoPhoi-Setup'
    - Lắng nghe DNS (Port 53) và HTTP (Port 80)
    - Trả về True nếu đã lưu WiFi và reboot, False nếu bỏ qua / timeout.
    """
    print("\n" + "=" * 55)
    print("[*] KHỞI CHẠY WIFI CAPTIVE PORTAL (WIFI MANAGER)")
    print(f"[*] Tên WiFi AP: {AP_SSID}")
    print(f"[*] Địa chỉ IP:  {AP_IP}")
    print("=" * 55 + "\n")

    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)

    ap_if.active(True)
    ap_if.ifconfig((AP_IP, AP_SUBNET, AP_IP, AP_IP))
    ap_if.config(essid=AP_SSID, authmode=network.AUTH_OPEN)

    time.sleep(1)
    networks = scan_networks(sta_if)
    print(f"[WiFi] Đã quét thấy {len(networks)} mạng xung quanh.")

    # 1. Khởi tạo DNS Server (Port 53 UDP)
    dns_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns_sock.setblocking(False)
    try:
        dns_sock.bind((AP_IP, 53))
        print("[WiFi] DNS Server đang lắng nghe trên cổng 53 (Auto-redirect)")
    except Exception as e:
        print("[!] Không thể mở cổng DNS:", e)
        dns_sock = None

    # 2. Khởi tạo HTTP Web Server (Port 80 TCP)
    http_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    http_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    http_sock.setblocking(False)
    http_sock.bind((AP_IP, 80))
    http_sock.listen(2)
    print("[WiFi] HTTP Web Server đang lắng nghe trên cổng 80")

    start_time = time.time()
    reboot_pending = False
    reboot_target_ssid = ""

    while True:
        gc.collect()

        # Kiểm tra timeout
        if time.time() - start_time > timeout_sec:
            print("[WiFi] Hết thời gian chờ cấu hình (Timeout). Tắt AP và chạy Offline.")
            break

        # A. Xử lý yêu cầu DNS (Bắt buộc để tự bật trang đăng nhập trên điện thoại)
        if dns_sock:
            try:
                data, addr = dns_sock.recvfrom(512)
                if data:
                    reply = make_dns_reply(data, AP_IP)
                    if reply:
                        dns_sock.sendto(reply, addr)
            except Exception:
                pass

        # B. Xử lý yêu cầu HTTP
        try:
            client, addr = http_sock.accept()
        except Exception:
            client = None

        if client:
            try:
                client.settimeout(2.0)
                req_bytes = client.recv(1024)
                req_str = req_bytes.decode('utf-8', 'ignore') if req_bytes else ""
                lines = req_str.split("\r\n")
                first_line = lines[0] if lines else ""
                parts = first_line.split(" ")
                method = parts[0] if len(parts) > 0 else ""
                path = parts[1] if len(parts) > 1 else "/"

                # 1. Xử lý lưu WiFi: POST /save hoặc GET /save?ssid=...
                if "POST" in method and "/save" in path:
                    # Đọc body của POST
                    body = req_str.split("\r\n\r\n")[-1] if "\r\n\r\n" in req_str else ""
                    # Nếu body bị cắt, đọc thêm
                    if "ssid=" not in body:
                        try:
                            extra = client.recv(512)
                            body += extra.decode('utf-8', 'ignore')
                        except:
                            pass

                    ssid = ""
                    password = ""
                    for param in body.split("&"):
                        if param.startswith("ssid="):
                            ssid = urldecode(param[5:])
                        elif param.startswith("password="):
                            password = urldecode(param[9:])

                    if ssid:
                        save_wifi_to_env(ssid, password)
                        resp_content = render_success_html(ssid)
                        resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nConnection: close\r\n\r\n" + resp_content
                        client.sendall(resp.encode('utf-8'))
                        client.close()
                        reboot_pending = True
                        reboot_target_ssid = ssid
                        break
                    else:
                        resp_content = render_html(networks, status_msg="Vui lòng nhập tên WiFi!")
                        resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nConnection: close\r\n\r\n" + resp_content
                        client.sendall(resp.encode('utf-8'))
                        client.close()

                # 2. Xử lý Bỏ qua / Chạy Offline
                elif "/skip" in path:
                    print("[WiFi] Người dùng chọn bỏ qua cấu hình WiFi.")
                    resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nConnection: close\r\n\r\n"
                    resp += "<h3>Đang chuyển sang chế độ Offline... Thiết bị sẵn sàng!</h3>"
                    client.sendall(resp.encode('utf-8'))
                    client.close()
                    break

                # 3. Yêu cầu bình thường hoặc Captive Portal redirect
                else:
                    resp_content = render_html(networks)
                    resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nConnection: close\r\n\r\n" + resp_content
                    client.sendall(resp.encode('utf-8'))
                    client.close()

            except Exception as e:
                try:
                    client.close()
                except:
                    pass

        time.sleep_ms(20)

    # Dọn dẹp tài nguyên
    if dns_sock:
        try:
            dns_sock.close()
        except:
            pass
    try:
        http_sock.close()
    except:
        pass

    ap_if.active(False)
    gc.collect()

    if reboot_pending:
        print(f"[WiFi] Chuẩn bị khởi động lại để kết nối WiFi: {reboot_target_ssid}...")
        time.sleep(2)
        machine.reset()
        return True

    return False

