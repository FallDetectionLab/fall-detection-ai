// LoginPage.jsx 올바른 수정 버전

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../App";

import "./LoginPage.css";

function LoginPage({ 
  userCredentials, 
  validateCredentials, 
  getUserByCredentials 
}) {
  const { login } = useAuth();
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    id: "",
    pw: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // 입력값 변경 핸들러
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (error) setError("");
  };

  // ✅ 핵심: async 키워드 추가!
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      // props로 받은 validateCredentials 함수 사용
      if (validateCredentials && validateCredentials(formData.id, formData.pw)) {
        // ✅ 이제 await 사용 가능!
        const user = await getUserByCredentials(formData.id, formData.pw);
        
        if (user) {
          // 백엔드에서 받은 사용자 정보 그대로 사용
          login({
            id: user.id || user.username || formData.id,
            username: user.username || user.id || formData.id,
            name: user.name || user.username || user.id || formData.id
          });
          navigate('/dashboard');
        } else {
          setError("로그인에 실패했습니다.");
        }
      } else {
        setError("아이디 또는 비밀번호가 올바르지 않습니다.");
      }
    } catch (error) {
      console.error('Login error:', error);
      setError("로그인 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  // 자동 로그인 핸들러 (각 서비스별 고정 정보로 로그인)
  const handleAutoLogin = async (username, password, serviceName) => {
    try {
      setIsLoading(true);
      setError("");
      
      // 해당 계정으로 로그인 시도
      if (validateCredentials && validateCredentials(username, password)) {
        const user = await getUserByCredentials(username, password);
        
        if (user) {
          login({
            id: user.id || user.username || username,
            username: user.username || user.id || username,
            name: user.name || user.username || username
          });
          navigate('/dashboard');
        } else {
          setError(`${serviceName} 로그인에 실패했습니다.`);
        }
      } else {
        setError(`${serviceName} 계정 정보가 올바르지 않습니다.`);
      }
    } catch (error) {
      console.error(`${serviceName} login error:`, error);
      setError(`${serviceName} 로그인 중 오류가 발생했습니다.`);
    } finally {
      setIsLoading(false);
    }
  };

  // 각 서비스별 로그인 핸들러
  const handleNaverLogin = () => handleAutoLogin("네이버", "12345678!", "Naver");
  const handleGoogleLogin = () => handleAutoLogin("구글", "12345678!", "Google");
  const handleKakaoLogin = () => handleAutoLogin("카카오", "12345678!", "Kakao");

  return (
    <div className="login-page">
      <div className="login-container">
        <h1>SafeFall 로그인</h1>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="id">아이디</label>
            <input
              type="text"
              id="id"
              name="id"
              value={formData.id}
              onChange={handleInputChange}
              placeholder="아이디를 입력하세요"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="pw">비밀번호</label>
            <input
              type="password"
              id="pw"
              name="pw"
              value={formData.pw}
              onChange={handleInputChange}
              placeholder="비밀번호를 입력하세요"
              required
              disabled={isLoading}
            />
          </div>

          {error && <div className="error-message">{error}</div>}
          
          <div className="TMmenuLoginBtnBox">
            <button type="submit" className="login-button" disabled={isLoading}>
              {isLoading ? "로그인 중..." : "로그인"}
            </button>
            <button type="button" className="SignUpBtn" disabled={isLoading}>
              회원가입
            </button>
          </div>
        </form>

        <div className="autoLoginBox">
          <p className="autoLogin-text">자동 로그인</p>
          
          <button 
            className="dumy001Btn" 
            onClick={handleNaverLogin}
            disabled={isLoading}
          >
            Naver 로그인
          </button>
          
          <button 
            className="dumy001Btn" 
            onClick={handleGoogleLogin}
            disabled={isLoading}
          >
            Google 로그인
          </button>
          
          <button 
            className="dumy001Btn" 
            onClick={handleKakaoLogin}
            disabled={isLoading}
          >
            Kakao 로그인
          </button>
        </div>

        <div className="login-footer">
          <button 
            className="back-button" 
            onClick={() => navigate('/')}
            disabled={isLoading}
          >
            홈으로 돌아가기
          </button>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;