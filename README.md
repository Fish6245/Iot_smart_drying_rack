# 👕 Hệ Thống IoT Giàn Phơi Thông Minh (Smart Clothesline)
> **Vi điều khiển:** WeMos D1 R2 (ESP8266)  
> **Ngôn ngữ & Môi trường:** MicroPython (uPyCraft IDE / Thonny)  
> **Cơ sở dữ liệu:** Google Firebase Realtime Database  
> **Cập nhật từ xa (OTA):** GitHub Repository (REST API)  
> **Giao diện điều khiển:** WebApp Dashboard thuần HTML5 / CSS3 / ES6+  

---

## 📁 1. Cấu Trúc Thư Mục Dự Án

```text
Iot_smart_drying_rack/
├── version.json             # Định danh phiên bản phục vụ GitHub OTA
├── firmware/                # Mã nguồn MicroPython chạy trên WeMos D1 R2
│   ├── boot.py              # Kết nối WiFi và khởi tạo cơ bản
│   ├── config.py            # Cấu hình WiFi, Firebase URL, chân GPIO & ngưỡng
│   ├── ads1x15.py           # Driver I2C đọc ADC ADS1115 (16-bit)
│   ├── ota.py               # Module tải và ghi đè firmware từ xa
│   └── main.py              # Luồng xử lý chính (Cảm biến, Servo, Nút cơ, Firebase)
├── webapp/                  # Bảng điều khiển Web Dashboard
│   ├── index.html           # Khung giao diện Responsive
│   ├── style.css            # Định dạng giao diện Modern IoT Dashboard
│   ├── config.js            # Cấu hình Firebase & GitHub cho WebApp
│   └── app.js               # Logic kết nối Firebase v10 và quản lý OTA
└── README.md                # Hướng dẫn chi tiết triển khai hệ thống
```

---

## 🔌 2. Sơ Đồ Đấu Nối Phần Cứng (Pinout Mapping)

| Thành phần ngoại vi | Chân linh kiện | Chân trên WeMos D1 R2 | Ghi chú kỹ thuật |
| :--- | :--- | :--- | :--- |
| **ADS1115 (16-Bit ADC)** | `SCL`, `SDA` | `D1 (GPIO 5)`, `D2 (GPIO 4)` | I2C địa chỉ `0x48` (chân `ADDR` nối `GND`) |
| | `VDD`, `GND` | `3V3`, `GND` | Nguồn cấp cho chip ADC |
| **Cảm biến Mưa (SEN1)** | Chân tín hiệu `S` | Kênh `A0` của ADS1115 | Khi ướt ADC giảm, khi khô ADC ~26400 |
| **Quang trở LDR1** | Chân phân áp trở `10k` | Kênh `A1` của ADS1115 | Trời nắng gắt ADC tăng |
| **Cảm biến nhiệt ẩm DHT22** | Chân tín hiệu `Out` | `D4 (GPIO 2)` | Đọc nhiệt độ và độ ẩm môi trường |
| **Nút nhấn cơ học (SW1)** | Một chân nối `GND` | `D6 (GPIO 12)` | Kéo trở `10k` lên `3V3`, ngắt ngoài IRQ |
| **Động cơ Servo SG90** | Dây cam (PWM) | `D7 (GPIO 13)` | Tần số 50Hz, ngắt xung sau khi quay |
| | Dây đỏ, nâu | `5V`, `GND` | Gắn tụ lọc `C1 100uF` song song nguồn 5V |

---

## ⚙️ 3. Các Bước Triển Khai Nhanh (Đơn Giản Nhất)

