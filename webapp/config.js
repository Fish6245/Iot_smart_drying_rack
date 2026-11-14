// ==============================================================================
// config.js - Cấu hình Firebase & GitHub cho WebApp V2.0
// Người dùng có thể chỉnh sửa trực tiếp hoặc thông qua tab Cài đặt trên WebApp
// ==============================================================================

async function loadLocalEnv() {
  try {
    const response = await fetch(new URL("./.env", import.meta.url), {
      cache: "no-store",
    });
    if (response.status === 404) return {};
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const values = {};
    for (const line of (await response.text()).split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const separator = trimmed.indexOf("=");
      if (separator < 0) continue;

      const key = trimmed.slice(0, separator).trim();
      let value = trimmed.slice(separator + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      values[key] = value;
    }
    return values;
  } catch (error) {
    console.warn("Không thể đọc webapp/.env; dùng cấu hình đã lưu trong trình duyệt.", error);
    return {};
  }
}

const localEnv = await loadLocalEnv();

export const DEFAULT_CONFIG = {
  // 1. Cấu hình Firebase Realtime Database
  firebase: {
    apiKey: localEnv.FIREBASE_API_KEY || "",
    databaseURL: localEnv.FIREBASE_DATABASE_URL || "",
    projectId: localEnv.FIREBASE_PROJECT_ID || "",
  },

  // 2. Cấu hình GitHub Repository phục vụ OTA
  github: {
    user: "chuvitvang",
    repo: "Iot_smart_drying_rack",
    branch: "main",
  },
};

export function loadUserConfig() {
  const saved = localStorage.getItem("clothesline_config_v2");
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      return {
        firebase: { ...DEFAULT_CONFIG.firebase, ...(parsed.firebase || {}) },
        github: { ...DEFAULT_CONFIG.github, ...(parsed.github || {}) },
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
