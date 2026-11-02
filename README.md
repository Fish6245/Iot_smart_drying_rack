# 🌤️ Hệ Thống IoT Sào Phơi Đồ Thông Minh (Smart Clothesline V2.0)
> **Vi điều khiển trung tâm:** WeMos D1 R2 (ESP8266)  
> **Môi trường phát triển Firmware:** uPyCraft IDE / Thonny (MicroPython)  
> **Cơ sở dữ liệu thời gian thực:** Google Firebase Realtime Database (Schema V2.0)  
> **Quản lý phiên bản & Cập nhật từ xa (OTA):** GitHub Repository (REST API / Raw Content)  
> **Giao diện người dùng (Frontend):** Ứng dụng đơn trang (SPA) 3 phân khu thuần HTML5, CSS3, Vanilla JavaScript (ES6+), tích hợp **Chart.js** và **Open-Meteo Weather API**.

---

## 📁 1. Cấu Trúc Thư Mục Dự Án

```text
Iot_smart_drying_rack/
├── version.json             # Định danh phiên bản V2.0 phục vụ GitHub OTA
├── firmware/                # Mã nguồn MicroPython chạy trên WeMos D1 R2
│   ├── boot.py              # Safe Boot chống brick, kết nối WiFi & WebREPL
│   ├── config.py            # Cấu hình chân GPIO, ngưỡng cảm biến, WiFi & Firebase V2.0
│   ├── ads1x15.py           # Driver I2C đọc ADC ADS1115 (16-bit)
│   ├── ota.py               # Quản lý cập nhật OTA qua nhánh maintenance & GitHub Raw
│   └── main.py              # Luồng xử lý V2.0: NTP UTC+7, ưu tiên mưa, hẹn giờ, lịch sử
├── webapp/                  # Bảng điều khiển Web Dashboard SPA 3 Trang
│   ├── index.html           # Khung giao diện SPA 3 phân khu
│   ├── style.css            # Định dạng Responsive Dashboard hiện đại
│   ├── config.js            # Cấu hình Firebase & GitHub cho WebApp
│   └── app.js               # Logic Firebase v10, Chart.js, Open-Meteo & GitHub OTA
└── README.md                # Tài liệu kỹ thuật & hướng dẫn triển khai V2.0
```

---

## 🔌 2. Ánh Xạ Phần Cứng & Sơ Đồ Chân (Pinout Mapping)

| Thành phần linh kiện | Kết nối trên sơ đồ nguyên lý | Chân GPIO (ESP8266) | Đường dẫn (Key) trên Firebase |
| :--- | :--- | :--- | :--- |
| **Module ADC ADS1115 (16-Bit)** | `D1_SCL` (Chân 15), `D2_SDA` (Chân 16), `ADDR` nối `GND` (`0x48`) | `GPIO 5` (SCL), `GPIO 4` (SDA) | `/smart_clothesline/telemetry` |
| **Cảm biến mưa / nước (SEN1)** | Chân tín hiệu `S` nối kênh `A0` của ADS1115 (`WATER_A0`) | Giao tiếp I2C (Kênh 0) | `/telemetry/water_a0` & `/telemetry/is_raining` |
| **Quang trở LDR1** | Phân áp qua trở `R2 (10k)` nối kênh `A1` của ADS1115 (`LDR_A1`) | Giao tiếp I2C (Kênh 1) | `/telemetry/ldr_a1` & `/telemetry/is_sunny` |
| **Cảm biến nhiệt ẩm DHT22** | Chân `Out` nối chân `D4_LED` (`DHT22_D4`) | `GPIO 2` | `/telemetry/temperature`, `/telemetry/humidity` |
| **Nút nhấn cơ học (SW1)** | Trở kéo lên `R1 (10k)` lên `3V3`, nối vào `D6_MISO` (`BUTTON_D6`) | `GPIO 12` (Ngắt ngoài - IRQ) | `/control/manual_command` |
| **Động cơ Servo SG90 (M1)** | Nguồn `5V` (lọc nhiễu tụ `C1 100uF`), xung PWM nối `D7_MOSI` (`SERVO_D7`) | `GPIO 13` (PWM 50 Hz) | `/control/servo_angle`, `/telemetry/clothesline_state` |

---

## 🗄️ 3. Kiến Trúc Cơ Sở Dữ Liệu Firebase (JSON Schema V2.0)

```json
{
  "smart_clothesline": {
    "telemetry": {
      "temperature": 32.4,
      "humidity": 62.0,
      "water_a0": 24500,
      "is_raining": false,
      "ldr_a1": 21000,
      "is_sunny": true,
      "clothesline_state": "OPEN",
      "sun_minutes_today": 245,
      "last_updated": 1730530000
    },
    "control": {
      "manual_command": "OPEN",
      "servo_angle": 90,
      "rain_threshold": 15000,
      "sun_threshold": 16000
    },
    "schedule": {
      "auto_schedule_enabled": true,
      "open_time": "07:00",
      "close_time": "18:00",
      "rain_priority_override": true
    },
    "maintenance": {
      "current_version": "2.0.0",
      "target_version": "2.0.0",
      "trigger_ota": false,
      "trigger_reset": false,
      "ota_status": "IDLE"
    },
    "history": {
      "1730526400": {
        "temp": 31.0,
        "hum": 65.0,
        "water_a0": 25100,
        "ldr_a1": 19500
      }
    }
  }
}
```

