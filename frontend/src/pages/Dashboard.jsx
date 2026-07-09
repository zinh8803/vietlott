import { useState, useEffect } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, CartesianGrid, Legend,
} from 'recharts';
import API from '../api';

function BallGroup({ numbers = [], type = 'primary', size = 'normal' }) {
  return (
    <div className="number-balls">
      {numbers.map((n, idx) => (
        <div key={`${idx}-${n}`} className={`ball ${type} ${size === 'sm' ? 'sm' : ''}`}>
          {String(n).padStart(2, '0')}
        </div>
      ))}
    </div>
  );
}

function StatCard({ icon, label, value, sub, color = 'blue' }) {
  return (
    <div className={`stat-card ${color} animate-in`}>
      <span className="stat-icon">{icon}</span>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value ?? '—'}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card" style={{ padding: '10px 14px', fontSize: 12 }}>
      <div style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</div>
      {payload.map(p => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name === 'precision' ? 'Precision' : p.name}: <strong>{typeof p.value === 'number' ? p.value.toFixed(1) + '%' : p.value}</strong>
        </div>
      ))}
    </div>
  );
};

export default function Dashboard() {
  const [product, setProduct] = useState('MEGA_645');
  const [summary, setSummary] = useState(null);
  const [trend, setTrend] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [sumRes, trendRes] = await Promise.all([
        API.get('/api/dashboard/summary'),
        API.get(`/api/metrics/live-trend?product_code=${product}&limit=30`),
      ]);
      setSummary(sumRes.data);
      setTrend(trendRes.data.map((m, i) => ({
        name: `Kỳ ${i + 1}`,
        precision: m.precision_at_6 != null ? +(m.precision_at_6 * 100).toFixed(1) : null,
        hit: m.metric_json?.hit_count ?? 0,
      })));
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, [product]);

  const data = summary?.[product];
  const champion = data?.champion;
  const latestPred = data?.latest_prediction;

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">🏠 Dashboard</h1>
          <div className="page-subtitle">Tổng quan hệ thống dự đoán xổ số Vietlott</div>
        </div>
        <div className="product-tabs">
          <button className={`product-tab ${product === 'MEGA_645' ? 'active' : ''}`}
            onClick={() => setProduct('MEGA_645')}>Mega 6/45</button>
          <button className={`product-tab ${product === 'POWER_655' ? 'active' : ''}`}
            onClick={() => setProduct('POWER_655')}>Power 6/55</button>
          <button className={`product-tab ${product === 'BINGO18' ? 'active' : ''}`}
            onClick={() => setProduct('BINGO18')}>Bingo18</button>
        </div>
      </div>

      <div className="page-body">
        {loading && !summary ? (
          <div className="loader-wrap"><div className="spin">⏳</div> Đang tải...</div>
        ) : (
          <>
            {/* Stats */}
            <div className="stat-grid mb-6">
              <StatCard icon="🎱" label="Tổng số kỳ quay" value={data?.total_draws?.toLocaleString() ?? '0'}
                sub={product === 'MEGA_645' ? 'Mega 6/45 (1–45)' : product === 'POWER_655' ? 'Power 6/55 (1–55)' : 'Bingo18 (1–6)'} color="blue" />
              <StatCard icon="🤖" label="Champion Model" value={champion?.algorithm?.toUpperCase() ?? 'Chưa có'}
                sub={champion ? `ID #${champion.model_id}` : 'Cần train model'} color="purple" />
              <StatCard icon="📊" label={product === 'BINGO18' ? 'Precision@3 Live' : 'Precision@6 Live'}
                value={data?.live_precision_avg != null ? `${(data.live_precision_avg * 100).toFixed(1)}%` : '—'}
                sub="Trung bình kỳ gần nhất" color="green" />
              <StatCard icon="🎯" label="Dự đoán gần nhất"
                value={latestPred ? `Kỳ ${latestPred.predicted_draw_no}` : '—'}
                sub={latestPred ? `${latestPred.hit_count ?? '?'}/${product === 'BINGO18' ? '3' : '6'} hit` : 'Chưa có dự đoán'} color="gold" />
            </div>

            {/* Latest prediction highlight */}
            {latestPred && (
              <div className="card mb-6 animate-in" style={{ animationDelay: '0.1s' }}>
                <div className="card-body">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="chart-title">🎯 Dự đoán mới nhất – Kỳ {latestPred.predicted_draw_no}</div>
                      <div className="chart-subtitle">
                        Trạng thái: <span className={`badge ${latestPred.status}`}>{latestPred.status}</span>
                        &nbsp;·&nbsp;{latestPred.generated_at.slice(0, 16).replace('T', ' ')}
                      </div>
                    </div>
                    {latestPred.hit_count != null && (
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 40, fontWeight: 800, color: latestPred.hit_count >= (product === 'BINGO18' ? 2 : 3) ? 'var(--accent-emerald)' : 'var(--text-primary)' }}>
                          {latestPred.hit_count}/{product === 'BINGO18' ? '3' : '6'}
                        </div>
                        <div className="text-sm text-muted">Số trúng</div>
                      </div>
                    )}
                  </div>
                  <div className="grid-2 gap-4">
                    <div>
                      <div className="text-sm text-muted mb-2">{product === 'BINGO18' ? 'Số dự đoán (Top 3)' : 'Số dự đoán'}</div>
                      <BallGroup numbers={latestPred.top6} type="predicted" />
                    </div>
                    {latestPred.actual_top6 && (
                      <div>
                        <div className="text-sm text-muted mb-2">Kết quả thực tế</div>
                        <BallGroup numbers={product === 'BINGO18' ? latestPred.actual_top6.filter(n => n > 0) : latestPred.actual_top6} type="primary" />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Charts */}
            <div className="grid-2 gap-4">
              <div className="card animate-in" style={{ animationDelay: '0.15s' }}>
                <div className="chart-container">
                  <div className="chart-title">📈 Xu hướng {product === 'BINGO18' ? 'Precision@3' : 'Precision@6'} Live (%)</div>
                  <ResponsiveContainer width="100%" height={200}>
                    <AreaChart data={trend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorP6" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                      <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} domain={[0, 100]} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area type="monotone" dataKey="precision" stroke="#3b82f6"
                        fill="url(#colorP6)" strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="card animate-in" style={{ animationDelay: '0.2s' }}>
                <div className="chart-container">
                  <div className="chart-title">🎯 Phân phối Hit Count</div>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={trend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                      <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="hit" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Champion info */}
            {champion && (
              <div className="card mt-4 animate-in" style={{ animationDelay: '0.25s' }}>
                <div className="card-body">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="badge champion">👑 Champion</div>
                    <span className="font-bold">{champion.model_name}</span>
                  </div>
                  <div className="stat-grid">
                    {[
                      { label: product === 'BINGO18' ? 'Precision@3' : 'Precision@6', val: champion.metrics?.precision_at_6, fmt: v => `${(v*100).toFixed(2)}%` },
                      { label: 'Log Loss',    val: champion.metrics?.log_loss,       fmt: v => v.toFixed(4) },
                      { label: 'Brier Score', val: champion.metrics?.brier_score,    fmt: v => v.toFixed(4) },
                    ].map(m => (
                      <div key={m.label} className="stat-card blue">
                        <div className="stat-label">{m.label}</div>
                        <div className="stat-value" style={{ fontSize: 20 }}>
                          {m.val != null ? m.fmt(m.val) : '—'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
