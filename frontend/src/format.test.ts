import { describe, expect, it } from 'vitest';
import { day, money } from './format';

describe('decision-facing formatting', () => {
  it('preserves cents in submitted costs and saved-plan amounts', () => {
    expect(money(4.25)).toBe('S$4.25');
    expect(money(1500.35)).toBe('S$1,500.35');
    expect(money(1500)).toBe('S$1,500');
  });
  it('interprets both source timestamps and calendar dates in Singapore time', () => {
    expect(day('2026-09-21T23:30:00Z', { day:'numeric', month:'long', year:'numeric' })).toBe('22 September 2026');
    expect(day('2026-09-22', { weekday:'long' })).toBe('Tuesday');
  });
});
