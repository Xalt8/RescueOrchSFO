import { MavicPanel } from './components/MavicPanel'
import { TiagoPanel } from './components/TiagoPanel'
import './App.css'

function App() {
  return (
    <div className="app">
      <header className="header">
        <h1>Rescue Command Center</h1>
        <span className="badge">SFO</span>
      </header>
      <main className="main">
        <section className="panel mavic-panel">
          <MavicPanel />
        </section>
        <section className="panel tiago-panel">
          <TiagoPanel />
        </section>
      </main>
    </div>
  )
}

export default App
