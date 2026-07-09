import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Ticket, History, LogOut, RefreshCw, Cpu, Sparkles, 
  Search, SlidersHorizontal, CheckCircle, AlertTriangle, 
  User, Compass, ShieldAlert
} from 'lucide-react';
import API from '../api';

const PRODUCTS = [
  { 
    code: 'MEGA_645', 
    label: 'Mega 6/45', 
    hint: 'Chọn 6 số từ 01 tới 45. Xác suất trúng giải đặc biệt cao.',
    desc: 'Cơ chế 6/45 tối ưu hóa tỷ lệ trúng thưởng.',
    accent: 'mega',
    emoji: '🔵'
  },
  { 
    code: 'POWER_655', 
    label: 'Power 6/55', 
    hint: 'Chọn 6 số từ 01 tới 55. Trúng jackpot với giải thưởng khủng.',
    desc: 'Giải Jackpot tích lũy không giới hạn.',
    accent: 'power',
    emoji: '🔴'
  },
  { 
    code: 'BINGO18', 
    label: 'Bingo18', 
    hint: 'Chọn 3 số từ 1 tới 6. Game quay thưởng nhanh 10 phút/lần.',
    desc: 'Game xổ số nhanh thế hệ mới.',
    accent: 'bingo',
    emoji: '🟣'
  },
];

function Balls({ numbers = [], productCode }) {
  // Filter out placeholder 0s for Bingo18
  const cleanNumbers = numbers.filter(n => n > 0);
  
  // Decide ball color class based on product
  const ballClass = productCode === 'MEGA_645' ? 'mega' : productCode === 'POWER_655' ? 'power' : 'bingo';

  return (
    <div className="number-balls" style={{ justifyContent: 'center', margin: '14px 0', gap: '10px' }}>
      {cleanNumbers.map((n, idx) => (
        <div key={`${idx}-${n}`} className={`ball predicted ${ballClass}`}>
          {String(n).padStart(2, '0')}
        </div>
      ))}
    </div>
  );
}

function TicketStub({ ticket, isNew }) {
  const formattedTime = useMemo(() => {
    try {
      return ticket.created_at.slice(0, 16).replace('T', ' ');
    } catch {
      return ticket.created_at;
    }
  }, [ticket.created_at]);

  const productInfo = useMemo(() => {
    return PRODUCTS.find(p => p.code === ticket.product_code) || { label: ticket.product_code, accent: 'mega' };
  }, [ticket.product_code]);

  const barcodeText = useMemo(() => {
    const ticketIdStr = String(ticket.ticket_id).padStart(6, '0');
    const predIdStr = String(ticket.prediction_id || 0).padStart(4, '0');
    return `987-${predIdStr}-${ticketIdStr}`;
  }, [ticket.ticket_id, ticket.prediction_id]);

  return (
    <div className={`ticket-stub-modern ${isNew ? 'ticket-print-new' : 'animate-in'}`}>
      <div className="ticket-shine-effect" />
      <div className="ticket-brand-header">
        <div>
          <span className="ticket-title-brand">Vietlot AI</span>
          <div className="text-secondary" style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.5px', textTransform: 'uppercase', marginTop: 2 }}>Ticket Voucher</div>
        </div>
        <span className="badge reconciled" style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
          <CheckCircle size={10} style={{ marginRight: 4 }} /> Hợp lệ
        </span>
      </div>

      <div className="ticket-divider" style={{ borderTopStyle: 'dashed', borderColor: 'rgba(255,255,255,0.1)' }}></div>

      <div className="ticket-meta">
        <div>
          <div className="ticket-meta-label">Sản phẩm</div>
          <div className="font-bold" style={{ color: 'var(--text-primary)', fontSize: 13.5 }}>{productInfo.label}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="ticket-meta-label">Kỳ quay số</div>
          <div className="font-bold font-mono" style={{ color: 'var(--accent-amber)', fontSize: 13.5 }}>#{ticket.predicted_draw_no}</div>
        </div>
        <div style={{ marginTop: 6 }}>
          <div className="ticket-meta-label">Mã vé</div>
          <div className="font-mono text-sm">#{ticket.ticket_id}</div>
        </div>
        <div style={{ marginTop: 6, textAlign: 'right' }}>
          <div className="ticket-meta-label">Thời gian</div>
          <div className="text-sm font-mono">{formattedTime}</div>
        </div>
      </div>

      <div className="ticket-divider" style={{ borderTopStyle: 'dashed', borderColor: 'rgba(255,255,255,0.1)' }}></div>

      <div style={{ textAlign: 'center' }}>
        <div className="ticket-meta-label" style={{ marginBottom: 4 }}>Bộ số dự đoán AI</div>
        <Balls numbers={ticket.numbers} productCode={ticket.product_code} />
      </div>

      <div className="ticket-barcode" style={{ marginTop: 12 }}>
        <div className="barcode-lines" style={{ background: 'repeating-linear-gradient(90deg, rgba(255,255,255,0.6), rgba(255,255,255,0.6) 1px, transparent 1px, transparent 4px, rgba(255,255,255,0.6) 4px, rgba(255,255,255,0.6) 5px, transparent 5px, transparent 7px)' }}></div>
        <div className="barcode-number" style={{ color: 'rgba(255,255,255,0.4)', fontSize: '8.5px' }}>{barcodeText}</div>
      </div>
    </div>
  );
}

