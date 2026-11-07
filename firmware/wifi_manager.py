# ==============================================================================
# wifi_manager.py - Tr&#236;nh Qu&#7843;n l&#253; WiFi & C&#7893;ng C&#7845;u h&#236;nh Captive Portal V2.0
# WeMos D1 R2 / ESP8266 - MicroPython
#
# Ch&#7913;c n&#259;ng:
#   1. Ph&#225;t WiFi Access Point m&#7903;: 'SaoPhoi-Setup' (IP: 192.168.4.1)
#   2. DNS redirect on port 53
#   3. Qu&#233;t danh s&#225;ch WiFi xung quanh (SSID + RSSI)
#   4. Web Server nh&#7865; (Port 80) nh&#7853;n SSID/Password v&#224; l&#432;u an to&#224;n v&#224;o .env
#   5. Reboot after saving WiFi
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
    """Decode URL-encoded values."""
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
    """Save WiFi credentials without replacing other settings."""
    lines = []
    # &#272;&#7885;c n&#7897;i dung hi&#7879;n c&#243; n&#7871;u c&#243;
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

    # Ghi &#273;&#232; v&#224;o .env
    with open(".env", "w") as f:
        for l in new_lines:
            f.write(l)
    print("[WiFi] &#272;&#227; l&#432;u th&#244;ng tin m&#7841;ng m&#7899;i v&#224;o .env th&#224;nh c&#244;ng!")

def make_dns_reply(data, ip_str=AP_IP):
    """T&#7841;o g&#243;i tin DNS Reply &#273;i&#7873;u h&#432;&#7899;ng m&#7885;i domain v&#7873; IP 192.168.4.1"""
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
    """Qu&#233;t c&#225;c m&#7841;ng WiFi 2.4GHz xung quanh"""
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
        # S&#7855;p x&#7871;p theo c&#432;&#7901;ng &#273;&#7897; s&#243;ng m&#7841;nh nh&#7845;t
        networks.sort(key=lambda x: x[1], reverse=True)
    except Exception as e:
        print("[WiFi] L&#7895;i qu&#233;t m&#7841;ng:", e)
    return networks

def render_html(networks, status_msg=""):
    """Render the WiFi setup page."""
    options_html = ""
    for ssid, rssi in networks[:15]:
        signal = "M&#7841;nh" if rssi > -65 else ("V&#7915;a" if rssi > -80 else "Y&#7871;u")
        options_html += (
            '<button class="net" type="button" onclick="selectSSID(\'{}\')">'
            '{} ({} dBm) - {}</button>'
        ).format(ssid, ssid, rssi, signal)

    if not options_html:
        options_html = "<p>Kh&#244;ng t&#236;m th&#7845;y WiFi.</p>"

    status_html = '<p class="alert">{}</p>'.format(status_msg) if status_msg else ""
    return (
        "<!doctype html><html lang=vi><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>WiFi - Gian phoi</title>"
        "<style>body{{font:16px sans-serif;max-width:440px;margin:20px auto;padding:12px}}"
        "input,button{{box-sizing:border-box;width:100%;padding:10px;margin:4px 0}}"
        ".net{{display:block}}.alert{{color:#b00}}</style>"
        "<script>function selectSSID(s){{document.getElementById('ssid').value=s;"
        "document.getElementById('password').focus()}}</script>"
        "<h2>Gian phoi thong minh</h2>{}"
        "<p>Chon WiFi hoac nhap ten mang:</p>{}"
        "<form method=POST action=/save>"
        "<input id=ssid name=ssid placeholder='WiFi SSID' required>"
        "<input id=password name=password type=password placeholder='Password'>"
        "<button type=submit>Luu WiFi va khoi dong lai</button></form>"
        "<p><a href=/skip>Bo qua, chay offline</a></p></html>"
    ).format(status_html, options_html)

def render_success_html(ssid):
    return (
        "<!doctype html><html lang=vi><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>Da luu WiFi</title><h2>Da luu WiFi!</h2>"
        "<p>Dang ket noi vao mang: <strong>{}</strong>.</p>"
        "<p>Thiet bi se khoi dong lai.</p></html>"
    ).format(ssid)

