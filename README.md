# 🌤️ Hệ Thống IoT Sào Phơi Đồ Thông Minh
> **Vi điều khiển trung tâm:** WeMos D1 R2 (ESP8266)<br>
> **Môi trường phát triển Firmware:** uPyCraft IDE / Thonny (MicroPython)<br>
> **Cơ sở dữ liệu thời gian thực:** Firebase Realtime Database<br>
> **Quản lý phiên bản & Cập nhật từ xa (OTA):** GitHub Repository (REST API / Raw Content)<br>
> **Giao diện người dùng (Frontend):** Ứng dụng đơn trang (SPA) HTML5, CSS3, Vanilla JavaScript (ES6+), tích hợp **Chart.js** và **Open-Meteo Weather API**.

---

## 📁 1. Cấu Trúc Thư Mục Dự Án

```text
Iot_smart_drying_rack/
├── version.json             # Version phát hành để WebApp và firmware kiểm tra OTA
├── firmware/                # Mã nguồn MicroPython chạy trên WeMos D1 R2
│   ├── boot.py              # Kết nối WiFi, mở captive portal khi cần
│   ├── config.py            # Cấu hình GPIO, cảm biến, Firebase và nguồn OTA
│   ├── main.py              # Điểm vào firmware, khai báo FIRMWARE_VERSION
│   ├── main_setup.py        # Khởi tạo phần cứng và trạng thái hệ thống
│   ├── main_loop.py         # Vòng điều khiển chính
│   ├── main_io.py           # Nút nhấn và đọc cảm biến
│   ├── main_control.py      # Logic AUTO/MANUAL và điều khiển servo
│   ├── main_sync.py         # Đồng bộ lệnh/cấu hình Firebase
│   ├── main_firebase.py     # Giao tiếp Firebase và telemetry
│   ├── main_periodic.py     # Thống kê phơi và lịch sử định kỳ
│   ├── wifi_manager.py      # Cổng cấu hình WiFi Captive Portal (SaoPhoi-Setup 192.168.4.1)
│   ├── ads1x15.py           # Driver I2C đọc ADC ADS1115 (16-bit)
│   └── ota.py               # Tải/cài firmware OTA
├── webapp/                  # Bảng điều khiển Web Dashboard SPA
│   ├── index.html           # Khung giao diện gồm 4 tab
│   ├── style.css            # Định dạng Responsive Dashboard hiện đại
│   ├── config.js            # Nạp cấu hình Firebase & GitHub cho WebApp
│   ├── .env                 # Cấu hình Firebase cục bộ; không commit
│   └── app.js               # Logic Firebase v10, Chart.js, Open-Meteo & GitHub OTA
└── README.md                # Tài liệu kỹ thuật và hướng dẫn
```

WebApp đọc `FIREBASE_API_KEY`, `FIREBASE_DATABASE_URL` và `FIREBASE_PROJECT_ID` từ `webapp/.env` qua HTTP. `.env` bị Git bỏ qua nên cần tự tạo trên máy hoặc cấu hình qua tab Cài đặt. Với hosting tĩnh như GitHub Pages, file bị ignore này không được deploy; hãy cấu hình Firebase trong tab Cài đặt. Dù dùng `.env`, các giá trị gửi tới trình duyệt vẫn xem được; không lưu secret quản trị/service account tại đây. Bảo vệ dữ liệu bằng Firebase Security Rules.

---

## 🔌 2. Ánh Xạ Phần Cứng & Sơ Đồ Chân (Pinout Mapping)