export default function UserPortal({ currentUser, setCurrentUser, onLogout, apiOnline }) {
  const navigate = useNavigate();
  const [product, setProduct] = useState('MEGA_645');
  const [useSampling, setUseSampling] = useState(true);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState(null);
  
  // States for search and filter
  const [searchQuery, setSearchQuery] = useState('');
  const [historyFilter, setHistoryFilter] = useState('ALL');
  
  // State to track the newly printed ticket ID for printing animation
  const [newlyPrintedId, setNewlyPrintedId] = useState(null);

  const selectedProduct = useMemo(() => PRODUCTS.find(p => p.code === product), [product]);
  const isLocked = currentUser?.is_locked && currentUser?.role !== 'admin';

  const loadTickets = async () => {
    if (!currentUser?.user_id) return;
    try {
      const res = await API.get(`/api/users/${currentUser.user_id}/tickets?limit=40`);
      setTickets(res.data.data);
      if (setCurrentUser) {
        setCurrentUser(res.data.user);
        localStorage.setItem('vietlot_current_user', JSON.stringify(res.data.user));
      }
    } catch (e) {
      console.error(e);
      setMessage({ type: 'error', text: 'Không thể tải danh sách vé.' });
    }
  };

  const load = async () => {
    if (!currentUser) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setMessage(null);
    await loadTickets();
    setLoading(false);
  };

  useEffect(() => {
    // Kích hoạt cào kết quả mới chạy ngầm nếu dữ liệu chưa cập nhật
    API.post('/api/crawler/check-and-sync-background')
      .then(res => {
        const results = res.data?.check_results;
        const queuedProducts = Object.keys(results || {}).filter(k => results[k].status === 'queued');
        if (queuedProducts.length > 0) {
          console.log("Kích hoạt cào dữ liệu mới chạy ngầm cho:", queuedProducts);
          // Đợi cào ngầm chạy một lát rồi tự động reload để cập nhật nếu có dữ liệu mới
          setTimeout(() => {
            loadTickets();
          }, 5000);
        }
      })
      .catch(err => {
        console.error("Lỗi khi kiểm tra dữ liệu cào ngầm:", err);
      });

    load();
  }, [currentUser?.user_id]);

  const createTicket = async () => {
    if (!currentUser) {
      navigate('/login');
      return;
    }
    
    setCreating(true);
    setMessage(null);
    try {
      const res = await API.post('/api/tickets', {
        user_id: Number(currentUser.user_id),
        product_code: product,
        random_sample: useSampling,
      });
      if (setCurrentUser) {
        setCurrentUser(res.data.user);
        localStorage.setItem('vietlot_current_user', JSON.stringify(res.data.user));
      }
      
      const newTicket = res.data.ticket;
      
      // Trigger new ticket printing animation
      setNewlyPrintedId(newTicket.ticket_id);
      setTimeout(() => {
        setNewlyPrintedId(null);
      }, 2000);

      setMessage({ type: 'success', text: `In vé #${newTicket.ticket_id} thành công! Chúc bạn trúng lớn.` });
      await loadTickets();
    } catch (e) {
      const detail = e.response?.data?.detail;
      if (detail && typeof detail === 'object' && detail.user) {
        if (setCurrentUser) {
          setCurrentUser(detail.user);
          localStorage.setItem('vietlot_current_user', JSON.stringify(detail.user));
        }
      }
      const text = typeof detail === 'object'
        ? detail.message
        : detail || e.message || 'Không thể in vé';
      setMessage({ type: 'error', text });
      await loadTickets();
    }
    setCreating(false);
  };

  // Quota Circle math parameters
  const quotaRatio = useMemo(() => {
    if (!currentUser) return 0;
    if (currentUser?.role === 'admin') return 1;
    const limit = currentUser?.daily_ticket_limit || 1;
    const used = currentUser?.used_today || 0;
    return Math.min(used / limit, 1);
  }, [currentUser]);

  const circumference = 2 * Math.PI * 30; // 188.4
  const strokeDashoffset = circumference - quotaRatio * circumference;

  // Filtered and Searched tickets list
  const filteredTickets = useMemo(() => {
    return tickets.filter(ticket => {
      // 1. Filter by product code
      if (historyFilter !== 'ALL' && ticket.product_code !== historyFilter) {
        return false;
      }
      // 2. Search query check (search ticket_id or draw_no)
      if (searchQuery.trim() !== '') {
        const query = searchQuery.toLowerCase().trim();
        const ticketIdMatches = String(ticket.ticket_id).includes(query);
        const drawNoMatches = String(ticket.predicted_draw_no).includes(query);
        const prodNameMatches = (PRODUCTS.find(p => p.code === ticket.product_code)?.label || '').toLowerCase().includes(query);
        return ticketIdMatches || drawNoMatches || prodNameMatches;
      }
      return true;
    });
  }, [tickets, historyFilter, searchQuery]);

  return (
    <div className="user-portal-layout">
      {/* Sleek Top Navbar */}
      <header className="user-top-navbar">
        <div className="user-navbar-brand" onClick={() => navigate('/')}>
          <div className="user-brand-logo">🎰</div>
          <div>
            <div className="user-brand-text">Vietlot AI</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.5px' }}>TẠO VÉ & LỊCH SỬ CÁ NHÂN</div>
          </div>
        </div>

        <div className="user-navbar-actions">
          {/* API Connection Indicator */}
          <div className="api-status" style={{ marginRight: 8 }}>
            <div className={`status-dot ${apiOnline ? '' : 'offline'}`} />
            <span style={{ fontSize: 12.5, fontWeight: 500 }} className="text-secondary">{apiOnline ? 'API Connected' : 'API Offline'}</span>
          </div>

          {/* User Profile Info / Login button */}
          {currentUser ? (
            <>
              <div className="user-profile-badge">
                <div className="user-profile-avatar">
                  {currentUser.display_name ? currentUser.display_name.slice(0, 2).toUpperCase() : 'U'}
                </div>
                <div>
                  <div className="font-bold" style={{ fontSize: 13, color: 'white', lineHeight: 1.2 }}>{currentUser.display_name}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>@{currentUser.username}</div>
                </div>
              </div>

              {/* Logout Button */}
              <button 
                className="btn btn-secondary btn-sm" 
                style={{ color: 'var(--accent-rose)', borderColor: 'rgba(244, 63, 94, 0.2)', background: 'rgba(244, 63, 94, 0.05)', display: 'flex', alignItems: 'center', gap: 6 }} 
                onClick={onLogout}
                title="Đăng xuất khỏi hệ thống"
              >
                <LogOut size={14} />
                <span>Đăng xuất</span>
              </button>
            </>
          ) : (
            <button 
              className="btn btn-primary glow-btn-primary btn-sm" 
              onClick={() => navigate('/login')}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 8 }}
            >
              <User size={14} />
              <span>Đăng nhập</span>
            </button>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="user-portal-body animate-in">
        
        {/* Banner chào mừng & Quota Card */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 1.2fr', gap: '20px', marginBottom: '24px' }} className="grid-2">
          
          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <h2 style={{ fontSize: 24, fontWeight: 900, marginBottom: 8, background: 'linear-gradient(90deg, #ffffff, #93c5fd)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              {currentUser ? `Xin chào, ${currentUser.display_name}! 👋` : 'Chào mừng đến với Vietlot AI! 🎰'}
            </h2>
            <p className="text-secondary" style={{ fontSize: 13.5, lineHeight: 1.5, margin: 0 }}>
              Chào mừng bạn đến với hệ thống tạo vé số thông minh. Các bộ số dưới đây được sinh ra từ các thuật toán Học máy (LightGBM, XGBoost) dựa trên dữ liệu lịch sử quay thưởng.
            </p>
          </div>

          <div className="glass-panel" style={{ padding: 0, overflow: 'hidden', display: 'flex' }}>
            {currentUser ? (
              <div className="quota-indicator-card">
                <div className="quota-progress-circle">
                  <svg className="quota-circle-svg" viewBox="0 0 80 80">
                    <defs>
                      <linearGradient id="quotaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#3b82f6" />
                        <stop offset="50%" stopColor="#a855f7" />
                        <stop offset="100%" stopColor="#f43f5e" />
                      </linearGradient>
                    </defs>
                    <circle className="quota-circle-bg" cx="40" cy="40" r="30" />
                    <circle 
                      className="quota-circle-fill" 
                      cx="40" 
                      cy="40" 
                      r="30" 
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                    />
                  </svg>
                  <div className="quota-progress-text">
                    {currentUser.remaining_today ?? '∞'}
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <div className="stat-label" style={{ marginBottom: 4 }}>Lượt tạo vé hôm nay</div>
                  <div className="font-bold" style={{ fontSize: 16, color: 'white' }}>
                    {currentUser.role === 'admin' ? 'Không giới hạn' : `${currentUser.remaining_today} vé còn lại`}
                  </div>
                  <div className="text-secondary" style={{ fontSize: 12, marginTop: 2 }}>
                    Đã in: {currentUser.used_today} / {currentUser.role === 'admin' ? '∞' : currentUser.daily_ticket_limit} vé hàng ngày
                  </div>
                </div>
              </div>
            ) : (
              <div className="quota-indicator-card" style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)', borderColor: 'rgba(255,255,255,0.08)' }}>
                <div className="quota-progress-circle">
                  <svg className="quota-circle-svg" viewBox="0 0 80 80">
                    <circle className="quota-circle-bg" cx="40" cy="40" r="30" />
                  </svg>
                  <div className="quota-progress-text" style={{ fontSize: 16 }}>🔒</div>
                </div>
                <div style={{ flex: 1 }}>
                  <div className="stat-label" style={{ marginBottom: 4 }}>Yêu cầu đăng nhập</div>
                  <div className="font-bold" style={{ fontSize: 14, color: 'white' }}>Đăng nhập để xem lượt in vé</div>
                  <div className="text-secondary" style={{ fontSize: 11, marginTop: 2 }}>Mỗi tài khoản được in tối đa 3 vé/ngày</div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
          
          {/* ALERT MESSAGES */}
          {isLocked && (
            <div className="alert alert-warning mb-6" style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 16 }}>
              <ShieldAlert size={18} style={{ color: 'var(--accent-amber)', marginTop: 2, marginRight: 8 }} />
              <div>
                <strong style={{ color: 'var(--accent-amber)', display: 'block', marginBottom: 2 }}>Đã đạt giới hạn in vé trong ngày</strong>
                <span>Bạn đã dùng hết lượt in vé miễn phí trong ngày hôm nay. Liên hệ Admin để được cấp thêm hạn ngạch in vé!</span>
              </div>
            </div>
          )}

          {message && (
            <div className={`alert ${message.type === 'success' ? 'alert-success' : 'alert-error'} mb-6`} style={{ borderRadius: 16 }}>
              {message.type === 'success' ? <CheckCircle size={18} style={{ marginRight: 8 }} /> : <AlertTriangle size={18} style={{ marginRight: 8 }} />}
              <div>{message.text}</div>
            </div>
          )}

          {/* 1. BẢNG ĐIỀU KHIỂN TẠO VÉ (TICKET GENERATOR) */}
          <div className="glass-panel" style={{ position: 'relative' }}>
            
            {/* PRINTING SIMULATION OVERLAY */}
            {creating && (
              <div className="printing-progress-overlay">
                <RefreshCw className="spin" size={32} style={{ color: '#3b82f6' }} />
                <div style={{ fontWeight: 700, fontSize: 16, color: 'white' }}>Đang kết nối máy chủ AI...</div>
                <div className="text-secondary" style={{ fontSize: 13 }}>Đang sinh bộ số tối ưu & in vé voucher</div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, gap: 16 }} className="flex-col items-center">
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: 'white', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Ticket size={20} style={{ color: '#3b82f6' }} /> Bảng điều khiển in vé AI
                </h3>
                <p className="text-secondary" style={{ fontSize: 13, marginTop: 4 }}>Chọn loại sản phẩm Vietlott và cấu hình chế độ lấy mẫu của Machine Learning.</p>
              </div>
              <button 
                className="btn btn-primary glow-btn-primary" 
                disabled={creating || isLocked} 
                onClick={createTicket}
                style={{ height: 46, padding: '0 24px', fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}
              >
                <Cpu size={16} />
                <span>In Vé Số Dự Đoán AI</span>
              </button>
            </div>

            {/* Product Selection Cards */}
            <div className="product-grid-modern">
              {PRODUCTS.map(p => (
                <div 
                  key={p.code}
                  className={`product-card-modern ${p.code} ${product === p.code ? 'active' : ''}`}
                  onClick={() => setProduct(p.code)}
                >
                  <div className="product-card-icon">
                    {p.code === 'MEGA_645' && <Compass size={22} />}
                    {p.code === 'POWER_655' && <Sparkles size={22} />}
                    {p.code === 'BINGO18' && <Cpu size={22} />}
                  </div>
                  <div className="font-bold" style={{ fontSize: 16, color: 'white', marginBottom: 4 }}>{p.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{p.hint}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8, fontStyle: 'italic' }}>{p.desc}</div>
                </div>
              ))}
            </div>

            {/* Advanced Generator Options */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'white', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <SlidersHorizontal size={14} style={{ color: 'var(--text-secondary)' }} />
                <span>Chế độ tạo số AI:</span>
              </div>

              <div className="options-grid-modern">
                <div 
                  className={`option-select-card ${useSampling ? 'active' : ''}`}
                  onClick={() => setUseSampling(true)}
                >
                  <div className="option-radio-dot" />
                  <div>
                    <div className="font-bold" style={{ fontSize: 14, color: 'white', marginBottom: 4 }}>Lấy mẫu ngẫu nhiên AI (Weighted Sampling - Khuyên dùng)</div>
                    <div className="text-secondary" style={{ fontSize: 12, lineHeight: 1.4 }}>
                      Sinh số ngẫu nhiên theo xác suất của AI làm trọng số. Giúp bạn in được nhiều vé khác nhau cho cùng một kỳ quay số để tối đa hóa độ bao phủ giải thưởng.
                    </div>
                  </div>
                </div>

                <div 
                  className={`option-select-card ${!useSampling ? 'active' : ''}`}
                  onClick={() => setUseSampling(false)}
                >
                  <div className="option-radio-dot" />
                  <div>
                    <div className="font-bold" style={{ fontSize: 14, color: 'white', marginBottom: 4 }}>Top 1 Xác suất AI cố định (Deterministic Top-N)</div>
                    <div className="text-secondary" style={{ fontSize: 12, lineHeight: 1.4 }}>
                      Lấy chính xác bộ số có xác suất trúng cao nhất từ mô hình Machine Learning. Kết quả sẽ không thay đổi khi bạn bấm in nhiều lần trong cùng một kỳ.
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* 2. LỊCH SỬ IN VÉ (TICKET HISTORY) */}
          <div className="glass-panel">
            {currentUser ? (
              <>
                <div className="history-tabs-container">
                  <div>
                    <h3 style={{ fontSize: 18, fontWeight: 800, color: 'white', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <History size={20} style={{ color: '#a855f7' }} /> Lịch sử vé đã in
                    </h3>
                    <p className="text-secondary" style={{ fontSize: 13, margin: 0 }}>Tổng số {tickets.length} vé dự đoán đã được hệ thống in cho tài khoản của bạn.</p>
                  </div>

                  {/* Search query box */}
                  <div className="search-input-wrap">
                    <Search size={16} className="search-icon-inside" />
                    <input 
                      type="text" 
                      className="history-search-input" 
                      placeholder="Tìm mã vé, kỳ quay, sản phẩm..." 
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>

                {/* History filter tab */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, gap: 16 }} className="flex-col items-center">
                  <div className="history-filter-tabs">
                    <button className={`history-filter-tab ${historyFilter === 'ALL' ? 'active' : ''}`} onClick={() => setHistoryFilter('ALL')}>Tất cả</button>
                    <button className={`history-filter-tab ${historyFilter === 'MEGA_645' ? 'active' : ''}`} onClick={() => setHistoryFilter('MEGA_645')}>Mega 6/45</button>
                    <button className={`history-filter-tab ${historyFilter === 'POWER_655' ? 'active' : ''}`} onClick={() => setHistoryFilter('POWER_655')}>Power 6/55</button>
                    <button className={`history-filter-tab ${historyFilter === 'BINGO18' ? 'active' : ''}`} onClick={() => setHistoryFilter('BINGO18')}>Bingo18</button>
                  </div>
                  
                  <button className="btn btn-secondary btn-sm" onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <RefreshCw size={12} />
                    <span>Làm mới danh sách</span>
                  </button>
                </div>

                {/* Ticket Grid Layout */}
                <div className="ticket-grid" style={{ padding: 0 }}>
                  {filteredTickets.length === 0 ? (
                    <div className="empty-state w-full" style={{ gridColumn: '1 / -1', padding: '60px 20px' }}>
                      <div className="empty-state-icon" style={{ fontSize: 44, opacity: 0.3, marginBottom: 12 }}>🎟️</div>
                      <h3 style={{ fontSize: 16, color: 'var(--text-secondary)', marginBottom: 6 }}>Không tìm thấy vé phù hợp</h3>
                      <p className="text-secondary" style={{ fontSize: 13, margin: 0 }}>
                        {searchQuery.trim() !== '' || historyFilter !== 'ALL' 
                          ? 'Không tìm thấy vé khớp với điều kiện tìm kiếm hoặc bộ lọc.' 
                          : 'Bạn chưa thực hiện in vé dự đoán AI nào.'}
                      </p>
                    </div>
                  ) : (
                    filteredTickets.map(ticket => (
                      <TicketStub 
                        key={ticket.ticket_id} 
                        ticket={ticket} 
                        isNew={ticket.ticket_id === newlyPrintedId} 
                      />
                    ))
                  )}
                </div>
              </>
            ) : (
              <div className="empty-state w-full" style={{ padding: '60px 20px' }}>
                <div className="empty-state-icon" style={{ fontSize: 48, opacity: 0.3, marginBottom: 16 }}>🔒</div>
                <h3 style={{ fontSize: 18, color: 'white', marginBottom: 8, fontWeight: 700 }}>Yêu cầu đăng nhập</h3>
                <p className="text-secondary" style={{ fontSize: 13.5, marginBottom: 20, maxWidth: 400, margin: '0 auto 20px' }}>
                  Bạn cần đăng nhập tài khoản để xem lịch sử vé đã in và theo dõi kết quả trúng thưởng dự đoán AI.
                </p>
                <button className="btn btn-primary glow-btn-primary btn-sm" onClick={() => navigate('/login')} style={{ padding: '8px 20px', borderRadius: 8 }}>Đăng nhập ngay</button>
              </div>
            )}
          </div>

        </div>

      </main>

      {/* Futuristic footer */}
      <footer style={{ padding: '40px 24px', textAlign: 'center', borderTop: '1px solid rgba(255, 255, 255, 0.05)', marginTop: 40 }}>
        <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
          Hệ thống chạy trên nền tảng dự báo Machine Learning của Vietlot AI &copy; {new Date().getFullYear()}. Mọi quyền được bảo lưu.
        </div>
      </footer>
    </div>
  );
}
