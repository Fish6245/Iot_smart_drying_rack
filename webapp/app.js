// ==============================================================================
// app.js - Logic Giao diện Bảng điều khiển Giàn phơi thông minh (Firebase Modular v10)
// ==============================================================================

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getDatabase, ref, onValue, update } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-database.js";
import { loadUserConfig, saveUserConfig, DEFAULT_CONFIG } from "./config.js";

// 1. TẢI CẤU HÌNH & KHỞI TẠO FIREBASE
let currentConfig = loadUserConfig();
let db = null;
let deviceCurrentVersion = "1.0.0";
let latestGithubVersion = null;
let currentControlState = {
  mode: "AUTO",
  clothesline_out: false,
  target_angle: 0,
  rain_threshold: 15000,
  light_threshold: 10000
};

function initFirebase() {
  if (!currentConfig.firebase.databaseURL || currentConfig.firebase.databaseURL.includes("your-project-id")) {
    console.log("[*] Firebase URL chưa được cấu hình. Hoạt động ở chế độ độc lập.");
    updateConnBadge(false, "Chưa kết nối Firebase (Bấm ⚙️ để nhập)");
    return;
  }
  try {
    const app = initializeApp(currentConfig.firebase);
    db = getDatabase(app);
    console.log("[+] Firebase đã được khởi tạo thành công");
    setupFirebaseListeners();
  } catch (err) {
    console.error("[!] Lỗi khi khởi tạo Firebase:", err);
    updateConnBadge(false, "Lỗi kết nối Firebase");
  }
}

// 2. LẮNG NGHE DỮ LIỆU THỜI GIAN THỰC (REALTIME LISTENERS)
function setupFirebaseListeners() {
  if (!db) return;

  // A. Giám sát Cảm biến (Telemetry)
  const telemetryRef = ref(db, 'smart_clothesline/telemetry');
  onValue(telemetryRef, (snapshot) => {
    const data = snapshot.val();
    if (!data) return;

    // Cập nhật Nhiệt độ & Độ ẩm
    if (data.temperature !== undefined) {
      document.getElementById('temp-val').innerText = `${Number(data.temperature).toFixed(1)} °C`;
    }
    if (data.humidity !== undefined) {
      document.getElementById('hum-val').innerText = `${Number(data.humidity).toFixed(1)} %`;
    }

    // Quy đổi ADC ADS1115 (3.3V single-ended: ~26400)
    if (data.rain_adc !== undefined) {
      // Khi bề mặt ướt -> điện trở giảm -> ADC giảm -> rainPercent tăng
      const rainPercent = Math.min(100, Math.max(0, Math.round((1 - data.rain_adc / 26400) * 100)));
      document.getElementById('rain-val').innerText = `${rainPercent} %`;
      document.getElementById('rain-adc-sub').innerText = `ADC raw: ${data.rain_adc} (ADS1115 A0)`;
    }

    if (data.ldr_adc !== undefined) {
      // Trời nắng gắt -> ADC cao -> lightPercent tăng
      const lightPercent = Math.min(100, Math.max(0, Math.round((data.ldr_adc / 26400) * 100)));
      document.getElementById('light-val').innerText = `${lightPercent} %`;
      document.getElementById('light-adc-sub').innerText = `ADC raw: ${data.ldr_adc} (ADS1115 A1)`;
    }

    // Kiểm tra trạng thái Online/Offline dựa vào độ trễ (Heartbeat)
    if (data.last_updated) {
      const nowEpoch = Math.floor(Date.now() / 1000);
      const isOnline = (nowEpoch - data.last_updated) < 15; // Phản hồi trong vòng 15 giây
      updateConnBadge(isOnline, isOnline ? "Thiết bị Online" : "Thiết bị mất kết nối");
    }
  });

  // B. Giám sát Bảng điều khiển (Control)
  const controlRef = ref(db, 'smart_clothesline/control');
  onValue(controlRef, (snapshot) => {
    const ctrl = snapshot.val();
    if (!ctrl) return;

    currentControlState = { ...currentControlState, ...ctrl };
    updateControlUI(currentControlState);
  });

  // C. Giám sát Trạng thái Cập nhật OTA
  const otaRef = ref(db, 'smart_clothesline/ota');
  onValue(otaRef, (snapshot) => {
    const ota = snapshot.val();
    if (!ota) return;

    if (ota.current_version) {
      deviceCurrentVersion = ota.current_version;
      document.getElementById('header-version-text').innerText = `v${deviceCurrentVersion}`;
      document.getElementById('device-ver').innerText = `v${deviceCurrentVersion}`;
    }

    const otaStatus = ota.status || "IDLE";
    const statusBadge = document.getElementById('ota-status-badge');
    statusBadge.innerText = otaStatus;
    statusBadge.className = "badge";

    if (otaStatus === "DOWNLOADING" || otaStatus === "REQUESTED") {
      statusBadge.classList.add("mode-manual");
    } else if (otaStatus === "SUCCESS") {
      statusBadge.classList.add("online");
    } else if (otaStatus === "FAILED") {
      statusBadge.classList.add("offline");
    }
  });
}

