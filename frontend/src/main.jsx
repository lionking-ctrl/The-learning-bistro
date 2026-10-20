import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  CalendarDays,
  CheckCircle2,
  Clock3,
  Phone,
  RefreshCw,
  Users,
  Database,
  FileUp,
  LoaderCircle,
  MessageCircle,
  Moon,
  Send,
  Sparkles,
  Sun,
  UtensilsCrossed,
} from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

async function api(path, opt = {}) {
  const r = await fetch(API + path, opt);
  const t = await r.text();
  let d = {};
  
  try {
    d = t ? JSON.parse(t) : {};
  } catch {
    d = { raw: t };
  }
  
  if (!r.ok) {
    throw Error(d.detail || d.message || `HTTP ${r.status}`);
  }
  return d;
}

function App() {
  const [dark, setDark] = useState(false);
  const [health, setHealth] = useState('checking');
  const [q, setQ] = useState('');
  const [ans, setAns] = useState();
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  
  const [file, setFile] = useState();
  const [up, setUp] = useState(false);
  const [upResult, setUpResult] = useState();
  
  const [book, setBook] = useState({
  customer_name: '',
  reservation_date: '',
  reservation_time: '',
  guests: 2,
  phone: '',
  });
  const [bookBusy, setBookBusy] = useState(false);
  const [bookResult, setBookResult] = useState();
  const [bookErr, setBookErr] = useState('');

  const [reservations, setReservations] = useState([]);
  const [reservationsBusy, setReservationsBusy] = useState(false);
  const [reservationsErr, setReservationsErr] = useState('');

  async function loadReservations() {
    setReservationsBusy(true);
    setReservationsErr('');
    try {
      const res = await api('/api/reservations');
      setReservations(Array.isArray(res) ? res : (res.reservations || []));
    } catch (e) {
      setReservationsErr(e.message || 'Unable to load reservations.');
    } finally {
      setReservationsBusy(false);
    }
  }

  useEffect(() => {
    api('/api/health')
      .then(() => setHealth('online'))
      .catch(() => setHealth('offline'));
    loadReservations();
  }, []);

  async function ask(e) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setErr('');
    setAns();
    try {
      const res = await api('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, message: q }),
      });
      setAns(res);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

async function reserve(e) {
  e.preventDefault();

  setBookBusy(true);
  setBookErr('');
  setBookResult();

  const payload = {
    customer_name: book.customer_name.trim(),
    reservation_date: book.reservation_date,
    reservation_time: book.reservation_time,
    guests: Number(book.guests),
    phone: book.phone.trim(),
  };

  console.log('RESERVATION REQUEST', payload);

  try {
    const res = await api('/api/reservations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    setBookResult(res);
    await loadReservations();
  } catch (e) {
    setBookErr(e.message);
  } finally {
    setBookBusy(false);
  }
}

  async function upload(e) {
    e.preventDefault();
    if (!file) return;
    setUp(true);
    setUpResult();
    try {
      let f = new FormData();
      f.append('file', file);
      const res = await api('/api/documents/upload', {
        method: 'POST',
        body: f,
      });
      setUpResult(res);
      e.target.reset();
      setFile();
    } catch (e) {
      setErr(e.message);
    } finally {
      setUp(false);
    }
  }

  const suggestions = [
    'What time does the restaurant open?',
    'What are the vegetarian dishes?',
    'What is the price of paneer tikka?',
  ];

  return (
    <div className={dark ? 'app dark' : 'app'}>
      <header>
        <div className="brand">
          <span>
            <UtensilsCrossed size={19} />
          </span>
          <div>
            <b>The Learning Bistro</b>
            <small>AI Restaurant Concierge</small>
          </div>
        </div>
        <div className="right">
          <small>
            <i className={health} />
            {health === 'online'
              ? 'Backend online'
              : health === 'offline'
              ? 'Backend offline'
              : 'Connecting...'}
          </small>
          <button onClick={() => setDark(!dark)}>
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </header>

      <main>
        <section className="hero">
          <div>
            <label>
              <Sparkles size={14} /> AI-powered dining assistant
            </label>
            <h1>
              Your table.<br />
              <em>Your questions.</em><br />
              One smart bistro.
            </h1>
            <p>
              Ask about our menu, opening hours, dishes and reservations. Your
              restaurant PDFs become searchable knowledge for the AI.
            </p>
            <div className="pills">
              <span>Ollama + Qwen3</span>
              <span>Cassandra</span>
              <span>RAG from PDF</span>
            </div>
          </div>
          <div className="heroCard">
            <div className="food">🍝</div>
            <h3>Good food, smart answers.</h3>
            <p>Let the AI concierge handle the questions.</p>
            <div className="stats">
              <b>
                11:00<small>Opens</small>
              </b>
              <b>
                23:00<small>Closes</small>
              </b>
              <b>
                4.9<small>Rating</small>
              </b>
            </div>
          </div>
        </section>

        <section className="grid">
          <article>
            <div className="title">
              <span className="purple">
                <MessageCircle size={18} />
              </span>
              <div>
                <h2>Ask the Bistro</h2>
                <small>Powered by your RAG knowledge base</small>
              </div>
            </div>
            <form onSubmit={ask}>
              <textarea
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Ask anything about the restaurant..."
              />
              <div className="suggest">
                {suggestions.map((x) => (
                  <button type="button" onClick={() => setQ(x)} key={x}>
                    {x}
                  </button>
                ))}
              </div>
              <button className="primary" disabled={busy || !q.trim()}>
                {busy ? <LoaderCircle className="spin" /> : <Send />}
                {busy ? 'Thinking...' : 'Ask AI'}
              </button>
            </form>
            {err && <div className="error">{err}</div>}
            {ans && (
              <div className="answer">
                <b>✦ AI ANSWER</b>
                <p>
                  {ans.answer ||
                    ans.response ||
                    ans.message ||
                    ans.raw ||
                    JSON.stringify(ans)}
                </p>
                {(ans.sources || ans.documents) && (
                  <small>
                    RAG sources: {JSON.stringify(ans.sources || ans.documents)}
                  </small>
                )}
              </div>
            )}
          </article>

          <article>
            <div className="title">
              <span className="orange">
                <CalendarDays size={18} />
              </span>
              <div>
                <h2>Reserve a Table</h2>
                <small>Send a reservation request</small>
              </div>
            </div>
            <form onSubmit={reserve} className="form">
              <div className="two">
                <label>
                  Name
                  <input
                    required
                    value={book.customer_name}
                    onChange={(e) =>
                    setBook({ ...book, customer_name: e.target.value })
                     }
                  />
                </label>
                <label>
                  Guests
                  <select
                    value={book.guests}
                    onChange={(e) =>
                      setBook({ ...book, guests: e.target.value })
                    }
                  >
                    {Array.from({ length: 10 }, (_, i) => (
                      <option key={i + 1}>{i + 1}</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="two">
                <label>
                  Date
                  <input
                    required
                    type="date"
                    value={book.reservation_date}
                    onChange={(e) =>
                    setBook({ ...book, reservation_date: e.target.value })
                    }
                  />
                </label>
                <label>
                  Time
                  <input
                    required
                    type="time"
                    value={book.reservation_time}
                    onChange={(e) =>
                    setBook({ ...book, reservation_time: e.target.value })
                    }
                  />
                </label>
              </div>
              <label>
                Phone
                <input
                  value={book.phone}
                  onChange={(e) =>
                    setBook({ ...book, phone: e.target.value })
                  }
                />
              </label>
              <button className="primary orangeBtn" disabled={bookBusy}>
                {bookBusy ? (
                  <LoaderCircle className="spin" />
                ) : (
                  <CalendarDays />
                )}
                {bookBusy ? 'Booking...' : 'Book table'}
              </button>
            </form>
            {bookErr && <div className="error">{bookErr}</div>}
            {bookResult && (
              <div className="success">
                <CheckCircle2 />
                <div>
                  <b>Reservation received</b>
                  <small>
                    {bookResult.message ||
                      bookResult.confirmation_id ||
                      'Your request was successful.'}
                  </small>
                </div>
              </div>
            )}
          </article>
        </section>

        <section className="reservationsPanel">
          <div className="title reservationTitle">
            <span className="blue"><CalendarDays size={18} /></span>
            <div><h2>Reservations</h2><small>Live reservations from Cassandra</small></div>
            <button type="button" className="refreshBtn" onClick={loadReservations} disabled={reservationsBusy}>
              <RefreshCw className={reservationsBusy ? 'spin' : ''} size={17} /> Refresh
            </button>
          </div>
          {reservationsErr && <div className="error">{reservationsErr}</div>}
          {reservationsBusy && reservations.length === 0 ? (
            <div className="reservationEmpty"><LoaderCircle className="spin" /><span>Loading reservations...</span></div>
          ) : reservations.length === 0 ? (
            <div className="reservationEmpty"><CalendarDays size={28} /><span>No reservations found.</span><small>New bookings will appear here automatically.</small></div>
          ) : (
            <div className="reservationTableWrap">
              <table className="reservationTable"><thead><tr><th>Customer</th><th>Date</th><th>Time</th><th>Guests</th><th>Phone</th><th>Status</th></tr></thead>
                <tbody>{reservations.map((r) => (
                  <tr key={r.reservation_id}>
                    <td><strong>{r.customer_name || 'Guest'}</strong><small className="reservationId">{r.reservation_id}</small></td>
                    <td><span className="cellIcon"><CalendarDays size={14} />{r.reservation_date}</span></td>
                    <td><span className="cellIcon"><Clock3 size={14} />{r.reservation_time}</span></td>
                    <td><span className="cellIcon"><Users size={14} />{r.guests}</span></td>
                    <td><span className="cellIcon"><Phone size={14} />{r.phone || '—'}</span></td>
                    <td><span className={r.status === 'CONFIRMED' ? 'status confirmed' : 'status'}>{r.status || 'UNKNOWN'}</span></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </section>

        <section className="upload">
          <div className="title">
            <span className="green">
              <FileUp size={18} />
            </span>
            <div>
              <h2>Update Restaurant Knowledge</h2>
              <small>PDF → extract → chunk → embed → Cassandra</small>
            </div>
          </div>
          <form onSubmit={upload}>
            <label className="drop">
              <FileUp /> {file ? file.name : 'Choose restaurant PDF'}
              <input
                type="file"
                accept="application/pdf,.pdf"
                onChange={(e) => setFile(e.target.files?.[0])}
              />
            </label>
            <button className="secondary" disabled={!file || up}>
              {up ? <LoaderCircle className="spin" /> : <Database />}
              {up ? 'Indexing...' : 'Upload & index'}
            </button>
          </form>
          {upResult && (
            <div className="success">
              <CheckCircle2 />
              <div>
                <b>Knowledge base updated</b>
                <small>
                  {upResult.message || JSON.stringify(upResult)}
                </small>
              </div>
            </div>
          )}
        </section>

        <section className="flow">
          <span>React UI</span>
          <i /> <span>FastAPI</span>
          <i /> <span>RAG</span>
          <i /> <span>Qwen3</span>
          <i /> <span>Cassandra</span>
        </section>
      </main>

      <footer>THE LEARNING BISTRO · AI RESTAURANT MANAGEMENT SYSTEM</footer>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);