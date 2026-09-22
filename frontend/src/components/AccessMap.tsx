import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import type { Feature } from 'geojson';
import { Layers, LocateFixed, MapPin, X } from 'lucide-react';
import type { Analysis, AnalysedCentre, AnalysedZone, Site, Snapshot } from '../types';
import { distance, number, titleCase } from '../format';
import { Tag } from './UI';

type MapSelection = { kind: 'centre'; value: AnalysedCentre } | { kind: 'zone'; value: AnalysedZone } | { kind: 'site'; value: Site };
const noSites: Site[] = [];
const singaporeBounds: L.LatLngBoundsExpression = [[1.220,103.60],[1.478,104.045]];
const escapeHtml = (value: string) => value.replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]!));

export default function AccessMap({ snapshot, analysis, sites = noSites, selectedArea, onAreaClear }: { snapshot: Snapshot; analysis: Analysis; sites?: Site[]; selectedArea?: string|null; onAreaClear?: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map|null>(null);
  const markersRef = useRef<L.LayerGroup|null>(null);
  const boundaryRef = useRef<L.GeoJSON|null>(null);
  const [selection, setSelection] = useState<MapSelection|null>(null);
  const [showOpen, setShowOpen] = useState(true);
  const [showZones, setShowZones] = useState(true);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    // Leaflet's CSS zoom completion timer can outlive a map removed during
    // navigation. This schematic map uses immediate transitions so switching
    // views never leaves a zoom callback pointing at detached map panes.
    const map = L.map(containerRef.current, { zoomControl:false, attributionControl:false, scrollWheelZoom:false, minZoom:10, maxZoom:15, zoomSnap:0.25, zoomDelta:0.5, zoomAnimation:false, markerZoomAnimation:false, fadeAnimation:false });
    map.fitBounds(singaporeBounds, { padding:[12,12], animate:false });
    mapRef.current = map;
    L.control.zoom({ position:'bottomright' }).addTo(map);
    L.control.attribution({ position:'bottomleft', prefix:false }).addAttribution('Singapore public data · schematic access map').addTo(map);
    L.control.scale({ imperial:false, position:'bottomleft' }).addTo(map);
    const resize = new ResizeObserver(() => {
      if (mapRef.current === map) map.invalidateSize({ animate:false });
    });
    resize.observe(containerRef.current);
    return () => { resize.disconnect(); mapRef.current = null; map.stop(); map.remove(); };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    boundaryRef.current?.remove();
    if (snapshot.boundaries) {
      boundaryRef.current = L.geoJSON(snapshot.boundaries, { style: { color:'#b3c3b6', weight:0.85, fillColor:'#e9ede2', fillOpacity:1 }, interactive:false }).addTo(map);
      boundaryRef.current.bringToBack();
    }
  }, [snapshot.boundaries]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    setSelection(null);
    markersRef.current?.remove();
    const layer = L.layerGroup().addTo(map);
    markersRef.current = layer;
    if (showZones) analysis.zones.filter(z => z.newly_exposed && (!selectedArea || z.planning_area === selectedArea)).forEach(zone => {
      if (zone.geometry) L.geoJSON({ type:'Feature', geometry:zone.geometry, properties:{} } as Feature, { style:{ color:'#d95436', weight:1.2, fillColor:'#e97b54', fillOpacity:0.23 } }).bindTooltip(`${escapeHtml(titleCase(zone.name))} · ${number(zone.residents)} census residents in flagged subzone`).on('click', () => setSelection({ kind:'zone', value:zone })).addTo(layer);
      const marker = L.circleMarker([zone.lat,zone.lng], { radius:Math.max(6,Math.min(17,Math.sqrt(zone.residents)/12)), color:'#d95436', weight:1.5, fillColor:'#e78866', fillOpacity:0.27 });
      marker.bindTooltip(`${escapeHtml(titleCase(zone.name))} · ${number(zone.residents)} residents in affected subzone`).on('click', () => setSelection({ kind:'zone', value:zone })).addTo(layer);
    });
    analysis.centres.filter(c => showOpen || c.status === 'closed').forEach(centre => {
      const closed = centre.status === 'closed';
      if (centre.food_access_eligible === false || centre.food_stalls === 0) return;
      const marker = L.marker([centre.lat, centre.lng], { icon:L.divIcon({ className:'centre-marker-wrapper', html:`<span class="centre-marker ${closed ? 'closed' : 'open'}">${closed ? '<svg width="12" height="12" viewBox="0 0 12 12"><path d="M3 3l6 6m0-6L3 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>' : ''}</span>`, iconSize:[closed ? 25 : 14,closed ? 25 : 14], iconAnchor:[closed ? 12.5 : 7,closed ? 12.5 : 7] }), keyboard:true, zIndexOffset:closed ? 1000 : 0, title:`${centre.name}, ${closed ? 'scheduled closed' : 'no resolved closure'}` });
      marker.bindTooltip(`${escapeHtml(centre.name)} · ${closed ? 'scheduled closed' : 'no resolved closure'}`).on('click', () => setSelection({ kind:'centre', value:centre })).addTo(layer);
    });
    sites.forEach((site,index) => {
      L.marker([site.lat, site.lng], { icon:L.divIcon({ className:'site-marker-wrapper', html:`<span class="site-marker"><b>${index+1}</b></span>`, iconSize:[32,36], iconAnchor:[16,34] }), title:`Proposed collection locality ${index+1}: ${site.name}`, keyboard:true, zIndexOffset:2000 }).on('click', () => setSelection({ kind:'site', value:site })).addTo(layer);
    });
    if (selectedArea) {
      const points = analysis.zones.filter(x => x.planning_area === selectedArea).map(z => [z.lat,z.lng] as L.LatLngTuple);
      if (points.length > 0) map.fitBounds(L.latLngBounds(points).pad(0.2), { maxZoom:13, padding:[35,35], animate:false });
    } else map.fitBounds(singaporeBounds, { padding:[12,12], animate:false });
  }, [analysis, sites, showOpen, showZones, selectedArea]);

  return <div className="map-shell">
    <div ref={containerRef} className="access-map" role="region" aria-label="Singapore hawker access map. Centre markers are keyboard accessible. Affected areas also appear in the table below."/>
    <div className="map-top-left"><span className="map-label"><span className="status-dot"/>SINGAPORE</span>{selectedArea && <button className="map-area-chip" onClick={onAreaClear}>{titleCase(selectedArea)} <X size={13}/></button>}</div>
    <button className="map-reset icon-button" onClick={() => { mapRef.current?.fitBounds(singaporeBounds, { animate:false }); onAreaClear?.(); }} aria-label="Show all of Singapore"><LocateFixed size={18}/></button>
    <div className="map-legend"><span><i className="legend-dot closed"/>Closed centre</span><button className={!showOpen ? 'disabled-layer' : ''} onClick={() => setShowOpen(!showOpen)} aria-pressed={showOpen}><i className="legend-dot open"/>No resolved closure</button><button className={!showZones ? 'disabled-layer' : ''} onClick={() => setShowZones(!showZones)} aria-pressed={showZones}><i className="legend-area"/>Flagged subzone</button>{sites.length > 0 && <span><i className="legend-dot site"/>Proposed locality</span>}<Layers size={14}/></div>
    {selection && <div className="map-detail" aria-live="polite"><button className="icon-button close-detail" onClick={() => setSelection(null)} aria-label="Close map detail"><X size={16}/></button><div className="eyebrow">{selection.kind === 'centre' ? 'HAWKER CENTRE' : selection.kind === 'zone' ? 'SUBZONE FLAGGED FOR REVIEW' : 'PROPOSED COLLECTION LOCALITY'}</div><h3>{titleCase(selection.value.name)}</h3>{selection.kind === 'centre' ? <><Tag tone={selection.value.status === 'closed' ? 'orange' : 'green'}>{selection.value.status === 'closed' ? 'Scheduled closure' : 'No resolved closure'}</Tag><p>{selection.value.address}</p><div className="map-detail-facts"><span>{number(selection.value.food_stalls)} food stalls</span><span>{titleCase(selection.value.planning_area)}</span></div>{selection.value.active_closures.map(c => <p className="caption" key={c.id}>{c.kind === 'cleaning' ? 'Cleaning' : 'Works'} · {c.start_date} – {c.end_date}</p>)}</> : selection.kind === 'zone' ? <><p>{number(selection.value.residents)} census residents · {number(selection.value.seniors)} aged 65+</p><div className="map-detail-facts"><span>Before: {distance(selection.value.baseline_distance_m)}</span><span>Now: {distance(selection.value.current_distance_m)}</span></div><p className="caption">Distance from subzone representative point. Area totals are a screening proxy, not a count of people lacking food access.</p></> : <><p><MapPin size={13}/> {number(selection.value.meals)} planned meals · {number(selection.value.estimated_demand)} assumed demand</p><p className="caption">Subzone representative point. A suitable venue and operator must be verified.</p></>}</div>}
  </div>;
}
