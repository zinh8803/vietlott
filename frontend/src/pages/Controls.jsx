import { useState } from 'react';
import API from '../api';

function StepCard({ step, title, desc, action, btnLabel, loading, done, error, children }) {
  return (
    <div className={`card animate-in ${done ? 'card-done' : ''}`} style={{
      borderLeft: `3px solid ${done ? 'var(--accent-emerald)' : error ? 'var(--accent-rose)' : 'var(--border)'}`,
    }}>
      <div className="card-body">
        <div className="flex items-center gap-3 mb-3">
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: done ? 'var(--accent-emerald)' : error ? 'var(--accent-rose)' : 'var(--bg-surface)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 14, fontWeight: 800, color: done || error ? '#fff' : 'var(--text-muted)',
            border: '2px solid ' + (done ? 'var(--accent-emerald)' : error ? 'var(--accent-rose)' : 'var(--border)'),
          }}>
            {done ? '✓' : error ? '✕' : step}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>{title}</div>
            <div className="text-sm text-muted">{desc}</div>
          </div>
        </div>
        <button
          className={`btn btn-primary ${loading ? 'btn-loading' : ''}`}
          onClick={action}
          disabled={loading}
        >
          {loading ? <span className="spin">⏳</span> : null} {btnLabel}
        </button>
        {children}
        {error && <div className="alert alert-error mt-4">{error}</div>}
        {done && <div className="alert alert-success mt-4">{done}</div>}
      </div>
    </div>
  );
}

