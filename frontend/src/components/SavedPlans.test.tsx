import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import type { Analysis, OptimiseParams, Plan } from '../types';
import SavedPlans from './SavedPlans';

const parameters:OptimiseParams = {date:'2026-09-28',radius_m:800,senior_weight:2,planning_areas:[],rescheduled_closure_ids:[],budget:1500,site_cost:300,meal_cost:4.25,meals_per_site:150,max_sites:3,participation_rate:.05};
const analysis:Analysis = {date:parameters.date,radius_m:800,data_as_of:'2026-09-22',model_version:'test',source_fingerprint:'test',summary:{total_centres:0,closed_centres:0,total_residents:0,total_seniors:0,baseline_covered_residents:0,remaining_covered_residents:0,newly_exposed_residents:0,newly_exposed_seniors:0,affected_zones:0,food_stalls_closed:0},centres:[],zones:[],area_ranking:[],calendar:[],limitations:[]};
function plan(id:string,title:string):Plan {
  return {id,title,status:'draft',date:parameters.date,created_at:'2026-09-22T00:00:00Z',updated_at:'2026-09-22T00:00:00Z',parameters,notes:'Original notes',result:{analysis,assumptions:parameters,sites:[],summary:{budget:1500,spent:500.25,unspent:999.75,total_meals:50,estimated_demand:60,unmet_demand:10,sites_selected:0,weighted_benefit:50,baseline_weighted_benefit:50,improvement_pct:0,solver_status:'optimal'},baseline:{name:'Largest demand first',total_meals:50,weighted_benefit:50,spent:500.25},sensitivity:[],explanation:'Test allocation',limitations:[],model_version:'test',source_fingerprint:'test'}};
}
const first = plan('first','Clementi proposal');
const second = plan('second','Bedok proposal');
const json = (data:unknown) => new Response(JSON.stringify(data),{status:200});
function renderPlans() { return render(<SavedPlans version={0} openPlanId={null} onOpened={vi.fn()} onNew={vi.fn()} notify={vi.fn()}/>); }
beforeEach(() => {
  vi.spyOn(window,'scrollTo').mockImplementation(() => undefined);
  Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:vi.fn(function(this:HTMLDialogElement){this.setAttribute('open','');})});
  Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:vi.fn(function(this:HTMLDialogElement){this.removeAttribute('open');})});
});
afterEach(() => {cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();});

