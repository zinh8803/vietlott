import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '../api';

const SESSION_KEY = 'vietlot_current_user';

export default function AuthPage({ onLogin }) {
  const navigate = useNavigate();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ username: '', password: '', display_name: '' });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const update = (key, value) => setForm(prev => ({ ...prev, [key]: value }));

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const payload = mode === 'login'
        ? { username: form.username, password: form.password }
        : form;
      const res = await API.post(endpoint, payload);
      localStorage.setItem(SESSION_KEY, JSON.stringify(res.data.user));
      if (onLogin) onLogin(res.data.user);
      setMessage({ type: 'success', text: mode === 'login' ? 'Dang nhap thanh cong' : 'Dang ky thanh cong' });
      navigate(res.data.user.role === 'admin' ? '/dashboard' : '/');
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.detail || e.message || 'Khong thanh cong' });
    }
    setLoading(false);
  };

  return (
    <>
      <div className="page-header" style={{ justifyContent: 'center', textAlign: 'center', flexDirection: 'column', padding: '40px 20px 20px' }}>
        <h1 className="page-title">{mode === 'login' ? 'Đăng nhập' : 'Đăng ký tài khoản'}</h1>
        <div className="page-subtitle" style={{ marginTop: 8 }}>Đăng nhập để tạo vé, xem lịch sử và theo dõi giới hạn trong ngày.</div>
      </div>

      <div className="page-body" style={{ display: 'flex', justifyContent: 'center', padding: '0 20px 40px' }}>
        <div className="card auth-card glass-panel animate-in" style={{ width: '100%', maxWidth: 420 }}>
          <div className="card-body">
            <div className="product-tabs mb-6" style={{ justifyContent: 'center' }}>
              <button className={`product-tab ${mode === 'login' ? 'active' : ''}`} onClick={() => setMode('login')}>Đăng nhập</button>
              <button className={`product-tab ${mode === 'register' ? 'active' : ''}`} onClick={() => setMode('register')}>Đăng ký</button>
            </div>

            {message && (
              <div className={`alert ${message.type === 'success' ? 'alert-success' : 'alert-error'} mb-6`} style={{ borderRadius: 12 }}>
                {message.text}
              </div>
            )}

            <form onSubmit={submit} className="form-stack">
              {mode === 'register' && (
                <label className="field-label">
                  Tên hiển thị
                  <input className="form-input" value={form.display_name} onChange={e => update('display_name', e.target.value)} placeholder="Nguyễn Văn A" style={{ borderRadius: 8 }} />
                </label>
              )}
              <label className="field-label">
                Tên đăng nhập
                <input className="form-input" value={form.username} onChange={e => update('username', e.target.value)} placeholder="Nhập username" style={{ borderRadius: 8 }} />
              </label>
              <label className="field-label">
                Mật khẩu
                <input className="form-input" type="password" value={form.password} onChange={e => update('password', e.target.value)} placeholder="Tối thiểu 6 ký tự" style={{ borderRadius: 8 }} />
              </label>
              <button className="btn btn-primary w-full glow-btn-primary" disabled={loading} style={{ height: 42, borderRadius: 8, marginTop: 8 }}>
                {loading ? 'Đang xử lý...' : mode === 'login' ? 'Đăng nhập' : 'Tạo tài khoản'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

export { SESSION_KEY };
