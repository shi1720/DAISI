import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import App from './App';

// Opt-in real HTTP test. This verifies React workflows and the live API contract;
// it does not substitute for visual browser or geographic-rendering verification.
vi.mock('./components/AccessMap',() => ({default:() => <div>Geographic view (not rendered in DOM tests)</div>}));
const baseUrl = process.env.HAWKERBRIDGE_TEST_API;
const networkFetch = globalThis.fetch;
let cookie = '';

describe.skipIf(!baseUrl)('real API community-planning workflow',() => {
  beforeEach(() => {
    cookie = '';
    vi.stubGlobal('fetch',async (input:string|URL|Request,options?:RequestInit) => {
      const raw = typeof input === 'string' ? input : input.toString();
      const headers = new Headers(options?.headers);
      if (cookie) headers.set('Cookie',cookie);
      const response = await networkFetch(new URL(raw,baseUrl),{...options,headers});
      const received = response.headers.get('set-cookie');
      if (received) cookie = received.split(';')[0];
      return response;
    });
    vi.spyOn(window,'scrollTo').mockImplementation(() => undefined);
    HTMLDialogElement.prototype.showModal = function() {this.setAttribute('open','');};
    HTMLDialogElement.prototype.close = function() {this.removeAttribute('open');};
  });
  afterEach(() => {cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();});
  it('authenticates, scopes, allocates, saves, edits, reviews, briefs, and deletes an actual private plan',async () => {
    render(<App/>);
    fireEvent.click(await screen.findByRole('button',{name:'Explore as a guest'}));
    expect(await screen.findByText('Residents in flagged subzones',{selector:'span'})).toBeInTheDocument();
    expect(screen.getByLabelText('Analysis date')).toHaveAttribute('min','2026-01-01');
    expect(screen.getByLabelText('Analysis date')).toHaveAttribute('max','2026-12-31');
    fireEvent.change(screen.getByLabelText('Analysis date'),{target:{value:'2026-09-22'}});
    fireEvent.change(screen.getByLabelText('Planning area scope'),{target:{value:'Clementi'}});
    fireEvent.click(screen.getByRole('button',{name:'Continuity planner'}));
    await waitFor(() => expect(screen.getByRole('button',{name:'Generate support proposal'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Cost, capacity & priority settings'}));
    expect(screen.getByRole('button',{name:'Generate support proposal'}).closest('form')!.checkValidity()).toBe(true);
    fireEvent.click(screen.getByRole('button',{name:'Generate support proposal'}));
    fireEvent.click(await screen.findByRole('button',{name:'Save proposal'}));
    const dialog = screen.getByRole('dialog');
    const title = within(dialog).getByLabelText('Plan title') as HTMLInputElement;
    const notes = within(dialog).getByLabelText(/Coordination notes/) as HTMLTextAreaElement;
    expect(title.maxLength).toBe(140);expect(notes.maxLength).toBe(4000);
    fireEvent.change(title,{target:{value:'Live DOM verification plan'}});
    fireEvent.change(notes,{target:{value:'Test record. No service dispatched.'}});
    fireEvent.click(within(dialog).getByRole('button',{name:'Save draft'}));
    expect(await screen.findByRole('heading',{name:'Live DOM verification plan'})).toBeInTheDocument();
    expect(screen.getByText('Clementi',{selector:'dd'})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Edit details'}));
    const editDialog = screen.getByRole('dialog');
    const editedTitle = within(editDialog).getByLabelText('Plan title') as HTMLInputElement;
    expect(editedTitle.maxLength).toBe(140);
    fireEvent.change(editedTitle,{target:{value:'Reviewed live DOM verification'}});
    fireEvent.click(within(editDialog).getByRole('button',{name:'Save changes'}));
    expect(await screen.findByRole('heading',{name:'Reviewed live DOM verification'})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Mark as reviewed'}));
    const reviewDialog = screen.getByRole('dialog');
    expect(within(reviewDialog).getByRole('button',{name:'Mark reviewed'})).toBeDisabled();
    within(reviewDialog).getAllByRole('checkbox').forEach(checkbox => fireEvent.click(checkbox));
    fireEvent.click(within(reviewDialog).getByRole('button',{name:'Mark reviewed'}));
    expect(await screen.findByText('Reviewed planning proposal')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Prepare brief'}));
    expect(await screen.findByRole('button',{name:'Copy brief'})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Delete this plan'}));
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Delete plan'}));
    expect(await screen.findByText('Your next good idea belongs here.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Evidence & methods'}));
    expect(await screen.findByText('Test the proposal, not just the story')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Sign out'}));
    expect(await screen.findByRole('button',{name:'Explore as a guest'})).toBeInTheDocument();
  },20000);
});