// 3. CẬP NHẬT GIAO DIỆN BẢNG ĐIỀU KHIỂN
function updateControlUI(ctrl) {
  const isAuto = ctrl.mode === "AUTO";
  const btnToggleMode = document.getElementById('btn-toggle-mode');
  const btnServo = document.getElementById('btn-toggle-clothesline');
  const badgeMode = document.getElementById('badge-mode');
  const headerModeText = document.getElementById('header-mode-text');
  const clothesDesc = document.getElementById('clothesline-status-desc');

  // Badge Header
  headerModeText.innerText = ctrl.mode;
  if (isAuto) {
    badgeMode.className = "badge mode-auto";
    btnToggleMode.innerText = "Đổi sang MANUAL";
    btnToggleMode.className = "btn btn-primary";
    btnToggleMode.dataset.mode = "AUTO";

    btnServo.disabled = true;
    btnServo.title = "Khóa ở chế độ AUTO (Hệ thống tự động điều khiển)";
  } else {
    badgeMode.className = "badge mode-manual";
    btnToggleMode.innerText = "Đổi sang AUTO";
    btnToggleMode.className = "btn btn-amber";
    btnToggleMode.dataset.mode = "MANUAL";

    btnServo.disabled = false;
    btnServo.title = "Bấm để thu vào / đưa ra giàn phơi";
  }

  // Trạng thái giàn phơi
  if (ctrl.clothesline_out) {
    clothesDesc.innerText = `Đang phơi ngoài trời (Góc quay: ${ctrl.target_angle || 90}°)`;
    btnServo.innerText = "Thu giàn vào trong";
    btnServo.className = "btn btn-amber";
    btnServo.dataset.out = "true";
  } else {
    clothesDesc.innerText = `Đã thu gọn trong nhà (Góc quay: ${ctrl.target_angle || 0}°)`;
    btnServo.innerText = "Đưa giàn ra ngoài";
    btnServo.className = "btn btn-success";
    btnServo.dataset.out = "false";
  }

  // Cập nhật giá trị hiển thị trên Sliders
  if (ctrl.rain_threshold !== undefined) {
    document.getElementById('slider-rain').value = ctrl.rain_threshold;
    document.getElementById('rain-thresh-val').innerText = ctrl.rain_threshold;
  }
  if (ctrl.light_threshold !== undefined) {
    document.getElementById('slider-light').value = ctrl.light_threshold;
    document.getElementById('light-thresh-val').innerText = ctrl.light_threshold;
  }
}

function updateConnBadge(isOnline, text) {
  const badge = document.getElementById('badge-connection');
  const connText = document.getElementById('conn-text');
  badge.className = `badge ${isOnline ? 'online' : 'offline'}`;
  connText.innerText = text;
}

// 4. XỬ LÝ SỰ KIỆN TƯƠNG TÁC NGƯỜI DÙNG
function bindUserEvents() {
  // Đổi chế độ AUTO / MANUAL
  document.getElementById('btn-toggle-mode').addEventListener('click', (e) => {
    if (!db) return;
    const currentMode = e.currentTarget.dataset.mode;
    const newMode = currentMode === "AUTO" ? "MANUAL" : "AUTO";
    update(ref(db, 'smart_clothesline/control'), { mode: newMode });
  });

  // Điều khiển vị trí giàn phơi (Servo SG90)
  document.getElementById('btn-toggle-clothesline').addEventListener('click', (e) => {
    if (!db) return;
    const isOut = e.currentTarget.dataset.out === "true";
    const nextOut = !isOut;
    update(ref(db, 'smart_clothesline/control'), {
      clothesline_out: nextOut,
      target_angle: nextOut ? 90 : 0
    });
  });

  // Thay đổi thanh trượt ngưỡng
  const sliderRain = document.getElementById('slider-rain');
  const sliderLight = document.getElementById('slider-light');

  sliderRain.addEventListener('input', (e) => {
    document.getElementById('rain-thresh-val').innerText = e.target.value;
  });

  sliderLight.addEventListener('input', (e) => {
    document.getElementById('light-thresh-val').innerText = e.target.value;
  });

  // Lưu ngưỡng lên Firebase
  document.getElementById('btn-save-thresholds').addEventListener('click', () => {
    if (!db) return;
    const rainVal = parseInt(sliderRain.value, 10);
    const lightVal = parseInt(sliderLight.value, 10);
    update(ref(db, 'smart_clothesline/control'), {
      rain_threshold: rainVal,
      light_threshold: lightVal
    }).then(() => {
      alert("Đã cập nhật ngưỡng kích hoạt thành công!");
    }).catch((err) => {
      alert("Lỗi khi lưu ngưỡng: " + err.message);
    });
  });

  // Kiểm tra cập nhật GitHub OTA
  document.getElementById('btn-check-update').addEventListener('click', checkGithubUpdate);

  // Kích hoạt cập nhật OTA
  document.getElementById('btn-trigger-ota').addEventListener('click', triggerOTA);

  // Cấu hình Modal
  setupSettingsModal();
}

