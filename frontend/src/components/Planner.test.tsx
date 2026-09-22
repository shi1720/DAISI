import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { Analysis, AnalysisParams, Optimisation, Snapshot } from '../types';
import Planner from './Planner';

vi.mock('./AccessMap',() => ({default:() => <div>Geographic view</div>}));

const params:AnalysisParams = {date:'2026-09-22',radius_m:800,senior_weight:2,rescheduled_closure_ids:[],planning_areas:['Clementi']};
const analysis:Analysis = {
  date:params.date,radius_m:800,data_as_of:'2026-09-22',model_version:'test',planning_areas:['Clementi'],
  summary:{total_centres:2,closed_centres:1,total_residents:1000,total_seniors:100,baseline_covered_residents:1000,remaining_covered_residents:0,newly_exposed_residents:1000,newly_exposed_seniors:100,affected_zones:1,food_stalls_closed:20},
  centres:[],zones:[],area_ranking:[],calendar:[],limitations:[],source_fingerprint:'source',
};
const snapshot:Snapshot = {manifest:{population_year:2020},centres:[],closures:[],demand_zones:[]};
const output:Optimisation = {
  analysis,assumptions:{...params,budget:1500,site_cost:300,meal_cost:4,meals_per_site:150,max_sites:3,participation_rate:.05},sites:[],
  summary:{budget:1500,spent:500,unspent:1000,total_meals:50,estimated_demand:50,unmet_demand:0,sites_selected:1,weighted_benefit:55,baseline_weighted_benefit:50,improvement_pct:10,solver_status:'optimal'},
  baseline:{name:'Largest demand first',total_meals:50,weighted_benefit:50,spent:500},sensitivity:[],explanation:'A comparable allocation under the selected constraints.',limitations:[],model_version:'test',source_fingerprint:'source',
};
afterEach(() => {cleanup();vi.unstubAllGlobals();});

describe('planning decisions remain connected to their assumptions',() => {
  it('passes the selected planning area and assumptions to the API, and prevents saving after inputs change',async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(output),{status:200}));vi.stubGlobal('fetch',fetchMock);
    render(<Planner analysis={analysis} snapshot={snapshot} params={params} setParams={vi.fn()} analysisLoading={false} onSaved={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Generate support proposal'}));
    await waitFor(() => expect(screen.getByRole('button',{name:'Save proposal'})).toBeEnabled());
    const request = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(request).toEqual({...params,budget:1500,site_cost:300,meal_cost:4,meals_per_site:150,max_sites:3,participation_rate:.05});
    fireEvent.click(screen.getByRole('button',{name:'S$2,500'}));
    expect(screen.getByRole('button',{name:'Save proposal'})).toBeDisabled();
    expect(screen.getByText(/Inputs have changed/)).toBeInTheDocument();
  });
  it('keeps a failed optimisation visible and does not offer a fabricated proposal',async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Source snapshot unavailable'}),{status:503})));
    render(<Planner analysis={analysis} snapshot={snapshot} params={params} setParams={vi.fn()} analysisLoading={false} onSaved={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Generate support proposal'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Source snapshot unavailable');
    expect(screen.queryByRole('button',{name:'Save proposal'})).not.toBeInTheDocument();
  });
  it('blocks a run while the date or access analysis is still being updated',() => {
    render(<Planner analysis={analysis} snapshot={snapshot} params={params} setParams={vi.fn()} analysisLoading onSaved={vi.fn()}/>);
    expect(screen.getByRole('button',{name:'Generate support proposal'})).toBeDisabled();
  });
  it('keeps defaults natively valid when advanced settings open and accepts cent-precision prices',() => {
    render(<Planner analysis={analysis} snapshot={snapshot} params={params} setParams={vi.fn()} analysisLoading={false} onSaved={vi.fn()}/>);
    const form = screen.getByRole('button',{name:'Generate support proposal'}).closest('form')!;
    expect(form.checkValidity()).toBe(true);
    fireEvent.click(screen.getByRole('button',{name:'Cost, capacity & priority settings'}));
    expect(form.checkValidity()).toBe(true);
    const setup = screen.getByRole('spinbutton',{name:/Setup cost per locality/}) as HTMLInputElement;
    const meal = screen.getByRole('spinbutton',{name:/Cost per meal/}) as HTMLInputElement;
    fireEvent.change(setup,{target:{value:'300.35'}});
    fireEvent.change(meal,{target:{value:'4.25'}});
    expect(form.checkValidity()).toBe(true);
    expect(setup.validity.stepMismatch).toBe(false);
    expect(meal.validity.stepMismatch).toBe(false);
    fireEvent.change(setup,{target:{value:'0'}});
    expect(form.checkValidity()).toBe(false);
    fireEvent.change(setup,{target:{value:'300'}});
    const capacity = screen.getByRole('spinbutton',{name:/Meal capacity per locality/});
    fireEvent.change(capacity,{target:{value:'5001'}});
    expect(form.checkValidity()).toBe(false);
    fireEvent.change(capacity,{target:{value:'5000'}});
    expect(form.checkValidity()).toBe(true);
    fireEvent.change(meal,{target:{value:'4.255'}});
    expect(form.checkValidity()).toBe(false);
  });
});
