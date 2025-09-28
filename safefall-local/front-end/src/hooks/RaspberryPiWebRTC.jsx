import { useEffect, useRef, useState } from 'react';

function FlaskVideoStream() {
  const videoRef = useRef(null);
  const [streamMode, setStreamMode] = useState('fallback'); // 'live' or 'fallback'
  const [streamStatus, setStreamStatus] = useState('checking');
  const [error, setError] = useState(null);
  
  const API_SERVER_URL = import.meta.env.VITE_API_BASE_URL || "";

  useEffect(() => {
    if (!API_SERVER_URL) {
      setStreamStatus('disabled');
      return;
    }

    let intervalId = null;
    let isActive = true;

    const initializeStream = async () => {
      try {
        setStreamStatus('checking');
        setError(null);

        // 1단계: 올바른 엔드포인트 (/stream/live)에서 스트림 정보 가져오기
        const streamResponse = await fetch(`${API_SERVER_URL}/stream/live`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          // 타임아웃 설정 (5초)
          signal: AbortSignal.timeout(5000)
        });

        if (!streamResponse.ok) {
          throw new Error(`Stream info fetch failed: ${streamResponse.status}`);
        }

        const streamInfo = await streamResponse.json();
        console.log('Stream info received:', streamInfo);

        // 2단계: 실제 라이브 스트림 시도
        if (streamInfo.streamUrl && streamInfo.status === 'online') {
          const success = await attemptLiveStream(streamInfo.streamUrl);
          if (success) {
            setStreamMode('live');
            setStreamStatus('live');
            console.log('Live stream mode activated');
            return;
          }
        }

        // 3단계: 라이브 스트림 실패 시 폴백 모드
        console.log('Falling back to recent video mode');
        setStreamMode('fallback');
        setStreamStatus('fallback');
        startFallbackMode();

      } catch (error) {
        console.error('Stream initialization failed:', error);
        setError(error.message);
        setStreamStatus('fallback');
        setStreamMode('fallback');
        startFallbackMode();
      }
    };

    const attemptLiveStream = async (streamUrl) => {
      try {
        // 일반적인 라즈베리파이 스트림 경로들 시도
        const possiblePaths = [
          '/video_feed',
          '/stream',
          '/mjpeg',
          '/camera/stream',
          ''  // 기본 경로
        ];

        for (const path of possiblePaths) {
          try {
            const fullUrl = `${streamUrl}${path}`;
            console.log(`Trying live stream: ${fullUrl}`);
            
            // 스트림 URL 테스트 (HEAD 요청으로 빠르게 확인)
            const testResponse = await fetch(fullUrl, { 
              method: 'HEAD',
              signal: AbortSignal.timeout(3000)  // 3초 타임아웃
            });
            
            if (testResponse.ok) {
              // 성공하면 실제 스트림 연결
              if (videoRef.current) {
                videoRef.current.src = fullUrl;
                videoRef.current.onerror = () => {
                  console.log(`Live stream failed for ${fullUrl}, trying next...`);
                  return false;
                };
                
                // 스트림이 로드되면 성공
                return new Promise((resolve) => {
                  videoRef.current.onloadstart = () => {
                    console.log(`Live stream success: ${fullUrl}`);
                    resolve(true);
                  };
                  
                  // 5초 후에도 로드 안되면 실패
                  setTimeout(() => resolve(false), 5000);
                });
              }
            }
          } catch (pathError) {
            console.log(`Path ${path} failed:`, pathError.message);
            continue;
          }
        }
        
        return false; // 모든 경로 실패
      } catch (error) {
        console.error('Live stream attempt failed:', error);
        return false;
      }
    };

    const startFallbackMode = () => {
      // 기존 방식: 최신 저장된 영상을 주기적으로 업데이트
      const fetchLatestFrame = async () => {
        if (!isActive) return;
        
        try {
          const response = await fetch(`${API_SERVER_URL}/videos?page=1&limit=1&sortBy=createdAt&sortOrder=desc`, {
            signal: AbortSignal.timeout(10000)  // 10초 타임아웃
          });
          
          if (response.ok) {
            const data = await response.json();
            if (data?.data?.length > 0 && videoRef.current) {
              const latest = data.data[0];
              const imageUrl = `${API_SERVER_URL}${latest.url}`;
              
              // 이미지가 실제로 로드 가능한지 확인
              const img = new Image();
              img.onload = () => {
                if (videoRef.current && isActive) {
                  videoRef.current.src = imageUrl;
                }
              };
              img.onerror = () => {
                console.warn('Failed to load image:', imageUrl);
              };
              img.src = imageUrl;
            }
          }
        } catch (err) {
          console.error("Fallback frame fetch error:", err);
          setError(`연결 오류: ${err.message}`);
        }
      };

      // 즉시 첫 프레임 로드
      fetchLatestFrame();
      
      // 2초마다 업데이트 (라이브 스트림이 아니므로 너무 자주 할 필요 없음)
      intervalId = setInterval(fetchLatestFrame, 2000);
    };

    // 스트림 초기화 시작
    initializeStream();

    // 컴포넌트 언마운트 시 정리
    return () => {
      isActive = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
      if (videoRef.current) {
        videoRef.current.src = '';
      }
    };
  }, [API_SERVER_URL]);

  // 수동 새로고침 함수
  const handleRefresh = () => {
    window.location.reload(); // 전체 컴포넌트 재초기화
  };

  if (!API_SERVER_URL) {
    return (
      <div style={{
        width: '100%', 
        height: '100%',
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '20px'
      }}>
        <span style={{ 
          opacity: 0.7, 
          fontSize: 16, 
          marginBottom: 10,
          color: '#666'
        }}>
          실시간 스트림이 비활성화되어 있습니다.
        </span>
        <span style={{ 
          opacity: 0.5, 
          fontSize: 12,
          color: '#999'
        }}>
          환경변수 VITE_API_BASE_URL이 설정되지 않았습니다.
        </span>
      </div>
    );
  }

  return (
    <div style={{ 
      position: 'relative', 
      width: '100%', 
      height: '100%',
      backgroundColor: '#000',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* 상태 표시 오버레이 */}
      <div style={{
        position: 'absolute',
        top: '10px',
        left: '10px',
        zIndex: 10,
        backgroundColor: 'rgba(0,0,0,0.7)',
        color: 'white',
        padding: '4px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '6px'
      }}>
        {/* 상태 인디케이터 */}
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: 
            streamStatus === 'live' ? '#00ff00' :
            streamStatus === 'fallback' ? '#ffa500' :
            streamStatus === 'checking' ? '#ffff00' :
            '#ff0000'
        }} />
        
        <span>
          {streamStatus === 'live' && '실시간 스트림'}
          {streamStatus === 'fallback' && '최신 영상'}
          {streamStatus === 'checking' && '연결 중...'}
          {streamStatus === 'disabled' && '비활성화'}
        </span>
        
        {/* 새로고침 버튼 */}
        <button
          onClick={handleRefresh}
          style={{
            background: 'none',
            border: '1px solid rgba(255,255,255,0.3)',
            color: 'white',
            borderRadius: '3px',
            padding: '2px 6px',
            fontSize: '10px',
            cursor: 'pointer',
            marginLeft: '4px'
          }}
          title="새로고침"
        >
          ↻
        </button>
      </div>

      {/* 에러 표시 */}
      {error && (
        <div style={{
          position: 'absolute',
          bottom: '10px',
          left: '10px',
          right: '10px',
          zIndex: 10,
          backgroundColor: 'rgba(255,0,0,0.8)',
          color: 'white',
          padding: '8px',
          borderRadius: '4px',
          fontSize: '12px'
        }}>
          {error}
        </div>
      )}

      {/* 실제 비디오/이미지 */}
      {streamMode === 'live' ? (
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          style={{ 
            width: '100%', 
            height: '100%', 
            objectFit: 'cover' 
          }}
        />
      ) : (
        <img
          ref={videoRef}
          alt="SafeFall 스트림"
          style={{ 
            width: '100%', 
            height: '100%', 
            objectFit: 'cover' 
          }}
          onError={() => {
            console.warn('Image load failed');
          }}
        />
      )}

      {/* 로딩 상태 */}
      {streamStatus === 'checking' && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          color: 'white',
          fontSize: '14px',
          textAlign: 'center'
        }}>
          <div>연결 중...</div>
          <div style={{ fontSize: '12px', opacity: 0.7, marginTop: '4px' }}>
            실시간 스트림을 확인하고 있습니다.
          </div>
        </div>
      )}
    </div>
  );
}

export default FlaskVideoStream;