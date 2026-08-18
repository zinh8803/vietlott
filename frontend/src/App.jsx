import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Predictions from './pages/Predictions';
import Models from './pages/Models';
import Draws from './pages/Draws';
import Controls from './pages/Controls';
import UserPortal from './pages/UserPortal';
import AdminPortal from './pages/AdminPortal';
import AuthPage from './pages/AuthPage';
import API from './api';

const SESSION_KEY = 'vietlot_current_user';

function getSessionUser() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function SEOTracker() {
  const location = useLocation();

  useEffect(() => {
    const seoMap = {
      '/': {
        title: 'VietlotAI – In Vé Số Dự Đoán AI Thông Minh',
        description: 'Tạo vé số dự đoán thông minh Vietlott (Mega 6/45, Power 6/55, Bingo18) bằng thuật toán Weighted Random Sampling & AI Machine Learning.'
      },
      '/dashboard': {
        title: 'Dashboard – VietlotAI ML Prediction System',
        description: 'Tổng quan hệ thống dự đoán xổ số Vietlott, thống kê độ chính xác Precision@6 và mô hình Champion.'
      },
      '/predictions': {
        title: 'Lịch Sử Dự Đoán AI – VietlotAI',
        description: 'Xem lại toàn bộ danh sách các bộ số dự đoán AI cho các kỳ quay Vietlott Mega, Power và Bingo18.'
      },
      '/draws': {
        title: 'Lịch Sử Kết Quả Xổ Số – VietlotAI',
        description: 'Tra cứu kết quả các kỳ quay số Vietlott chính thức Mega 6/45, Power 6/55 và Bingo18 mới nhất.'
      },
      '/login': {
        title: 'Đăng Nhập / Đăng Ký – VietlotAI',
        description: 'Đăng nhập hoặc đăng ký tài khoản VietlotAI để nhận hạn ngạch in vé dự đoán hàng ngày.'
      },
      '/admin': {
        title: 'Quản Lý Admin – VietlotAI',
        description: 'Trang quản trị hệ thống, cấp hạn ngạch in vé cho người dùng và theo dõi hoạt động.'
      },
      '/models': {
        title: 'Quản Lý Mô Hình ML – VietlotAI',
        description: 'Bảng xếp hạng Leaderboard các mô hình Machine Learning: Baseline, LightGBM, XGBoost.'
      },
      '/controls': {
        title: 'Bảng Điều Khiển Pipeline – VietlotAI',
        description: 'Kích hoạt crawler đồng bộ kết quả, build sliding-window features, huấn luyện mô hình và đối chiếu.'
      }
    };

    const currentSeo = seoMap[location.pathname] || {
      title: 'VietlotAI – Hệ Thống AI Dự Đoán Xổ Số Vietlott Thông Minh',
      description: 'Hệ thống phân tích Machine Learning & AI dự đoán kết quả xổ số Vietlott (Mega 6/45, Power 6/55, Bingo18).'
    };

    document.title = currentSeo.title;

    const metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) {
      metaDesc.setAttribute('content', currentSeo.description);
    }
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) {
      ogTitle.setAttribute('content', currentSeo.title);
    }
    const ogDesc = document.querySelector('meta[property="og:description"]');
    if (ogDesc) {
      ogDesc.setAttribute('content', currentSeo.description);
    }
  }, [location.pathname]);

  return null;
}

