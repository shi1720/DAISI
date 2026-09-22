import { afterEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import L from 'leaflet';
import AccessMap from './AccessMap';
import type { Analysis, Snapshot } from '../types';

const snapshot:Snapshot={manifest:{population_year:2020},centres:[],closures:[],demand_zones:[]};
const analysis:Analysis={
  date:'2026-09-28',radius_m:800,data_as_of:'2026-09-22',model_version:'test',source_fingerprint:'test',
  summary:{total_centres:0,closed_centres:0,total_residents:0,total_seniors:0,baseline_covered_residents:0,remaining_covered_residents:0,newly_exposed_residents:0,newly_exposed_seniors:0,affected_zones:0,food_stalls_closed:0},
  centres:[],zones:[],area_ranking:[],calendar:[],limitations:[],
};

afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();});

it('ignores a queued resize after navigation and creates a working replacement map',()=>{
  const callbacks:Array<()=>void>=[];
  const disconnect=vi.fn();
  vi.stubGlobal('ResizeObserver',class {
    constructor(callback:()=>void){callbacks.push(callback);}
    observe(){}
    disconnect(){disconnect();}
  });
  const invalidate=vi.spyOn(L.Map.prototype,'invalidateSize');
  const first=render(<AccessMap snapshot={snapshot} analysis={analysis}/>);
  act(()=>callbacks[0]());
  expect(invalidate).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button',{name:'Show all of Singapore'}));
  first.unmount();
  expect(disconnect).toHaveBeenCalledTimes(1);
  // Browsers may already have queued an observer delivery before disconnect.
  act(()=>callbacks[0]());
  expect(invalidate).toHaveBeenCalledTimes(1);
  render(<AccessMap snapshot={snapshot} analysis={analysis}/>);
  act(()=>{callbacks[0]();callbacks[1]();});
  expect(invalidate).toHaveBeenCalledTimes(2);
  expect(screen.getByRole('region',{name:/Singapore hawker access map/})).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Show all of Singapore'}));
});
