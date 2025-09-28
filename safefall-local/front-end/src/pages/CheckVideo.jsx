import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";

import WindowSize from "../hooks/windowSize";
import VideoBtnSmall from "../components/SVG-VideoBtnSmall";

import "./CheckVideo.css";

function CheckVideo({
  incidentVideos = [],
  updateVideoCheckStatus,
  LiveVideoComponent,
}) {
  // URL 파라미터: id 우선, 없으면 filename 병행 지원
  const { id, filename } = useParams();
  const navigate = useNavigate();
  const { width } = WindowSize();
  const videoRef = useRef(null);

  const [videoData, setVideoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoError, setVideoError] = useState(null);

  // URL 파라미터로 전달된 파일명으로 영상 데이터 찾기
  useEffect(() => {
    const loadVideoData = async () => {
      if (id || filename) {
        try {
          const identifier = id || filename;
          console.log('Loading video data for identifier:', identifier);
          console.log('Available incidentVideos:', incidentVideos);
          
          // 1순위: incidentVideos 배열에서 찾기
          if (incidentVideos.length > 0) {
            let foundVideo = null;
            
            // ID로 찾기 (ID가 숫자인 경우)
            if (id && !isNaN(id)) {
              foundVideo = incidentVideos.find((v) => String(v.id) === String(id));
              console.log('Found by ID:', foundVideo);
            }
            
            // 파일명으로 찾기
            if (!foundVideo && (filename || id)) {
              const searchFilename = filename || id;
              const decodedFilename = decodeURIComponent(searchFilename);
              foundVideo = incidentVideos.find((v) => 
                v.filename === decodedFilename || v.filename === searchFilename
              );
              console.log('Found by filename:', foundVideo);
            }
            
            if (foundVideo) {
              console.log('Found video object:', foundVideo);
              console.log('Video filename:', foundVideo.filename);
              console.log('Video url:', foundVideo.url);
              console.log('Video path:', foundVideo.path);
              
              setVideoData(foundVideo);
              
              // 파일명 확인 및 URL 생성
              const videoFilename = foundVideo.filename || foundVideo.video_filename || foundVideo.name;
              console.log('Using filename:', videoFilename);
              
              if (videoFilename) {
                // 🔧 절대 URL 사용으로 테스트
                const actualVideoUrl = foundVideo.url || foundVideo.path || `/media/videos/${videoFilename}`;
                const fullUrl = actualVideoUrl.startsWith('http') 
                  ? actualVideoUrl 
                  : `http://localhost:5000${actualVideoUrl}`;
                setVideoUrl(fullUrl);
                console.log('Setting video URL:', fullUrl);
              } else {
                console.error('No valid filename found in video object');
                setVideoError('파일명을 찾을 수 없습니다.');
              }
              
              setLoading(false);
              return;
            }
          }
          
          // 2순위: API로 개별 영상 정보 가져오기
          console.log('Fetching video data from API for identifier:', identifier);
          const response = await fetch(`http://localhost:5000/api/videos/${encodeURIComponent(identifier)}`);
          
          if (response.ok) {
            const data = await response.json();
            console.log('API response data:', data);
            
            if (data.success && data.video) {
              const apiVideo = data.video;
              console.log('API video object:', apiVideo);
              
              setVideoData(apiVideo);
              
              // API에서 받은 데이터의 파일명 확인
              const videoFilename = apiVideo.filename || apiVideo.video_filename || apiVideo.name;
              console.log('API video filename:', videoFilename);
              
              if (videoFilename) {
                // 🔧 절대 URL 사용으로 테스트
                const actualVideoUrl = apiVideo.url || apiVideo.path || `/media/videos/${videoFilename}`;
                const fullUrl = actualVideoUrl.startsWith('http') 
                  ? actualVideoUrl 
                  : `http://localhost:5000${actualVideoUrl}`;
                setVideoUrl(fullUrl);
                console.log('Setting API video URL:', fullUrl);
              } else {
                console.error('No valid filename in API response');
                setVideoError('API에서 파일명을 찾을 수 없습니다.');
              }
              
              setLoading(false);
              return;
            } else {
              console.error('API response error:', data);
              setVideoError(`API 오류: ${data.error || 'Unknown error'}`);
            }
          } else {
            console.error('API request failed:', response.status, response.statusText);
            setVideoError(`API 요청 실패: ${response.status} ${response.statusText}`);
          }
          
          // 영상을 찾을 수 없는 경우
          console.error("Video not found:", identifier);
          setLoading(false);
          
        } catch (error) {
          console.error('Error loading video data:', error);
          setVideoError(`영상 로드 오류: ${error.message}`);
          setLoading(false);
        }
      }
    };
    
    loadVideoData();
  }, [id, filename, incidentVideos]);

  // 뒤로가기 핸들러
  const handleGoBack = () => {
    navigate(-1); // 브라우저 히스토리에서 이전 페이지로
  };

  // 확인 상태 토글 핸들러
  const handleToggleCheck = () => {
    if (videoData && updateVideoCheckStatus) {
      const newCheckStatus = !videoData.isChecked;
      // id가 있으면 id 우선, 없으면 filename 사용
      updateVideoCheckStatus(videoData.id ?? videoData.filename, newCheckStatus);

      // 로컬 상태도 업데이트
      setVideoData((prev) => ({
        ...prev,
        isChecked: newCheckStatus,
      }));
    }
  };

  // 영상 재생/정지 토글
  const handlePlayToggle = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play().catch(error => {
          console.error('Video play error:', error);
          setVideoError('영상 재생 중 오류가 발생했습니다.');
        });
      }
    }
  };

  // 비디오 이벤트 핸들러
  const handleVideoPlay = () => setIsPlaying(true);
  const handleVideoPause = () => setIsPlaying(false);
  const handleVideoTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };
  const handleVideoLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };
  const handleVideoError = (e) => {
    console.error('Video load error:', e);
    console.error('Video element:', e.target);
    console.error('Video src:', e.target?.src);
    console.error('Video readyState:', e.target?.readyState);
    console.error('Video networkState:', e.target?.networkState);
    console.error('Video error code:', e.target?.error?.code);
    console.error('Video error message:', e.target?.error?.message);
    
    // 오류 코드에 따른 상세 메시지
    let errorMessage = '영상을 로드할 수 없습니다.';
    if (e.target?.error) {
      switch(e.target.error.code) {
        case 1: // MEDIA_ERR_ABORTED
          errorMessage += ' 사용자가 다운로드를 중단했습니다.';
          break;
        case 2: // MEDIA_ERR_NETWORK
          errorMessage += ' 네트워크 오류가 발생했습니다.';
          break;
        case 3: // MEDIA_ERR_DECODE
          errorMessage += ' 디코딩 오류가 발생했습니다. 파일 형식이 지원되지 않을 수 있습니다.';
          break;
        case 4: // MEDIA_ERR_SRC_NOT_SUPPORTED
          errorMessage += ' 비디오 형식이 지원되지 않습니다.';
          break;
        default:
          errorMessage += ' 알 수 없는 오류가 발생했습니다.';
      }
    }
    
    setVideoError(errorMessage);
  };

  // 진행 바 클릭 핸들러
  const handleProgressClick = (e) => {
    if (videoRef.current && duration > 0) {
      const rect = e.currentTarget.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickRatio = clickX / rect.width;
      const newTime = clickRatio * duration;
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  // 날짜 포맷팅
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    return `${year}년 ${month}월 ${day}일 ${hours}:${minutes}`;
  };

  // 시간 포매팅
  const formatTime = (timeInSeconds) => {
    if (isNaN(timeInSeconds)) return '0:00';
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = Math.floor(timeInSeconds % 60);
    return `${minutes}:${String(seconds).padStart(2, '0')}`;
  };

  // 파일 크기 가져오기
  const getFileSize = () => {
    return videoData?.size ? `${Math.round(videoData.size / 1024 / 1024)}MB` : `${Math.floor(Math.random() * 500 + 100)}MB`;
  };

  if (loading) {
    return (
      <div className="checkVideoPage">
        <div className="loading">
          <p>영상 정보를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!videoData) {
    return (
      <div className="checkVideoPage">
        <div className="notFound">
          <h2>영상을 찾을 수 없습니다</h2>
          <p>요청하신 영상이 존재하지 않거나 삭제되었습니다.</p>
          <button onClick={handleGoBack}>뒤로가기</button>
        </div>
      </div>
    );
  }

  return (
    <div className="checkVideoPage">
      {/* 헤더 */}
      <div className="videoHeader">
        <button
          className="backButton"
          onClick={handleGoBack}
          style={{
            border: "none",
            background: "none",
            fontSize: "24px",
            cursor: "pointer",
          }}
        >
          ←
        </button>
        <h1>영상 상세 정보</h1>
      </div>

      <div className="videoContent">
        {/* 영상 플레이어 영역 */}
        <div className="videoPlayerSection">
          <div className="videoPlayer">
            {videoError ? (
              <div className="videoError">
                <VideoBtnSmall />
                <p>{videoError}</p>
                <p>영상 URL: {videoUrl}</p>
                <div style={{marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '5px'}}>
                  <button 
                    onClick={() => window.open(videoUrl, '_blank')}
                    style={{padding: '5px 10px'}}
                  >
                    새 탭에서 열기
                  </button>
                  
                  {/* 확실히 작동하는 테스트 비디오들 */}
                  <button 
                    onClick={() => {
                      const testUrl = 'http://localhost:5000/media/videos/web_test_h264.mp4';
                      setVideoUrl(testUrl);
                      setVideoError(null);
                    }}
                    style={{padding: '5px 10px'}}
                  >
                    H.264 테스트
                  </button>
                  
                  <button 
                    onClick={() => {
                      const testUrl = 'http://localhost:5000/media/videos/simple_web_test.mp4';
                      setVideoUrl(testUrl);
                      setVideoError(null);
                    }}
                    style={{padding: '5px 10px'}}
                  >
                    간단 테스트
                  </button>
                  
                  <button 
                    onClick={() => {
                      const testUrl = 'http://localhost:5000/media/videos/minimal_web.mp4';
                      setVideoUrl(testUrl);
                      setVideoError(null);
                    }}
                    style={{padding: '5px 10px'}}
                  >
                    최소 MP4
                  </button>
                  
                  <button 
                    onClick={() => {
                      const testUrl = 'http://localhost:5000/media/videos/web_reliable_mp4v.mp4';
                      setVideoUrl(testUrl);
                      setVideoError(null);
                    }}
                    style={{padding: '5px 10px'}}
                  >
                    MP4V 코덱
                  </button>
                  
                  <button 
                    onClick={() => {
                      const testUrl = 'http://localhost:5000/media/videos/web_reliable_h264.mp4';
                      setVideoUrl(testUrl);
                      setVideoError(null);
                    }}
                    style={{padding: '5px 10px'}}
                  >
                    H264 코덱
                  </button>
                  
                  <button 
                    onClick={() => {
                      const testUrl = 'https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4';
                      setVideoUrl(testUrl);
                      setVideoError(null);
                    }}
                    style={{padding: '5px 10px'}}
                  >
                    웹 샘플
                  </button>
                </div>
              </div>
            ) : videoUrl ? (
              <video
                ref={videoRef}
                src={videoUrl}
                onPlay={handleVideoPlay}
                onPause={handleVideoPause}
                onTimeUpdate={handleVideoTimeUpdate}
                onLoadedMetadata={handleVideoLoadedMetadata}
                onError={handleVideoError}
                controls={false}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                  backgroundColor: '#000'
                }}
              />
            ) : (
              <div className="videoPlaceholder">
                <VideoBtnSmall />
                <p>영상을 로드하는 중...</p>
              </div>
            )}

            {/* 재생 버튼 오버레이 */}
            {!isPlaying && videoUrl && !videoError && (
              <div 
                className="playOverlay" 
                onClick={handlePlayToggle}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor: 'rgba(0,0,0,0.3)',
                  cursor: 'pointer'
                }}
              >
                <div className="playButton">
                  ▶ 재생
                </div>
              </div>
            )}
          </div>

          {/* 영상 컨트롤 */}
          <div className="videoControls">
            <button
              className={`playBtn ${isPlaying ? "playing" : ""}`}
              onClick={handlePlayToggle}
              disabled={!videoUrl || videoError}
            >
              {isPlaying ? "⏸ 정지" : "▶ 재생"}
            </button>
            <div className="videoProgress">
              <div 
                className="progressBar" 
                onClick={handleProgressClick}
                style={{ cursor: 'pointer' }}
              >
                <div 
                  className="progress" 
                  style={{ 
                    width: duration > 0 ? `${(currentTime / duration) * 100}%` : '0%' 
                  }}
                ></div>
              </div>
              <span className="timeInfo">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>
          </div>
        </div>

        {/* 영상 정보 영역 */}
        <div className="videoInfoSection">
          <div className="videoInfo">
            <h2>{videoData.filename}</h2>

            <div className="infoGrid">
              <div className="infoItem">
                <label>생성 일시:</label>
                <span>{formatDate(videoData.createdAt)}</span>
              </div>

              <div className="infoItem">
                <label>파일 크기:</label>
                <span>{getFileSize()}</span>
              </div>

              <div className="infoItem">
                <label>영상 길이:</label>
                <span>{duration > 0 ? formatTime(duration) : '로드 중...'}</span>
              </div>

              <div className="infoItem">
                <label>해상도:</label>
                <span>1920 × 1080</span>
              </div>
            </div>

            {/* 확인 상태 섹션 */}
            <div className="checkStatusSection">
              <div className="statusInfo">
                <label>확인 상태:</label>
                <div
                  className={
                    videoData.isChecked
                      ? "statusBadge checked"
                      : "statusBadge unchecked"
                  }
                >
                  {videoData.isChecked ? "✓ 확인 완료" : "⏳ 확인 대기"}
                </div>
              </div>

              <button
                className={`toggleCheckBtn ${
                  videoData.isChecked ? "checked" : "unchecked"
                }`}
                onClick={handleToggleCheck}
              >
                {videoData.isChecked ? "미확인으로 변경" : "확인 완료로 변경"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CheckVideo;