// 5. QUẢN LÝ CẬP NHẬT GITHUB OTA
async function checkGithubUpdate() {
  const gh = currentConfig.github;
  const versionUrl = `https://raw.githubusercontent.com/${gh.user}/${gh.repo}/${gh.branch}/version.json?t=${Date.now()}`;
  const btnCheck = document.getElementById('btn-check-update');
  const btnTrigger = document.getElementById('btn-trigger-ota');
  const githubVerEl = document.getElementById('github-ver');
  const changelogEl = document.getElementById('changelog-text');

  btnCheck.disabled = true;
  githubVerEl.innerText = "Đang kiểm tra...";

  try {
    const res = await fetch(versionUrl);
    if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
    const data = await res.json();

    latestGithubVersion = data.version;
    githubVerEl.innerText = `v${data.version}`;
    changelogEl.innerText = data.changelog || "Không có ghi chú thay đổi.";

    // Cho phép kích hoạt OTA
    btnTrigger.disabled = false;
    if (data.version === deviceCurrentVersion) {
      changelogEl.innerText += "\n\n(Thiết bị đã ở phiên bản mới nhất. Bạn vẫn có thể nạp lại nếu muốn).";
    }
  } catch (err) {
    console.error("Lỗi kiểm tra GitHub OTA:", err);
    githubVerEl.innerText = "Không thể lấy thông tin";
    changelogEl.innerText = "Lỗi kết nối GitHub Raw API: " + err.message;
    btnTrigger.disabled = true;
  } finally {
    btnCheck.disabled = false;
  }
}

function triggerOTA() {
  if (!latestGithubVersion) return;

  if (!db || currentConfig.firebase.databaseURL.includes("your-project-id")) {
    alert("⚠️ Bạn chưa cấu hình Firebase Database URL trên WebApp!\n\n💡 Để cập nhật OTA mà KHÔNG cần Firebase:\nNhấn và giữ nút nhấn cơ SW1 (GPIO 12) trên mạch trong 3 giây.\nThiết bị sẽ tự động tải firmware mới nhất trực tiếp từ GitHub về nạp!");
    return;
  }
  const gh = currentConfig.github;
  const downloadUrl = `https://raw.githubusercontent.com/${gh.user}/${gh.repo}/${gh.branch}/firmware/main.py`;

  if (!confirm(`Bạn có chắc chắn muốn nạp Firmware phiên bản v${latestGithubVersion} từ xa vào ESP8266?`)) {
    return;
  }

  update(ref(db, 'smart_clothesline/ota'), {
    target_version: latestGithubVersion,
    trigger_update: true,
    status: "REQUESTED",
    download_url: downloadUrl
  }).then(() => {
    alert("Yêu cầu cập nhật OTA đã được gửi tới thiết bị!");
  }).catch((err) => {
    alert("Lỗi khi gửi yêu cầu OTA: " + err.message);
  });
}

// 6. CỬA SỔ CÀI ĐẶT CẤU HÌNH (SETTINGS MODAL)
function setupSettingsModal() {
  const modal = document.getElementById('modal-settings');
  const btnOpen = document.getElementById('btn-open-settings');
  const btnClose = document.getElementById('btn-close-settings');
  const btnSave = document.getElementById('btn-save-settings');
  const btnReset = document.getElementById('btn-reset-settings');

  const inputUrl = document.getElementById('cfg-firebase-url');
  const inputKey = document.getElementById('cfg-firebase-key');
  const inputProj = document.getElementById('cfg-firebase-project');
  const inputGhUser = document.getElementById('cfg-github-user');
  const inputGhRepo = document.getElementById('cfg-github-repo');

  function populateInputs() {
    inputUrl.value = currentConfig.firebase.databaseURL || "";
    inputKey.value = currentConfig.firebase.apiKey || "";
    inputProj.value = currentConfig.firebase.projectId || "";
    inputGhUser.value = currentConfig.github.user || "";
    inputGhRepo.value = currentConfig.github.repo || "";
  }

  btnOpen.addEventListener('click', () => {
    populateInputs();
    modal.classList.add('active');
  });

  btnClose.addEventListener('click', () => {
    modal.classList.remove('active');
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('active');
  });

  btnReset.addEventListener('click', () => {
    currentConfig = JSON.parse(JSON.stringify(DEFAULT_CONFIG));
    populateInputs();
  });

  btnSave.addEventListener('click', () => {
    currentConfig.firebase.databaseURL = inputUrl.value.trim();
    currentConfig.firebase.apiKey = inputKey.value.trim();
    currentConfig.firebase.projectId = inputProj.value.trim();
    currentConfig.github.user = inputGhUser.value.trim();
    currentConfig.github.repo = inputGhRepo.value.trim();

    saveUserConfig(currentConfig);
    modal.classList.remove('active');
    alert("Đã lưu cài đặt! Trang web sẽ được tải lại.");
    window.location.reload();
  });
}

// Khởi chạy ứng dụng
document.addEventListener('DOMContentLoaded', () => {
  bindUserEvents();
  initFirebase();
  checkGithubUpdate();
});

