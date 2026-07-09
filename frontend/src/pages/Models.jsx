import { useState, useEffect } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from 'recharts';
import API from '../api';

const ALGO_COLORS = {
  dummy: '#475569',
  logreg: '#3b82f6',
  random_forest: '#8b5cf6',
  lightgbm: '#10b981',
  xgboost: '#f59e0b',
};

const StatusBadge = ({ status }) => (
  <span className={`badge ${status}`}>
    {status === 'champion' ? '👑' : status === 'challenger' ? '⚔️' : '📦'} {status}
  </span>
);

export default function Models() {
  const [product, setProduct] = useState('MEGA_645');
  const [models, setModels] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [modRes, lbRes] = await Promise.all([
        API.get(`/internal/models?product_code=${product}`),
        API.get(`/api/metrics/leaderboard?product_code=${product}`),
      ]);
      setModels(modRes.data);
      setLeaderboard(lbRes.data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const loadDetail = async (modelId) => {
    try {
      const res = await API.get(`/internal/reports/backtests/${modelId}`);
      setDetail(res.data);
    } catch (e) { setDetail(null); }
  };

  useEffect(() => { load(); setSelected(null); setDetail(null); }, [product]);

  const handleSelect = (m) => {
    setSelected(m);
    loadDetail(m.model_id);
  };

  const metricLabel = product === 'BINGO18' ? 'P@3 (%)' : 'P@6 (%)';
  const precisionTitle = product === 'BINGO18' ? 'Precision@3' : 'Precision@6';

  // Chart data
  const chartData = leaderboard.slice(0, 5).map(m => ({
    name: m.algorithm,
    [metricLabel]: m.precision_at_6 != null ? +(m.precision_at_6 * 100).toFixed(2) : 0,
    'Log Loss': m.log_loss != null ? +m.log_loss.toFixed(3) : 0,
  }));

  const radarData = selected ? [
    { metric: precisionTitle, value: (selected.precision_at_6 ?? 0) * 100 },
    { metric: 'Low LoglLoss', value: selected.log_loss != null ? Math.max(0, (1 - selected.log_loss) * 100) : 0 },
    { metric: 'Low Brier',    value: selected.brier_score != null ? Math.max(0, (1 - selected.brier_score) * 100) : 0 },
  ] : [];

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">🤖 Models</h1>
          <div className="page-subtitle">Leaderboard và chi tiết model theo sản phẩm</div>
        </div>
        <div className="product-tabs">
          <button className={`product-tab ${product === 'MEGA_645' ? 'active' : ''}`} onClick={() => setProduct('MEGA_645')}>Mega 6/45</button>
          <button className={`product-tab ${product === 'POWER_655' ? 'active' : ''}`} onClick={() => setProduct('POWER_655')}>Power 6/55</button>
          <button className={`product-tab ${product === 'BINGO18' ? 'active' : ''}`} onClick={() => setProduct('BINGO18')}>Bingo18</button>
        </div>
      </div>

      <div className="page-body">
        {loading ? (
          <div className="loader-wrap"><div className="spin">⏳</div> Đang tải...</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>
            {/* Main panel */}
            <div>
              {/* Chart */}
              {chartData.length > 0 && (
                <div className="card mb-4 animate-in">
                  <div className="chart-container">
                    <div className="chart-title">📊 Precision So sánh (Top 5 models)</div>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                        <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                        <Tooltip
                          contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }}
                          labelStyle={{ color: 'var(--text-secondary)' }}
                        />
                        <Bar dataKey={metricLabel} radius={[4, 4, 0, 0]}
                          fill="#3b82f6"
                          cells={chartData.map((d, i) => (
                            <rect key={i} fill={ALGO_COLORS[d.name] || '#3b82f6'} />
                          ))}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Table */}
              <div className="card animate-in">
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Tên model</th>
                        <th>Algorithm</th>
                        <th>{precisionTitle}</th>
                        <th>Log Loss</th>
                        <th>Brier</th>
                        <th>Trạng thái</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {leaderboard.length === 0 ? (
                        <tr><td colSpan={8}>
                          <div className="empty-state"><div className="empty-state-icon">🤖</div>
                            <h3>Chưa có model</h3><p>Vào Điều khiển → Train để tạo model.</p></div>
                        </td></tr>
                      ) : leaderboard.map((m, i) => (
                        <tr key={m.model_id}
                          className={`animate-in ${selected?.model_id === m.model_id ? '' : ''}`}
                          style={{ cursor: 'pointer', background: selected?.model_id === m.model_id ? 'rgba(59,130,246,0.08)' : '' }}
                          onClick={() => handleSelect(m)}>
                          <td>
                            <span style={{ fontWeight: 700, color: i === 0 ? 'var(--accent-amber)' : 'var(--text-muted)', fontSize: 16 }}>
                              {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i+1}`}
                            </span>
                          </td>
                          <td>
                            <span className="font-mono text-sm">{m.model_name}</span>
                          </td>
                          <td>
                            <span style={{ color: ALGO_COLORS[m.algorithm] || 'var(--text-primary)', fontWeight: 600 }}>
                              {m.algorithm}
                            </span>
                          </td>
                          <td>
                            <div className="prob-bar-wrap">
                              <div className="prob-bar" style={{ width: 60 }}>
                                <div className="prob-fill" style={{ width: `${((m.precision_at_6 ?? 0) / 0.5 * 100).toFixed(1)}%` }} />
                              </div>
                              <span className="font-mono text-sm">{m.precision_at_6 != null ? `${(m.precision_at_6 * 100).toFixed(1)}%` : '—'}</span>
                            </div>
                          </td>
                          <td><span className="font-mono text-sm">{m.log_loss?.toFixed(4) ?? '—'}</span></td>
                          <td><span className="font-mono text-sm">{m.brier_score?.toFixed(4) ?? '—'}</span></td>
                          <td><StatusBadge status={m.status} /></td>
                          <td>
                            <button className="btn btn-secondary btn-sm" onClick={e => { e.stopPropagation(); handleSelect(m); }}>
                              Chi tiết
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Detail panel */}
            <div>
              {selected ? (
                <div className="card animate-in" style={{ position: 'sticky', top: 24 }}>
                  <div className="card-body">
                    <div className="flex items-center gap-2 mb-4">
                      <StatusBadge status={selected.status} />
                      <span className="text-sm text-muted">#{selected.model_id}</span>
                    </div>
                    <div className="font-bold" style={{ fontSize: 13, wordBreak: 'break-all', marginBottom: 12 }}>
                      {selected.model_name}
                    </div>

                    {radarData.length > 0 && (
                      <ResponsiveContainer width="100%" height={160}>
                        <RadarChart data={radarData}>
                          <PolarGrid stroke="var(--border)" />
                          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                          <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
                        </RadarChart>
                      </ResponsiveContainer>
                    )}

                    {detail?.metrics?.map(m => (
                      <div key={m.metric_id} className="mt-4" style={{ background: 'var(--bg-surface)', borderRadius: 8, padding: '10px 14px' }}>
                        <div className="text-sm text-muted mb-2">{m.eval_scope}{m.fold_no != null ? ` / fold ${m.fold_no}` : ''}</div>
                        <div className="stat-grid" style={{ gap: 8 }}>
                          {[
                            [product === 'BINGO18' ? 'P@3' : 'P@6', m.precision_at_6 != null ? `${(m.precision_at_6*100).toFixed(1)}%` : '—'],
                            ['LogLoss', m.log_loss?.toFixed(4) ?? '—'],
                            ['Brier', m.brier_score?.toFixed(4) ?? '—'],
                          ].map(([k, v]) => (
                            <div key={k}>
                              <div className="stat-label">{k}</div>
                              <div className="font-mono font-bold" style={{ fontSize: 14 }}>{v}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="card" style={{ padding: 32, textAlign: 'center' }}>
                  <div style={{ fontSize: 36, marginBottom: 12 }}>👈</div>
                  <div className="text-secondary text-sm">Chọn một model để xem chi tiết</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