export default function Controls() {
  const [product, setProduct] = useState('MEGA_645');
  const [states, setStates] = useState({});
  const [log, setLog] = useState([]);
  const [useSampling, setUseSampling] = useState(false);

  const appendLog = (msg) => setLog(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev.slice(0, 49)]);

  const setStep = (key, patch) => setStates(prev => ({ ...prev, [key]: { ...(prev[key] || {}), ...patch } }));

  const run = async (key, label, fn) => {
    setStep(key, { loading: true, done: null, error: null });
    appendLog(`▶ ${label}...`);
    try {
      const result = await fn();
      const msg = JSON.stringify(result?.data || result, null, 2);
      setStep(key, { loading: false, done: `✅ Hoàn thành: ${msg.slice(0, 120)}` });
      appendLog(`✅ ${label} xong!`);
    } catch (e) {
      const err = e.response?.data?.detail || e.message || 'Lỗi không xác định';
      setStep(key, { loading: false, error: `❌ ${err}` });
      appendLog(`❌ ${label} lỗi: ${err}`);
    }
  };

  const steps = [
    {
      key: 'seed',
      step: 1,
      title: 'Seed dữ liệu mẫu',
      desc: 'Tạo 100 kỳ quay ngẫu nhiên vào DB (không cần mạng)',
      btnLabel: '🌱 Seed Data',
      action: () => run('seed', 'Seed data', () =>
        API.post('/internal/crawler/sync-draws', { product_code: product, use_seed: true })
      ),
    },
    {
      key: 'crawl',
      step: '1b',
      title: 'Crawl từ vietlott.vn',
      desc: 'Scrape kết quả thật từ website (cần kết nối mạng)',
      btnLabel: '🕷️ Crawl Now',
      action: () => run('crawl', 'Crawl', () =>
        API.post('/internal/crawler/sync-draws', { product_code: product, use_seed: false })
      ),
    },
    {
      key: 'features',
      step: 2,
      title: 'Build Features',
      desc: 'Tạo sliding-window feature vector cho tất cả kỳ quay',
      btnLabel: '⚙️ Build Features',
      action: () => run('features', 'Build features', () =>
        API.post('/internal/features/build', { product_code: product, window_size: 20, feature_version: 'v1' })
      ),
    },
    {
      key: 'train',
      step: 3,
      title: 'Train Models',
      desc: 'Train Baseline + LightGBM + XGBoost rồi chọn Champion (mất vài phút)',
      btnLabel: '🚀 Train All',
      action: () => run('train', 'Train models', () =>
        API.post('/internal/train', { product_code: product, window_size: 20, feature_version: 'v1', use_celery: false })
      ),
    },
    {
      key: 'trainProducts',
      step: '3b',
      title: 'Train Mega 6/45 + Power 6/55',
      desc: 'Build lại feature và train thêm model cho cả hai giải chính',
      btnLabel: 'Train 6/45 + 6/55',
      action: () => run('trainProducts', 'Train Mega + Power', () =>
        API.post('/internal/train/products', {
          product_codes: ['MEGA_645', 'POWER_655'],
          window_size: 20,
          feature_version: 'v1',
          force: true,
          use_celery: false,
        })
      ),
    },
    {
      key: 'learnResults',
      step: '3c',
      title: 'Tự học từ kết quả trúng',
      desc: 'Sync kết quả mới, đối chiếu số trúng rồi tự retrain 6/45 và 6/55 nếu cần',
      btnLabel: 'Learn From Results',
      action: () => run('learnResults', 'Learn from results', () =>
        API.post('/internal/train/learn-from-results', {
          product_codes: ['MEGA_645', 'POWER_655'],
          sync_latest: true,
          count: 1,
          window_size: 20,
          feature_version: 'v1',
          force_retrain: false,
          use_celery: false,
        })
      ),
    },
    {
      key: 'predict',
      step: 4,
      title: 'Sinh Dự đoán',
      desc: 'Dùng Champion model để dự đoán kỳ kế tiếp',
      btnLabel: '🎯 Predict Next',
      action: () => run('predict', 'Predict next', () =>
        API.post('/internal/predict/next', { product_code: product, request_type: 'manual', random_sample: useSampling })
      ),
    },
    {
      key: 'reconcile',
      step: 5,
      title: 'Đối chiếu kết quả',
      desc: 'So sánh dự đoán với kết quả thực tế, tính hit count',
      btnLabel: '✅ Reconcile',
      action: () => run('reconcile', 'Reconcile', () =>
        API.post('/internal/reconcile', { product_code: product })
      ),
    },
  ];

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">⚙️ Điều khiển</h1>
          <div className="page-subtitle">Chạy pipeline từng bước: seed → feature → train → predict → reconcile</div>
        </div>
        <div className="product-tabs">
          <button className={`product-tab ${product === 'MEGA_645' ? 'active' : ''}`} onClick={() => setProduct('MEGA_645')}>Mega 6/45</button>
          <button className={`product-tab ${product === 'POWER_655' ? 'active' : ''}`} onClick={() => setProduct('POWER_655')}>Power 6/55</button>
          <button className={`product-tab ${product === 'BINGO18' ? 'active' : ''}`} onClick={() => setProduct('BINGO18')}>Bingo18</button>
        </div>
      </div>

      <div className="page-body">
        <div className="alert alert-warning mb-6">
          ⚠️ <strong>Lưu ý:</strong> Hệ thống này là nền tảng học tập và backtest, <strong>không phải cam kết thắng</strong>.
          Kết quả quay số là ngẫu nhiên hoàn toàn. Xổ số chỉ dành cho người từ đủ 18 tuổi.
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 16, alignItems: 'start' }}>
          {/* Steps */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {steps.map(s => (
              <StepCard
                key={s.key}
                step={s.step}
                title={s.title}
                desc={s.desc}
                btnLabel={s.btnLabel}
                action={s.action}
                loading={states[s.key]?.loading}
                done={states[s.key]?.done}
                error={states[s.key]?.error}
              >
                {s.key === 'predict' && (
                  <div className="mt-2">
                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', color: 'var(--text-secondary)' }}>
                      <input
                        type="checkbox"
                        checked={useSampling}
                        onChange={(e) => setUseSampling(e.target.checked)}
                        style={{ cursor: 'pointer' }}
                      />
                      <span>🎲 Lấy mẫu ngẫu nhiên (Weighted Sampling)</span>
                    </label>
                  </div>
                )}
              </StepCard>
            ))}
          </div>

          {/* Log panel */}
          <div className="card animate-in" style={{ position: 'sticky', top: 24 }}>
            <div className="card-body">
              <div className="flex items-center justify-between mb-3">
                <div className="chart-title">📋 Activity Log</div>
                <button className="btn btn-secondary btn-sm" onClick={() => setLog([])}>Xóa</button>
              </div>
              <div style={{
                fontFamily: 'JetBrains Mono',
                fontSize: 11.5,
                height: 400,
                overflowY: 'auto',
                background: 'var(--bg-base)',
                borderRadius: 8,
                padding: 12,
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}>
                {log.length === 0 ? (
                  <div className="text-muted text-sm" style={{ fontFamily: 'Inter' }}>Chưa có hoạt động nào...</div>
                ) : log.map((l, i) => (
                  <div key={i} style={{
                    color: l.startsWith('[') && l.includes('✅') ? 'var(--accent-emerald)'
                         : l.includes('❌') ? 'var(--accent-rose)'
                         : l.includes('▶') ? 'var(--accent-blue)'
                         : 'var(--text-secondary)',
                    lineHeight: 1.4,
                    padding: '2px 0',
                    borderBottom: '1px solid rgba(255,255,255,0.03)',
                  }}>
                    {l}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
