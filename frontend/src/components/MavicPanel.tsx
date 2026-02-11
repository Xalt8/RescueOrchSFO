import { useState, useEffect, useCallback } from 'react'
import { mavic } from '../api'
import './MavicPanel.css'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export function MavicPanel() {
  const [status, setStatus] = useState<{ connected: boolean; flying: boolean; altitude: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [active, setActive] = useState<Record<string, boolean>>({})

  const fetchStatus = useCallback(async () => {
    try {
      const s = await mavic.status()
      setStatus(s)
      setError(null)
    } catch (e) {
      setError('Backend not reachable – start it with ./run.sh')
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 2000)
    return () => clearInterval(id)
  }, [fetchStatus])

  const sendVelocity = (pitch: number, roll: number, yaw: number, vertical: number) => {
    mavic.velocity({ pitch, roll, yaw, vertical }).catch((e) => setError(e?.message || 'Command failed'))
  }

  const handleKey = (key: string, down: boolean, pitch: number, roll: number, yaw: number, vertical: number) => {
    setActive(prev => ({ ...prev, [key]: down }))
    const mult = down ? 1 : 0
    sendVelocity(pitch * mult, roll * mult, yaw * mult, vertical * mult)
  }

  return (
    <div className="mavic-panel">
      <div className="panel-header">
        <h2>Mavic 2 Pro</h2>
        <div className="status-row">
          <span className={`status-dot ${status?.connected ? 'ok' : 'err'}`} />
          {status?.flying ? (
            <span className="status-text flying">In flight · {status.altitude.toFixed(1)}m</span>
          ) : (
            <span className="status-text">Ground</span>
          )}
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="camera-feed">
        <img
          src={`${API_BASE}/mavic/camera/stream`}
          alt="Mavic camera"
          className="camera-view"
        />
        <span className="camera-label">Live feed</span>
      </div>

      <div className="controls">
        <div className="action-buttons">
          <button onClick={() => mavic.takeoff().then(fetchStatus).catch(() => setError('Command failed'))} className="btn btn-takeoff">
            Take Off
          </button>
          <button onClick={() => mavic.land().then(fetchStatus).catch(() => setError('Command failed'))} className="btn btn-land">
            Land
          </button>
          <button onClick={() => mavic.hover().then(fetchStatus).catch(() => setError('Command failed'))} className="btn btn-hover">
            Hover
          </button>
        </div>

        <div className="joystick-grid">
          <div />
          <button
            className={`joy-btn ${active.fwd ? 'active' : ''}`}
            onMouseDown={() => handleKey('fwd', true, -1.5, 0, 0, 0)}
            onMouseUp={() => handleKey('fwd', false, 0, 0, 0, 0)}
            onMouseLeave={() => active.fwd && handleKey('fwd', false, 0, 0, 0, 0)}
          >
            ▲
          </button>
          <div />
          <button
            className={`joy-btn ${active.left ? 'active' : ''}`}
            onMouseDown={() => handleKey('left', true, 0, 1, 0, 0)}
            onMouseUp={() => handleKey('left', false, 0, 0, 0, 0)}
            onMouseLeave={() => active.left && handleKey('left', false, 0, 0, 0, 0)}
          >
            ◀
          </button>
          <div className="center-cell" />
          <button
            className={`joy-btn ${active.right ? 'active' : ''}`}
            onMouseDown={() => handleKey('right', true, 0, -1, 0, 0)}
            onMouseUp={() => handleKey('right', false, 0, 0, 0, 0)}
            onMouseLeave={() => active.right && handleKey('right', false, 0, 0, 0, 0)}
          >
            ▶
          </button>
          <div />
          <button
            className={`joy-btn ${active.back ? 'active' : ''}`}
            onMouseDown={() => handleKey('back', true, 1.5, 0, 0, 0)}
            onMouseUp={() => handleKey('back', false, 0, 0, 0, 0)}
            onMouseLeave={() => active.back && handleKey('back', false, 0, 0, 0, 0)}
          >
            ▼
          </button>
          <div />
        </div>

        <div className="altitude-control">
          <label>Altitude (m)</label>
          <div className="alt-buttons">
            <button onClick={() => mavic.altitude((status?.altitude ?? 0) + 0.5).catch(() => setError('Command failed'))}>+</button>
            <span className="alt-value">{status?.altitude.toFixed(1) ?? '0.0'}</span>
            <button onClick={() => mavic.altitude(Math.max(0, (status?.altitude ?? 0) - 0.5)).catch(() => setError('Command failed'))}>−</button>
          </div>
        </div>
      </div>
    </div>
  )
}
