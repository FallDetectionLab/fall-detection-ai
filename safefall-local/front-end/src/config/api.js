/**
 * API 설정 파일 — 프런트 전역에서 공통 사용
 * - httpClient.js, services/api.js가 요구하는 모든 export를 포함합니다.
 */

// === 안전 보정 유틸 ===
const trimEndSlash = (s = "") => s.replace(/\/+$/, "");         // 끝 슬래시 제거
const trimSlash = (s = "") => s.replace(/^\/+|\/+$/g, "");       // 양끝 슬래시 제거
const ensureLeadSlash = (s = "") => (s.startsWith("/") ? s : `/${s}`);

// === 환경 변수 ===
export const DEBUG_MODE = import.meta.env.VITE_DEBUG_MODE === "true";
export const MOCK_DATA  = import.meta.env.VITE_MOCK_DATA === "true";

// API Base URL (운영: http 사용)
export const API_BASE_URL = trimEndSlash(
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api"
);

// WebSocket URL (옵션)
export const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || "ws://localhost:8080";

// === 공통 헤더 ===
export const DEFAULT_HEADERS = {
  "Content-Type": "application/json",
  "Accept": "application/json",
  // "X-Requested-With": "XMLHttpRequest", // Preflight 유발 → 기본 비활성화 권장
};

// === 디버그 로그 ===
export const debugLog = (...args) => {
  if (DEBUG_MODE) console.log("[SafeFall Debug]", ...args);
};

// === HTTP 상태 코드 ===
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503,
  GATEWAY_TIMEOUT: 504,
};

// === 에러 메시지 상수 ===
export const ERROR_MESSAGES = {
  NETWORK_ERROR: "네트워크 연결을 확인해주세요.",
  NETWORK_TIMEOUT: "요청이 시간 초과되었습니다.",
  SERVER_ERROR: "서버에 일시적인 문제가 발생했습니다.",
  UNAUTHORIZED: "인증이 필요합니다.",
  FORBIDDEN: "접근 권한이 없습니다.",
  NOT_FOUND: "요청한 리소스를 찾을 수 없습니다.",
  VALIDATION_ERROR: "입력한 정보를 다시 확인해주세요.",
};

// === 인증(토큰) 키/설정 ===
export const AUTH_CONFIG = {
  TOKEN_KEY: "accessToken",
  REFRESH_TOKEN_KEY: "refreshToken",
  TOKEN_EXPIRE_MINUTES: parseInt(import.meta.env.VITE_TOKEN_EXPIRE_MINUTES || "60", 10),
  AUTO_REFRESH_THRESHOLD: 5, // 만료 5분 전 자동 갱신 여유값
};

// === 페이지네이션 ===
export const PAGINATION_CONFIG = {
  DEFAULT_PAGE: 1,
  DEFAULT_PAGE_SIZE: parseInt(import.meta.env.VITE_DEFAULT_PAGE_SIZE || "20", 10),
  MAX_PAGE_SIZE: 100,
};

// === 캐시 설정 ===
export const CACHE_CONFIG = {
  ENABLE_CACHE: true,
  DEFAULT_CACHE_TIME: 5 * 60 * 1000,     // 5분
  VIDEO_LIST_CACHE_TIME: 2 * 60 * 1000,  // 2분
  STATS_CACHE_TIME: 30 * 1000,           // 30초
};

// === 엔드포인트 (반드시 상대 경로 유지) ===
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: "/auth/login",
    LOGOUT: "/auth/logout",
    REFRESH: "/auth/refresh-token",
    CHECK_SESSION: "/auth/check-session",
    CHANGE_PASSWORD: "/auth/change-password",
  },
  USERS: {
    PROFILE: "/users/profile",
    UPDATE_PROFILE: "/users/profile",
    LIST: "/users",
    CREATE: "/users",
    DELETE: "/users/:id",
  },
  VIDEOS: {
    LIST: "/videos",
    DETAIL: "/videos/:id",
    CREATE: "/videos",
    UPDATE: "/videos/:id",
    DELETE: "/videos/:id",
    STATUS: "/videos/:id/status",
    DOWNLOAD: "/videos/:id/download",
    THUMBNAIL: "/videos/:id/thumbnail",
  },
  STREAM: {
    LIVE: "/stream/live",
    STATUS: "/stream/status",
    START: "/stream/start",
    STOP: "/stream/stop",
    SETTINGS: "/stream/settings",
  },
  DASHBOARD: {
    STATS: "/dashboard/stats",
    RECENT_VIDEOS: "/dashboard/recent-videos",
    CHART_DATA: "/dashboard/chart-data",
    ALERTS: "/dashboard/alerts",
  },
  SETTINGS: {
    GENERAL: "/settings/general",
    NOTIFICATIONS: "/settings/notifications",
    CAMERA: "/settings/camera",
    THRESHOLD: "/settings/threshold",
  },
  UPLOAD: {
    VIDEO: "/upload/video",
    IMAGE: "/upload/image",
    PRESIGNED_URL: "/upload/presigned-url",
  },
};

// === URL Builder ===
export const buildApiUrl = (endpoint, params = {}) => {
  // endpoint는 상대 경로여야 하며, 앞 슬래시를 보장
  let url = `${API_BASE_URL}${ensureLeadSlash(endpoint)}`;
  // path param 치환 (:id 등)
  Object.keys(params).forEach((key) => {
    url = url.replace(`:${key}`, params[key]);
  });
  return url;
};

// === QueryString Builder ===
export const buildQueryString = (params = {}) => {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    if (Array.isArray(value)) {
      value.forEach((v) => sp.append(key, v));
    } else {
      sp.append(key, value);
    }
  });
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
};

// 디버그 출력(선택)
if (DEBUG_MODE) {
  debugLog("API_BASE_URL =", API_BASE_URL);
  debugLog("MOCK_DATA    =", MOCK_DATA);
}

if (DEBUG_MODE) console.log("[DEBUG] API_BASE_URL =", API_BASE_URL);
