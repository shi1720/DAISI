import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import Auth from './Auth';

afterEach(() => {cleanup();vi.unstubAllGlobals();});
describe('authentication',() => {
  it('supports genuine account registration with bounds aligned to the API',async () => {
    const onSession = vi.fn();
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({user:{id:'new',name:'Test User',email:'test@example.com',mode:'local'},csrf_token:'csrf',auth_mode:'local'}),{status:200})));
    render(<Auth session={{user:null,csrf_token:null,auth_mode:'local'}} onSession={onSession}/>);
    fireEvent.click(screen.getByRole('button',{name:'Create an account'}));
    const name = screen.getByLabelText('Full name') as HTMLInputElement;
    const password = screen.getByLabelText('Password') as HTMLInputElement;
    expect(name.minLength).toBe(2);expect(name.maxLength).toBe(80);
    expect(password.minLength).toBe(12);expect(password.maxLength).toBe(256);
    fireEvent.change(name,{target:{value:'Test User'}});
    fireEvent.change(screen.getByLabelText('Email address'),{target:{value:'test@example.com'}});
    fireEvent.change(password,{target:{value:'a strong example password'}});
    expect(name.closest('form')!.checkValidity()).toBe(true);
    fireEvent.click(screen.getByRole('button',{name:'Create account'}));
    await waitFor(() => expect(onSession).toHaveBeenCalledOnce());
  });
  it('does not expose local signup or guest sessions when platform identity is required',() => {
    render(<Auth session={{user:null,csrf_token:null,auth_mode:'databricks'}} onSession={vi.fn()}/>);
    expect(screen.queryByRole('button',{name:'Explore as a guest'})).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Email address')).not.toBeInTheDocument();
    expect(screen.getByText(/Sign in through your Databricks workspace/)).toBeInTheDocument();
  });
});
