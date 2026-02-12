import { useState, useEffect, useCallback } from 'react'
import { tiago } from '../api'
import './TiagoPanel.css'

export function TiagoPanel() {
  const [status, setStatus] = useState<{ connected: boolean } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [active, setActive] = useState<Record<string, boolean>>({})

  const fetchStatus = useCallback(async () => {
    try {
      const s = await tiago.status()
      setStatus(s)
      setError(null)
    } catch {
      setError('Backend not reachable – start it with ./run.sh')
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 2000)
    return () => clearInterval(id)
  }, [fetchStatus])

  const sendVelocity = (linear_x: number, linear_y: number, angular: number) => {
    tiago.velocity({ linear_x, linear_y, angular }).catch((e) => setError(e?.message || 'Command failed'))
  }

  const handleKey = (key: string, down: boolean, lx: number, ly: number, ang: number) => {
    setActive(prev => ({ ...prev, [key]: down }))
    const mult = down ? 1 : 0
    sendVelocity(lx * mult, ly * mult, ang * mult)
  }

  return (
    <div className="tiago-panel">
      <div className="panel-header">
        <h2>Tiago Base</h2>
        <div className="status-row">
          <span className={`status-dot ${status?.connected ? 'ok' : 'err'}`} />
          <span className="status-text">{status?.connected ? 'Connected' : 'Offline'}</span>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="controls">
        <div className="action-buttons">
          <button onClick={() => tiago.action('stop')} className="btn btn-stop">
            Stop
          </button>
        </div>

        <div className="joystick-grid">
          <div />
          <button
            className={`joy-btn ${active.fwd ? 'active' : ''}`}
            onMouseDown={() => handleKey('fwd', true, 0.5, 0, 0)}
            onMouseUp={() => handleKey('fwd', false, 0, 0, 0)}
            onMouseLeave={() => active.fwd && handleKey('fwd', false, 0, 0, 0)}
          >
            ▲
          </button>
          <div />
          <button
            className={`joy-btn ${active.left ? 'active' : ''}`}
            onMouseDown={() => handleKey('left', true, 0, 0, 0.5)}
            onMouseUp={() => handleKey('left', false, 0, 0, 0)}
            onMouseLeave={() => active.left && handleKey('left', false, 0, 0, 0)}
          >
            ◀
          </button>
          <div className="center-cell" />
          <button
            className={`joy-btn ${active.right ? 'active' : ''}`}
            onMouseDown={() => handleKey('right', true, 0, 0, -0.5)}
            onMouseUp={() => handleKey('right', false, 0, 0, 0)}
            onMouseLeave={() => active.right && handleKey('right', false, 0, 0, 0)}
          >
            ▶
          </button>
          <div />
          <button
            className={`joy-btn ${active.back ? 'active' : ''}`}
            onMouseDown={() => handleKey('back', true, -0.5, 0, 0)}
            onMouseUp={() => handleKey('back', false, 0, 0, 0)}
            onMouseLeave={() => active.back && handleKey('back', false, 0, 0, 0)}
          >
            ▼
          </button>
          <div />
        </div>

        <p className="hint">Use buttons to move Tiago base. Stop to halt immediately.</p>
      </div>
    </div>
  )
}
