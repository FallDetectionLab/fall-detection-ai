import httpClient from './httpClient';

// 디버그 로그 함수
const debugLog = (message, data = null) => {
  console.log(`[SafeFall Debug] ${message}`, data || '');
  
  // 8000포트 사용 경고
  if (message.includes('8000')) {
    console.warn('[SafeFall] 🚨 8000포트 사용 감지! httpClient 설정을 확인하세요.');
  }
};

// 알림 관련 API
export const getLatestNotifications = async () => {
  try {
    debugLog('Fetching latest notifications...');
    const response = await httpClient.get('/api/v1/notifications/latest');
    debugLog('Latest notifications fetched successfully', response);
    return response;
  } catch (error) {
    debugLog('Failed to fetch latest notifications:', error.message);
    throw error;
  }
};

export const getNotificationStats = async () => {
  try {
    debugLog('Fetching notification stats');
    const response = await httpClient.get('/api/notifications/stats');
    return response;
  } catch (error) {
    debugLog('Failed to fetch notification stats:', error.message);
    throw error;
  }
};

// 대시보드 관련 API
export const getDashboardStats = async () => {
  try {
    debugLog('Fetching dashboard stats');
    const response = await httpClient.get('/api/dashboard/stats');
    return response;
  } catch (error) {
    debugLog('Failed to fetch dashboard stats:', error.message);
    throw error;
  }
};

export const getRecentVideos = async (limit = 6) => {
  try {
    debugLog(`Fetching recent videos (limit: ${limit})`);
    const response = await httpClient.get(`/api/dashboard/recent-videos?limit=${limit}`);
    
    // 데이터 처리 개선
    if (response.success && response.data) {
      const videos = response.data.map(video => {
        const actualFilename = video.filename || video.video_filename || video.name;
        return {
          ...video,
          filename: actualFilename,  // ✅ 명시적 filename 설정
          video_filename: actualFilename,
          name: actualFilename,
          url: video.url || `/media/videos/${actualFilename}`,
          path: video.path || `/media/videos/${actualFilename}`
        };
      });
      
      return {
        ...response,
        data: videos
      };
    }
    
    return response;
  } catch (error) {
    debugLog('Failed to fetch recent videos:', error.message);
    throw error;
  }
};

// CheckHistory에서 사용할 대시보드 API 호출 함수 추가
export const getVideosFromDashboard = async (limit = 50) => {
  try {
    debugLog(`Fetching videos from dashboard API (limit: ${limit})`);
    const response = await httpClient.get(`/api/dashboard/recent-videos?limit=${limit}`);
    
    // 데이터 형식을 CheckHistory에 맞게 변환
    const videos = (response.data || []).map(video => {
      const actualFilename = video.filename || video.video_filename || video.name;
      return {
        id: video.id,
        filename: actualFilename,  // ✅ 명시적 설정
        video_filename: actualFilename,  // 백업 필드
        name: actualFilename,
        title: video.title || `낙상 감지 #${video.id}`,
        createdAt: video.createdAt || video.created_at,
        created_at: video.createdAt || video.created_at,
        isChecked: video.isChecked || video.processed || false,
        processed: video.isChecked || video.processed || false,
        confidence: video.confidence || 0.95,
        device_id: video.device_id || 'camera_01',
        trigger_type: 'manual',
        path: video.url || `/media/videos/${actualFilename}`,
        url: video.url || `/media/videos/${actualFilename}`,
        type: 'fall'
      };
    });
    
    return {
      data: videos,
      count: videos.length,
      success: response.success || true
    };
  } catch (error) {
    debugLog('Failed to fetch videos from dashboard:', error.message);
    throw error;
  }
};

// 스트림 관련 API
export const getStreamStatus = async () => {
  try {
    const response = await httpClient.get('/api/stream/status');
    return response;
  } catch (error) {
    debugLog('Failed to fetch stream status:', error.message);
    throw error;
  }
};

export const getRealtimeStatus = async () => {
  try {
    const response = await httpClient.get('/api/realtime/status');
    return response;
  } catch (error) {
    debugLog('Failed to fetch realtime status:', error.message);
    throw error;
  }
};

// 낙상 이벤트 관련 API
export const getFallEvents = async (limit = 100) => {
  try {
    debugLog(`Fetching fall events (limit: ${limit})`);
    const response = await httpClient.get(`/api/events/falls?limit=${limit}`);
    return response;
  } catch (error) {
    debugLog('Failed to fetch fall events:', error.message);
    throw error;
  }
};

