const BASE = import.meta.env.VITE_API_URL || '/api';

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// Mavic API
export const mavic = {
  status: () => fetchJson<{ connected: boolean; flying: boolean; altitude: number }>('/mavic/status'),
  velocity: (data: { pitch?: number; roll?: number; yaw?: number; vertical?: number }) =>
    fetchJson('/mavic/velocity', { method: 'POST', body: JSON.stringify(data) }),
  altitude: (altitude: number) =>
    fetchJson('/mavic/altitude', { method: 'POST', body: JSON.stringify({ altitude }) }),
  takeoff: () => fetchJson('/mavic/takeoff', { method: 'POST' }),
  land: () => fetchJson('/mavic/land', { method: 'POST' }),
  hover: () => fetchJson('/mavic/hover', { method: 'POST' }),
};

// Tiago API
export const tiago = {
  status: () => fetchJson<{ connected: boolean; position?: unknown }>('/tiago/status'),
  velocity: (data: { linear_x?: number; linear_y?: number; angular?: number }) =>
    fetchJson('/tiago/velocity', { method: 'POST', body: JSON.stringify(data) }),
  action: (action: 'stop') =>
    fetchJson('/tiago/action', { method: 'POST', body: JSON.stringify({ action }) }),
  stop: () => fetchJson('/tiago/stop', { method: 'POST' }),
};
