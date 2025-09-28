import { useState, useEffect, createContext, useContext, useRef } from "react";
import { HashRouter, Routes, Route, Navigate } from "react-router-dom";

import BeforeLogin from "./pages/BeforeLogin";
import AfterLogin from "./pages/AfterLogin";
import LoginPage from "./pages/LoginPage";
import CheckHistory from "./pages/CheckHistory";
import CheckVideo from "./pages/CheckVideo";

import { DataProvider, useData } from "./hooks/DataContext";

import Header from "./components/Header";
import Footer from "./components/Footer";
import Alert from "./components/Alter";  // ✅ Alert 컴포넌트 추가

import apiService from "./services/api";  // ✅ API 서비스 추가

import "./App.css";

// 인증 컨텍스트 생성
const AuthContext = createContext();

// 인증 프로바이더 컴포넌트
export const AuthProvider = ({ children }) => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  // 컴포넌트 마운트 시 로컬스토리지에서 로그인 상태 확인
  useEffect(() => {
    const savedUser = localStorage.getItem("currentUser");
    const savedLoginState = localStorage.getItem("isLoggedIn");

    if (savedUser && savedLoginState === "true") {
      setCurrentUser(JSON.parse(savedUser));
      setIsLoggedIn(true);
    }
  }, []);

  // 로그인 함수
  const login = (userData) => {
    console.log('🔍 Login userData:', userData); // 디버그용
    setIsLoggedIn(true);
    setCurrentUser(userData);

    // 로컬스토리지에 저장
    localStorage.setItem("isLoggedIn", "true");
    localStorage.setItem("currentUser", JSON.stringify(userData));
  };

  // 로그아웃 함수
  const logout = () => {
    setIsLoggedIn(false);
    setCurrentUser(null);

    // 로컬스토리지에서 제거
    localStorage.removeItem("isLoggedIn");
    localStorage.removeItem("currentUser");
  };

  return (
    <AuthContext.Provider
      value={{
        isLoggedIn,
        currentUser,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// 인증 컨텍스트 사용을 위한 커스텀 훅
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

// 보호된 라우트 컴포넌트
const ProtectedRoute = ({ children }) => {
  const { isLoggedIn } = useAuth();

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// 공개 라우트 컴포넌트 (로그인 시 리다이렉트)
const PublicRoute = ({ children }) => {
  const { isLoggedIn } = useAuth();

  if (isLoggedIn) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// 알람 관리 컴포넌트 (PageWrapper 내부에서 사용)
const AlertManager = () => {
  const { isLoggedIn } = useAuth();
  const { refreshIncidentVideos } = useData(); // 🔥 데이터 새로고침 함수 추가
  const [showAlert, setShowAlert] = useState(false);
  const [alertData, setAlertData] = useState({});
  const [isPollingActive, setIsPollingActive] = useState(false);
  const shownIdsRef = useRef(new Set()); // ★ 이미 표시한 알림 ID 저장

  // 알람 표시 함수
  const showNotification = (title, message, severity, additionalData = {}) => {
    setAlertData({
      createdAt: new Date().toISOString(),
      device_id: additionalData.device_id || "camera_01",
      type: severity === "high" ? "fall" : 
            severity === "medium" ? "frame" : "normal",
      filename: additionalData.filename || `alert_${Date.now()}.mp4`,
      title,
      message,
      severity,
      ...additionalData
    });
    setShowAlert(true);
  };

  // 알람 닫기 함수
  const handleCloseAlert = () => {
    setShowAlert(false);
    setAlertData({});
  };
  
  // 🔥 기록 확인 후 데이터 새로고침 함수
  const handleGoToHistory = async () => {
    console.log('🔄 알림에서 기록 확인 - 데이터 새로고침 시작');
    
    try {
      if (refreshIncidentVideos) {
        await refreshIncidentVideos();
        console.log('✅ 데이터 새로고침 완료 - CheckHistory에서 최신 데이터 표시됨');
      } else {
        console.warn('⚠️ refreshIncidentVideos 함수가 없음');
      }
    } catch (error) {
      console.error('❌ 데이터 새로고침 실패:', error);
      throw error; // Alert 컴포넌트에서 에러 처리
    }
  };

  // 알람 폴링 (로그인 상태일 때만 활성화)
  useEffect(() => {
    if (!isLoggedIn) {
      setIsPollingActive(false);
      return;
    }

    setIsPollingActive(true);
    console.log('🔄 Starting notification polling...');

    const pollInterval = setInterval(async () => {
      try {
        // 5000번 포트 강제 사용
        console.log('🔎 알림 폴링 요청 중...'); // 디버그 로그 추가
        const data = await fetch('http://localhost:5000/api/v1/notifications/latest', {
          headers: { 'Content-Type': 'application/json' }
        }).then(res => res.json());
        
        console.log('📜 알림 API 응답:', data); // 디버그 로그 추가
        
        if (data && data.count > 0 && Array.isArray(data.notifications)) {
          console.log(`🔔 새로운 알림 발견: ${data.notifications.length}개`); // 디버그 로그 추가
          
          // 새(already unseen) 알림만 필터
            const fresh = data.notifications.filter(n => {
              if (!n?.id) return false;
              if (shownIdsRef.current.has(n.id)) return false;
              return true;
            });
            
            console.log(`🆕 미표시 알림: ${fresh.length}개`); // 디버그 로그 추가
            
            // 첫 번째 새 알림만(폭주 방지) 표시
            if (fresh.length) {
              const first = fresh[0];
              console.log('😨 알림 표시 시작:', first); // 디버그 로그 추가
              
              shownIdsRef.current.add(first.id);
              showNotification(
                first.title || "알림",
                first.message || "새로운 알림이 있습니다",
                first.severity || "medium",
                {
                  id: first.id,
                  device_id: first.device_id,
                  type: first.type,
                  filename: first.filename,
                  createdAt: first.createdAt
                }
              );
              
              // 🔧 수정: 나머지 ID는 캐시에 추가하지 않음 (다음 폴링에서 하나씩 처리)
              // for (let i = 1; i < fresh.length; i++) {
              //   if (fresh[i]?.id) shownIdsRef.current.add(fresh[i].id);
              // }
            }
        } else {
          console.log('🔕 새로운 알림 없음'); // 디버그 로그 추가
        }
      } catch (error) {
        console.error('❌ Notification polling failed:', error);
      }
    }, 3000); // 3초마다

    // 컴포넌트 언마운트 시 인터벌 정리
    return () => {
      console.log('🛑 Stopping notification polling...');
      clearInterval(pollInterval);
      setIsPollingActive(false);
    };
  }, [isLoggedIn]);

  // 개발/테스트용 전역 함수 등록
  useEffect(() => {
    // 브라우저 콘솔에서 테스트용
    window.triggerTestAlert = (type = 'fall', severity = 'high') => {
      const testNotifications = {
        fall: {
          title: "낙상 감지",
          message: "거실에서 낙상이 감지되었습니다",
          severity: "high"
        },
        frame: {
          title: "이상 상황",
          message: "카메라에서 이상 상황이 감지되었습니다",
          severity: "medium"
        },
        normal: {
          title: "일반 알림",
          message: "시스템 정상 동작 중입니다",
          severity: "low"
        }
      };

      const notif = testNotifications[type] || testNotifications.fall;
      showNotification(notif.title, notif.message, severity);
    };

    window.showTestNotification = showNotification;
    
    // 📡 백엔드 알림 API 직접 테스트 함수 추가
    window.testNotificationAPI = async () => {
      console.log('🧪 백엔드 알림 API 직접 테스트...');
      try {
        const response = await fetch('http://localhost:5000/api/v1/notifications/latest');
        const data = await response.json();
        console.log('✅ 알림 API 응답:', data);
        return data;
      } catch (error) {
        console.error('❌ 알림 API 테스트 실패:', error);
        return { error: error.message };
      }
    };
    
    // 📡 낙상 감지 테스트 함수 추가 
    window.testFallDetection = async () => {
      console.log('🧪 낙상 감지 테스트...');
      try {
        const response = await fetch('http://localhost:5000/api/test-fall-alert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confidence: 0.95 })
        });
        const data = await response.json();
        console.log('✅ 낙상 감지 테스트 결과:', data);
        return data;
      } catch (error) {
        console.error('❌ 낙상 감지 테스트 실패:', error);
        return { error: error.message };
      }
    };
    
    // 📡 알림 후 기록 확인 시뮬레이션 함수
    window.simulateAlertToHistory = async () => {
      console.log('🎬 알림 후 기록 확인 시뮬레이션...');
      try {
        // 1. 낙상 감지 테스트
        console.log('1단계: 낙상 감지 테스트');
        await window.testFallDetection();
        
        // 2. 잠시 대기 (알림이 나타날 때까지)
        console.log('2단계: 5초 대기 (알림 표시 대기)');
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // 3. 알림 포스 쳋크
        console.log('3단계: 알림 발생 중...');
        console.log('ℹ️ 알림이 나타나면 "기록 확인하기" 버튼을 클릭하세요!');
        console.log('ℹ️ 버튼 클릭 시 영상 녹화 완료까지 10초 대기 후 데이터 새로고침됩니다.');
        console.log('ℹ️ 또는 window.triggerTestAlert("fall", "high")로 알림을 수동 표시할 수 있습니다.');
        
        return '시뮬레이션 완료 - 알림에서 "기록 확인하기" 버튼 클릭 대기중';
      } catch (error) {
        console.error('❌ 시뮬레이션 실패:', error);
        return { error: error.message };
      }
    };
    
    // 📡 대시보드 더보기 테스트 함수
    window.testDashboardMoreButton = () => {
      console.log('📊 대시보드 더보기 버튼 테스트');
      console.log('ℹ️ 대시보드에서 "더보기" 버튼을 클릭하면 데이터 새로고침 후 CheckHistory로 이동합니다.');
      return '대시보드에서 "더보기" 버튼 클릭 대기중';
    };
    
    // 🔥 알림 캐시 관리 함수들 추가
    window.clearNotificationCache = () => {
      shownIdsRef.current.clear();
      console.log('✅ 알림 캐시 초기화 완료');
      return '알림 캐시가 초기화되었습니다';
    };
    
    window.getNotificationCacheSize = () => {
      const size = shownIdsRef.current.size;
      console.log(`📊 캐시된 알림 ID 개수: ${size}`);
      return size;
    };
    
    window.getNotificationCacheIds = () => {
      const ids = Array.from(shownIdsRef.current);
      console.log('📋 캐시된 알림 IDs:', ids);
      return ids;
    };

    // cleanup
    return () => {
      delete window.triggerTestAlert;
      delete window.showTestNotification;
      delete window.testNotificationAPI;
      delete window.testFallDetection;
      delete window.simulateAlertToHistory;
      delete window.testDashboardMoreButton;
      delete window.clearNotificationCache;  // 🔥 새 함수 정리 추가
      delete window.getNotificationCacheSize;
      delete window.getNotificationCacheIds;
    };
  }, []);

  // 폴링 상태 디버그 정보 (개발 환경에서만)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('📊 Alert polling status:', {
        isLoggedIn,
        isPollingActive,
        showAlert
      });
    }
  }, [isLoggedIn, isPollingActive, showAlert]);

  return (
    <Alert 
      isVisible={showAlert}
      onClose={handleCloseAlert}
      alertData={alertData}
      onGoToHistory={handleGoToHistory}  // 🔥 데이터 새로고침 함수 전달
    />
  );
};

