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
          <TiagoPanel robotId="1" robotName="Tiago #1" />
        </section>
        <section className="panel tiago-panel">
          <TiagoPanel robotId="2" robotName="Tiago #2" />
        </section>
        <section className="panel tiago-panel">
          <TiagoPanel robotId="3" robotName="Tiago #3" />
        </section>
      </main>
    </div>
  )
}

export default App
