import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom"; // React Router 추가

import WindowSize from "../hooks/windowSize";
import Logo from "../assets/Logo";

import "./TMslideMenu.css";

function TMslideMenu({
  isOpen,
  onClose,
  isLoggedIn,
  currentUser,
  onLogin,
  onLogout,
  currentPath, // 현재 경로 정보 추가
}) {
  const { width, height } = WindowSize();
  const navigate = useNavigate(); // React Router의 useNavigate 사용

  // TMmenuBG 클릭 핸들러 (메뉴 닫기)
  const handleBGClick = (e) => {
    // 배경(TMmenuBG) 클릭시에만 메뉴 닫기
    if (e.target.classList.contains("TMmenuBG")) {
      onClose();
    }
  };

  // ESC 키로 메뉴 닫기
  useEffect(() => {
    const handleEscKey = (event) => {
      if (event.key === "Escape" && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscKey);
      // 스크롤 방지
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscKey);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  // 메뉴 항목 클릭 핸들러
  const handleMenuClick = (action, path) => {
    // 메뉴 항목 클릭 후 메뉴 닫기
    onClose();
    
    // 각 액션 실행
    if (action === "login") {
      onLogin();
    } else if (action === "logout") {
      onLogout();
    } else if (path) {
      // 페이지 이동
      navigate(path);
    }
  };

  // 현재 페이지인지 확인하는 함수
  const isActivePage = (path) => {
    return currentPath === path;
  };

  return (
    <div className={`TMmenuBox ${isOpen ? "open" : ""}`}>
      <div className="TMmenuBG" onClick={handleBGClick}></div>
      <menu className="TMmenu">
        <div className="TMmenuLogobox-header">
          <Logo />
        </div>

        {isLoggedIn ? (
          // 로그인된 상태
          <>
            <ul>
              <li 
                onClick={() => handleMenuClick(null, '/dashboard')}
                className={isActivePage('/dashboard') ? 'active' : ''}
              >
                대시보드
              </li>
              <li 
                onClick={() => handleMenuClick(null, '/history')}
                className={isActivePage('/history') ? 'active' : ''}
              >
                기록보기
              </li>
              <li 
                onClick={() => handleMenuClick(null, '/live')}
                className={isActivePage('/live') ? 'active' : ''}
              >
                실시간 영상
              </li>
              <li onClick={() => handleMenuClick()}>문의하기</li>
            </ul>
            <div className="TMmenuLoginBox">
              <div className="TMmenuUserInfo">
                <p>
                  안녕하세요,<br/><strong>{currentUser?.id}</strong>님
                </p>
              </div>
              <button onClick={() => handleMenuClick("logout")}>Log out</button>
            </div>
          </>
        ) : (
          // 로그인 안된 상태
          <>
            <ul>
              <li 
                onClick={() => handleMenuClick(null, '/')}
                className={isActivePage('/') ? 'active' : ''}
              >
                서비스 소개
              </li>
              <li onClick={() => handleMenuClick()}>문의하기</li>
            </ul>
            <div className="TMmenuLoginBox">
              <button onClick={() => handleMenuClick("login")}>SignIn</button>
              <button onClick={() => handleMenuClick()}>SignUp</button>
            </div>
          </>
        )}
      </menu>
    </div>
  );
}

export default TMslideMenu;