// URL 생성 함수들 - httpClient의 baseURL 사용
export const getEventVideo = (eventId) => {
  try {
    debugLog(`Getting event video URL: ${eventId}`);
    // 메디어 비디오 URL 사용
    return `${httpClient.defaults.baseURL}/media/videos/${eventId}`;
  } catch (error) {
    debugLog('Failed to get event video URL:', error.message);
    throw error;
  }
};

// 비디오 스트림 URL - httpClient의 baseURL 사용
export const getVideoStreamUrl = () => {
  return `${httpClient.defaults.baseURL}/video_feed`;  // ✅ 주요 라우트 사용
};

export const getLiveStreamUrl = () => {
  return `${httpClient.defaults.baseURL}/api/stream/live`;
};

// 서버 연결 테스트 함수
export const testConnection = async () => {
  try {
    debugLog('Testing server connection...');
    const response = await httpClient.get('/api/stream/status');
    debugLog('✅ Server connection successful', response);
    return true;
  } catch (error) {
    debugLog('❌ Server connection failed:', error.message);
    return false;
  }
};

// 에러 처리 헬퍼
export const handleApiError = (error, context = '') => {
  const errorMessage = error.response?.data?.message || error.message || 'Unknown error';
  const statusCode = error.response?.status;
  
  debugLog(`API Error ${context}:`, {
    message: errorMessage,
    status: statusCode,
    url: error.config?.url
  });

  // 네트워크 에러 처리
  if (error.code === 'ERR_NETWORK' || error.message.includes('ERR_CONNECTION_REFUSED')) {
    return {
      type: 'NETWORK_ERROR',
      message: '서버에 연결할 수 없습니다. Flask 서버가 실행 중인지 확인해주세요.',
      originalError: error
    };
  }

  // HTTP 상태 코드별 처리
  switch (statusCode) {
    case 404:
      return { type: 'NOT_FOUND', message: '요청한 리소스를 찾을 수 없습니다.', originalError: error };
    case 500:
      return { type: 'SERVER_ERROR', message: '서버 내부 오류가 발생했습니다.', originalError: error };
    default:
      return { type: 'UNKNOWN_ERROR', message: errorMessage, originalError: error };
  }
};

// 비디오 관련 API 추가 (🔥 주요 수정)
export const getVideos = async (params = {}) => {
  try {
    const { trigger_type, limit = 50, ...otherParams } = params;
    debugLog(`Fetching videos (trigger_type: ${trigger_type || 'ALL'}, limit: ${limit})`);
    
    // 🔥 수정: trigger_type이 없으면 모든 영상 가져오기
    const queryString = new URLSearchParams({
      ...(trigger_type ? { trigger_type } : {}),  // trigger_type이 있을 때만 추가
      limit: limit.toString(),
      ...otherParams
    }).toString();
    
    const response = await httpClient.get(`/api/videos/saved?${queryString}`);
    debugLog('Raw API response:', response);
    
    // 🔥 주요 버그 수정: response.videos 배열 사용
    const videosArray = response.videos || [];
    debugLog('Videos array from response:', videosArray);
    
    // 데이터 형식을 프론트엔드에 맞게 변환
    const videos = videosArray.map(video => {
      // 파일명 우선순위: filename > video_filename > name
      const actualFilename = video.filename || video.video_filename || video.name;
      debugLog(`Processing video: ${video.id}, filename: ${actualFilename}`);
      
      return {
        id: video.id,
        filename: actualFilename,  // ✅ 주요 수정: 명시적 filename 설정
        video_filename: actualFilename,  // 백업 필드
        name: actualFilename,
        title: video.title || `낙상 감지 #${video.id}`,
        createdAt: video.created_at || video.createdAt,
        created_at: video.created_at || video.createdAt,
        isChecked: video.processed || video.isChecked || false,
        processed: video.processed || video.isChecked || false,
        confidence: video.confidence || 0.95,
        device_id: video.device_id || 'manual_trigger',
        trigger_type: video.trigger_type || 'manual',
        path: video.path || `/media/videos/${actualFilename}`,
        url: video.url || `/media/videos/${actualFilename}`,
        type: 'fall'
      };
    });
    
    debugLog('Processed videos:', videos);
    
    return {
      data: videos,
      count: videos.length,
      success: response.success || true
    };
  } catch (error) {
    debugLog('Failed to fetch videos:', error.message);
    throw error;
  }
};

