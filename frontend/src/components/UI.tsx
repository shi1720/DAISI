import { ArrowUpRight, Check, LoaderCircle, X, AlertCircle, Info } from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { PropsWithChildren, ReactNode } from 'react';

export function Brand({ compact = false }: { compact?: boolean }) {
  return <div className={`brand ${compact ? 'compact' : ''}`}><svg aria-hidden="true" width="38" height="38" viewBox="0 0 48 48"><rect width="48" height="48" rx="13" fill="currentColor"/><path d="M10 31v-8a14 14 0 0 1 28 0v8M10 25h28M17 25v9m14-9v9" fill="none" stroke="#f7f6f0" strokeWidth="3" strokeLinecap="round"/><path d="M21 15h6" stroke="#ed9d65" strokeWidth="3" strokeLinecap="round"/></svg>{!compact && <span>Hawker<span className="brand-bridge">Bridge</span></span>}</div>;
}
export function Spinner({ label = 'Loading…', small = false }: { label?: string; small?: boolean }) {
  return <span className={`loading ${small ? 'small' : ''}`} role="status"><LoaderCircle className="spin" size={small ? 16 : 22}/><span>{label}</span></span>;
}
export function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="notice error" role="alert"><AlertCircle size={19}/><div>{message}</div>{retry && <button className="text-button" onClick={retry}>Try again <ArrowUpRight size={15}/></button>}</div>;
}
export function Note({ children, className = '' }: PropsWithChildren<{ className?: string }>) {
  return <div className={`notice note ${className}`}><Info size={16}/><div>{children}</div></div>;
}
export function Tag({ children, tone = 'neutral' }: PropsWithChildren<{ tone?: 'neutral'|'orange'|'green' }>) {
  return <span className={`tag ${tone}`}>{children}</span>;
}
export function Metric({ label, value, note, tone, icon }: { label: string; value: ReactNode; note: ReactNode; tone?: string; icon?: ReactNode }) {
  return <div className={`metric ${tone ?? ''}`}><div className="metric-top"><span>{label}</span>{icon}</div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>;
}
export function Modal({ title, children, onClose }: PropsWithChildren<{ title: string; onClose: () => void }>) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);
  return <dialog className="modal" ref={ref} onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => { if (event.target === ref.current) onClose(); }} aria-labelledby="modal-heading"><div className="modal-heading"><h2 id="modal-heading">{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={20}/></button></div>{children}</dialog>;
}
export function Toast({ children }: PropsWithChildren) { return <div className="toast" role="status"><Check size={18}/>{children}</div>; }
export function Empty({ icon, title, children, action }: PropsWithChildren<{ icon: ReactNode; title: string; action?: ReactNode }>) {
  return <div className="empty-state"><div className="empty-icon">{icon}</div><h3>{title}</h3><p>{children}</p>{action}</div>;
}