function ProtectedRoute({ children, currentUser, requireAdmin }) {
  if (!currentUser) {
    return <Navigate to="/login" replace />;
  }
  if (requireAdmin && currentUser.role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  return children;
}

function Sidebar({ apiOnline, currentUser, onLogout }) {
  const navItems = [
    { to: '/dashboard',   icon: '⚡', label: 'Dashboard' },
    { to: '/predictions', icon: '🎯', label: 'Dự đoán' },
    { to: '/draws',       icon: '🎱', label: 'Kết quả' },
    { to: '/models',      icon: '🤖', label: 'Models' },
    { to: '/controls',    icon: '⚙️', label: 'Điều khiển' },
    { to: '/admin',       icon: '👑', label: 'Admin Portal' },
    { to: '/',            icon: '🎫', label: 'In Vé AI' }
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-badge">
          <div className="logo-icon">🎰</div>
          <div>
            <div className="logo-text">VietlotAI</div>
            <div className="logo-sub">ML Prediction System</div>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/dashboard'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        {currentUser ? (
          <div className="user-profile-summary animate-in">
            <div className="user-profile-info">
              <div className="user-profile-name" title={currentUser.display_name}>
                {currentUser.display_name}
              </div>
              <div className="user-profile-role">
                {currentUser.role === 'admin' 
                  ? 'Admin System' 
                  : `Hạn vé: ${currentUser.remaining_today ?? 0}/${currentUser.daily_ticket_limit}`}
              </div>
            </div>
            <button className="btn-logout-icon" onClick={onLogout} title="Đăng xuất">
              🚪
            </button>
          </div>
        ) : null}
        <div className="api-status" style={{ marginTop: currentUser ? 8 : 0 }}>
          <div className={`status-dot ${apiOnline ? '' : 'offline'}`} />
          <span>{apiOnline ? 'API Connected' : 'API Offline'}</span>
        </div>
      </div>
    </aside>
  );
}

function App() {
  const [apiOnline, setApiOnline] = useState(false);
  const [currentUser, setCurrentUser] = useState(() => getSessionUser());

  useEffect(() => {
    API.get('/health')
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
    const interval = setInterval(() => {
      API.get('/health')
        .then(() => setApiOnline(true))
        .catch(() => setApiOnline(false));
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleLogin = (user) => {
    setCurrentUser(user);
  };

  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY);
    setCurrentUser(null);
  };

  const showSidebar = currentUser && currentUser.role === 'admin';

  return (
    <BrowserRouter>
      <SEOTracker />
      <div className={showSidebar ? "app-wrapper" : "user-portal-layout"}>
        {showSidebar && <Sidebar apiOnline={apiOnline} currentUser={currentUser} onLogout={handleLogout} />}
        <main className={showSidebar ? "main-content" : "main-content user-portal-main"}>
          <Routes>
            <Route path="/"             element={
              <UserPortal currentUser={currentUser} setCurrentUser={setCurrentUser} onLogout={handleLogout} apiOnline={apiOnline} />
            } />
            <Route path="/dashboard"    element={
              <ProtectedRoute currentUser={currentUser} requireAdmin={true}>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/predictions"  element={
              <ProtectedRoute currentUser={currentUser} requireAdmin={true}>
                <Predictions />
              </ProtectedRoute>
            } />
            <Route path="/draws"        element={
              <ProtectedRoute currentUser={currentUser} requireAdmin={true}>
                <Draws />
              </ProtectedRoute>
            } />
            <Route path="/login"        element={
              currentUser ? <Navigate to={currentUser.role === 'admin' ? "/dashboard" : "/"} replace /> : <AuthPage onLogin={handleLogin} />
            } />
            
            {/* Redirect /user to / */}
            <Route path="/user" element={<Navigate to="/" replace />} />

            {/* Admin Protected Routes */}
            <Route path="/admin" element={
              <ProtectedRoute currentUser={currentUser} requireAdmin={true}>
                <AdminPortal currentUser={currentUser} setCurrentUser={setCurrentUser} />
              </ProtectedRoute>
            } />
            <Route path="/models" element={
              <ProtectedRoute currentUser={currentUser} requireAdmin={true}>
                <Models />
              </ProtectedRoute>
            } />
            <Route path="/controls" element={
              <ProtectedRoute currentUser={currentUser} requireAdmin={true}>
                <Controls />
              </ProtectedRoute>
            } />

            {/* Fallback */}
            <Route path="*" element={<Navigate to={showSidebar ? "/dashboard" : "/"} replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;

