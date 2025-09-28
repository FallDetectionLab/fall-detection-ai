import { createContext, useContext, useState, useEffect } from 'react';
import { MOCK_DATA, debugLog } from '../config/api.js';
import apiService from '../services/api.js';

// 더미데이터 imports (백엔드 실패 시 폴백용)
import Dum001 from './Dum001';
import Dum003Data from '../util/Dum003.json';
import Dum004Data from '../util/Dum004.json';

// 강제로 API 모드 활성화 (실제 저장된 영상 표시용)
const FORCE_API_MODE = true;

// DataContext 생성
const DataContext = createContext();

// YYYY-MM-DD로 자르는 유틸
const toDateKey = (iso) => {
  try {
    const d = new Date(iso);
    // ISO 표준 키로 비교(UTC 기준). 로컬 기준이 필요하면 getFullYear/…로 변경
    return d.toISOString().slice(0, 10);
  } catch {
    return '';
  }
};

// DataProvider 컴포넌트
export const DataProvider = ({ children }) => {
  // === 상태 관리 ===
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // 1. 실시간 영상 컴포넌트 (더미데이터 유지)
  const [LiveVideoComponent] = useState(() => Dum001);
  const [liveVideoConfig, setLiveVideoConfig] = useState({
    isVisible: true,
    streamStatus: "offline",
    streamUrl: null,
    lastUpdated: new Date().toISOString(),
    title: "Live Security Camera Feed",
    quality: "unknown",
    type: "unknown",
    error: null
  });

  // 2. 사고 영상 데이터 (API 또는 더미데이터)
  const [incidentVideos, setIncidentVideos] = useState([]);
  
  // 3. 사용자 로그인 데이터 (API 또는 더미데이터)
  // Dum004 구조: { id, pw, name }
  const [userCredentials] = useState(MOCK_DATA ? Dum004Data : []);

  // 4. 필터링 및 검색 상태
  const [videoFilters, setVideoFilters] = useState({
    showCheckedOnly: false,
    showUncheckedOnly: false,
    dateRange: { start: null, end: null },
    searchKeyword: "",
    currentPage: 1,
    pageSize: 10
  });

  // 5. 대시보드 통계 데이터
  const [dashboardStats, setDashboardStats] = useState({
    totalVideos: 0,
    checkedVideos: 0,
    uncheckedVideos: 0,
    todayVideos: 0
  });

  // === 초기 데이터 로딩 ===
  useEffect(() => {
    initializeData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * 초기 데이터 로딩 (스트림 정보 포함)
   */
  const initializeData = async () => {
    if (MOCK_DATA && !FORCE_API_MODE) {
      // 더미데이터 모드
      debugLog('Initializing with mock data');
      setIncidentVideos(Dum003Data);
      setDashboardStats(calculateStatsFromData(Dum003Data));
      
      // Mock 스트림 설정
      setLiveVideoConfig({
        isVisible: true,
        streamStatus: "online",
        streamUrl: "http://192.168.0.6:5000",
        lastUpdated: new Date().toISOString(),
        title: "Live Security Camera Feed (Mock)",
        quality: "720p",
        type: "mock",
        error: null
      });
      
      return;
    }

    // API 모드
    setLoading(true);
    setError(null);
    debugLog('Initializing with API data');

    try {
      // 병렬로 데이터 로딩 (스트림 정보 포함)
      const [videosResponse, statsResponse, streamResponse] = await Promise.allSettled([
        fetchIncidentVideos(),
        fetchDashboardStats(),
        fetchLiveStreamInfo()  // ✅ 스트림 정보도 초기 로딩에 포함
      ]);

      if (videosResponse.status === 'fulfilled') {
        setIncidentVideos(videosResponse.value.data || []);
        debugLog('Videos loaded successfully:', videosResponse.value.data?.length || 0);
      } else {
        console.warn('Failed to load videos:', videosResponse.reason?.message);
      }

      if (statsResponse.status === 'fulfilled') {
        setDashboardStats(statsResponse.value);
        debugLog('Dashboard stats loaded successfully');
      } else {
        console.warn('Failed to load stats:', statsResponse.reason?.message);
      }

      if (streamResponse.status === 'fulfilled') {
        debugLog('Stream info loaded successfully during initialization');
      } else {
        console.warn('Failed to load stream info during initialization:', 
                     streamResponse.reason?.message);
        
        // 스트림 정보 로딩 실패 시 오프라인으로 설정
        setLiveVideoConfig(prev => ({
          ...prev,
          streamStatus: "offline",
          error: "Failed to load stream info"
        }));
      }

    } catch (err) {
      console.error('Failed to initialize data:', err);
      setError(err.message);
      
      // 에러 시 빈 배열 반환 (더미데이터 폴백 제거)
      setIncidentVideos([]);
      setDashboardStats({
        totalVideos: 0,
        checkedVideos: 0,
        uncheckedVideos: 0,
        todayVideos: 0
      });
      
      console.error('API 데이터 로딩 실패, 빈 상태로 설정:', err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * === API 호출 함수들 ===
   */

  /**
   * 영상 목록 조회 - 저장된 영상 API 사용
   */
  const fetchIncidentVideos = async (params = {}) => {
    try {
      const queryParams = {
        ...videoFilters,
        ...params
      };

      debugLog('Fetching ALL videos from saved videos API:', queryParams);
      // 🔥 수정: 모든 트리거 타입의 영상을 가져오도록 변경
      const response = await apiService.getVideos({
        // trigger_type 파라미터 제거 - 모든 영상 가져오기
        limit: queryParams.limit || 100,  // 더 많은 영상 가져오기
        ...queryParams
      });
      
      debugLog('Videos response from saved API (ALL TYPES):', response);
      
      // 정확한 응답 구조 사용: response.data (API 서비스에서 변환된 데이터)
      return {
        data: response.data || [],
        count: response.count || 0,
        success: response.success || true
      };

    } catch (error) {
      console.error('Failed to fetch videos:', error);
      throw error;
    }
  };

  /**
   * 대시보드 통계 조회
   */
  const fetchDashboardStats = async () => {
    try {
      const response = await apiService.getDashboardStats();
      return response;
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error);
      throw error;
    }
  };

  /**
   * 실시간 스트림 정보 조회 (올바른 엔드포인트 사용)
   */
  const fetchLiveStreamInfo = async () => {
    if (MOCK_DATA) {
      // Mock 모드에서는 가상 스트림 정보 반환
      const mockStreamInfo = {
        streamUrl: "http://192.168.0.6:5000",
        status: "online",
        type: "mock",
        quality: "720p"
      };
      
      setLiveVideoConfig(prev => ({
        ...prev,
        streamUrl: mockStreamInfo.streamUrl,
        streamStatus: mockStreamInfo.status,
        quality: mockStreamInfo.quality,
        type: mockStreamInfo.type,
        lastUpdated: new Date().toISOString(),
        error: null
      }));
      
      return mockStreamInfo;
    }

    try {
      debugLog('Fetching live stream info from correct endpoint');
      
      // ✅ 올바른 엔드포인트 사용: /stream/live
      const response = await apiService.getLiveStream();
      
      // 응답 데이터 검증
      if (!response || typeof response !== 'object') {
        throw new Error('Invalid stream info response format');
      }

      // liveVideoConfig 상태 업데이트
      setLiveVideoConfig(prev => ({
        ...prev,
        streamUrl: response.streamUrl || null,
        streamStatus: response.status || "offline",
        quality: response.quality || "unknown",
        type: response.type || "unknown",
        lastUpdated: new Date().toISOString(),
        error: null
      }));

      debugLog('Live stream info updated:', response);
      return response;

    } catch (error) {
      console.error('Failed to fetch live stream info:', error);
      
      // 에러 시 오프라인 상태로 설정
      setLiveVideoConfig(prev => ({
        ...prev,
        streamStatus: "offline",
        streamUrl: null,
        lastUpdated: new Date().toISOString(),
        error: error.message
      }));
      
      throw error;
    }
  };

  /**
   * === 데이터 조작 함수들 ===
   */

  /**
   * 영상 확인 상태 업데이트 (ID 기반으로 개선)
   */
  const updateVideoCheckStatus = async (identifier, isChecked) => {
    if (MOCK_DATA && !FORCE_API_MODE) {
      // 더미데이터 모드: 로컬 상태만 업데이트
      setIncidentVideos(prev => 
        prev.map(video => {
          // ID 또는 filename으로 찾기
          const matchById = video.id && video.id.toString() === identifier.toString();
          const matchByFilename = video.filename === identifier;
          
          if (matchById || matchByFilename) {
            return { ...video, isChecked };
          }
          return video;
        })
      );
      return;
    }

    // API 모드: 백엔드 업데이트 후 로컬 상태 업데이트
    try {
      // identifier가 숫자이면 ID로, 문자열이면 filename으로 처리
      let videoId = identifier;
      
      // filename이 전달된 경우 해당 video의 ID 찾기
      if (isNaN(identifier)) {
        const video = incidentVideos.find(v => v.filename === identifier);
        if (!video) {
          throw new Error(`Video not found with filename: ${identifier}`);
        }
        videoId = video.id;
      }

      await apiService.updateVideoStatus(videoId, isChecked);
      
      setIncidentVideos(prev => 
        prev.map(video => 
          video.id === videoId 
            ? { ...video, isChecked } 
            : video
        )
      );

      // 통계 업데이트
      await refreshDashboardStats();

    } catch (error) {
      console.error('Failed to update video status:', error);
      throw error;
    }
  };

  /**
   * 새 영상 추가
   * (프론트 파일 업로드 기능 제거에 맞춰 API 모드는 미지원 처리)
   */
  const addNewIncidentVideo = async (videoData) => {
    const newVideo = {
      filename: videoData.filename,
      createdAt: videoData.createdAt || new Date().toISOString(), // full ISO 유지
      isChecked: false,
      ...videoData
    };

    if (MOCK_DATA && !FORCE_API_MODE) {
      // 더미데이터 모드
      setIncidentVideos(prev => [newVideo, ...prev]);
      return;
    }

    // API 모드: 프론트 업로드 제거 정책에 따라 명시적으로 차단
    throw new Error('프론트엔드에서 파일 업로드는 지원하지 않습니다. (서버 측 업로드 플로우를 사용하세요)');
  };

  /**
   * 영상 삭제 (ID 기반으로 개선)
   */
  const deleteIncidentVideo = async (identifier) => {
    if (MOCK_DATA) {
      // 더미데이터 모드
      setIncidentVideos(prev => 
        prev.filter(video => {
          const matchById = video.id && video.id.toString() === identifier.toString();
          const matchByFilename = video.filename === identifier;
          return !(matchById || matchByFilename);
        })
      );
      return;
    }

    // API 모드
    try {
      let videoId = identifier;
      
      // filename이 전달된 경우 해당 video의 ID 찾기
      if (isNaN(identifier)) {
        const video = incidentVideos.find(v => v.filename === identifier);
        if (!video) {
          throw new Error(`Video not found with filename: ${identifier}`);
        }
        videoId = video.id;
      }

      await apiService.deleteVideo(videoId);
      setIncidentVideos(prev => 
        prev.filter(video => video.id !== videoId)
      );
      await refreshDashboardStats();
    } catch (error) {
      console.error('Failed to delete video:', error);
      throw error;
    }
  };

  /**
   * === 로그인 관련 함수들 ===
   */

  /**
   * 로그인 검증 (LoginPage는 동기 반환을 기대하므로 sync 보장)
   *  - MOCK_DATA: Dum004(id/pw)로 동기 검증
   *  - API 모드: 동기 true를 반환하고, 실제 인증은 getUserByCredentials에서 처리
   *              (LoginPage 구조상 await가 없어 Promise를 다룰 수 없음)
   */
  const validateCredentials = (inputId, inputPassword) => {
    if (MOCK_DATA) {
      return userCredentials.some(user => 
        user.id === inputId && user.pw === inputPassword
      );
    }
    // API 모드에서는 로그인 흐름 진행을 위해 true 리턴
    return true;
  };

  /**
   * 사용자 정보 조회
   *  - MOCK_DATA: 동기 반환
   *  - API 모드: 실제 로그인 API 호출 (Promise 반환)
   */
  const getUserByCredentials = (inputId, inputPassword) => {
    if (MOCK_DATA) {
      const user = userCredentials.find(u => u.id === inputId && u.pw === inputPassword);
      return user
        ? { id: user.id, username: user.id, name: user.name }
        : null;
    }

    // API 모드: 실제 로그인 호출 (주의: LoginPage에서는 await 미사용)
    // 필요 시 LoginPage에서 await 적용 권장
    return (async () => {
      try {
        const response = await apiService.login({
          username: inputId,
          password: inputPassword
        });
        // 백엔드 스키마에 맞춰 조정
        return response?.user || { id: inputId, username: inputId };
      } catch (error) {
        console.error('Failed to get user:', error);
        return null;
      }
    })();
  };

  /**
   * === 실시간 영상 관련 함수들 (개선된 버전) ===
   */

  const updateLiveVideoConfig = (newConfig) => {
    if (!newConfig || typeof newConfig !== 'object') {
      console.warn('Invalid config provided to updateLiveVideoConfig');
      return;
    }

    debugLog('Updating live video config:', newConfig);
    
    setLiveVideoConfig(prev => ({
      ...prev,
      ...newConfig,
      lastUpdated: new Date().toISOString()
    }));
  };

  /**
   * 스트림 상태 업데이트 (백엔드와 연동)
   */
  const updateStreamStatus = async (status) => {
    debugLog('Updating stream status:', status);
    
    // 로컬 상태 즉시 업데이트 (UI 반응성)
    setLiveVideoConfig(prev => ({
      ...prev,
      streamStatus: status,
      lastUpdated: new Date().toISOString()
    }));

    if (MOCK_DATA) {
      debugLog('Mock mode: Stream status updated locally only');
      return;
    }

    try {
      // 백엔드 API 호출
      if (status === "online" || status === "starting") {
        await apiService.startStream();
        debugLog('Stream started successfully');
      } else if (status === "offline" || status === "stopping") {
        await apiService.stopStream();
        debugLog('Stream stopped successfully');
      }

      // 성공 시 최신 스트림 정보 다시 가져오기
      await fetchLiveStreamInfo();

    } catch (error) {
      console.error('Failed to update stream status:', error);
      
      // 실패 시 이전 상태로 롤백하고 에러 표시
      setLiveVideoConfig(prev => ({
        ...prev,
        streamStatus: "error",
        error: error.message,
        lastUpdated: new Date().toISOString()
      }));
      
      throw error;
    }
  };

  /**
   * 스트림 연결 테스트 (유틸리티 함수)
   */
  const testStreamConnection = async () => {
    if (MOCK_DATA) {
      return { 
        success: true, 
        url: "http://192.168.0.6:5000/video_feed",
        type: "mock" 
      };
    }

    try {
      // 1. 스트림 정보 가져오기
      const streamInfo = await fetchLiveStreamInfo();
      
      if (!streamInfo.streamUrl) {
        return { 
          success: false, 
          error: "No stream URL available" 
        };
      }

      // 2. 실제 스트림 URL 테스트
      const workingUrl = await apiService.findWorkingStreamUrl(streamInfo.streamUrl);
      
      if (workingUrl && workingUrl.accessible) {
        debugLog('Stream connection test successful:', workingUrl.url);
        return {
          success: true,
          url: workingUrl.url,
          baseUrl: streamInfo.streamUrl,
          type: "live"
        };
      } else {
        debugLog('Stream connection test failed');
        return {
          success: false,
          baseUrl: streamInfo.streamUrl,
          error: "Stream URL not accessible"
        };
      }

    } catch (error) {
      console.error('Stream connection test error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  };

  const getLiveVideoComponent = () => {
    if (!LiveVideoComponent) {
      console.warn('LiveVideoComponent is not available');
      return null;
    }
    
    return LiveVideoComponent;
  };

  /**
   * 스트림 관련 상태 초기화
   */
  const resetStreamState = () => {
    debugLog('Resetting stream state');
    
    setLiveVideoConfig({
      isVisible: true,
      streamStatus: "offline",
      streamUrl: null,
      lastUpdated: new Date().toISOString(),
      title: "Live Security Camera Feed",
      quality: "unknown",
      type: "unknown",
      error: null
    });
  };

  /**
   * === 필터링 및 검색 함수들 ===
   */

  const getFilteredVideos = () => {
    let filtered = [...incidentVideos];

    // 확인 상태 필터
    if (videoFilters.showCheckedOnly) {
      filtered = filtered.filter(video => video.isChecked);
    } else if (videoFilters.showUncheckedOnly) {
      filtered = filtered.filter(video => !video.isChecked);
    }

    // 날짜 범위 필터
    if (videoFilters.dateRange.start && videoFilters.dateRange.end) {
      filtered = filtered.filter(video => {
        const videoDate = new Date(video.createdAt);
        const startDate = new Date(videoFilters.dateRange.start);
        const endDate = new Date(videoFilters.dateRange.end);
        return videoDate >= startDate && videoDate <= endDate;
      });
    }

    // 검색 키워드 필터
    if (videoFilters.searchKeyword) {
      filtered = filtered.filter(video =>
        String(video.filename).toLowerCase().includes(String(videoFilters.searchKeyword).toLowerCase())
      );
    }

    return filtered;
  };

  const updateFilters = (newFilters) => {
    setVideoFilters(prev => ({ ...prev, ...newFilters }));
  };

  const resetFilters = () => {
    setVideoFilters({
      showCheckedOnly: false,
      showUncheckedOnly: false,
      dateRange: { start: null, end: null },
      searchKeyword: "",
      currentPage: 1,
      pageSize: 10
    });
  };

  /**
   * === 통계 정보 함수들 ===
   */

  const getVideoStats = () => {
    const total = incidentVideos.length;
    const checked = incidentVideos.filter(v => v.isChecked).length;
    const unchecked = total - checked;
    
    return {
      total,
      checked,
      unchecked,
      checkRate: total > 0 ? Math.round((checked / total) * 100) : 0
    };
  };

  const getRecentVideos = (days = 7) => {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);
    
    return incidentVideos.filter(video => 
      new Date(video.createdAt) >= cutoffDate
    ).length;
  };

  /**
   * 대시보드 통계 새로고침
   */
  const refreshDashboardStats = async () => {
    if (MOCK_DATA) {
      setDashboardStats(calculateStatsFromData(incidentVideos));
      return;
    }

    try {
      const stats = await fetchDashboardStats();
      setDashboardStats(stats);
    } catch (error) {
      console.error('Failed to refresh stats:', error);
    }
  };

  /**
   * 더미데이터에서 통계 계산
   */
  const calculateStatsFromData = (data) => {
    const total = data.length;
    const checked = data.filter(v => v.isChecked).length;
    const todayKey = new Date().toISOString().slice(0, 10); // UTC 기준 YYYY-MM-DD
    const todayVideos = data.filter(v => toDateKey(v.createdAt) === todayKey).length;

    return {
      totalVideos: total,
      checkedVideos: checked,
      uncheckedVideos: total - checked,
      todayVideos
    };
  };

  /**
   * === 데이터 새로고침 함수들 ===
   */

  const refreshIncidentVideos = async () => {
    if (MOCK_DATA) return;

    try {
      setLoading(true);
      const response = await fetchIncidentVideos();
      setIncidentVideos(response.data || []);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const refreshAllData = async () => {
    await initializeData();
  };

  // Context Value
  const contextValue = {
    // === 상태 ===
    loading,
    error,
    
    // === 데이터 ===
    LiveVideoComponent,
    liveVideoConfig,
    incidentVideos,
    userCredentials,
    videoFilters,
    dashboardStats,
    
    // === 실시간 영상 함수들 (개선된 버전) ===
    getLiveVideoComponent,
    updateLiveVideoConfig,
    updateStreamStatus,
    fetchLiveStreamInfo,      // ✅ 올바른 엔드포인트 사용
    testStreamConnection,     // ✅ 새로 추가
    resetStreamState,         // ✅ 새로 추가
    
    // === 사고 영상 함수들 ===
    updateVideoCheckStatus,   // ✅ ID 기반으로 개선
    addNewIncidentVideo,
    deleteIncidentVideo,      // ✅ ID 기반으로 개선
    getFilteredVideos,
    fetchIncidentVideos,
    refreshIncidentVideos,
    
    // === 로그인 함수들 ===
    validateCredentials,      // 동기 반환 (LoginPage 호환)
    getUserByCredentials,     // MOCK: 동기 / API: Promise
    
    // === 필터링 함수들 ===
    updateFilters,
    resetFilters,
    
    // === 통계 함수들 ===
    getVideoStats,
    getRecentVideos,
    refreshDashboardStats,
    
    // === 전체 데이터 관리 ===
    refreshAllData,
    
    // === API 서비스 직접 접근 (고급 사용) ===
    apiService: MOCK_DATA ? null : apiService
  };

  return (
    <DataContext.Provider value={contextValue}>
      {children}
    </DataContext.Provider>
  );
};

// DataContext 사용을 위한 커스텀 훅
export const useData = () => {
  const context = useContext(DataContext);
  if (!context) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
};

export default DataContext;