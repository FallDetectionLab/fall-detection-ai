import { useState, useEffect } from 'react';

function WindowSize() {
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    // 리사이즈 핸들러
    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    // 이벤트 리스너 등록
    window.addEventListener('resize', handleResize);

    // cleanup 함수
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return windowSize;
}

export default WindowSize;