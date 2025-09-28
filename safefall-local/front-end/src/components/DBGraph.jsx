import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

import WindowSize from "../hooks/windowSize";
import DBdata from "../hooks/DBdata"; // DBdata 함수 import

import "./DBGraph.css"

const DBGraph = ({ incidentVideos }) => {
  const { width } = WindowSize();
  
  // DBdata 함수에 props로 받은 데이터 전달
  const { chartData, tableData, rawData } = DBdata(incidentVideos);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="tooltip">
          <p className="tooltip-label">{`날짜: ${data.originalDate}`}</p>
          <p className="tooltip-entry">{`전체 영상: ${payload[0].value}개`}</p>
        </div>
      );
    }
    return null;
  };

  // 데이터가 없을 때 로딩 상태 표시
  if (!rawData || rawData.length === 0) {
    return (
      <div className="video-count-chart">
        <div className="chart-container">
          <div className="loading-state">
            <p>데이터를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  // X축 설정: 0~11 (Jan=0) + tick 포맷을 MM로 표시
  const xTicks = Array.from({ length: 12 }, (_, i) => i);

  return (
    <div className="video-count-chart">
      {/* 차트 */}
      <div className="chart-container">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              domain={[0, 11]}
              dataKey="xPosition"
              ticks={xTicks}
              tickFormatter={(value) => `${String(value + 1).padStart(2, '0')}`}
            />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="total"
              stroke="#3b82f6"
              strokeWidth={2}
              name="전체 영상"
              dot={{ fill: "#3b82f6", strokeWidth: 2, r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 데이터 테이블 - 모바일에서만 표시 */}
      {width < 1200 ? (
        <div className="data-table-container">
          <h3>월별 상세 데이터</h3>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>날짜</th>
                  <th>전체</th>
                  <th>확인됨</th>
                  <th>미확인</th>
                </tr>
              </thead>
              <tbody>
                {tableData.map((row, index) => (
                  <tr key={`${row.month}-${index}`}>
                    <td className="date-cell">{row.date}</td>
                    <td className="count-cell">{row.total}개</td>
                    <td className="count-cell checked">{row.checked}개</td>
                    <td className="count-cell unchecked">{row.unchecked}개</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div></div>
      )}
    </div>
  );
};

export default DBGraph;