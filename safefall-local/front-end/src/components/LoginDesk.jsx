import { useState } from "react";

import "./LoginDesk.css";

function LoginDesk({ isLoggedIn, currentUser, onLogin, onLogout }) {
  
  if (isLoggedIn && currentUser) {
    // 로그인된 상태 UI
    return (
      <div className="SignInSignUpContactUsBtn">
        <button onClick={onLogout}>Log out</button>
        <p 
          onClick={onLogout} 
          style={{ cursor: 'pointer', color: '#69BDF9' }}
          className="user-id-text"
        >
          {currentUser.id}
        </p>
      </div>
    );
  }

  // 로그인 안된 상태 UI (기존)
  return (
    <div className="SignInSignUpContactUsBtn">
      <button>문의하기</button>
      <p>/</p>
      <button onClick={onLogin}>Sign In</button>
      <p>/</p>
      <button>Sign Up</button>
    </div>
  );
}

export default LoginDesk;