import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import AccountSettings from './AccountSettings';
import type { Session } from '../types';

const member:Session = {user:{id:'test',name:'Test Planner',email:'planner@example.test',mode:'firebase'},auth_mode:'firebase',csrf_token:'test'};
beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','');}});
  Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open');}});
});
afterEach(() => {cleanup();vi.unstubAllGlobals();});
describe('account privacy and deletion',() => {
  it('requires an explicit destructive confirmation before deleting the account',async () => {
    const fetchMock=vi.fn().mockResolvedValue(new Response(null,{status:204}));vi.stubGlobal('fetch',fetchMock);
    const onDeleted=vi.fn().mockResolvedValue(undefined);
    render(<AccountSettings session={member} onClose={vi.fn()} onDeleted={onDeleted} onLogout={vi.fn()}/>);
    expect(screen.getByText('planner@example.test')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Delete account'}));
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Keep my account'}));
    expect(screen.getByRole('heading',{name:'Account settings'})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Delete account'}));
    fireEvent.click(screen.getByRole('button',{name:'Delete account and plans'}));
    await waitFor(() => expect(onDeleted).toHaveBeenCalledOnce());
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/account',expect.objectContaining({method:'DELETE'}));
  });
  it('keeps the account usable and explains a failed deletion',async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Deletion service unavailable. Try again.'}),{status:503})));
    const onDeleted=vi.fn();render(<AccountSettings session={member} onClose={vi.fn()} onDeleted={onDeleted} onLogout={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Delete account'}));
    fireEvent.click(screen.getByRole('button',{name:'Delete account and plans'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Deletion service unavailable');
    expect(onDeleted).not.toHaveBeenCalled();
    expect(screen.getByRole('button',{name:'Keep my account'})).toBeEnabled();
  });
  it('explains temporary hosted guest retention without offering account deletion',() => {
    render(<AccountSettings session={{...member,user:{...member.user!,mode:'guest',email:''}}} onClose={vi.fn()} onDeleted={vi.fn()} onLogout={vi.fn()}/>);
    expect(screen.getByText(/expires after 7 days/)).toHaveTextContent('Signing out deletes its saved plans immediately');
    expect(screen.queryByRole('button',{name:'Delete account'})).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Sign out of guest workspace'})).toBeInTheDocument();
  });
});