| Thành phần linh kiện | Kết nối trên sơ đồ nguyên lý | Chân GPIO (ESP8266) | Đường dẫn (Key) trên Firebase |
| :--- | :--- | :--- | :--- |
| **Module ADC ADS1115 (16-Bit)** | `D1_SCL` (Chân 15), `D2_SDA` (Chân 16), `ADDR` nối `GND` (`0x48`) | `GPIO 5` (SCL), `GPIO 4` (SDA) | `/smart_clothesline/telemetry` |
| **Cảm biến mưa / nước (SEN1)** | Chân tín hiệu `S` nối kênh `A2` của ADS1115 (`WATER_A2`) | Giao tiếp I2C (Kênh 02) | `/smart_clothesline/telemetry/water_a0` & `/smart_clothesline/telemetry/is_raining` |
| **Quang trở LDR1** | Phân áp qua trở `R2 (10k)` nối kênh `A1` của ADS1115 (`LDR_A1`) | Giao tiếp I2C (Kênh 1) | `/smart_clothesline/telemetry/ldr_a1` & `/smart_clothesline/telemetry/is_sunny` |
| **Cảm biến nhiệt ẩm DHT11** | Chân `Out` nối chân `D4_LED` (`DHT11_D4`) | `GPIO 2` | `/smart_clothesline/telemetry/temperature`, `/smart_clothesline/telemetry/humidity` |
| **Nút nhấn cơ học (SW1)** | Trở kéo lên `R1 (10k)` lên `3V3`, nối vào `D6_MISO` (`BUTTON_D6`) | `GPIO 12` (Ngắt ngoài - IRQ) | `/smart_clothesline/control/manual_command` |
| **Động cơ Servo SG90 (M1)** | Nguồn `5V` (lọc nhiễu tụ `C1 100uF`), xung PWM nối `D7_MOSI` (`SERVO_D7`) | `GPIO 13` (PWM 50 Hz) | `/smart_clothesline/control/servo_angle`, `/smart_clothesline/telemetry/clothesline_state` |

---

## 🗄️ 3. Cấu Trúc Dữ Liệu Firebase

```json
{
  "smart_clothesline": {
    "telemetry": {
      "temperature": 32.4,
      "humidity": 62.0,
      "water_a0": 500,
      "is_raining": true,
      "ldr_a1": 3000,
      "is_sunny": true,
      "is_humid": false,
      "clothesline_state": "CLOSED",
      "firmware_version": "3.2.0",
      "sun_minutes_today": 245,
      "sun_seconds_remainder": 0,
      "sun_minutes_date": "2026-11-16",
      "last_updated": 1730530000
    },
    "control": {
      "mode": "AUTO",
      "manual_command": "NONE",
      "servo_angle": 90,
      "rain_threshold": 2000,
      "sun_threshold": 2000,
      "humidity_threshold": 80
    },
    "schedule": {
      "auto_schedule_enabled": true,
      "open_time": "07:00",
      "close_time": "18:00",
      "rain_priority_override": true
    },
    "maintenance": {
      "target_version": "3.2.0",
      "trigger_ota": false,
      "trigger_reset": false,
      "ota_status": "IDLE"
    },
    "history": {
      "1730526400": {
        "temp": 31.0,
        "hum": 65.0,
        "water_a0": 500,
        "ldr_a1": 3000
      }
    }
  }
}
```

Firmware báo phiên bản đang chạy ở `telemetry.firmware_version`. `maintenance.current_version` cũ có thể còn trong Firebase sau OTA; firmware hiện không cập nhật trường này khi khởi động, nên không dùng nó làm nguồn version hiện hành.

---

## 🖥️ 4. Giao Diện Web (4 Tab SPA)

1. **Trang 1: Trang Tổng quan (Overview Dashboard):**
   - Trạng thái sào phơi: ĐANG MỞ / ĐANG THU; chọn **Tự động/Thủ công** bên dưới nút thu/mở. Nút thu/mở cũng tự chuyển sang thủ công.
   - Xác thực thời tiết tại chỗ: Thẻ báo Có mưa / Không mưa (`WATER_A2`) và Có nắng / Không nắng (`LDR_A1`).
   - Tích hợp **Open-Meteo Weather API**: Nhiệt độ ngoài trời, lượng mưa, tốc độ gió và độ ẩm khu vực.
   - 4 thẻ cảm biến thời gian thực: Cảm biến nước A2, Quang trở LDR A1, Nhiệt độ và Độ ẩm DHT11.
   - Điều khiển servo, chọn AUTO/MANUAL và xem telemetry cảm biến.