describe('saved-plan identity and asynchronous briefs', () => {
  it('never shows a delayed brief under a different selected plan', async () => {
    let finishFirst!:(response:Response) => void;
    let briefSignal:AbortSignal|null|undefined;
    vi.stubGlobal('fetch',vi.fn(async (url:string,options?:RequestInit) => {
      if(url==='/api/plans')return json({plans:[first,second]});
      if(url==='/api/plans/first')return json(first);
      if(url==='/api/plans/second')return json(second);
      if(url==='/api/brief?plan_id=first'){briefSignal=options?.signal;return new Promise<Response>(resolve => {finishFirst=resolve;});}
      if(url==='/api/brief?plan_id=second')return json({text:'Brief for Bedok only.'});
      throw new Error(`Unexpected request ${url}`);
    }));
    renderPlans();
    fireEvent.click(await screen.findByRole('button',{name:/Clementi proposal/}));
    await screen.findByRole('heading',{name:'Clementi proposal'});
    fireEvent.click(screen.getByRole('button',{name:'Prepare brief'}));
    fireEvent.click(screen.getByRole('button',{name:'All saved plans'}));
    fireEvent.click(await screen.findByRole('button',{name:/Bedok proposal/}));
    await screen.findByRole('heading',{name:'Bedok proposal'});
    expect(briefSignal?.aborted).toBe(true);
    await act(async () => finishFirst(json({text:'Outdated brief for Clementi.'})));
    expect(screen.queryByText('Outdated brief for Clementi.')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Prepare brief'}));
    expect(await screen.findByText('Brief for Bedok only.')).toBeInTheDocument();
  });
  it('invalidates a prepared brief when the underlying plan details change', async () => {
    vi.stubGlobal('fetch',vi.fn(async (url:string,options?:RequestInit) => {
      if(url==='/api/plans')return json({plans:[first]});
      if(url==='/api/plans/first' && options?.method==='PATCH')return json({...first,...JSON.parse(String(options.body))});
      if(url==='/api/plans/first')return json(first);
      if(url==='/api/brief?plan_id=first')return json({text:'Brief based on original notes.'});
      throw new Error(`Unexpected request ${url}`);
    }));
    renderPlans();
    fireEvent.click(await screen.findByRole('button',{name:/Clementi proposal/}));
    await screen.findByRole('heading',{name:'Clementi proposal'});
    fireEvent.click(screen.getByRole('button',{name:'Prepare brief'}));
    await screen.findByText('Brief based on original notes.');
    fireEvent.click(screen.getByRole('button',{name:'Edit details'}));
    fireEvent.change(screen.getByLabelText('Coordination notes'),{target:{value:'Updated operational checks'}});
    fireEvent.click(screen.getByRole('button',{name:'Save changes'}));
    await screen.findByText('Updated operational checks');
    expect(screen.queryByText('Brief based on original notes.')).not.toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Prepare brief'})).toBeEnabled();
  });
  it('keeps unsaved edits after a revision conflict and requires comparison with the latest version', async () => {
    let loads=0;const submitted:Record<string,unknown>[]=[];
    const latest={...first,updated_at:'2026-09-22T01:00:00Z',notes:'A newer note from another tab'};
    vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
      if(url==='/api/plans')return json({plans:[first]});
      if(url==='/api/plans/first'&&options?.method==='PATCH'){
        const body=JSON.parse(String(options.body));submitted.push(body);
        if(submitted.length===1)return new Response(JSON.stringify({detail:'This plan changed in another session. Load the latest version before saving.'}),{status:409});
        return json({...latest,...body,updated_at:'2026-09-22T02:00:00Z'});
      }
      if(url==='/api/plans/first')return json(loads++ ? latest : first);
      throw new Error(`Unexpected request ${url}`);
    }));
    renderPlans();fireEvent.click(await screen.findByRole('button',{name:/Clementi proposal/}));
    await screen.findByRole('heading',{name:'Clementi proposal'});
    fireEvent.click(screen.getByRole('button',{name:'Edit details'}));
    const dialog=within(screen.getByRole('dialog'));
    fireEvent.change(dialog.getByLabelText('Coordination notes'),{target:{value:'My unsaved local changes'}});
    fireEvent.click(dialog.getByRole('button',{name:'Save changes'}));
    expect(await dialog.findByRole('alert')).toHaveTextContent('changed in another session');
    expect(dialog.getByLabelText('Coordination notes')).toHaveValue('My unsaved local changes');
    expect(dialog.getByRole('button',{name:'Save changes'})).toBeDisabled();
    expect(submitted[0].expected_updated_at).toBe(first.updated_at);
    fireEvent.click(dialog.getByRole('button',{name:'Load latest and compare'}));
    await dialog.findByText('A newer note from another tab');
    expect(dialog.getByLabelText('Coordination notes')).toHaveValue('My unsaved local changes');
    fireEvent.change(dialog.getByLabelText('Coordination notes'),{target:{value:'Merged notes from both tabs'}});
    fireEvent.click(dialog.getByRole('button',{name:'Save changes'}));
    await screen.findByText('Merged notes from both tabs');
    expect(submitted[1].expected_updated_at).toBe(latest.updated_at);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('never retries a deleted plan as a new proposal and keeps unsaved text available',async()=>{
    vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
      if(url==='/api/plans')return json({plans:[first]});
      if(url==='/api/plans/first'&&options?.method==='PATCH')return new Response(JSON.stringify({detail:'Plan not found in this workspace.'}),{status:404});
      if(url==='/api/plans/first')return json(first);
      throw new Error(`Unexpected request ${url}`);
    }));
    renderPlans();fireEvent.click(await screen.findByRole('button',{name:/Clementi proposal/}));
    await screen.findByRole('heading',{name:'Clementi proposal'});
    fireEvent.click(screen.getByRole('button',{name:'Edit details'}));
    const editor=within(screen.getByRole('dialog'));
    fireEvent.change(editor.getByLabelText('Coordination notes'),{target:{value:'Text worth keeping'}});
    fireEvent.click(editor.getByRole('button',{name:'Save changes'}));
    await editor.findByText(/This plan has been deleted/);
    expect(editor.getByLabelText('Coordination notes')).toHaveValue('Text worth keeping');
    expect(editor.getByRole('button',{name:'Save changes'})).toBeDisabled();
    expect(editor.queryByRole('button',{name:'Load latest and compare'})).not.toBeInTheDocument();
  });

});
