import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import "./Alter.css";

function Alert({ 
  isVisible = false, 
  onClose, 
  alertData = {},
  onGoToHistory  // 🔥 새로운 prop 추가
}) {
  const navigate = useNavigate();
  const [isAnimating, setIsAnimating] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false); // 🔥 대기 상태 추가

  // 알람이 표시될 때 애니메이션 시작
  useEffect(() => {
    if (isVisible) {
      setIsAnimating(true);
      // TODO: 알림음 재생 기능 추가 예정
      // playAlertSound();
    } else {
      setIsAnimating(false);
    }
  }, [isVisible]);

  // TODO: 알림음 재생 함수 (향후 구현)
  // const playAlertSound = () => {
  //   try {
  //     const audio = new Audio('/sounds/alert.mp3');
  //     audio.play();
  //   } catch (error) {
  //     console.warn('Alert sound failed to play:', error);
  //   }
  // };

  // 알람 닫기 핸들러
  const handleClose = () => {
    setIsAnimating(false);
    setTimeout(() => {
      if (onClose) {
        onClose();
      }
    }, 300); // 애니메이션 완료 후 닫기
  };

  // 기록보기 페이지로 이동
  const handleGoToHistory = async () => {
    console.log('📜 기록 확인 버튼 클릭 - 영상 녹화 완료 대기 후 데이터 새로고침');
    
    try {
      // 1단계: 영상 녹화 완료 대기 (8초 영상 + DB 처리 시간)
      console.log('⏰ 영상 녹화 완료 대기중... (18초)');
      await new Promise(resolve => setTimeout(resolve, 18000)); // 🔥 12초 → 18초로 증가
      console.log('✅ 영상 녹화 완료 대기 완료');
      
      // 2단계: 데이터 새로고침 (여러 번 시도)
      if (onGoToHistory) {
        console.log('🔄 데이터 새로고침 시작 (1차 시도)...');
        await onGoToHistory(); 
        
        // 잠시 대기 후 다시 새로고침 (혹시 놀친 경우를 대비)
        console.log('🔄 데이터 새로고침 시작 (2차 시도)...');
        await new Promise(resolve => setTimeout(resolve, 2000)); // 2초 대기
        await onGoToHistory();
        
        console.log('✅ 데이터 새로고침 완료');
      }
      
      // 3단계: 페이지 이동
      console.log('📝 CheckHistory 페이지로 이동');
      navigate('/history');
      
      // 4단계: 알림 닫기
      handleClose();
      
    } catch (error) {
      console.error('❌ 데이터 새로고침 오류:', error);
      // 에러가 있어도 페이지는 이동
      navigate('/history');
      handleClose();
    } finally {
      // 대기 상태 종료
      setIsWaiting(false);
    }
  };

  // ESC 키로 알람 닫기
  useEffect(() => {
    const handleEscKey = (event) => {
      if (event.key === 'Escape' && isVisible) {
        handleClose();
      }
    };

    if (isVisible) {
      document.addEventListener('keydown', handleEscKey);
    }

    return () => {
      document.removeEventListener('keydown', handleEscKey);
    };
  }, [isVisible]);

  // 알람이 보이지 않으면 렌더링하지 않음
  if (!isVisible) {
    return null;
  }

  return (
    <div className={`alert-overlay ${isAnimating ? 'show' : ''}`}>
      <div className={`alert-modal ${isAnimating ? 'animate' : ''}`}>
        
        {/* 알람 헤더 */}
        <div className="alert-header">
          <div className="alert-icon">
            ⚠️
          </div>
          <h2 className="alert-title">낙상 감지 알람</h2>
        </div>

        {/* 알람 내용 */}
        <div className="alert-content">
          <p className="alert-message">
            {alertData.type === 'fall' ? '낙상이 감지되었습니다!' : 
             alertData.type === 'frame' ? '이상 상황이 감지되었습니다!' : 
             '알림이 도착했습니다!'}
          </p>
          
          <div className="alert-details">
            <div className="detail-item">
              <span className="detail-label">감지 시간:</span>
              <span className="detail-value">
                {alertData.createdAt ? 
                  new Date(alertData.createdAt).toLocaleString('ko-KR', {
                    year: 'numeric',
                    month: '2-digit', 
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                  }) : 
                  new Date().toLocaleString('ko-KR')
                }
              </span>
            </div>
            
            <div className="detail-item">
              <span className="detail-label">카메라:</span>
              <span className="detail-value">
                {alertData.device_id ? 
                  alertData.device_id.replace('camera_', '카메라 ').replace('_', ' ') : 
                  "알 수 없음"}
              </span>
            </div>
            
            <div className="detail-item">
              <span className="detail-label">유형:</span>
              <span className={`detail-value event-type ${alertData.type || 'fall'}`}>
                {alertData.type === 'fall' ? '🚨 낙상' : 
                 alertData.type === 'frame' ? '📷 일반' : 
                 alertData.type === 'normal' ? '✅ 정상' : '❓ 기타'}
              </span>
            </div>

            {alertData.filename && (
              <div className="detail-item">
                <span className="detail-label">파일명:</span>
                <span className="detail-value filename">
                  {alertData.filename}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* 알람 버튼들 */}
        <div className="alert-buttons">
          <button 
            className="alert-btn alert-btn-secondary"
            onClick={handleClose}
            disabled={isWaiting}
          >
            알람 끄기
          </button>
          
          <button 
            className="alert-btn alert-btn-primary"
            onClick={handleGoToHistory}
            disabled={isWaiting}
          >
            {isWaiting ? (
              <>
                <span style={{marginRight: '8px'}}>⏳</span>
                영상 녹화 완료 대기중...
              </>
            ) : (
              '기록 확인하기'
            )}
          </button>
        </div>

        {/* 닫기 X 버튼 */}
        <button 
          className="alert-close-x"
          onClick={handleClose}
          aria-label="알람 닫기"
        >
          ×
        </button>
      </div>
    </div>
  );
}

export default Alert;