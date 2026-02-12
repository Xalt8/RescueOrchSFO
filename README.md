# RescueOrch SFO

Rescue Command Center for controlling Mavic 2 Pro and Tiago++ robots in Webots rescue simulations.

## Project Structure

```
RescueOrchSFO/
├── backend/          # FastAPI backend (control API)
├── frontend/         # React Rescue Command Center UI
├── controllers/      # Webots controllers
└── worlds/           # Webots simulation (rescue_orch.wbt)
```

## Quick Start

### Using run script (recommended)

Start both backend and frontend with one command:

```bash
./run.sh
```

Press Ctrl+C to stop both. The script creates a venv and installs dependencies automatically on first run. Make it executable if needed: `chmod +x run.sh`.

If you see **"Address already in use"** or **"Offline"** in the UI, ports 8000 or 5173 may be occupied by a previous run. The run script now frees these ports automatically; or run manually: `lsof -ti:8000 | xargs kill -9` and `lsof -ti:5173 | xargs kill -9`, then `./run.sh` again.

To run backend and frontend in **separate terminals** instead, use `./run_backend.sh` and `./run_frontend.sh`.

- Backend API docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

### Manual setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Run Webots (for robot control)

To have Mavic and Tiago **respond to the UI**, you must also run the Webots simulation. **Important:** Start the backend first so it's ready when Webots controllers connect:

1. **First:** Run `./run.sh` – wait until you see "Rescue Command Center running"
2. **Then:** Open `worlds/rescue_orch.wbt` in Webots and click **Play**
3. Open http://localhost:5173 in your browser and use the controls

The Webots console should show `[mavic_api] Connected to Rescue Command Center API` and `[tiago_api] Connected...` when the controllers reach the backend. If you don't see these, the backend may not be running or port 8000 may be blocked.

- **Mavic:** Click **Take Off** first, then use the arrow pad and altitude buttons
- **Tiago:** Use the arrow pad to move the base; **Stop** to halt

## API Usage

The FastAPI backend can be used **programmatically** from any client. See [backend/README.md](backend/README.md) for full documentation, curl examples, and Python/JavaScript snippets.

## License

See project license.
