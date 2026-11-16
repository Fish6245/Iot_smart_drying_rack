# ==============================================================================
# wifi_manager.py - Tr&#236;nh Qu&#7843;n l&#253; WiFi & C&#7893;ng C&#7845;u h&#236;nh Captive Portal V2.0
# WeMos D1 R2 / ESP8266 - MicroPython
#
# Ch&#7913;c n&#259;ng:
#   1. Ph&#225;t WiFi Access Point m&#7903;: 'SaoPhoi-Setup' (IP: 192.168.4.1)
#   2. DNS redirect on port 53
#   3. Nh&#7853;p SSID v&#224; m&#7853;t kh&#7849;u WiFi th&#7911; c&#244;ng (gi&#7843;m d&#249;ng RAM)
#   4. Web Server nh&#7865; (Port 80) nh&#7853;n SSID/Password v&#224; l&#432;u v&#224;o config.ini
#   5. Reboot after saving WiFi
# ==============================================================================
import gc
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

def save_wifi_to_config(ssid, password):
    """Append WiFi overrides without loading the full config into limited heap."""
    gc.collect()
    with open("config.ini", "a") as f:
        f.write('\nWIFI_SSID="{}"\n'.format(ssid))
        f.write('WIFI_PASSWORD="{}"\n'.format(password))
    print("[WiFi] Da luu WiFi vao config.ini thanh cong!")

def make_dns_reply(data, ip_str=AP_IP):
    """Reply to IPv4 (A) DNS queries with the portal address."""
    try:
        if len(data) < 17:
            return None
        tid = data[:2]
        flags = b'\x81\x80'
        idx = 12
        while idx < len(data) and data[idx] != 0:
            idx += data[idx] + 1
        idx += 5
        if idx > len(data):
            return None
        question = data[12:idx]
        qtype = data[idx - 4:idx - 2]
        qclass = data[idx - 2:idx]
        answer = b''
        if qtype == b'\x00\x01' and qclass == b'\x00\x01':
            ip_bytes = bytes([int(x) for x in ip_str.split('.')])
            answer = b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04' + ip_bytes
        counts = b'\x00\x01' + (b'\x00\x01' if answer else b'\x00\x00') + b'\x00\x00\x00\x00'
        return tid + flags + counts + question + answer
    except Exception:
        return None

def send_http_response(client, body, status="200 OK"):
    body_bytes = body.encode("utf-8")
    headers = (
        "HTTP/1.1 " + status + "\r\n"
        "Content-Type: text/html; charset=UTF-8\r\n"
        "Content-Length: " + str(len(body_bytes)) + "\r\n"
        "Connection: close\r\n\r\n"
    )
    client.sendall(headers.encode("utf-8"))
    client.sendall(body_bytes)
    client.close()

def read_http_body(client, request, header_end):
    headers = request[:header_end].split(b"\r\n")
    content_length = None
    for line in headers:
        if line.lower().startswith(b"content-length:"):
            content_length = int(line.split(b":", 1)[1].strip())
            break

    body = bytearray(request[header_end + 4:])
    if content_length is None:
        return body.decode("utf-8", "ignore")
    if content_length > 512:
        raise ValueError("HTTP form body is too large")
    if len(body) > content_length:
        del body[content_length:]

    while len(body) < content_length:
        chunk = client.recv(min(256, content_length - len(body)))
        if not chunk:
            raise ValueError("Incomplete HTTP form body")
        body.extend(chunk)
    return body.decode("utf-8", "ignore")

def read_http_headers(client, max_header_size=1024):
    request = bytearray()
    header_end = -1
    while header_end < 0:
        if len(request) >= max_header_size:
            raise ValueError("HTTP headers exceed size limit")
        chunk = client.recv(min(256, max_header_size - len(request)))
        if not chunk:
            raise ValueError("Incomplete HTTP headers")
        request.extend(chunk)
        header_end = request.find(b"\r\n\r\n")
    return request, header_end

def escape_html(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))