2. **Tab 2: Biểu đồ và Lịch sử (Charts & Analytics):**
   - Thống kê thời gian phơi đồ trong ngày: Tổng số giờ, phút sào phơi ở trạng thái `OPEN`.
   - Bộ lọc khung thời gian: 12 mốc (~1 giờ), 36 mốc (~3 giờ), 72 mốc (~6 giờ).
   - Biểu đồ **Chart.js** trực quan: Biểu đồ biến thiên Nhiệt độ - Độ ẩm và biểu đồ cảm biến Nước A2 - Quang trở LDR A1.

3. **Tab 3: Cài đặt và Hẹn giờ (Settings & Schedule):**
   - Cài đặt giờ mở sào (mặc định `07:00`), giờ thu sào (mặc định `18:00`), công tắc Bật/Tắt lịch trình.
   - Khi bật lịch, sào mở trong khung giờ và thu ngoài khung giờ; `rain_priority_override` bật thì mưa/ẩm cao cũng thu sào trong giờ phơi. Khi tắt lịch, AUTO bỏ qua giờ: khô ráo thì mở, mưa hoặc ẩm cao thì thu.
   - Hiệu chuẩn ngưỡng cảm biến mưa (`rain_threshold`, mặc định 2000), ngưỡng nắng (`sun_threshold`, mặc định 2000) và độ ẩm (`humidity_threshold`, mặc định 80%).
   - Cấu hình thông số kết nối Firebase RTDB & GitHub Repository trực tiếp trên giao diện.

4. **Tab 4: Bảo trì:** Kiểm tra version GitHub, gửi yêu cầu OTA qua Firebase và gửi lệnh reset thiết bị.

5. **🛠️ Dev Simulator Bar (Công cụ mô phỏng & kiểm thử ngoại vi):**
   - **Kịch bản nhanh (Quick Scenarios):** ☀️ Nắng to (Phơi đồ), 🌧️ Đổ mưa (Thu sào khẩn cấp), 🌥️ Râm mát / Tối, 🌙 Đêm khuya.
   - **Thanh trượt điều khiển thủ công:** Cảm biến Nước A2 (ADS1115), Quang trở LDR A1, Nhiệt độ và Độ ẩm DHT11.
   - **2 chế độ kiểm thử:**
     - `Local Mock`: Cập nhật trực tiếp lên giao diện Dashboard & Biểu đồ mà không cần Firebase/mạng.
     - `Firebase Sync`: Ghi telemetry giả lập vào `/smart_clothesline/telemetry`. Lệnh này không điều khiển servo hay thay thế các lệnh điều khiển firmware.
   - **Tự động sinh dữ liệu (Auto-drift):** Tự động phát sinh dao động cảm biến mỗi 3 giây để vẽ đường biểu đồ thời gian thực.
   - **Nút ghi lịch sử (Push History Record):** Thêm 1 điểm dữ liệu tức thì vào biểu đồ Chart.js.

---

## ⚡ 5. Quy Tắc Ưu Tiên Xử Lý Trên Firmware (MicroPython)

1. **Đồng bộ thời gian thực qua NTP (`ntptime`):**
   - Tự động đồng bộ thời gian từ máy chủ NTP sau khi kết nối Wi-Fi, cộng độ lệch múi giờ Việt Nam ($\text{UTC}+7 = +25200\text{s}$) để so khớp giờ mở/thu sào và tự động đặt lại `sun_minutes_today` về 0 lúc `00:00`.
