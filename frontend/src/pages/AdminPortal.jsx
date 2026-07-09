import { useEffect, useMemo, useState } from 'react';
import API from '../api';

const PRODUCTS = [
  { code: 'MEGA_645', label: 'Mega 6/45' },
  { code: 'POWER_655', label: 'Power 6/55' },
  { code: 'BINGO18', label: 'Bingo18' },
];

function Balls({ numbers = [] }) {
  return (
    <div className="number-balls">
      {numbers.map((n, idx) => (
        <div key={`${idx}-${n}`} className="ball predicted sm">
          {String(n).padStart(2, '0')}
        </div>
      ))}
    </div>
  );
}

export default function AdminPortal() {
  const [users, setUsers] = useState([]);
  const [product, setProduct] = useState('MEGA_645');
  const [adminTickets, setAdminTickets] = useState([]);
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const admin = useMemo(() => users.find(u => u.role === 'admin'), [users]);
  const normalUsers = useMemo(() => users.filter(u => u.role !== 'admin'), [users]);

  const loadUsers = async () => {
    const res = await API.get('/api/users');
    setUsers(res.data);
    const adminUser = res.data.find(u => u.role === 'admin');
    if (adminUser) {
      const ticketsRes = await API.get(`/api/users/${adminUser.user_id}/tickets?limit=20`);
      setAdminTickets(ticketsRes.data.data);
    }
  };

  const load = async () => {
    setLoading(true);
    try {
      await loadUsers();
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const updateQuota = async (user, patch) => {
    setMessage(null);
    try {
      const res = await API.patch(`/api/admin/users/${user.user_id}/quota`, patch);
      setUsers(prev => prev.map(u => u.user_id === user.user_id ? res.data.user : u));
      setMessage({ type: 'success', text: `Da cap nhat gioi han cho ${user.display_name}` });
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.detail || e.message });
    }
  };

  const createAdminTicket = async () => {
    if (!admin) return;
    setCreating(true);
    setMessage(null);
    try {
      const res = await API.post('/api/tickets', {
        user_id: admin.user_id,
        product_code: product,
        random_sample: true,
      });
      setMessage({ type: 'success', text: `Admin da tao ve #${res.data.ticket.ticket_id}` });
      await loadUsers();
    } catch (e) {
      setMessage({ type: 'error', text: e.response?.data?.detail || e.message });
    }
    setCreating(false);
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1 className="page-title">Admin Quan Ly Ve</h1>
          <div className="page-subtitle">Admin tao ve khong gioi han va tang gioi han cho user bi khoa.</div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={load}>Lam moi</button>
      </div>

      <div className="page-body">
        {loading ? (
          <div className="loader-wrap"><div className="spin">...</div> Dang tai...</div>
        ) : (
          <>
            {message && (
              <div className={`alert ${message.type === 'success' ? 'alert-success' : 'alert-error'} mb-6`}>
                {message.text}
              </div>
            )}

            <div className="grid-2 gap-4">
              <div className="card">
                <div className="card-body">
                  <div className="chart-title">Admin tao ve khong gioi han</div>
                  <div className="product-tabs mb-4">
                    {PRODUCTS.map(p => (
                      <button
                        key={p.code}
                        className={`product-tab ${product === p.code ? 'active' : ''}`}
                        onClick={() => setProduct(p.code)}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                  <button className="btn btn-primary" disabled={creating || !admin} onClick={createAdminTicket}>
                    {creating ? 'Dang tao...' : 'Tao ve admin'}
                  </button>
                </div>
              </div>

              <div className="card">
                <div className="card-body">
                  <div className="chart-title">Thong tin admin</div>
                  <div className="stat-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                    <div>
                      <div className="stat-label">Tai khoan</div>
                      <div className="font-bold">{admin?.display_name || 'Admin'}</div>
                    </div>
                    <div>
                      <div className="stat-label">Quyen</div>
                      <div className="font-bold">Khong gioi han</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="card mt-6">
              <div className="card-body">
                <div className="chart-title">Quan ly gioi han user</div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>Gioi han/ngay</th>
                        <th>Da dung</th>
                        <th>Con lai</th>
                        <th>Trang thai</th>
                        <th>Hanh dong</th>
                      </tr>
                    </thead>
                    <tbody>
                      {normalUsers.map(user => (
                        <tr key={user.user_id}>
                          <td>
                            <div className="font-bold">{user.display_name}</div>
                            <div className="text-sm text-muted">{user.username}</div>
                          </td>
                          <td><span className="font-mono">{user.daily_ticket_limit}</span></td>
                          <td><span className="font-mono">{user.used_today}</span></td>
                          <td><span className="font-mono">{user.remaining_today}</span></td>
                          <td>
                            <span className={`badge ${user.is_locked ? 'pending' : 'reconciled'}`}>
                              {user.is_locked ? 'Bi khoa' : 'Dang mo'}
                            </span>
                          </td>
                          <td>
                            <div className="flex gap-2">
                              <button className="btn btn-secondary btn-sm" onClick={() => updateQuota(user, { add_quota: 1, unlock: true })}>+1</button>
                              <button className="btn btn-secondary btn-sm" onClick={() => updateQuota(user, { add_quota: 5, unlock: true })}>+5</button>
                              <button className="btn btn-success btn-sm" onClick={() => updateQuota(user, { daily_ticket_limit: Math.max(user.daily_ticket_limit, user.used_today + 1), unlock: true })}>
                                Mo khoa
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="card mt-6">
              <div className="card-body">
                <div className="chart-title">Ve admin gan day</div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Ve</th>
                        <th>San pham</th>
                        <th>Ky</th>
                        <th>Bo so</th>
                        <th>Thoi gian</th>
                      </tr>
                    </thead>
                    <tbody>
                      {adminTickets.length === 0 ? (
                        <tr><td colSpan={5}><div className="empty-state">Admin chua tao ve nao.</div></td></tr>
                      ) : adminTickets.map(t => (
                        <tr key={t.ticket_id}>
                          <td><span className="font-mono">#{t.ticket_id}</span></td>
                          <td>{t.product_code}</td>
                          <td><span className="font-mono">#{t.predicted_draw_no}</span></td>
                          <td><Balls numbers={t.numbers} /></td>
                          <td><span className="text-sm text-secondary">{t.created_at.slice(0, 16).replace('T', ' ')}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
