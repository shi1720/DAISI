import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';
import type { Analysis, AnalysisParams, Snapshot } from './types';

vi.mock('./components/AccessMap',()=>({default:()=> <div>Map placeholder for DOM regression</div>}));
vi.mock('./format',async original=>({...await original<typeof import('./format')>(),todaySingapore:()=> '2027-01-20'}));

const snapshot:Snapshot={manifest:{closures_year:2026,population_year:2020,fetched_at:'2026-09-22'},centres:[],closures:[],demand_zones:[]};
function analysis(parameters:AnalysisParams):Analysis {
  return {date:parameters.date,radius_m:parameters.radius_m,data_as_of:'2026-09-22',model_version:'test',source_fingerprint:'test',summary:{total_centres:0,closed_centres:0,total_residents:0,total_seniors:0,baseline_covered_residents:0,remaining_covered_residents:0,newly_exposed_residents:0,newly_exposed_seniors:0,affected_zones:0,food_stalls_closed:0},centres:[],zones:[],area_ranking:[],calendar:[],limitations:[]};
}
function responses(failSecondAnalysis=false) {
  const requests:AnalysisParams[]=[];
  vi.stubGlobal('fetch',vi.fn(async (url:string,options?:RequestInit)=>{
    let payload:unknown;let status=200;
    if(url==='/api/auth/session')payload={user:{id:'safety-test',name:'Guest',email:'',mode:'guest'},csrf_token:'test',auth_mode:'local'};
    else if(url==='/api/snapshot')payload=snapshot;
    else if(url==='/api/analyse'){
      const parameters=JSON.parse(String(options?.body)) as AnalysisParams;requests.push(parameters);
      if(failSecondAnalysis&&requests.length>1){status=503;payload={detail:'Data service temporarily unavailable'};}
      else payload=analysis(parameters);
    }else throw new Error(`Unexpected request ${url}`);
    return new Response(JSON.stringify(payload),{status});
  }));
  vi.spyOn(window,'scrollTo').mockImplementation(()=>undefined);
  return requests;
}
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();});
describe('date provenance and failed-refresh safeguards',()=>{
  it('initialises a future browser clock to the first supported schedule date before analysis',async()=>{
    const requests=responses();render(<App/>);
    expect(await screen.findByText('Residents in flagged subzones',{selector:'span'})).toBeInTheDocument();
    expect(screen.getByLabelText('Analysis date')).toHaveValue('2026-01-01');
    expect(screen.getByLabelText('Analysis date')).toHaveAttribute('min','2026-01-01');
    expect(screen.getByLabelText('Analysis date')).toHaveAttribute('max','2026-12-31');
    expect(requests.length).toBeGreaterThan(0);
    expect(requests.every(request=>request.date==='2026-01-01')).toBe(true);
    expect(screen.getByText(/Public data snapshot.*2026/)).toBeInTheDocument();
  });
  it('marks the last result stale after a failed refresh, removes updating feedback, and blocks planning',async()=>{
    responses(true);render(<App/>);
    expect(await screen.findByText('Residents in flagged subzones',{selector:'span'})).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Nearby access threshold'),{target:{value:'1000'}});
    expect(await screen.findByRole('alert')).toHaveTextContent('Data service temporarily unavailable');
    expect(screen.getByText(/The last successful outlook is shown below/)).toBeInTheDocument();
    expect(screen.queryByText('Updating access outlook…')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Continuity planner'}));
    expect(screen.getByRole('button',{name:'Generate support proposal'})).toBeDisabled();
  });
});


describe('mobile navigation and request ordering',()=>{
  it('removes closed navigation from the accessibility tree and traps focus while open',async()=>{
    vi.stubGlobal('matchMedia',vi.fn().mockReturnValue({matches:true,addEventListener:vi.fn(),removeEventListener:vi.fn()}));
    responses();render(<App/>);
    await screen.findByText('Residents in flagged subzones',{selector:'span'});
    expect(screen.queryByRole('navigation',{name:'Main navigation'})).not.toBeInTheDocument();
    const trigger=screen.getByRole('button',{name:'Open navigation'});trigger.focus();fireEvent.click(trigger);
    expect(screen.getByRole('button',{name:'Overview'})).toHaveFocus();
    expect(document.body.style.overflow).toBe('hidden');
    screen.getByRole('button',{name:'Sign out'}).focus();
    fireEvent.keyDown(document,{key:'Tab'});
    expect(screen.getByRole('button',{name:'Close menu'})).toHaveFocus();
    fireEvent.keyDown(document,{key:'Escape'});
    expect(screen.queryByRole('navigation',{name:'Main navigation'})).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();expect(document.body.style.overflow).toBe('');
  });
  it('ignores an aborted response that arrives after a newer area request',async()=>{
    const pending:Record<string,(response:Response)=>void>={};
    const scopedSnapshot={...snapshot,demand_zones:['Bedok','Clementi'].map((planning_area,i)=>({id:String(i),name:planning_area,planning_area,lat:1.3,lng:103.8,residents:100,seniors:20}))};
    vi.spyOn(window,'scrollTo').mockImplementation(()=>undefined);
    vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>{
      let payload:unknown;
      if(url==='/api/auth/session')payload={user:{id:'race-test',name:'Guest',email:'',mode:'guest'},csrf_token:'test',auth_mode:'local'};
      else if(url==='/api/snapshot')payload=scopedSnapshot;
      else if(url==='/api/analyse'){
        const parameters=JSON.parse(String(options?.body)) as AnalysisParams;
        const area=parameters.planning_areas[0];
        if(area)return new Promise<Response>(resolve=>{pending[area]=resolve;});
        payload=analysis(parameters);
      }else throw new Error(`Unexpected request ${url}`);
      return new Response(JSON.stringify(payload),{status:200});
    }));
    render(<App/>);await screen.findByText('Residents in flagged subzones',{selector:'span'});
    fireEvent.click(screen.getByRole('button',{name:'Continuity planner'}));
    fireEvent.change(screen.getByLabelText('Planning area scope'),{target:{value:'Clementi'}});
    expect(screen.getByRole('button',{name:'Generate support proposal'})).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Planning area scope'),{target:{value:'Bedok'}});
    const parameters:AnalysisParams={date:'2026-01-01',radius_m:800,senior_weight:2,rescheduled_closure_ids:[],planning_areas:['Bedok']};
    await act(async()=>pending.Bedok(new Response(JSON.stringify({...analysis(parameters),planning_areas:['Bedok']}),{status:200})));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Generate support proposal'})).toBeEnabled());
    await act(async()=>pending.Clementi(new Response(JSON.stringify({...analysis({...parameters,planning_areas:['Clementi']}),planning_areas:['Clementi']}),{status:200})));
    expect(screen.getByRole('button',{name:'Generate support proposal'})).toBeEnabled();
    expect(screen.getByLabelText('Planning area scope')).toHaveValue('Bedok');
    expect(screen.queryByText('Updating access outlook…')).not.toBeInTheDocument();
  });
});