def start_portal(timeout_sec=180):
    """
    K&#237;ch ho&#7841;t C&#7893;ng C&#7845;u h&#236;nh Captive Portal:
    - B&#7853;t Access Point 'SaoPhoi-Setup'
    - L&#7855;ng nghe DNS (Port 53) v&#224; HTTP (Port 80)
    - Returns True after saving WiFi, False on skip or timeout.
    """
    print("\n" + "=" * 55)
    print("[*] KH&#7902;I CH&#7840;Y WIFI CAPTIVE PORTAL (WIFI MANAGER)")
    print(f"[*] T&#234;n WiFi AP: {AP_SSID}")
    print(f"[*] &#272;&#7883;a ch&#7881; IP:  {AP_IP}")
    print("=" * 55 + "\n")

    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)

    time.sleep(1)
    networks = scan_networks(sta_if)
    print(f"[WiFi] &#272;&#227; qu&#233;t th&#7845;y {len(networks)} m&#7841;ng xung quanh.")
    sta_if.active(False)

    ap_if.config(essid=AP_SSID, authmode=network.AUTH_OPEN)
    ap_if.active(True)
    ap_if.ifconfig((AP_IP, AP_SUBNET, AP_IP, AP_IP))

    # 1. Kh&#7903;i t&#7841;o DNS Server (Port 53 UDP)
    dns_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns_sock.setblocking(False)
    try:
        dns_sock.bind((AP_IP, 53))
        print("[WiFi] DNS Server &#273;ang l&#7855;ng nghe tr&#234;n c&#7893;ng 53 (Auto-redirect)")
    except Exception as e:
        print("[!] Kh&#244;ng th&#7875; m&#7903; c&#7893;ng DNS:", e)
        dns_sock = None

    # 2. Kh&#7903;i t&#7841;o HTTP Web Server (Port 80 TCP)
    http_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    http_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    http_sock.setblocking(False)
    http_sock.bind((AP_IP, 80))
    http_sock.listen(2)
    print("[WiFi] HTTP Web Server &#273;ang l&#7855;ng nghe tr&#234;n c&#7893;ng 80")

    start_time = time.time()
    reboot_pending = False
    reboot_target_ssid = ""

    while True:
        gc.collect()

        # Ki&#7875;m tra timeout
        if time.time() - start_time > timeout_sec:
            print("[WiFi] Setup timed out; disabling AP.")
            break

        # A. Handle DNS requests.
        if dns_sock:
            try:
                data, addr = dns_sock.recvfrom(512)
                if data:
                    reply = make_dns_reply(data, AP_IP)
                    if reply:
                        dns_sock.sendto(reply, addr)
            except Exception:
                pass

        # B. X&#7917; l&#253; y&#234;u c&#7847;u HTTP
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

                # 1. X&#7917; l&#253; l&#432;u WiFi: POST /save ho&#7863;c GET /save?ssid=...
                if "POST" in method and "/save" in path:
                    # &#272;&#7885;c body c&#7911;a POST
                    body = req_str.split("\r\n\r\n")[-1] if "\r\n\r\n" in req_str else ""
                    # N&#7871;u body b&#7883; c&#7855;t, &#273;&#7885;c th&#234;m
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
                        resp = (
                            "HTTP/1.1 200 OK\r\nContent-Type: text/html; "
                            "charset=UTF-8\r\nConnection: close\r\n\r\n"
                        ) + resp_content
                        client.sendall(resp.encode("utf-8"))
                        client.close()
                        reboot_pending = True
                        reboot_target_ssid = ssid
                        break
                    else:
                        resp_content = render_html(networks, status_msg="Vui l&#242;ng nh&#7853;p t&#234;n WiFi!")
                        resp = (
                            "HTTP/1.1 200 OK\r\nContent-Type: text/html; "
                            "charset=UTF-8\r\nConnection: close\r\n\r\n"
                        ) + resp_content
                        client.sendall(resp.encode('utf-8'))
                        client.close()

                # 2. X&#7917; l&#253; B&#7887; qua / Ch&#7841;y Offline
                elif "/skip" in path:
                    print("[WiFi] Ng&#432;&#7901;i d&#249;ng ch&#7885;n b&#7887; qua c&#7845;u h&#236;nh WiFi.")
                    resp = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=UTF-8\r\nConnection: close\r\n\r\n"
                    resp += (
                        "<h3>&#272;ang chuy&#7875;n sang ch&#7871; &#273;&#7897; "
                        "Offline - Thi&#7871;t b&#7883; s&#7861;n s&#224;ng!</h3>"
                    )
                    client.sendall(resp.encode('utf-8'))
                    client.close()
                    break

                # 3. Y&#234;u c&#7847;u b&#236;nh th&#432;&#7901;ng ho&#7863;c Captive Portal redirect
                else:
                    resp_content = render_html(networks)
                    resp = (
                        "HTTP/1.1 200 OK\r\nContent-Type: text/html; "
                        "charset=UTF-8\r\nConnection: close\r\n\r\n"
                    ) + resp_content
                    client.sendall(resp.encode('utf-8'))
                    client.close()

            except Exception as e:
                try:
                    client.close()
                except:
                    pass

        time.sleep_ms(20)

    # D&#7885;n d&#7865;p t&#224;i nguy&#234;n
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
        print("[WiFi] Rebooting to connect to: {}".format(reboot_target_ssid))
        time.sleep(2)
        machine.reset()
        return True

    return False
