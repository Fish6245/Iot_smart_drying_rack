// ==============================================================================
// app.js - Logic Giao diện Bảng điều khiển Sào phơi thông minh (V2.0)
// Tích hợp: Firebase RTDB Modular v10, Chart.js, Open-Meteo Weather API, GitHub OTA
// & Dev Simulator Bar (Kiểm thử cảm biến & kịch bản thời tiết)
// ==============================================================================

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getDatabase, ref, onValue, update, query, limitToLast } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-database.js";
import { loadUserConfig, saveUserConfig } from "./config.js";

// 1. TẢI CẤU HÌNH HỆ THỐNG
let currentConfig = loadUserConfig();
let db = null;
let firebaseApp = null;
let historyUnsubscribe = null;

const WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast?latitude=10.8231&longitude=106.6297&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&timezone=Asia%2FBangkok";

function getGithubVersionUrl() {
  const user = currentConfig.github.user || "chuvitvang";
  const repo = currentConfig.github.repo || "Iot_smart_drying_rack";
  const branch = currentConfig.github.branch || "main";
  return `https://raw.githubusercontent.com/${user}/${repo}/${branch}/version.json`;
}

// Khởi tạo Firebase
function initFirebase() {
  const fbCfg = currentConfig.firebase;
  if (!fbCfg || !fbCfg.databaseURL || fbCfg.databaseURL.includes("your-project-id")) {
    console.warn("[*] Firebase URL chưa được cấu hình. Hoạt động ở chế độ thử nghiệm cục bộ.");
    const statusBadge = document.getElementById('device-status');
    if (statusBadge) {
      statusBadge.innerText = "Chế độ Thử nghiệm (Local Mock)";
      statusBadge.className = "badge";
    }
    return;
  }

  try {
    firebaseApp = initializeApp(fbCfg);
    db = getDatabase(firebaseApp);
    console.log("[+] Firebase đã được khởi tạo thành công");
    setupFirebaseListeners();
    loadHistoryCharts(parseInt(document.getElementById('chart-limit')?.value || "36"));
  } catch (err) {
    console.error("[!] Lỗi khi khởi tạo Firebase:", err);
    const statusBadge = document.getElementById('device-status');
    if (statusBadge) {
      statusBadge.innerText = "Lỗi kết nối Firebase";
      statusBadge.className = "badge offline";
    }
  }
}

// ==================== ĐIỀU HƯỚNG TAB SPA ====================
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    const targetSection = document.getElementById(btn.dataset.target);
    if (targetSection) {
      targetSection.classList.add('active');
      // Khi mở tab Biểu đồ, kích hoạt resize để vẽ chính xác theo khung
      if (btn.dataset.target === 'tab-charts') {
        setTimeout(() => {
          if (dhtChart) dhtChart.resize();
          if (adcChart) adcChart.resize();
        }, 50);
      }
    }
  });
});

// ==================== KHỞI TẠO BIỂU ĐỒ (CHART.JS) ====================
const dhtCanvas = document.getElementById('dhtChart');
const adcCanvas = document.getElementById('adcChart');

let dhtChart = null;
let adcChart = null;

if (dhtCanvas && typeof Chart !== "undefined") {
  dhtChart = new Chart(dhtCanvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Nhiệt độ (°C)', data: [], borderColor: '#ef4444', backgroundColor: 'rgba(239, 68, 68, 0.1)', tension: 0.3, fill: true },
        { label: 'Độ ẩm (%)', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.1)', tension: 0.3, fill: true }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'top' } }
    }
  });
}

if (adcCanvas && typeof Chart !== "undefined") {
  adcChart = new Chart(adcCanvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        { label: 'Cảm biến Nước A0 (ADC)', data: [], borderColor: '#0284c7', backgroundColor: 'rgba(2, 132, 199, 0.1)', tension: 0.3, fill: true },
        { label: 'Quang trở LDR A1 (ADC)', data: [], borderColor: '#eab308', backgroundColor: 'rgba(234, 179, 8, 0.1)', tension: 0.3, fill: true }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'top' } }
    }
  });
}

