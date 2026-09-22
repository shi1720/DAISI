import { useState } from 'react';
import { ArrowRight, ArrowUpRight, Check, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { post, errorMessage, useSessionToken } from '../api';
import type { Session } from '../types';
import { Brand, ErrorNotice, Spinner } from './UI';

export default function Auth({ session, onSession }: { session: Session; onSession: (session: Session) => void }) {
  const [mode, setMode] = useState<'login'|'register'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState<string|null>(null);
  const [error, setError] = useState('');
  async function authenticate(method: 'demo'|'login'|'register') {
    setBusy(method); setError('');
    try {
      const next = await post<Session>(`/auth/${method}`, method === 'demo' ? {} : { email, password, ...(method === 'register' ? { name } : {}) });
      useSessionToken(next); onSession(next);
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(null); }
  }
  return <main className="auth-layout">
    <section className="auth-story">
      <Brand/>
      <div className="auth-story-content"><div className="eyebrow light"><span className="status-dot"/> SINGAPORE · COMMUNITY CONTINUITY</div><h1>Keep the<br/>neighbourhood<br/>at the <em>table.</em></h1><p>When a hawker centre closes, a daily routine disappears. Help community teams turn an access gap into a practical meal support plan.</p>
      <div className="auth-flow"><div><span>01</span>See the gap</div><ArrowRight size={16}/><div><span>02</span>Plan the support</div><ArrowRight size={16}/><div><span>03</span>Act together</div></div></div>
      <div className="auth-illustration" aria-hidden="true"><svg viewBox="0 0 650 210"><path d="M-30 175Q120 95 310 132T700 92" fill="none" stroke="#40776b" strokeWidth="1"/><path d="M-20 195Q155 117 328 154T690 116" fill="none" stroke="#40776b" strokeWidth="1"/><path d="M110 111h430l-33-31H145z" fill="#d49b6f"/><path d="M130 111h390v7H130z" fill="#f3d5ad"/><path d="M145 120v67m90-67v67m175-67v67m94-67v67" stroke="#b7cebc" strokeWidth="6"/><path d="M255 96h134" stroke="#123b36" strokeWidth="5"/><path d="M277 146h92m-74 3v32m57-32v32m-90-17h-19m-7-15v33m169-18h-19m19-15v33" stroke="#e8dcc6" strokeWidth="6"/><circle cx="460" cy="53" r="20" fill="#d95436"/><path d="M190 90v-32m0-1q24-30 46 0-22 30-46 0m-58 0q28-33 58 0-30 33-58 0" stroke="#7caa8b" fill="#7caa8b"/><path d="M40 181h560" stroke="#517c68" strokeWidth="2"/></svg></div>
      <div className="auth-story-footer"><span>Built for people. Grounded in public data.</span><span>HawkerBridge / SG</span></div>
    </section>
    <section className="auth-form-section">
      <div className="auth-top"><span>A continuity desk for community teams</span><span className="tag green">DAISI 2026</span></div>
      <div className="auth-form-wrap"><div className="eyebrow">A SMALL PLAN. A MEANINGFUL DIFFERENCE.</div><h2>{mode === 'login' ? 'Welcome to the desk.' : 'Make room for your team.'}</h2><p className="muted">{mode === 'login' ? 'Explore Singapore’s hawker access, compare support options, and keep your plans in one place.' : 'Create an account to keep your community continuity plans across visits.'}</p>
      {error && <ErrorNotice message={error}/>}
      {session.auth_mode === 'databricks' ? <div className="notice note"><ShieldCheck/><p>Sign in through your Databricks workspace to access this application. Your workspace identity secures your plans.</p></div> : <>
        <button className="button primary full demo-button" onClick={() => authenticate('demo')} disabled={!!busy}>{busy === 'demo' ? <Spinner small label="Opening your desk…"/> : <>Explore as a guest <ArrowRight size={18}/></>}</button>
        <p className="guest-hint"><Check size={13}/> Real public data. No account needed. Your own guest workspace.</p>
        <div className="divider-label"><span/>or {mode === 'login' ? 'sign in to your account' : 'create an account'}<span/></div>
        <form onSubmit={event => { event.preventDefault(); void authenticate(mode); }}>
          {mode === 'register' && <label className="field">Full name<input value={name} onChange={e => setName(e.target.value)} autoComplete="name" required minLength={2} maxLength={80} placeholder="Your name"/></label>}
          <label className="field">Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" required minLength={5} maxLength={254} placeholder="you@example.com"/></label>
          <label className="field">Password<div className="password-input"><input type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'register' ? 12 : 1} maxLength={256} placeholder={mode === 'register' ? 'At least 12 characters' : 'Enter your password'}/><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(x => !x)}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>
          <button className="button secondary full" type="submit" disabled={!!busy}>{busy && busy !== 'demo' ? <Spinner small label="Please wait…"/> : <>{mode === 'login' ? 'Sign in' : 'Create account'}<ArrowUpRight size={17}/></>}</button>
        </form>
        <p className="auth-switch">{mode === 'login' ? 'New to HawkerBridge?' : 'Already have an account?'} <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></p>
      </>}
      <div className="auth-trust"><ShieldCheck size={20}/><p>Plans are private to your session or account. Guest access ends when your session expires. No personal resident data is collected.</p></div>
      </div><footer className="auth-footer">Community decision support · Singapore national open data</footer>
    </section>
  </main>;
}
