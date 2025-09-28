import { useMemo } from 'react';

function DBdata(incidentVideos = []) {

  // 그래프용 데이터 (기존 방식 유지)
  const chartData = useMemo(() => {
    if (!incidentVideos.length) return [];
    
    // 실제 데이터를 일별로 집계
    const dailyData = {};
    
    incidentVideos.forEach(item => {
      const date = item.createdAt;
      if (!dailyData[date]) {
        dailyData[date] = {
          date: date,
          total: 0,
          checked: 0,
          unchecked: 0
        };
      }
      
      dailyData[date].total += 1;
      if (item.isChecked) {
        dailyData[date].checked += 1;
      } else {
        dailyData[date].unchecked += 1;
      }
    });

    // 일별 데이터를 월 좌표계로 변환
    const chartPoints = Object.values(dailyData).map(item => {
      const dateObj = new Date(item.date);
      const month = dateObj.getMonth() + 1; // 1~12
      const day = dateObj.getDate();
      const daysInMonth = new Date(2024, month, 0).getDate(); // 해당 월의 총 일수
      
      // 월 내에서의 위치 계산 (월 시작을 0, 월 끝을 1로 하는 비율)
      const positionInMonth = (day - 1) / (daysInMonth - 1);
      
      // 실제 X축 좌표 (월 번호 + 월 내 위치)
      const xPosition = month + positionInMonth - 1; // 1월을 1, 2월을 2로 시작
      
      return {
        date: `${String(month).padStart(2, '0')}월`,
        xPosition: xPosition,
        originalDate: item.date,
        total: item.total,
        checked: item.checked,
        unchecked: item.unchecked
      };
    });

    return chartPoints.sort((a, b) => a.xPosition - b.xPosition);
  }, [incidentVideos]);

  // 테이블용 월별 집계 데이터
  const tableData = useMemo(() => {
    if (!incidentVideos.length) return [];
    
    // 월별 데이터 초기화 (1월~12월)
    const monthlyData = {};
    for (let month = 1; month <= 12; month++) {
      monthlyData[month] = {
        month: month,
        date: `${String(month).padStart(2, '0')}월`,
        total: 0,
        checked: 0,
        unchecked: 0
      };
    }
    
    // 실제 데이터를 월별로 집계
    incidentVideos.forEach(item => {
      const dateObj = new Date(item.createdAt);
      const month = dateObj.getMonth() + 1; // 1~12
      
      monthlyData[month].total += 1;
      if (item.isChecked) {
        monthlyData[month].checked += 1;
      } else {
        monthlyData[month].unchecked += 1;
      }
    });

    // 객체를 배열로 변환하고 월순으로 정렬
    return Object.values(monthlyData).sort((a, b) => a.month - b.month);
  }, [incidentVideos]);

  // 원본 데이터와 가공된 데이터를 모두 반환
  return {
    rawData: incidentVideos, // DataContext에서 가져온 데이터
    chartData,
    tableData
  };
}

export default DBdata;

/*
향후 백엔드 연결 시 사용할 코드:

import { useMemo, useState, useEffect } from 'react';
import { useData } from './DataContext';
import { api } from '../utils/api';

function useDBdata() {
  // DataContext에서 필요한 함수들 가져오기
  const { 
    incidentVideos, 
    updateVideoCheckStatus, 
    addNewIncidentVideo,
    setIncidentVideos 
  } = useData();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 백엔드에서 데이터 가져오기 (옵션)
  const fetchDataFromAPI = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 환경에 따라 실제 API 또는 Mock 데이터 사용
      const data = process.env.NODE_ENV === 'development' 
        ? await api.getMockVideoData()  // 개발 환경: Mock 데이터
        : await api.getVideoData();     // 프로덕션: 실제 API
        
      // DataContext에 데이터 업데이트
      setIncidentVideos(data);
    } catch (err) {
      console.error('데이터 로딩 실패:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 비디오 상태 업데이트 함수 (백엔드 연동)
  const updateVideoStatusAPI = async (filename, isChecked) => {
    try {
      await api.updateVideoStatus(filename, isChecked);
      
      // DataContext 상태 업데이트
      updateVideoCheckStatus(filename, isChecked);
    } catch (err) {
      console.error('비디오 상태 업데이트 실패:', err);
      throw err;
    }
  };

  // 그래프용 데이터 (동일한 로직)
  const chartData = useMemo(() => {
    // ... 동일한 로직
  }, [incidentVideos]);

  // 테이블용 월별 집계 데이터 (동일한 로직)
  const tableData = useMemo(() => {
    // ... 동일한 로직
  }, [incidentVideos]);

  return {
    rawData: incidentVideos,
    chartData,
    tableData,
    loading,
    error,
    updateVideoStatus: updateVideoStatusAPI,
    refreshData: fetchDataFromAPI
  };
}

export default useDBdata;
*/