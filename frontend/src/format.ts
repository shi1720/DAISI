export const number = (value: number | null | undefined) => new Intl.NumberFormat('en-SG', { maximumFractionDigits: 0 }).format(value ?? 0);
export const money = (value: number) => `S$${new Intl.NumberFormat('en-SG', { minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(value)}`;
export const percent = (value: number) => `${new Intl.NumberFormat('en-SG', { maximumFractionDigits: 1 }).format(value)}%`;
export const day = (value: string, options: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' }) => {
  const parsed = new Date(value.length === 10 ? `${value}T12:00:00+08:00` : value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString('en-SG', { ...options, timeZone:'Asia/Singapore' });
};
export const titleCase = (value: string) => value.toLowerCase().replace(/\b\w/g, x => x.toUpperCase());
export const distance = (value: number | null) => value === null ? 'Unavailable' : value >= 1000 ? `${(value / 1000).toFixed(1)} km` : `${number(value)} m`;
export const todaySingapore = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Singapore', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
export function readable(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return number(value);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.map(readable).join(' · ');
  if (value && typeof value === 'object') return Object.entries(value).map(([k,v]) => `${k.replaceAll('_',' ')}: ${readable(v)}`).join('; ');
  return 'Not available';
}
