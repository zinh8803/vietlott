import { useState, useEffect } from 'react';
import API from '../api';

function BallGroup({ numbers = [], predicted = [], size = 'normal' }) {
  const predictedSet = new Set(predicted.map(Number));
  return (
    <div className="number-balls">
      {numbers.map((n, idx) => (
        <div key={`${idx}-${n}`} className={`ball ${predictedSet.has(n) ? 'hit' : 'primary'} ${size === 'sm' ? 'sm' : ''}`}>
          {String(n).padStart(2, '0')}
        </div>
      ))}
    </div>
  );
}

function PredBalls({ numbers = [], actual = [] }) {
  const actualSet = new Set(actual.map(Number));
  return (
    <div className="number-balls">
      {numbers.map(n => (
        <div key={n} className={`ball ${actual.length ? (actualSet.has(n) ? 'hit' : 'miss') : 'predicted'} sm`}>
          {String(n).padStart(2, '0')}
        </div>
      ))}
    </div>
  );
}

export default function Predictions() {
  const [product, setProduct] = useState('MEGA_645');
  const [data, setData] = useState({ total: 0, data: [] });
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const PER_PAGE = 20;

  const load = async () => {
    setLoading(true);
    try {
      const res = await API.get(`/api/predictions?product_code=${product}&limit=${PER_PAGE}&offset=${page * PER_PAGE}`);
      setData(res.data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { setPage(0); }, [product]);
  useEffect(() => { load(); }, [product, page]);

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">🎯 Dự đoán</h1>
          <div className="page-subtitle">Lịch sử dự đoán và kết quả đối chiếu</div>
        </div>
        <div className="product-tabs">
          <button className={`product-tab ${product === 'MEGA_645' ? 'active' : ''}`} onClick={() => setProduct('MEGA_645')}>Mega 6/45</button>
          <button className={`product-tab ${product === 'POWER_655' ? 'active' : ''}`} onClick={() => setProduct('POWER_655')}>Power 6/55</button>
          <button className={`product-tab ${product === 'BINGO18' ? 'active' : ''}`} onClick={() => setProduct('BINGO18')}>Bingo18</button>
        </div>
      </div>

      <div className="page-body">
        <div className="card">
          <div className="card-body flex items-center justify-between mb-4" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
            <span className="text-secondary text-sm">Tổng {data.total} dự đoán</span>
            <button className="btn btn-secondary btn-sm" onClick={load}>🔄 Làm mới</button>
          </div>

          {loading ? (
            <div className="loader-wrap"><div className="spin">⏳</div> Đang tải...</div>
          ) : data.data.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🎯</div>
              <h3>Chưa có dự đoán</h3>
              <p>Vào trang Điều khiển để train model và sinh dự đoán.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Kỳ</th>
                    <th>Số dự đoán</th>
                    <th>Kết quả thực tế</th>
                    <th>Hit</th>
                    <th>Trạng thái</th>
                    <th>Model ID</th>
                    <th>Thời gian tạo</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map(p => (
                    <tr key={p.prediction_id} className="animate-in">
                      <td>
                        <span className="font-mono font-bold">#{p.predicted_draw_no}</span>
                        <div className="text-sm text-muted">{p.predicted_draw_date}</div>
                      </td>
                      <td><PredBalls numbers={p.top6 || []} actual={p.actual_top6 || []} /></td>
                      <td>
                        {p.actual_top6
                          ? <BallGroup numbers={product === 'BINGO18' ? p.actual_top6.filter(n => n > 0) : p.actual_top6} predicted={p.top6 || []} size="sm" />
                          : <span className="text-muted text-sm">Chưa có kết quả</span>
                        }
                      </td>
                      <td>
                        {p.hit_count != null ? (
                          <span style={{
                            fontSize: 20, fontWeight: 800,
                            color: p.hit_count >= (product === 'BINGO18' ? 2 : 3) ? 'var(--accent-emerald)' : p.hit_count >= 1 ? 'var(--accent-amber)' : 'var(--text-muted)'
                          }}>
                            {p.hit_count}/{product === 'BINGO18' ? '3' : '6'}
                          </span>
                        ) : '—'}
                      </td>
                      <td><span className={`badge ${p.status}`}>{p.status}</span></td>
                      <td><span className="font-mono text-sm">#{p.model_id}</span></td>
                      <td><span className="text-sm text-secondary">{p.generated_at.slice(0, 16).replace('T', ' ')}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          <div className="flex items-center justify-between" style={{ padding: '16px 24px', borderTop: '1px solid var(--border)' }}>
            <button className="btn btn-secondary btn-sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Trước</button>
            <span className="text-sm text-muted">Trang {page + 1} / {Math.ceil(data.total / PER_PAGE) || 1}</span>
            <button className="btn btn-secondary btn-sm" disabled={(page + 1) * PER_PAGE >= data.total} onClick={() => setPage(p => p + 1)}>Tiếp →</button>
          </div>
        </div>
      </div>
    </>
  );
}
