import { useState } from "react";
import { useNavigate } from "react-router-dom"; // React Router 추가

import WindowSize from "../hooks/windowSize";

import "./BeforeLogin.css";

// 무한 슬라이더 컴포넌트
function InfiniteSlider({ images, speed = 30 }) {
  return (
    <div className="infinite-slider-wrapper">
      <div 
        className="infinite-slider-track" 
        style={{ animationDuration: `${speed}s` }}
      >
        {/* 원본 이미지들 */}
        {images.map((image, index) => (
          <img 
            key={`original-${index}`}
            src={image} 
            alt={`이미지${index + 1}`}
            className="infinite-slider-img"
          />
        ))}
        {/* 복사본 1 */}
        {images.map((image, index) => (
          <img 
            key={`copy1-${index}`}
            src={image} 
            alt={`이미지${index + 1}`}
            className="infinite-slider-img"
          />
        ))}
        {/* 복사본 2 */}
        {images.map((image, index) => (
          <img 
            key={`copy2-${index}`}
            src={image} 
            alt={`이미지${index + 1}`}
            className="infinite-slider-img"
          />
        ))}
      </div>
    </div>
  );
}

function BeforeLogin() {
  const { width } = WindowSize();
  const navigate = useNavigate(); // React Router의 useNavigate 사용

  // 로그인 페이지로 이동하는 핸들러
  const handleGoToLogin = () => {
    navigate('/login');
  };

  // SafeFall 시작하기 버튼 핸들러 (향후 회원가입 페이지로 연결 가능)
  const handleStartSafeFall = () => {
    // 현재는 로그인 페이지로 이동, 향후 회원가입 페이지로 변경 가능
    navigate('/login');
  };

  // 각 섹션별 이미지 배열
  const imageGroups = {
    section1: ["01_001.png", "01_002.png", "01_003.png"],
    section2: ["02_001.png", "02_002.png", "02_003.png"],
    section3: ["03_001.png", "03_002.png", "03_003.png"],
    section4: ["04_001.png", "04_002.png", "04_003.png"],
    section5: ["05_001.png", "05_002.png", "05_003.png"]
  };

  return (
    <div className="BeforeLoginWindow">
      <div className="OurInfo OurInfo001">
        <div className="SimpleInfo InfoRight">
          <div className="SimpleInfoMobile">
            <h3>착용이 필요 없는 완전 비접촉식 시스템</h3>
            <p>
              기존의 웨어러블 기기 착용 방식에서 벗어나,<br />사용자의 별도착용 없이
              모니터링 하여<br />사용자의 편의성과 심리적 부담을 줄여줍니다
            </p>
          </div>
          <div className="BeforeSignInSignUpBox">
            <button onClick={handleStartSafeFall}>SafeFall 시작하기</button>
            {width > 1200 ? <p>또는</p> : <div className="unkown"></div>}
            <button onClick={handleGoToLogin}>로그인 바로가기</button>
          </div>
        </div>
        <div className="SimpleInfoImg">
          <InfiniteSlider images={imageGroups.section1} speed={25} />
        </div>
      </div>
      
      <div className="OurInfo OurInfo002">
        <div className="SimpleInfo InfoLeft">
          <div className="SimpleInfoMobile">
            <h3>실시간 판단 및 자동 알림 구조</h3>
            <p>
              위험 상황을 실시간으로 판단해 즉시 보호자에게<br />문자, 푸시 알림
              등으로 신속히 전달합니다
            </p>
          </div>
          <div className="BeforeSignInSignUpBox">
            <button onClick={handleStartSafeFall}>SafeFall 시작하기</button>
            {width > 1200 ? <p>또는</p> : <div className="unkown"></div>}
            <button onClick={handleGoToLogin}>로그인 바로가기</button>
          </div>
        </div>
        <div className="SimpleInfoImg">
          <InfiniteSlider images={imageGroups.section2} speed={30} />
        </div>
      </div>
      
      <div className="OurInfo OurInfo003">
        <div className="SimpleInfo InfoRight">
          <div className="SimpleInfoMobile">
            <h3>사용자 맞춤 임계값 설정 가능성</h3>
            <p>
              사용자 개개인의 생활 습관이나 환경에 따라<br />맞춤설정이 가능합니다
            </p>
          </div>
          <div className="BeforeSignInSignUpBox">
            <button onClick={handleStartSafeFall}>SafeFall 시작하기</button>
            {width > 1200 ? <p>또는</p> : <div className="unkown"></div>}
            <button onClick={handleGoToLogin}>로그인 바로가기</button>
          </div>
        </div>
        <div className="SimpleInfoImg">
          <InfiniteSlider images={imageGroups.section3} speed={35} />
        </div>
      </div>
      
      <div className="OurInfo OurInfo004">
        <div className="SimpleInfo InfoLeft">
          <div className="SimpleInfoMobile">
            <h3>다양한 실내 환경에 최적화된 설치 구조</h3>
            <p>
              3D 프린팅을 활용한 맞춤형 하우징 설계로 다양한 실내 구조와<br />조건에
              유연한 설치가 가능합니다
            </p>
          </div>
          <div className="BeforeSignInSignUpBox">
            <button onClick={handleStartSafeFall}>SafeFall 시작하기</button>
            {width > 1200 ? <p>또는</p> : <div className="unkown"></div>}
            <button onClick={handleGoToLogin}>로그인 바로가기</button>
          </div>
        </div>
        <div className="SimpleInfoImg">
          <InfiniteSlider images={imageGroups.section4} speed={20} />
        </div>
      </div>
      
      <div className="OurInfo OurInfo005">
        <div className="SimpleInfo InfoRight">
          <div className="SimpleInfoMobile">
            <h3>기존 복지 서비스와의 명확한 비교 우위</h3>
            <p>
              기존의 응급안전알림서비스와는 달리 AI 기반으로 상태를<br />자동으로
              인식 하기에 인지 능력이 낮거나<br />조작이 어려운 고령자도 안전하게
              지켜드립니다.
            </p>
          </div>
          <div className="BeforeSignInSignUpBox">
            <button onClick={handleStartSafeFall}>SafeFall 시작하기</button>
            {width > 1200 ? <p>또는</p> : <div className="unkown"></div>}
            <button onClick={handleGoToLogin}>로그인 바로가기</button>
          </div>
        </div>
        <div className="SimpleInfoImg">
          <InfiniteSlider images={imageGroups.section5} speed={28} />
        </div>
      </div>
    </div>
  );
}

export default BeforeLogin;