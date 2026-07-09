import { useState, useEffect } from 'react';
import API from '../api';

function FrequencyBar({ number, count, maxCount, total }) {
  const pct = maxCount > 0 ? (count / maxCount * 100).toFixed(1) : 0;
  const freq = total > 0 ? (count / total * 100).toFixed(1) : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        background: 'linear-gradient(145deg, #3b82f6, #1d4ed8)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 700, color: '#fff', flexShrink: 0,
        fontFamily: 'JetBrains Mono',
      }}>
        {String(number).padStart(2, '0')}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ height: 6, background: 'var(--bg-surface)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${pct}%`,
            background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
            borderRadius: 3, transition: 'width 0.5s ease',
          }} />
        </div>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono', width: 42, textAlign: 'right' }}>
        {freq}%
      </div>
    </div>
  );
}

export default function Draws() {
  const [product, setProduct] = useState('MEGA_645');
  const [data, setData] = useState({ total: 0, data: [] });
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [freqMap, setFreqMap] = useState({});
  const [selectedYear, setSelectedYear] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [years, setYears] = useState([]);
  const PER_PAGE = 30;

  const load = async (customSearch = null, customYear = null) => {
    setLoading(true);
    try {
      const qSearch = customSearch !== null ? customSearch : searchQuery;
      const qYear = customYear !== null ? customYear : selectedYear;

      let url = `/api/draws?product_code=${product}&limit=200&offset=0`;
      if (qYear) {
        url += `&year=${qYear}`;
      }
      if (qSearch) {
        url += `&search=${encodeURIComponent(qSearch)}`;
      }
      const res = await API.get(url);
      setData({ total: res.data.total, data: res.data.data });
      if (res.data.years) {
        setYears(res.data.years);
      }

      // Tính frequency từ dữ liệu đã load
      const freq = {};
      res.data.data.forEach(d => {
        d.numbers?.forEach(n => { freq[n] = (freq[n] || 0) + 1; });
      });
      setFreqMap(freq);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  // Tự động tải lại khi đổi sản phẩm hoặc đổi năm
  useEffect(() => {
    setPage(0);
    load();
  }, [product, selectedYear]);

  // Xử lý tìm kiếm bằng tay
  const handleSearch = () => {
    setPage(0);
    load();
  };

  // Reset bộ lọc
  const handleReset = () => {
    setSelectedYear('');
    setSearchQuery('');
    setPage(0);
    // Gọi tải lại trực tiếp với tham số rỗng để tránh race condition do set state không đồng bộ
    load('', '');
  };

  const maxCount = Math.max(...Object.values(freqMap), 1);
  const totalAppearances = Object.values(freqMap).reduce((a, b) => a + b, 0);
  const numSpace = product === 'MEGA_645' ? 45 : product === 'POWER_655' ? 55 : 6;
  const allNumbers = Array.from({ length: numSpace }, (_, i) => i + 1);

  // Paginated draws
  const pagedDraws = data.data.slice(page * PER_PAGE, (page + 1) * PER_PAGE);

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">🎱 Kết quả quay số</h1>
          <div className="page-subtitle">Lịch sử kỳ quay và phân tích tần suất</div>
        </div>
        <div className="product-tabs">
          <button className={`product-tab ${product === 'MEGA_645' ? 'active' : ''}`} onClick={() => setProduct('MEGA_645')}>Mega 6/45</button>
          <button className={`product-tab ${product === 'POWER_655' ? 'active' : ''}`} onClick={() => setProduct('POWER_655')}>Power 6/55</button>
          <button className={`product-tab ${product === 'BINGO18' ? 'active' : ''}`} onClick={() => setProduct('BINGO18')}>Bingo18</button>
        </div>
      </div>

      {/* Bộ lọc kết quả */}
      <div className="card animate-in" style={{ marginBottom: 16 }}>
        <div className="card-body" style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center', padding: '12px 24px' }}>
          {/* Lọc theo năm */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Năm:</span>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="select-input"
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                color: 'var(--text)',
                padding: '6px 12px',
                fontSize: 13,
                outline: 'none',
                minWidth: 100
              }}
            >
              <option value="">Tất cả</option>
              {years.map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          {/* Tìm kiếm theo kỳ hoặc ngày */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 200 }}>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Tìm kiếm:</span>
            <input
              type="text"
              placeholder="Nhập kỳ quay hoặc ngày (YYYY-MM-DD)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
              style={{
                flex: 1,
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                color: 'var(--text)',
                padding: '6px 12px',
                fontSize: 13,
                outline: 'none'
              }}
            />
            <button className="btn btn-primary btn-sm" onClick={handleSearch}>Tìm</button>
            {(selectedYear || searchQuery) && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleReset}
              >
                Xóa lọc
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="page-body">
        {loading ? (
          <div className="loader-wrap"><div className="spin">⏳</div> Đang tải...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 16, alignItems: 'start' }}>
            {/* Draw history */}
            <div className="card animate-in">
              <div className="card-body flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 16, marginBottom: 0 }}>
                <span className="text-secondary text-sm">Tổng <strong>{data.total}</strong> kỳ quay</span>
                <button className="btn btn-secondary btn-sm" onClick={load}>🔄</button>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Kỳ</th>
                      <th>Ngày</th>
                      <th>{product === 'BINGO18' ? '3 Số chính' : '6 Số chính'}</th>
                      {product === 'POWER_655' && <th>Bonus</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {pagedDraws.length === 0 ? (
                      <tr><td colSpan={4}>
                        <div className="empty-state">
                          <div className="empty-state-icon">🎱</div>
                          <h3>Chưa có dữ liệu</h3>
                          <p>Vào Điều khiển → Seed Data để tạo dữ liệu mẫu.</p>
                        </div>
                      </td></tr>
                    ) : pagedDraws.map(d => (
                      <tr key={d.draw_id} className="animate-in">
                        <td><span className="font-mono font-bold">#{d.draw_no}</span></td>
                        <td><span className="text-sm text-secondary">{d.draw_date}</span></td>
                        <td>
                          <div className="number-balls">
                            {(product === 'BINGO18' ? (d.numbers || []).filter(n => n > 0) : (d.numbers || [])).map((n, idx) => (
                              <div key={`${idx}-${n}`} className="ball primary sm">{String(n).padStart(2, '0')}</div>
                            ))}
                          </div>
                        </td>
                        {product === 'POWER_655' && (
                          <td>
                            {d.bonus_number ? <div className="ball bonus sm">{String(d.bonus_number).padStart(2, '0')}</div> : '—'}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between" style={{ padding: '16px 24px', borderTop: '1px solid var(--border)' }}>
                <button className="btn btn-secondary btn-sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Trước</button>
                <span className="text-sm text-muted">Trang {page + 1} / {Math.ceil(data.data.length / PER_PAGE) || 1}</span>
                <button className="btn btn-secondary btn-sm" disabled={(page + 1) * PER_PAGE >= data.data.length} onClick={() => setPage(p => p + 1)}>Tiếp →</button>
              </div>
            </div>

            {/* Frequency panel */}
            <div className="card animate-in" style={{ position: 'sticky', top: 24 }}>
              <div className="card-body">
                <div className="chart-title mb-4">📊 Tần suất xuất hiện</div>
                <div style={{ maxHeight: 500, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {[...allNumbers]
                    .sort((a, b) => (freqMap[b] || 0) - (freqMap[a] || 0))
                    .map(n => (
                      <FrequencyBar
                        key={n}
                        number={n}
                        count={freqMap[n] || 0}
                        maxCount={maxCount}
                        total={totalAppearances}
                      />
                    ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