---

## 🖥️ 4. Kiến Trúc Giao Diện Frontend (3 Phân Khu SPA)

1. **Trang 1: Trang Tổng quan (Overview Dashboard):**
   - Trạng thái sào phơi: ĐANG MỞ / ĐANG THU, nút điều khiển thủ công **Mở sào (Phơi đồ)**, **Thu sào (Cất đồ)**.
   - Xác thực thời tiết tại chỗ: Thẻ báo Có mưa / Không mưa (`WATER_A0`) và Có nắng / Không nắng (`LDR_A1`).
   - Tích hợp **Open-Meteo Weather API**: Nhiệt độ ngoài trời, lượng mưa, tốc độ gió và độ ẩm khu vực.
   - 4 thẻ cảm biến thời gian thực: Cảm biến nước A0 (kèm % độ ướt), Quang trở LDR A1 (kèm % cường độ sáng), Nhiệt độ và Độ ẩm DHT22.
   - Khối bảo trì: Kiểm tra bản cập nhật GitHub, kích hoạt **Update Firmware (OTA)** và nút **Reset thiết bị**.

2. **Trang 2: Trang Biểu đồ và Lịch sử (Charts & Analytics):**
   - Thống kê thời gian phơi đồ trong ngày: Tổng số giờ, phút sào phơi ở trạng thái `OPEN`.
   - Bộ lọc khung thời gian: 12 mốc (~1 giờ), 36 mốc (~3 giờ), 72 mốc (~6 giờ).
   - Biểu đồ **Chart.js** trực quan: Biểu đồ biến thiên Nhiệt độ - Độ ẩm và biểu đồ cảm biến Nước A0 - Quang trở LDR A1.

3. **Trang 3: Trang Cài đặt và Hẹn giờ (Settings & Schedule):**
   - Cài đặt giờ mở sào (mặc định `07:00`), giờ thu sào (mặc định `18:00`), công tắc Bật/Tắt lịch trình.
   - **Chế độ ưu tiên chống mưa (Rain Priority Override):** Thu sào ngay lập tức khi cảm biến A0 phát hiện mưa bất kể đang trong lịch phơi.
   - Hiệu chuẩn ngưỡng cảm biến mưa (`rain_threshold`) và ngưỡng nắng (`sun_threshold`).
   - Cấu hình thông số kết nối Firebase RTDB & GitHub Repository trực tiếp trên giao diện.

---

## ⚡ 5. Quy Tắc Ưu Tiên Xử Lý Trên Firmware (MicroPython)

1. **Đồng bộ thời gian thực qua NTP (`ntptime`):**
   - Tự động đồng bộ thời gian từ máy chủ NTP sau khi kết nối Wi-Fi, cộng độ lệch múi giờ Việt Nam ($\text{UTC}+7 = +25200\text{s}$) để so khớp giờ mở/thu sào và tự động đặt lại `sun_minutes_today` về 0 lúc `00:00`.
2. **Thứ tự 3 mức ưu tiên điều khiển Servo SG90:**
   - **Mức ưu tiên 1 (Chế độ ưu tiên mưa - Rain Override):** Nếu `rain_priority_override == True` và `WATER_A0 < rain_threshold` $\rightarrow$ Ngay lập tức thu sào ($0^\circ$), `clothesline_state = "CLOSED"`.
   - **Mức ưu tiên 2 (Lệnh thủ công qua Web hoặc nút bấm cơ SW1):** Nhấn nhả nút SW1 hoặc bấm nút trên Web sẽ điều khiển sào lập tức.
   - **Mức ưu tiên 3 (Lịch hẹn giờ tự động):** Khi `auto_schedule_enabled == True` và không có mưa, sào mở ($90^\circ$) nếu trong khoảng `[open_time, close_time]`, ngoài khung giờ sẽ tự thu sào ($0^\circ$).
3. **Thống kê & Ghi nhận lịch sử:**
   - Mỗi 1 phút: nếu sào `OPEN` thì cộng 1 vào `sun_minutes_today`.
   - Mỗi 5 phút: ghi một bản ghi vào `/smart_clothesline/history/<timestamp>`.
4. **Cơ chế bảo trì từ xa:**
   - Khi `trigger_reset == True`: Reset mạch từ xa qua `machine.reset()`.
   - Khi `trigger_ota == True`: Tải bản firmware mới từ GitHub Raw URL, ghi đè Flash và khởi động lại an toàn.