function loadHistoryCharts(limitCount = 36) {
  if (!db) return;
  if (historyUnsubscribe) {
    historyUnsubscribe();
  }

  const historyQuery = query(ref(db, 'smart_clothesline/history'), limitToLast(limitCount));
  historyUnsubscribe = onValue(historyQuery, (snapshot) => {
    const hist = snapshot.val();
    if (!hist || !dhtChart || !adcChart) return;

    const labels = [], temps = [], hums = [], waters = [], ldrs = [];
    Object.keys(hist).sort().forEach(ts => {
      const date = new Date(parseInt(ts) * 1000);
      labels.push(date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }));
      temps.push(hist[ts].temp ?? null);
      hums.push(hist[ts].hum ?? null);
      waters.push(hist[ts].water_a0 ?? null);
      ldrs.push(hist[ts].ldr_a1 ?? null);
    });

    dhtChart.data.labels = labels;
    dhtChart.data.datasets[0].data = temps;
    dhtChart.data.datasets[1].data = hums;
    dhtChart.update();

    adcChart.data.labels = labels;
    adcChart.data.datasets[0].data = waters;
    adcChart.data.datasets[1].data = ldrs;
    adcChart.update();
  });
}

document.getElementById('chart-limit')?.addEventListener('change', (e) => {
  loadHistoryCharts(parseInt(e.target.value));
});

// ==================== CẬP NHẬT GIAO DIỆN TỪ TELEMETRY ====================
function updateUIWithTelemetry(data, isSimulated = false) {
  if (!data) return;

  // 1. Trạng thái kết nối
  const statusBadge = document.getElementById('device-status');
  if (statusBadge) {
    if (isSimulated) {
      statusBadge.innerText = "Giả lập (Simulated)";
      statusBadge.className = "badge online";
    } else {
      const nowSec = Math.floor(Date.now() / 1000);
      const lastUp = data.last_updated || 0;
      const isOnline = (nowSec - lastUp) < 30;
      statusBadge.innerText = isOnline ? "Trực tuyến (Online)" : "Mất kết nối (Offline)";
      statusBadge.className = `badge ${isOnline ? 'online' : 'offline'}`;
    }
  }

  // 2. Cảm biến nước A0
  const waterA0 = data.water_a0 ?? 0;
  const wetPercent = Math.min(100, Math.max(0, Math.round((1 - waterA0 / 26400) * 100)));
  const elWaterVal = document.getElementById('val-water-a0');
  const elWaterSub = document.getElementById('sub-water-a0');
  if (elWaterVal) elWaterVal.innerText = waterA0;
  if (elWaterSub) elWaterSub.innerText = `ADC 16-bit (Độ ướt: ${wetPercent}%)`;

  const rainBadge = document.getElementById('rain-status-badge');
  if (rainBadge) {
    rainBadge.innerText = data.is_raining ? "🌧️ Có mưa" : "☁️ Không mưa";
    rainBadge.className = `tag ${data.is_raining ? 'tag-rain' : 'tag-safe'}`;
  }

  // 3. Quang trở LDR A1
  const ldrA1 = data.ldr_a1 ?? 0;
  const lightPercent = Math.min(100, Math.max(0, Math.round((ldrA1 / 26400) * 100)));
  const elLdrVal = document.getElementById('val-ldr-a1');
  const elLdrSub = document.getElementById('sub-ldr-a1');
  if (elLdrVal) elLdrVal.innerText = ldrA1;
  if (elLdrSub) elLdrSub.innerText = `ADC 16-bit (Cường độ: ${lightPercent}%)`;

  const sunBadge = document.getElementById('sun-status-badge');
  if (sunBadge) {
    sunBadge.innerText = data.is_sunny ? "☀️ Có nắng" : "🌥️ Không nắng";
    sunBadge.className = `tag ${data.is_sunny ? 'tag-sun' : 'tag-shade'}`;
  }

  // 4. Nhiệt ẩm DHT22
  const elTemp = document.getElementById('val-temp');
  const elHum = document.getElementById('val-hum');
  if (elTemp) elTemp.innerText = `${Number(data.temperature ?? 0).toFixed(1)} °C`;
  if (elHum) elHum.innerText = `${Number(data.humidity ?? 0).toFixed(1)} %`;

  // 5. Trạng thái sào phơi
  const poleState = document.getElementById('clothesline-state-text');
  if (poleState) {
    if (data.clothesline_state === "OPEN") {
      poleState.innerText = "ĐANG MỞ";
      poleState.style.color = "#16a34a";
    } else {
      poleState.innerText = "ĐANG THU";
      poleState.style.color = "#d97706";
    }
  }

  // 6. Thống kê thời gian phơi trong ngày
  const totalMinutes = data.sun_minutes_today ?? 0;
  const statDrying = document.getElementById('stat-drying-time');
  if (statDrying) {
    statDrying.innerText = `${Math.floor(totalMinutes / 60)} giờ ${totalMinutes % 60} phút`;
  }
}

