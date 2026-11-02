// ==============================================================================
// config.js - Cấu hình Firebase & GitHub cho WebApp V2.0
// Người dùng có thể chỉnh sửa trực tiếp hoặc thông qua tab Cài đặt trên WebApp
// ==============================================================================

export const DEFAULT_CONFIG = {
  // 1. Cấu hình Firebase Realtime Database
  firebase: {
    apiKey: "AIzaSy_DEFAULT_IOT_KEY",
    databaseURL: "https://iotsmartdryingrack-default-rtdb.asia-southeast1.firebasedatabase.app",
    projectId: "iotsmartdryingrack-default-rtdb"
  },

  // 2. Cấu hình GitHub Repository phục vụ OTA
  github: {
    user: "chuvitvang",
    repo: "Iot_smart_drying_rack",
    branch: "main"
  }
};

export function loadUserConfig() {
  const saved = localStorage.getItem("clothesline_config_v2");
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      return {
        firebase: { ...DEFAULT_CONFIG.firebase, ...(parsed.firebase || {}) },
        github: { ...DEFAULT_CONFIG.github, ...(parsed.github || {}) }
      };
    } catch (e) {
      console.error("Lỗi đọc cấu hình LocalStorage:", e);
    }
  }
  return DEFAULT_CONFIG;
}

export function saveUserConfig(cfg) {
  localStorage.setItem("clothesline_config_v2", JSON.stringify(cfg));
}