// 페이지 래퍼 컴포넌트
const PageWrapper = () => {
  const {
    // 실시간 영상 관련
    LiveVideoComponent,
    liveVideoConfig,
    getLiveVideoComponent,
    updateLiveVideoConfig,
    updateStreamStatus,

    // 사고 영상 관련
    incidentVideos,
    updateVideoCheckStatus,
    addNewIncidentVideo,
    deleteIncidentVideo,
    getFilteredVideos,

    // 로그인 관련
    userCredentials,
    validateCredentials,
    getUserByCredentials,

    // 필터링 관련
    videoFilters,
    updateFilters,
    resetFilters,

    // 통계 관련
    getVideoStats,
    getRecentVideos,
    
    // 데이터 새로고침 관련 🔥
    refreshIncidentVideos,
  } = useData();

  return (
    <>
      <Header />
      <Routes>
        {/* 공개 라우트 */}
        <Route
          path="/"
          element={
            <PublicRoute>
              <BeforeLogin />
            </PublicRoute>
          }
        />
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage
                userCredentials={userCredentials}
                validateCredentials={validateCredentials}
                getUserByCredentials={getUserByCredentials}
              />
            </PublicRoute>
          }
        />

        {/* 보호된 라우트 */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AfterLogin
                incidentVideos={incidentVideos}
                LiveVideoComponent={LiveVideoComponent}
                liveVideoConfig={liveVideoConfig}
                refreshIncidentVideos={refreshIncidentVideos}  // 🔥 데이터 새로고침 함수 추가
                // 원본 변형 방지를 위해 복사 후 정렬
                getRecentVideos={(count = 6) => {
                  return [...incidentVideos]
                    .sort(
                      (a, b) =>
                        new Date(b.createdAt).getTime() -
                        new Date(a.createdAt).getTime()
                    )
                    .slice(0, count);
                }}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <CheckHistory
                incidentVideos={incidentVideos}
                updateVideoCheckStatus={updateVideoCheckStatus}
                deleteIncidentVideo={deleteIncidentVideo}
                getFilteredVideos={getFilteredVideos}
                videoFilters={videoFilters}
                updateFilters={updateFilters}
                resetFilters={resetFilters}
                getVideoStats={getVideoStats}
                refreshIncidentVideos={refreshIncidentVideos}  // 🔥 새로고침 함수 추가
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/video/:id"
          element={
            <ProtectedRoute>
              <CheckVideo
                incidentVideos={incidentVideos}
                updateVideoCheckStatus={updateVideoCheckStatus}
                LiveVideoComponent={LiveVideoComponent}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/live"
          element={
            <ProtectedRoute>
              <CheckVideo
                LiveVideoComponent={LiveVideoComponent}
                liveVideoConfig={liveVideoConfig}
                updateStreamStatus={updateStreamStatus}
              />
            </ProtectedRoute>
          }
        />

        {/* 404 페이지 → 공개 홈으로 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      
      <Footer />
      
      {/* ✅ 알람 관리자 - 모든 페이지에서 활성화 */}
      <AlertManager />
    </>
  );
};

function App() {
  useEffect(() => {
    window.sfGetDetectionMetrics = () => apiService.getDetectionMetrics().then(r => { console.log('[SafeFall] detection metrics:', r); return r; });
    window.sfGetLastDetection = () => apiService.getLastDetection().then(r => { console.log('[SafeFall] last detection:', r); return r; });
    window.sfMockDetection = (c = 0.95) => apiService.mockDetection(c).then(r => { console.log('[SafeFall] mock detection triggered:', r); return r; });
    window.sfDetectDebug = () => apiService.getDetectionDebug().then(r => { console.log('[SafeFall] detect debug:', r); return r; });
    window.sfGetDetectThreshold = () => apiService.getDetectionThreshold().then(r => { console.log('[SafeFall] threshold:', r); return r; });
    window.sfSetDetectThreshold = (t=0.5) => apiService.setDetectionThreshold(t).then(r => { console.log('[SafeFall] threshold set:', r); return r; });
    // 추가: 마지막 양성 감지 결과
    window.sfGetLastPositive = () => apiService.getLastPositiveDetection().then(r => { console.log('[SafeFall] last positive detection:', r); return r; });
    return () => {
      delete window.sfGetDetectionMetrics;
      delete window.sfGetLastDetection;
      delete window.sfMockDetection;
      delete window.sfDetectDebug;
      delete window.sfGetDetectThreshold;
      delete window.sfSetDetectThreshold;
      delete window.sfGetLastPositive;
    };
  }, []);

  return (
    <HashRouter>
      <DataProvider>
        <AuthProvider>
          <PageWrapper />
        </AuthProvider>
      </DataProvider>
    </HashRouter>
  );
}

export default App;