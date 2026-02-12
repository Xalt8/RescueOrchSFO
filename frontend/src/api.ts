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

// Tiago API - supports multiple robots (1, 2, 3)
export const tiago = {
  status: (robotId: string = '1') => fetchJson<{ connected: boolean; position?: unknown }>(`/tiago/${robotId}/status`),
  velocity: (data: { linear_x?: number; linear_y?: number; angular?: number }, robotId: string = '1') =>
    fetchJson(`/tiago/${robotId}/velocity`, { method: 'POST', body: JSON.stringify(data) }),
  arm: (data: { arm: 'left' | 'right'; joint_positions?: number[]; pose?: unknown }, robotId: string = '1') =>
    fetchJson(`/tiago/${robotId}/arm`, { method: 'POST', body: JSON.stringify(data) }),
  head: (data: { head_1?: number; head_2?: number }, robotId: string = '1') =>
    fetchJson(`/tiago/${robotId}/head`, { method: 'POST', body: JSON.stringify(data) }),
  torso: (data: { height: number }, robotId: string = '1') =>
    fetchJson(`/tiago/${robotId}/torso`, { method: 'POST', body: JSON.stringify(data) }),
  gripper: (data: { arm: 'left' | 'right'; action: 'open' | 'close' }, robotId: string = '1') =>
    fetchJson(`/tiago/${robotId}/gripper`, { method: 'POST', body: JSON.stringify(data) }),
  action: (action: 'stop' | 'home_arms' | 'open_gripper' | 'close_gripper', robotId: string = '1') =>
    fetchJson(`/tiago/${robotId}/action`, { method: 'POST', body: JSON.stringify({ action }) }),
  stop: (robotId: string = '1') => fetchJson(`/tiago/${robotId}/stop`, { method: 'POST' }),
};