export const getVideoById = async (videoId) => {
  try {
    debugLog(`Fetching video by ID: ${videoId}`);
    const response = await httpClient.get(`/api/videos/${videoId}`);
    
    // 비디오 데이터 처리
    if (response.success && response.video) {
      const video = response.video;
      const actualFilename = video.filename || video.video_filename || video.name;
      
      return {
        success: true,
        video: {
          id: video.id,
          filename: actualFilename,  // ✅ 명시적 filename 설정
          video_filename: actualFilename,
          name: actualFilename,
          title: video.title || `낙상 감지 #${video.id}`,
          createdAt: video.created_at || video.createdAt,
          created_at: video.created_at || video.createdAt,
          isChecked: video.processed || video.isChecked || false,
          processed: video.processed || video.isChecked || false,
          confidence: video.confidence || 0.95,
          device_id: video.device_id || 'manual_trigger',
          path: video.path || `/media/videos/${actualFilename}`,
          url: video.url || `/media/videos/${actualFilename}`,
          type: 'fall'
        }
      };
    }
    
    return response;
  } catch (error) {
    debugLog('Failed to fetch video by ID:', error.message);
    throw error;
  }
};

export const updateVideoStatus = async (videoId, isChecked) => {
  try {
    debugLog(`Updating video status: ${videoId} -> ${isChecked}`);
    const response = await httpClient.put(`/api/videos/${videoId}/status`, {
      isChecked
    });
    return response;
  } catch (error) {
    debugLog('Failed to update video status:', error.message);
    throw error;
  }
};

export const deleteVideo = async (videoId) => {
  try {
    debugLog(`Deleting video: ${videoId}`);
    const response = await httpClient.delete(`/api/videos/${videoId}`);
    return response;
  } catch (error) {
    debugLog('Failed to delete video:', error.message);
    throw error;
  }
};

// 스트림 관련 API 추가
export const getLiveStream = async () => {
  try {
    debugLog('Fetching live stream info');
    const response = await httpClient.get('/api/stream/live');
    return response;
  } catch (error) {
    debugLog('Failed to fetch live stream info:', error.message);
    throw error;
  }
};

export const startStream = async () => {
  try {
    debugLog('Starting stream');
    const response = await httpClient.post('/api/stream/start');
    return response;
  } catch (error) {
    debugLog('Failed to start stream:', error.message);
    throw error;
  }
};

export const stopStream = async () => {
  try {
    debugLog('Stopping stream');
    const response = await httpClient.post('/api/stream/stop');
    return response;
  } catch (error) {
    debugLog('Failed to stop stream:', error.message);
    throw error;
  }
};

export const findWorkingStreamUrl = async (baseUrl) => {
  try {
    debugLog(`Testing stream URL: ${baseUrl}`);
    const response = await httpClient.get('/api/stream/test', {
      params: { url: baseUrl }
    });
    return response;
  } catch (error) {
    debugLog('Failed to test stream URL:', error.message);
    return { accessible: false, url: baseUrl };
  }
};

// 로그인 관련 API 추가
export const login = async (credentials) => {
  try {
    debugLog('Attempting login');
    const response = await httpClient.post('/api/auth/login', credentials);
    return response;
  } catch (error) {
    debugLog('Failed to login:', error.message);
    throw error;
  }
};

export const getLastPositiveDetection = async () => {
  try {
    debugLog('Fetching last positive detection');
    const response = await httpClient.get('/api/detect/last_positive');
    return response;
  } catch (error) {
    debugLog('Failed to fetch last positive detection:', error.message);
    return {
      detection: {
        fall_detected: false,
        confidence: 0.0,
        timestamp: Date.now(),
        bbox: []
      },
      success: false
    };
  }
};

export const getLatestFrame = async () => {
  try {
    debugLog('Fetching latest frame');
    const response = await httpClient.get('/api/frame/latest');
    return response;
  } catch (error) {
    debugLog('Failed to fetch latest frame:', error.message);
    return {
      frame_data: null,
      timestamp: Date.now(),
      success: false,
      message: 'Camera not available'
    };
  }
};

const apiService = {
  // 알림 관련
  getLatestNotifications,
  getNotificationStats,
  
  // 대시보드 관련
  getDashboardStats,
  getRecentVideos,
  getVideosFromDashboard,  // 추가
  
  // 스트리밍 관련
  getStreamStatus,
  getRealtimeStatus,
  getLiveStream,
  startStream,
  stopStream,
  findWorkingStreamUrl,
  
  // 비디오 관련 (🔥 수정됨)
  getVideos,
  getVideoById,
  updateVideoStatus,
  deleteVideo,
  
  // 낙상 이벤트 관련
  getFallEvents,
  getEventVideo,
  getLastPositiveDetection,
  
  // 프레임 관련
  getLatestFrame,
  
  // URL 생성
  getVideoStreamUrl,
  getLiveStreamUrl,
  
  // 로그인 관련
  login,
  
  // 유틸리티
  testConnection,
  handleApiError
};

export default apiService;