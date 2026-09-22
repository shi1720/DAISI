import { useState } from 'react';
import { ShieldCheck, Trash2 } from 'lucide-react';
import { api, errorMessage } from '../api';
import type { Session } from '../types';
import { ErrorNotice, Modal, Spinner } from './UI';

export default function AccountSettings({session,onClose,onDeleted,onLogout}: {session:Session;onClose:()=>void;onDeleted:()=>Promise<void>;onLogout:()=>Promise<void>}) {
  const [confirm,setConfirm] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const user = session.user!;
  const guest = user.mode === 'guest';
  async function removeAccount() {
    setBusy(true);setError('');
    try {await api('/auth/account',{method:'DELETE'});await onDeleted();}
    catch(e) {setError(errorMessage(e));setBusy(false);}
  }
  return <Modal title={confirm ? 'Delete your account?' : 'Account settings'} onClose={() => {if(!busy)onClose();}}>
    {error && <ErrorNotice message={error}/>}
    {confirm ? <><p className="account-description">This permanently deletes your sign-in account and every saved plan in this workspace. Download any plans you need before continuing. This cannot be undone.</p><div className="modal-actions"><button className="button secondary" disabled={busy} onClick={() => setConfirm(false)}>Keep my account</button><button className="button danger" disabled={busy} onClick={() => void removeAccount()}>{busy ? <Spinner small label="Deleting…"/> : <><Trash2 size={16}/>Delete account and plans</>}</button></div></> : <>
      <div className="account-profile"><span className="avatar">{user.name.slice(0,1).toUpperCase()}</span><div><strong>{guest ? 'Guest workspace' : user.name}</strong>{!guest && <span>{user.email}</span>}</div></div>
      <div className="account-privacy"><ShieldCheck size={19}/><div><h3>Your information</h3><p>{guest ? session.auth_mode === 'firebase' ? 'This temporary workspace expires after 7 days. Signing out deletes its saved plans immediately. Export anything you want to keep before you leave.' : 'This workspace is private to your current guest session. Export any plans you want to keep before you leave.' : 'Your account name and email are stored for sign-in. Saved plans and coordination notes are private to your account. You can permanently delete this information below.'}</p><p>The planning model uses aggregate public population counts. It does not hold individual resident records. Keep personal resident details out of coordination notes.</p></div></div>
      <a className="account-source" href="https://github.com/shi1720/DAISI" target="_blank" rel="noreferrer">Read the source code and methodology</a>
      <div className="modal-actions"><button className="button secondary" onClick={onClose}>Done</button>{guest ? <button className="button secondary" disabled={busy} onClick={async() => {setBusy(true);await onLogout();setBusy(false);}}>Sign out of guest workspace</button> : <button className="button danger-outline" onClick={() => setConfirm(true)}><Trash2 size={15}/>Delete account</button>}</div>
    </>}
  </Modal>;
}