// ==================== LẮNG NGHE DỮ LIỆU FIREBASE ====================
function setupFirebaseListeners() {
  if (!db) return;

  // 1. Giám sát Cảm biến (Telemetry)
  const telemetryRef = ref(db, 'smart_clothesline/telemetry');
  onValue(telemetryRef, (snapshot) => {
    const data = snapshot.val();
    if (!data) return;
    updateUIWithTelemetry(data, false);
  });

  // 2. Giám sát Cơ chế Bảo trì (Maintenance)
  const maintRef = ref(db, 'smart_clothesline/maintenance');
  onValue(maintRef, (snap) => {
    const m = snap.val();
    if (!m) return;
    const curVer = document.getElementById('curr-fw-ver');
    const otaStat = document.getElementById('ota-status-text');
    if (curVer && m.current_version) curVer.innerText = `v${m.current_version}`;
    if (otaStat && m.ota_status) otaStat.innerText = m.ota_status;
  });

  // 3. Giám sát Lịch trình (Schedule)
  const scheduleRef = ref(db, 'smart_clothesline/schedule');
  onValue(scheduleRef, (snap) => {
    const s = snap.val();
    if (!s) return;
    const autoSchedule = document.getElementById('toggle-auto-schedule');
    const openTime = document.getElementById('input-open-time');
    const closeTime = document.getElementById('input-close-time');
    const rainPriority = document.getElementById('toggle-rain-priority');

    if (autoSchedule) autoSchedule.checked = !!s.auto_schedule_enabled;
    if (openTime && s.open_time) openTime.value = s.open_time;
    if (closeTime && s.close_time) closeTime.value = s.close_time;
    if (rainPriority) rainPriority.checked = s.rain_priority_override !== false;
  });

  // 4. Giám sát Điều khiển & Ngưỡng (Control)
  const controlRef = ref(db, 'smart_clothesline/control');
  onValue(controlRef, (snap) => {
    const c = snap.val();
    if (!c) return;
    const rainThresh = document.getElementById('input-rain-thresh');
    const sunThresh = document.getElementById('input-sun-thresh');
    if (rainThresh && c.rain_threshold) rainThresh.value = c.rain_threshold;
    if (sunThresh && c.sun_threshold) sunThresh.value = c.sun_threshold;
  });
}

// ==================== ĐIỀU KHIỂN THỦ CÔNG ====================
document.getElementById('btn-open-pole')?.addEventListener('click', () => {
  if (db) {
    update(ref(db, 'smart_clothesline/control'), { manual_command: "OPEN", servo_angle: 90 });
  } else {
    // Cập nhật giả lập cục bộ khi không kết nối Firebase
    const poleState = document.getElementById('clothesline-state-text');
    if (poleState) {
      poleState.innerText = "ĐANG MỞ";
      poleState.style.color = "#16a34a";
    }
  }
});

document.getElementById('btn-close-pole')?.addEventListener('click', () => {
  if (db) {
    update(ref(db, 'smart_clothesline/control'), { manual_command: "CLOSE", servo_angle: 0 });
  } else {
    // Cập nhật giả lập cục bộ khi không kết nối Firebase
    const poleState = document.getElementById('clothesline-state-text');
    if (poleState) {
      poleState.innerText = "ĐANG THU";
      poleState.style.color = "#d97706";
    }
  }
});