2. **Hai mode điều khiển Servo SG90:**
   - Mặc định sau khi khởi động/reset board là `AUTO`; khi bật lịch, sào theo giờ mở/thu và `rain_priority_override` quyết định có thu vì mưa/ẩm trong giờ phơi hay không. Khi tắt lịch, AUTO bỏ qua giờ và chỉ dựa vào thời tiết: khô ráo thì mở, mưa hoặc ẩm cao thì thu.
   - Chọn `MANUAL` trên Web hoặc nhấn SW1 (D6) để chuyển sang thủ công. Nút **Mở sào** / **Thu sào** chuyển sang thủ công và áp dụng đúng trạng thái đã chọn; mode thủ công không bị lịch hay thời tiết ghi đè.
   - Reset board đặt `mode = "AUTO"` và `manual_command = "NONE"` trên Firebase để không khôi phục lệnh thủ công cũ.
3. **Thống kê & Ghi nhận lịch sử:**
   - Thống kê số phút sào `OPEN` theo thời gian đã trôi qua; đồng bộ thống kê khi dữ liệu ngày đã được khôi phục từ Firebase.
   - Mỗi 5 phút: ghi một bản ghi vào `/smart_clothesline/history/<timestamp>`.
4. **Cơ chế bảo trì từ xa:**
   - Khi `trigger_reset == True`: Reset mạch từ xa qua `machine.reset()`.
   - Khi `trigger_ota == True`: Tải các module được hardcode trong `firmware/ota.py` và `main.py` từ cùng thư mục firmware trên GitHub Raw, rồi reset sau khi hoàn tất. Danh sách `files` trong `version.json` hiện chỉ là metadata, không quyết định file OTA tải.
   - OTA hiện thay từng file ngay sau khi tải; không có rollback nguyên bộ nếu tải giữa chừng thất bại. Chỉ phát hành từ nhánh đã có đủ các file firmware tương thích.
   - Firmware tự kiểm tra OTA lúc boot chỉ khi `CHECK_GITHUB_OTA_ON_BOOT=1`; mặc định là tắt. Khi bật, code hiện coi mọi version khác nhau là cần cập nhật, kể cả version thấp hơn, nên không bật nếu nhánh OTA có thể thấp version hơn thiết bị.
   - WebApp và firmware có cấu hình GitHub branch riêng. Đảm bảo WebApp kiểm tra cùng nhánh mà firmware tải (firmware đọc `GITHUB_BRANCH` từ cấu hình thiết bị).

Mỗi lần phát hành, cập nhật `FIRMWARE_VERSION` trong `firmware/main.py` và `version` trong `version.json` thành cùng giá trị. `main.py` gán version vào `config.CURRENT_VERSION` để các module firmware đang dùng chung đọc được.

---

## 📡 6. Cổng Cấu Hình WiFi Thông Minh (WiFi Captive Portal)

Đối với người dùng mới hoặc khi mang thiết bị sang môi trường WiFi khác:
1. **Kích hoạt chủ động:** Cấp nguồn hoặc nhấn RST, sau đó nhấn SW1 (D6) trong 3 giây đầu khởi động. Khi nhận nút, Access Point bật trong 3 phút:
   - **Tên WiFi:** `SaoPhoi-Setup` (mở, không cần mật khẩu).
   - **Địa chỉ IP:** `192.168.4.1` (DNS redirect giúp thiết bị di động mở trang cấu hình; nếu không tự hiện, mở địa chỉ này trên trình duyệt).
2. **Tự động kích hoạt:** Nếu không yêu cầu cấu hình bằng D6 và mạch không kết nối được WiFi sau 20 giây, AP cấu hình tự bật trong 3 phút. Nếu D6 đã mở AP nhưng hết giờ, board thử kết nối bằng thông tin WiFi đã lưu và không mở AP lần hai trong cùng lần khởi động.
3. **Thao tác người dùng:**
   - Kết nối điện thoại vào WiFi `SaoPhoi-Setup`.
   - Nhập SSID và mật khẩu WiFi nhà bạn. Trang hiện không quét/liệt kê các mạng WiFi.
   - Bấm **"Lưu WiFi & Khởi Động Lại"**. Mạch lưu WiFi vào `config.ini` để dễ xem/chỉnh sửa trong uPyCraft. Các thiết lập khác trong file được giữ nguyên và cấu hình đã lưu được dùng sau mỗi lần reset.