### Bước 1: Cấu hình Firebase Realtime Database
1. Truy cập [Firebase Console](https://console.firebase.google.com/) tạo project mới.
2. Tạo **Realtime Database** (chọn vị trí gần nhất, ví dụ `Singapore`).
3. Trong tab **Rules (Quy tắc)**, thiết lập quyền đọc/ghi trong quá trình thử nghiệm:
   ```json
   {
     "rules": {
       ".read": true,
       ".write": true
     }
   }
   ```
4. Copy đường dẫn `databaseURL` (ví dụ: `https://my-project-default-rtdb.firebaseio.com/`).

### Bước 2: Cấu hình Biến môi trường & Nạp Firmware
1. **Cấu hình thông tin kết nối an toàn với `.env`:**
   * Tạo bản sao từ `.env.example` thành `.env`:
     ```bash
     cp .env.example .env
     ```
   * Mở file `.env` và điền thông tin của bạn:
     ```ini
     WIFI_SSID="Tên_WiFi_Của_Bạn"
     WIFI_PASSWORD="Mat_Khau_WiFi"
     FIREBASE_URL="https://your-project-id-default-rtdb.firebaseio.com"
     ```
   > 💡 *File `.env` đã được cấu hình trong `.gitignore`, giúp bạn yên tâm không bao giờ bị lộ mật khẩu WiFi hay URL bí mật khi đưa code lên GitHub.*

2. **Nạp Firmware lên WeMos D1 (uPyCraft hoặc Thonny):**
   * Cài đặt firmware MicroPython cho ESP8266 (nếu board mới hoàn toàn).
   * Dùng uPyCraft IDE hoặc Thonny nạp các tệp trong thư mục `firmware/` (`boot.py`, `config.py`, `ads1x15.py`, `ota.py`, `main.py`) cùng file `.env` vào bộ nhớ flash của ESP8266.
   * Bấm nút **RST** trên WeMos D1 để khởi động. Quan sát cửa sổ Terminal để kiểm tra địa chỉ IP và trạng thái kết nối.

### Bước 3: Khởi chạy Giao diện Web (Dashboard)
1. Mở thư mục `webapp/`.
2. Mở trực tiếp tệp `index.html` bằng trình duyệt (hoặc dùng VS Code extension *Live Server*).
3. Bấm nút **⚙️ Cấu hình** ở góc phải trên cùng màn hình:
   - Nhập `Firebase Database URL` và `Project ID`.
   - Bấm **Lưu cài đặt**.
4. Lúc này giao diện sẽ kết nối trực tiếp đến Firebase:
   - Hiển thị thông số nhiệt độ, độ ẩm, mức mưa, ánh sáng.
   - Nút bật/tắt chế độ `AUTO` / `MANUAL`.
   - Nút điều khiển xào phơi và thanh trượt điều chỉnh ngưỡng.

---

## 🚀 4. Quy Trình Cập Nhật Firmware Từ Xa (GitHub OTA)

Hệ thống hỗ trợ **2 cơ chế cập nhật OTA linh hoạt**:

### Cách 1: Cập nhật trực tiếp từ GitHub (KHÔNG CẦN FIREBASE)
Nếu bạn chưa có tài khoản Firebase hoặc không muốn dùng cơ sở dữ liệu:
1. Đẩy code mới lên nhánh `main` trên GitHub và nâng số phiên bản trong `version.json`.
2. **Kích hoạt nạp firmware mới trên mạch bằng 1 trong 2 cách:**
   * **Cách A (Nhấn giữ nút SW1):** Nhấn và giữ nút cơ `SW1` (chân `D6 / GPIO 12`) trong **3 giây**. Mạch sẽ nhận diện thao tác nhấn giữ, tự kết nối GitHub Raw, tải tệp `main.py` mới nhất và tự reset máy.
   * **Cách B (Tự động khi khởi động):** Mỗi lần cắm điện/reset, mạch sẽ tự động đọc `version.json` từ GitHub. Nếu phát hiện phiên bản trên GitHub lớn hơn phiên bản hiện tại, mạch sẽ tự nâng cấp.
> 💡 *Lưu ý: Quá trình OTA chỉ cập nhật tệp logic chương trình (`main.py`), hoàn toàn giữ nguyên tệp `.env` và `config.py` nên bạn không bao giờ bị mất mật khẩu WiFi.*

---

### Cách 2: Cập nhật qua Web Dashboard (Khi có Firebase)
1. Khi bạn sửa đổi logic trong `firmware/main.py`:
   - Nâng số phiên bản trong `version.json` (ví dụ `1.0.0` -> `1.0.1`).
   - Cập nhật ghi chú `changelog`.
2. Commit và Push mã nguồn lên nhánh `main` của GitHub repository:
   ```bash
   git add .
   git commit -m "Update firmware v1.0.1"
   git push origin main
   ```
3. Trên WebApp, mục **"CẬP NHẬT TỪ XA (GITHUB OTA)"**:
   - Bấm **"Kiểm tra cập nhật"**: Hệ thống sẽ đọc tệp `version.json` mới nhất từ GitHub Raw.
   - Bấm **"Tiến hành OTA"**: Lệnh cập nhật được gửi qua Firebase. ESP8266 sẽ tự động tải `main.py` mới, ghi đè an toàn vào Flash và tự khởi động lại (`machine.reset()`).