// ==================== TÍCH HỢP OPEN-METEO WEATHER API ====================
async function fetchWeatherAPI() {
  try {
    const res = await fetch(WEATHER_API_URL);
    const data = await res.json();
    const cur = data.current;
    const tempEl = document.getElementById('api-temp');
    const descEl = document.getElementById('api-desc');
    const windEl = document.getElementById('api-wind');

    if (tempEl) tempEl.innerText = `${cur.temperature_2m} °C`;
    if (descEl) {
      descEl.innerText = cur.precipitation > 0
        ? `🌧️ Khu vực có mưa (${cur.precipitation} mm)`
        : `🌤️ Thời tiết khu vực khô ráo`;
    }
    if (windEl) {
      windEl.innerText = `Gió: ${cur.wind_speed_10m} km/h | Độ ẩm: ${cur.relative_humidity_2m}%`;
    }
  } catch (e) {
    const descEl = document.getElementById('api-desc');
    if (descEl) descEl.innerText = "Lỗi tải API thời tiết";
  }
}
fetchWeatherAPI();
setInterval(fetchWeatherAPI, 300000);

// ==================== CƠ CHẾ BẢO TRÌ (OTA & RESET) ====================
document.getElementById('btn-check-ota')?.addEventListener('click', async () => {
  const gitVerEl = document.getElementById('git-fw-ver');
  const btnOta = document.getElementById('btn-update-ota');
  if (gitVerEl) gitVerEl.innerText = "Đang kiểm tra...";

  try {
    const versionUrl = getGithubVersionUrl();
    const res = await fetch(`${versionUrl}?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const remoteGitData = await res.json();

    if (gitVerEl) gitVerEl.innerText = `v${remoteGitData.version}`;
    const curr = document.getElementById('curr-fw-ver')?.innerText.replace('v', '') || "2.0.0";

    if (btnOta) {
      btnOta.disabled = (remoteGitData.version === curr);
      btnOta.onclick = () => {
        if (!db) { alert("Cần kết nối Firebase để gửi lệnh OTA!"); return; }
        update(ref(db, 'smart_clothesline/maintenance'), {
          target_version: remoteGitData.version,
          trigger_ota: true,
          ota_status: "REQUESTED"
        });
      };
    }
  } catch (e) {
    console.error("Lỗi kiểm tra GitHub OTA:", e);
    if (gitVerEl) gitVerEl.innerText = "Không thể kết nối GitHub";
  }
});

document.getElementById('btn-reset-mcu')?.addEventListener('click', () => {
  if (!db) { alert("Cần kết nối Firebase để gửi lệnh Reset!"); return; }
  if (confirm("Xác nhận khởi động lại mạch WeMos D1 R2 (ESP8266)?")) {
    update(ref(db, 'smart_clothesline/maintenance'), { trigger_reset: true });
  }
});

// ==================== TRANG 3: CÀI ĐẶT & HẸN GIỜ ====================
function populateConfigUI() {
  const fb = currentConfig.firebase;
  const gh = currentConfig.github;

  const dbUrlInput = document.getElementById('input-cfg-db-url');
  const apiKeyInput = document.getElementById('input-cfg-api-key');
  const projInput = document.getElementById('input-cfg-project-id');
  const ghUserInput = document.getElementById('input-cfg-gh-user');
  const ghRepoInput = document.getElementById('input-cfg-gh-repo');

  if (dbUrlInput && fb.databaseURL && !fb.databaseURL.includes("your-project-id")) {
    dbUrlInput.value = fb.databaseURL;
  }
  if (apiKeyInput && fb.apiKey && !fb.apiKey.includes("YOUR_")) {
    apiKeyInput.value = fb.apiKey;
  }
  if (projInput && fb.projectId && !projInput.value) {
    projInput.value = fb.projectId;
  }
  if (ghUserInput) ghUserInput.value = gh.user || "chuvitvang";
  if (ghRepoInput) ghRepoInput.value = gh.repo || "Iot_smart_drying_rack";
}

populateConfigUI();

document.getElementById('btn-save-settings')?.addEventListener('click', async () => {
  const autoSchedule = document.getElementById('toggle-auto-schedule')?.checked;
  const openTime = document.getElementById('input-open-time')?.value || "07:00";
  const closeTime = document.getElementById('input-close-time')?.value || "18:00";
  const rainPriority = document.getElementById('toggle-rain-priority')?.checked;

  const rainThresh = parseInt(document.getElementById('input-rain-thresh')?.value || "15000");
  const sunThresh = parseInt(document.getElementById('input-sun-thresh')?.value || "16000");

  const newDbUrl = document.getElementById('input-cfg-db-url')?.value.trim();
  const newApiKey = document.getElementById('input-cfg-api-key')?.value.trim();
  const newProjectId = document.getElementById('input-cfg-project-id')?.value.trim();
  const newGhUser = document.getElementById('input-cfg-gh-user')?.value.trim();
  const newGhRepo = document.getElementById('input-cfg-gh-repo')?.value.trim();

  let reconnectNeeded = false;
  if (newDbUrl && newDbUrl !== currentConfig.firebase.databaseURL) {
    currentConfig.firebase.databaseURL = newDbUrl;
    reconnectNeeded = true;
  }
  if (newApiKey) currentConfig.firebase.apiKey = newApiKey;
  if (newProjectId) currentConfig.firebase.projectId = newProjectId;
  if (newGhUser) currentConfig.github.user = newGhUser;
  if (newGhRepo) currentConfig.github.repo = newGhRepo;

  saveUserConfig(currentConfig);

  if (db) {
    try {
      await update(ref(db, 'smart_clothesline/schedule'), {
        auto_schedule_enabled: autoSchedule,
        open_time: openTime,
        close_time: closeTime,
        rain_priority_override: rainPriority
      });

      await update(ref(db, 'smart_clothesline/control'), {
        rain_threshold: rainThresh,
        sun_threshold: sunThresh
      });
    } catch (err) {
      console.error("Lỗi lưu lên Firebase:", err);
    }
  } else if (reconnectNeeded) {
    initFirebase();
  }

  const toast = document.getElementById('save-toast');
  if (toast) {
    toast.innerText = "✓ Đã lưu cài đặt thành công!";
    setTimeout(() => { toast.innerText = ""; }, 3000);
  }
});

// ==============================================================================
// 🛠️ DEV SIMULATOR BAR - LOGIC KIỂM THỬ MÔ PHỎNG NGOẠI VI
// ==============================================================================
const simBar = document.getElementById('dev-sim-bar');
const simCollapseBtn = document.getElementById('btn-toggle-sim-collapse');
const simCollapseIcon = document.getElementById('sim-collapse-icon');
const simCollapseText = document.getElementById('sim-collapse-text');
const simHeaderToggle = document.getElementById('sim-header-toggle');

const sliderRain = document.getElementById('sim-slider-rain');
const sliderLdr = document.getElementById('sim-slider-ldr');
const sliderTemp = document.getElementById('sim-slider-temp');
const sliderHum = document.getElementById('sim-slider-hum');

const valRain = document.getElementById('sim-val-rain');
const subRain = document.getElementById('sim-sub-rain');
const valLdr = document.getElementById('sim-val-ldr');
const subLdr = document.getElementById('sim-sub-ldr');
const valTemp = document.getElementById('sim-val-temp');
const valHum = document.getElementById('sim-val-hum');

const modeBadge = document.getElementById('sim-mode-badge');
const modeLocal = document.getElementById('sim-mode-local');
const modeFirebase = document.getElementById('sim-mode-firebase');

let autoDriftInterval = null;

// 1. Thu gọn / Mở rộng Dev Simulator
function toggleSimBar(forceExpand = null) {
  if (!simBar) return;
  const isCollapsed = forceExpand !== null ? !forceExpand : simBar.classList.contains('collapsed');
  if (isCollapsed) {
    simBar.classList.remove('collapsed');
    if (simCollapseIcon) simCollapseIcon.innerText = "▼";
    if (simCollapseText) simCollapseText.innerText = "Thu gọn";
  } else {
    simBar.classList.add('collapsed');
    if (simCollapseIcon) simCollapseIcon.innerText = "▲";
    if (simCollapseText) simCollapseText.innerText = "Mở Simulator";
  }
}

simCollapseBtn?.addEventListener('click', (e) => {
  e.stopPropagation();
  toggleSimBar();
});

simHeaderToggle?.addEventListener('click', () => {
  toggleSimBar();
});

// 2. Chế độ đồng bộ (Local vs Firebase)
function updateSimMode() {
  const isSync = modeFirebase?.checked && !!db;
  if (modeBadge) {
    modeBadge.innerText = isSync ? "FIREBASE SYNC" : "LOCAL MOCK";
    modeBadge.className = `badge badge-sim ${isSync ? 'sync' : ''}`;
  }
}
modeLocal?.addEventListener('change', updateSimMode);
modeFirebase?.addEventListener('change', updateSimMode);

// 3. Cập nhật nhãn khi kéo Slider
function updateSliderLabels() {
  const rain = parseInt(sliderRain?.value || "25000");
  const ldr = parseInt(sliderLdr?.value || "22000");
  const temp = parseFloat(sliderTemp?.value || "32.5");
  const hum = parseFloat(sliderHum?.value || "60.0");

  const rainThresh = parseInt(document.getElementById('input-rain-thresh')?.value || "15000");
  const sunThresh = parseInt(document.getElementById('input-sun-thresh')?.value || "16000");

  if (valRain) valRain.innerText = rain;
  if (subRain) subRain.innerText = rain < rainThresh ? "(Đang mưa)" : "(Khô ráo)";

  if (valLdr) valLdr.innerText = ldr;
  if (subLdr) subLdr.innerText = ldr > sunThresh ? "(Nắng)" : "(Râm / Tối)";

  if (valTemp) valTemp.innerText = `${temp.toFixed(1)} °C`;
  if (valHum) valHum.innerText = `${hum.toFixed(1)} %`;
}

[sliderRain, sliderLdr, sliderTemp, sliderHum].forEach(s => {
  s?.addEventListener('input', () => {
    updateSliderLabels();
  });
});

// 4. Áp dụng dữ liệu giả lập (Push / Apply)
function applySimulatedData() {
  const rain = parseInt(sliderRain?.value || "25000");
  const ldr = parseInt(sliderLdr?.value || "22000");
  const temp = parseFloat(sliderTemp?.value || "32.5");
  const hum = parseFloat(sliderHum?.value || "60.0");

  const rainThresh = parseInt(document.getElementById('input-rain-thresh')?.value || "15000");
  const sunThresh = parseInt(document.getElementById('input-sun-thresh')?.value || "16000");
  const rainPriority = document.getElementById('toggle-rain-priority')?.checked !== false;

  const isRaining = rain < rainThresh;
  const isSunny = ldr > sunThresh;

  // Xác định trạng thái sào theo quy tắc ưu tiên
  let clotheslineState = "OPEN";
  if (rainPriority && isRaining) {
    clotheslineState = "CLOSED";
  } else if (!isRaining && isSunny) {
    clotheslineState = "OPEN";
  } else {
    clotheslineState = "CLOSED";
  }

  const simulatedPayload = {
    temperature: temp,
    humidity: hum,
    water_a0: rain,
    is_raining: isRaining,
    ldr_a1: ldr,
    is_sunny: isSunny,
    clothesline_state: clotheslineState,
    sun_minutes_today: 185,
    last_updated: Math.floor(Date.now() / 1000)
  };

  // Nếu chọn ghi vào Firebase và có kết nối
  if (modeFirebase?.checked && db) {
    update(ref(db, 'smart_clothesline/telemetry'), simulatedPayload)
      .then(() => console.log("[Sim] Đã đẩy telemetry giả lập lên Firebase"))
      .catch(err => console.error("[Sim] Lỗi đẩy Firebase:", err));
  } else {
    // Cập nhật giao diện cục bộ (Local Mock)
    updateUIWithTelemetry(simulatedPayload, true);
  }
}

document.getElementById('btn-sim-apply')?.addEventListener('click', applySimulatedData);

// 5. Kịch bản nhanh (Quick Scenarios)
const scenarios = {
  sunny: { rain: 25200, ldr: 23500, temp: 34.0, hum: 52.0 },
  rainy: { rain: 6000, ldr: 7000, temp: 25.5, hum: 92.0 },
  cloudy: { rain: 25500, ldr: 12000, temp: 28.5, hum: 70.0 },
  night: { rain: 26000, ldr: 2200, temp: 23.5, hum: 84.0 }
};

document.querySelectorAll('.sim-scenario-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const sc = scenarios[btn.dataset.scenario];
    if (!sc) return;

    if (sliderRain) sliderRain.value = sc.rain;
    if (sliderLdr) sliderLdr.value = sc.ldr;
    if (sliderTemp) sliderTemp.value = sc.temp;
    if (sliderHum) sliderHum.value = sc.hum;

    updateSliderLabels();
    applySimulatedData();
  });
});

// 6. Ghi 1 mốc dữ liệu vào Biểu đồ Lịch sử
document.getElementById('btn-sim-push-hist')?.addEventListener('click', () => {
  const rain = parseInt(sliderRain?.value || "25000");
  const ldr = parseInt(sliderLdr?.value || "22000");
  const temp = parseFloat(sliderTemp?.value || "32.5");
  const hum = parseFloat(sliderHum?.value || "60.0");
  const nowTs = Math.floor(Date.now() / 1000);

  if (modeFirebase?.checked && db) {
    update(ref(db, `smart_clothesline/history/${nowTs}`), {
      temp: temp,
      hum: hum,
      water_a0: rain,
      ldr_a1: ldr
    }).then(() => {
      alert("✓ Đã ghi 1 mốc lịch sử lên Firebase!");
    });
  } else {
    // Cập nhật biểu đồ Chart.js cục bộ
    if (dhtChart && adcChart) {
      const timeLabel = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      dhtChart.data.labels.push(timeLabel);
      dhtChart.data.datasets[0].data.push(temp);
      dhtChart.data.datasets[1].data.push(hum);
      if (dhtChart.data.labels.length > 36) {
        dhtChart.data.labels.shift();
        dhtChart.data.datasets[0].data.shift();
        dhtChart.data.datasets[1].data.shift();
      }
      dhtChart.update();

      adcChart.data.labels.push(timeLabel);
      adcChart.data.datasets[0].data.push(rain);
      adcChart.data.datasets[1].data.push(ldr);
      if (adcChart.data.labels.length > 36) {
        adcChart.data.labels.shift();
        adcChart.data.datasets[0].data.shift();
        adcChart.data.datasets[1].data.shift();
      }
      adcChart.update();

      alert("✓ Đã cập nhật 1 mốc dữ liệu vào biểu đồ cục bộ!");
    }
  }
});

// 7. Đặt lại mặc định
document.getElementById('btn-sim-reset')?.addEventListener('click', () => {
  if (sliderRain) sliderRain.value = 25000;
  if (sliderLdr) sliderLdr.value = 22000;
  if (sliderTemp) sliderTemp.value = 32.5;
  if (sliderHum) sliderHum.value = 60.0;
  updateSliderLabels();
  applySimulatedData();
});

// 8. Tự động phát sinh dữ liệu (Auto-drift mỗi 3 giây)
document.getElementById('sim-toggle-auto')?.addEventListener('change', (e) => {
  if (e.target.checked) {
    autoDriftInterval = setInterval(() => {
      if (!sliderTemp || !sliderHum || !sliderLdr) return;
      let curTemp = parseFloat(sliderTemp.value);
      let curHum = parseFloat(sliderHum.value);
      let curLdr = parseInt(sliderLdr.value);

      // Thêm biến động ngẫu nhiên nhỏ
      curTemp = Math.min(42, Math.max(18, curTemp + (Math.random() - 0.5) * 0.4));
      curHum = Math.min(95, Math.max(30, curHum + (Math.random() - 0.5) * 0.8));
      curLdr = Math.min(26400, Math.max(1000, curLdr + Math.round((Math.random() - 0.5) * 400)));

      sliderTemp.value = curTemp.toFixed(1);
      sliderHum.value = curHum.toFixed(1);
      sliderLdr.value = curLdr;

      updateSliderLabels();
      applySimulatedData();
    }, 3000);
  } else {
    if (autoDriftInterval) {
      clearInterval(autoDriftInterval);
      autoDriftInterval = null;
    }
  }
});

// Khởi tạo nhãn cho simulator
updateSliderLabels();
updateSimMode();

// Khởi chạy Firebase khi trang load
initFirebase();
