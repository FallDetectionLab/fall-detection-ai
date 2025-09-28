import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom"; // React Router 추가

import Logo from "../assets/Logo";
import LoginDesk from "./LoginDesk";
import LoginMobile from "./LoginMobile";
import WindowSize from "../hooks/windowSize";
import TMslideMenu from "./TMslideMenu";
import { useAuth } from "../App";

import "./Header.css";

function Header() {
  const { width, height } = WindowSize();
  const { isLoggedIn, currentUser, logout } = useAuth();
  const navigate = useNavigate(); // React Router의 useNavigate 사용
  const location = useLocation(); // 현재 경로 정보
  
  // TMslideMenu 열림/닫힘 상태
  const [isTMMenuOpen, setIsTMMenuOpen] = useState(false);

  // Logo 클릭 핸들러
  const handleLogoClick = () => {
    if (isLoggedIn) {
      navigate('/dashboard'); // 로그인 상태면 대시보드로
    } else {
      navigate('/'); // 비로그인 상태면 홈으로
    }
  };

  // 로그인 페이지로 이동
  const handleNavigateToLogin = () => {
    navigate('/login');
  };

  // 로그아웃 핸들러
  const handleLogout = () => {
    logout();
    navigate('/'); // 로그아웃 후 홈으로 리다이렉트
  };

  // TMslideMenu 열기
  const handleTMMenuOpen = () => {
    setIsTMMenuOpen(true);
  };

  // TMslideMenu 닫기
  const handleTMMenuClose = () => {
    setIsTMMenuOpen(false);
  };

  return (
    <>
      <header>
        <div className="HeaderSection">
          {/* Logo 클릭 시 홈으로 이동 */}
          <div onClick={handleLogoClick} style={{ cursor: 'pointer' }}>
            <Logo />
          </div>
          
          {width < 1200 ? (
            <div className="mainmenuBtn">
              {/* LoginMobile 클릭 시 TMslideMenu 열기 */}
              <div onClick={handleTMMenuOpen} style={{ cursor: 'pointer' }}>
                <LoginMobile />
              </div>
            </div>
          ) : (
            // 데스크톱 버전: LoginDesk에 로그인 상태 전달
            <LoginDesk 
              isLoggedIn={isLoggedIn}
              currentUser={currentUser}
              onLogin={handleNavigateToLogin}
              onLogout={handleLogout}
            />
          )}
        </div>
      </header>
      
      {/* TMslideMenu 컴포넌트 */}
      <TMslideMenu 
        isOpen={isTMMenuOpen}
        onClose={handleTMMenuClose}
        isLoggedIn={isLoggedIn}
        currentUser={currentUser}
        onLogin={handleNavigateToLogin}
        onLogout={handleLogout}
        currentPath={location.pathname} // 현재 경로 정보 전달
      />
    </>
  );
}

export default Header;