def iter_setup_page(status_msg=""):
    yield (
        "<!doctype html><html lang=vi><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>WiFi - Gian phoi</title>"
        "<style>body{font:16px sans-serif;max-width:440px;margin:20px auto;padding:12px}"
        "input,button{box-sizing:border-box;width:100%;padding:10px;margin:4px 0}"
        ".alert{color:#b00}</style>"
        "<h2>Gian phoi thong minh</h2>"
    )
    if status_msg:
        yield '<p class="alert">{}</p>'.format(status_msg)
    yield "<p>Nhap ten WiFi va mat khau:</p>"

    yield (
        "<form method=POST action=/save>"
        "<input id=ssid name=ssid placeholder='WiFi SSID' required>"
        "<input id=password name=password type=password placeholder='Password'>"
        "<button type=submit>Luu WiFi va khoi dong lai</button></form>"
        "<p><a href=/skip>Bo qua, chay offline</a></p></html>"
    )

def send_setup_page(client, status_msg=""):
    gc.collect()
    content_length = 0
    for part in iter_setup_page(status_msg):
        content_length += len(part.encode("utf-8"))
    gc.collect()

    headers = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=UTF-8\r\n"
        "Content-Length: " + str(content_length) + "\r\n"
        "Connection: close\r\n\r\n"
    )
    client.sendall(headers.encode("utf-8"))
    for part in iter_setup_page(status_msg):
        client.sendall(part.encode("utf-8"))
    client.close()

def render_success_html(ssid):
    return (
        "<!doctype html><html lang=vi><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>Da luu WiFi</title><h2>Da luu WiFi!</h2>"
        "<p>Dang ket noi vao mang: <strong>{}</strong>.</p>"
        "<p>Thiet bi se khoi dong lai.</p></html>"
    ).format(escape_html(ssid))

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

    gc.collect()
    ap_if = network.WLAN(network.AP_IF)

    ap_if.active(True)
    ap_if.config(essid=AP_SSID, authmode=network.AUTH_OPEN)
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
                req_bytes, header_end = read_http_headers(client)
                req_str = req_bytes[:header_end].decode('utf-8', 'ignore')
                lines = req_str.split("\r\n")
                first_line = lines[0] if lines else ""
                parts = first_line.split(" ")
                method = parts[0] if len(parts) > 0 else ""
                path = parts[1] if len(parts) > 1 else "/"
                print("[WiFi] HTTP", method, path.split("?", 1)[0], "from", addr)

                # 1. X&#7917; l&#253; l&#432;u WiFi: POST /save ho&#7863;c GET /save?ssid=...
                if "POST" in method and "/save" in path:
                    body = read_http_body(client, req_bytes, header_end)

                    ssid = ""
                    password = ""
                    for param in body.split("&"):
                        if param.startswith("ssid="):
                            ssid = urldecode(param[5:])
                        elif param.startswith("password="):
                            password = urldecode(param[9:])

                    print("[WiFi] WiFi form received: SSID length={}, password length={}".format(
                        len(ssid), len(password)
                    ))
                    del body, param, req_bytes, req_str, lines, first_line, parts, header_end
                    gc.collect()
                    if ssid:
                        print("[WiFi] Saving WiFi credentials...")
                        save_wifi_to_config(ssid, password)
                        reboot_pending = True
                        reboot_target_ssid = ssid
                        resp_content = render_success_html(ssid)
                        try:
                            send_http_response(client, resp_content)
                        except OSError as e:
                            print("[WiFi] Client disconnected after saving; restarting:", e)
                        print("[WiFi] WiFi saved. Keeping setup page available briefly before restart.")
                        break
                    else:
                        send_setup_page(
                            client,
                            status_msg="Vui l&#242;ng nh&#7853;p t&#234;n WiFi!"
                        )

                # 2. X&#7917; l&#253; B&#7887; qua / Ch&#7841;y Offline
                elif "/skip" in path:
                    print("[WiFi] Ng&#432;&#7901;i d&#249;ng ch&#7885;n b&#7887; qua c&#7845;u h&#236;nh WiFi.")
                    resp = (
                        "<h3>&#272;ang chuy&#7875;n sang ch&#7871; &#273;&#7897; "
                        "Offline - Thi&#7871;t b&#7883; s&#7861;n s&#224;ng!</h3>"
                    )
                    send_http_response(client, resp)
                    break

                elif method != "GET" or path == "/favicon.ico":
                    send_http_response(client, "", "404 Not Found")

                # 3. Captive Portal probes and normal page requests
                else:
                    del req_bytes, req_str, lines, first_line, parts, header_end
                    gc.collect()
                    send_setup_page(client)

            except Exception as e:
                print("[WiFi] HTTP request error:", e)
                try:
                    client.close()
                except:
                    pass

        time.sleep_ms(20)

    if reboot_pending:
        time.sleep(4)

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
