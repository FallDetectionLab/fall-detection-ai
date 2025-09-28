/**
 * HTTP 클라이언트 유틸리티
 * Fetch API를 래핑하여 인증, 에러 처리, 캐싱, 타임아웃, 재시도 등을 제공합니다.
 */

import { 
  API_BASE_URL, 
  DEFAULT_HEADERS, 
  AUTH_CONFIG, 
  HTTP_STATUS, 
  ERROR_MESSAGES,
  debugLog 
} from '../config/api.js';

class HttpClient {
  constructor() {
    this.baseURL = API_BASE_URL;            // 예: http://.../api/v1
    this.cache = new Map();
    this.pendingRequests = new Map();
    this.defaultTimeoutMs = 15000;      // 기본 타임아웃 15s
    this.defaultRetries = 1;            // 기본 재시도 1회
  }

  buildFullUrl(url) {
    try {
      if (/^https?:\/\//i.test(url)) return url;
      return new URL(url, this.baseURL.endsWith('/') ? this.baseURL : this.baseURL + '/').toString();
    } catch (e) {
      return url.startsWith('http') ? url : `${this.baseURL}${url.startsWith('/') ? '' : '/'}${url}`;
    }
  }

  // 인증 토큰 관리
  getAuthToken() { return localStorage.getItem(AUTH_CONFIG.TOKEN_KEY); }
  setAuthToken(token) { token ? localStorage.setItem(AUTH_CONFIG.TOKEN_KEY, token) : localStorage.removeItem(AUTH_CONFIG.TOKEN_KEY); }
  getRefreshToken() { return localStorage.getItem(AUTH_CONFIG.REFRESH_TOKEN_KEY); }
  setRefreshToken(token) { token ? localStorage.setItem(AUTH_CONFIG.REFRESH_TOKEN_KEY, token) : localStorage.removeItem(AUTH_CONFIG.REFRESH_TOKEN_KEY); }
  clearAuthTokens() {
    localStorage.removeItem(AUTH_CONFIG.TOKEN_KEY);
    localStorage.removeItem(AUTH_CONFIG.REFRESH_TOKEN_KEY);
  }

  buildHeaders(customHeaders = {}) {
    const headers = { ...DEFAULT_HEADERS, ...customHeaders };
    const token = this.getAuthToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
  }

  async handleResponseError(response, url) {
    const errorData = { status: response.status, statusText: response.statusText, url };
    try {
      const bodyText = await response.text();
      if (bodyText) errorData.body = JSON.parse(bodyText);
    } catch (_) {}

    debugLog('HTTP Error:', errorData);

    switch (response.status) {
      case HTTP_STATUS.UNAUTHORIZED:
        if (this.getRefreshToken()) {
          const refreshSuccess = await this.refreshAuthToken();
          if (refreshSuccess) throw new Error('TOKEN_REFRESHED');
        }
        this.clearAuthTokens();
        window.location.href = '/login';
        throw new Error(ERROR_MESSAGES.UNAUTHORIZED || '인증이 필요합니다.');

      case HTTP_STATUS.FORBIDDEN:
        throw new Error(errorData.body?.message || ERROR_MESSAGES.FORBIDDEN || '접근 권한이 없습니다.');

      case HTTP_STATUS.NOT_FOUND:
        throw new Error(errorData.body?.message || `${ERROR_MESSAGES.NOT_FOUND || '리소스를 찾을 수 없습니다.'}\n→ ${url}`);

      case 405:
        throw new Error(errorData.body?.message || `허용되지 않은 메서드입니다(405).\n→ ${url}`);

      case HTTP_STATUS.UNPROCESSABLE_ENTITY:
        throw new Error(errorData.body?.message || ERROR_MESSAGES.VALIDATION_ERROR || '유효성 검사 오류입니다.');

      case HTTP_STATUS.INTERNAL_SERVER_ERROR:
      case HTTP_STATUS.BAD_GATEWAY:
      case HTTP_STATUS.SERVICE_UNAVAILABLE:
        throw new Error(errorData.body?.message || ERROR_MESSAGES.SERVER_ERROR || '서버 오류가 발생했습니다.');

      default:
        throw new Error(errorData.body?.message || ERROR_MESSAGES.NETWORK_ERROR || '네트워크 에러가 발생했습니다.');
    }
  }

  async refreshAuthToken() {
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) return false;

      const resp = await fetch(this.buildFullUrl('/auth/refresh-token'), {
        method: 'POST',
        headers: DEFAULT_HEADERS,
        body: JSON.stringify({ refreshToken })
      });

      if (resp.ok) {
        const data = await resp.json();
        this.setAuthToken(data.accessToken);
        if (data.refreshToken) this.setRefreshToken(data.refreshToken);
        debugLog('Token refreshed successfully');
        return true;
      }
      return false;
    } catch (error) {
      debugLog('Token refresh failed:', error);
      return false;
    }
  }

  getCacheKey(url, method, body) {
    return `${method}:${url}:${body ? JSON.stringify(body) : ''}`;
  }
  getFromCache(key, cacheTime = 5 * 60 * 1000) {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < cacheTime) {
      debugLog('Cache hit:', key);
      return cached.data;
    }
    return null;
  }
  setCache(key, data) { this.cache.set(key, { data, timestamp: Date.now() }); }
  clearCache(pattern = null) {
    if (pattern) {
      for (const key of this.cache.keys()) if (key.includes(pattern)) this.cache.delete(key);
    } else {
      this.cache.clear();
    }
  }

  async handleDuplicateRequest(key, requestFn) {
    if (this.pendingRequests.has(key)) return await this.pendingRequests.get(key);
    const requestPromise = requestFn();
    this.pendingRequests.set(key, requestPromise);
    try {
      const result = await requestPromise;
      this.pendingRequests.delete(key);
      return result;
    } catch (error) {
      this.pendingRequests.delete(key);
      throw error;
    }
  }

  async request(url, options = {}) {
    const {
      method = 'GET',
      headers = {},
      body = null,
      cache = false,
      cacheTime = 5 * 60 * 1000,
      retries = this.defaultRetries,
      timeoutMs = this.defaultTimeoutMs,
      ...otherOptions
    } = options;

    const fullUrl = this.buildFullUrl(url);
    const methodUpper = String(method).toUpperCase();

    const requestHeaders = this.buildHeaders(headers);

    if (body instanceof FormData) delete requestHeaders['Content-Type'];
    if (!body && (methodUpper === 'GET' || methodUpper === 'HEAD' || methodUpper === 'DELETE')) {
      delete requestHeaders['Content-Type'];
    }
    if (!body && requestHeaders['X-Requested-With']) {
      delete requestHeaders['X-Requested-With'];
    }

    const config = { method: methodUpper, headers: requestHeaders, ...otherOptions };
    if (body && !(body instanceof FormData)) {
      config.body = typeof body === 'string' ? body : JSON.stringify(body);
    } else if (body instanceof FormData) {
      config.body = body;
    }

    debugLog(`${methodUpper} ${fullUrl}`, { headers: requestHeaders, body });

    if (methodUpper === 'GET' && cache) {
      const cacheKey = this.getCacheKey(fullUrl, methodUpper, body);
      const cachedData = this.getFromCache(cacheKey, cacheTime);
      if (cachedData) return cachedData;
    }

    const requestKey = this.getCacheKey(fullUrl, methodUpper, body);

    return await this.handleDuplicateRequest(requestKey, async () => {
      let lastError;

      for (let attempt = 0; attempt <= retries; attempt++) {
        const controller = new AbortController();
        const timerId = setTimeout(() => controller.abort(), timeoutMs);

        try {
          const response = await fetch(fullUrl, { ...config, signal: controller.signal });
          clearTimeout(timerId);

          if (!response.ok) {
            await this.handleResponseError(response, fullUrl);
          }

          const contentType = response.headers.get('content-type') || '';
          let data;
          if (contentType.includes('application/json')) {
            data = await response.json();
          } else if (contentType.includes('text/')) {
            data = await response.text();
          } else {
            data = await response.blob();
          }

          debugLog(`Response ${response.status}:`, data);

          if (methodUpper === 'GET' && cache && response.ok) {
            const cacheKey = this.getCacheKey(fullUrl, methodUpper, body);
            this.setCache(cacheKey, data);
          }

          return data;

        } catch (error) {
          clearTimeout(timerId);
          lastError = error;

          if (error?.message === 'TOKEN_REFRESHED' && attempt < retries) {
            config.headers = this.buildHeaders(headers);
            continue;
          }

          const isNetworkLike =
            error?.name === 'AbortError' ||
            error?.name === 'TypeError' ||
            (typeof error?.message === 'string' && /fetch|network|timeout|Failed to fetch/i.test(error.message));

          if (attempt < retries && isNetworkLike) {
            await new Promise(res => setTimeout(res, 1000 * (attempt + 1)));
            continue;
          }

          break;
        }
      }

      if (lastError?.name === 'AbortError') {
        throw new Error(ERROR_MESSAGES.NETWORK_TIMEOUT || '요청이 시간 초과되었습니다.');
      }
      throw lastError || new Error(ERROR_MESSAGES.NETWORK_ERROR || '네트워크 에러가 발생했습니다.');
    });
  }

  // 편의 메서드
  async get(url, options = {})    { return this.request(url, { ...options, method: 'GET' }); }
  async post(url, body = null, options = {})  { return this.request(url, { ...options, method: 'POST', body }); }
  async put(url, body = null, options = {})   { return this.request(url, { ...options, method: 'PUT', body }); }
  async patch(url, body = null, options = {}) { return this.request(url, { ...options, method: 'PATCH', body }); }
  async delete(url, options = {}) { return this.request(url, { ...options, method: 'DELETE' }); }
}

// 싱글톤 인스턴스
export const httpClient = new HttpClient();
export default httpClient;
