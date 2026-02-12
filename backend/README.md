# Rescue Command Center API

FastAPI backend for controlling the Mavic 2 Pro drone and Tiago++ robot in rescue operations. This API is designed to be consumed **programmatically** from any client—Python scripts, curl, other services, or the React frontend.

## Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://localhost:8000/docs  
- ReDoc: http://localhost:8000/redoc  

## Programmatic Usage

### Base URL

Default: `http://localhost:8000`

### Mavic (Drone) Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mavic/status` | Get drone status (connected, flying, altitude) |
| POST | `/mavic/velocity` | Set velocity (pitch, roll, yaw, vertical) |
| POST | `/mavic/altitude` | Set target altitude (meters) |
| POST | `/mavic/action` | Execute takeoff, land, or hover |
| POST | `/mavic/takeoff` | Take off |
| POST | `/mavic/land` | Land |
| POST | `/mavic/hover` | Hover in place |

**Velocity command** (`POST /mavic/velocity`):

```json
{
  "pitch": 0.0,   // -2 to 2, forward/backward
  "roll": 0.0,    // -1 to 1, strafe left/right
  "yaw": 0.0,     // -1.5 to 1.5, rotate
  "vertical": 0.0 // -1 to 1, altitude change
}
```

**Altitude command** (`POST /mavic/altitude`):

```json
{
  "altitude": 1.0  // meters, 0–50
}
```

### Tiago (Robot) Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tiago/status` | Get robot status |
| POST | `/tiago/velocity` | Set base velocity |
| POST | `/tiago/arm` | Command arm position/pose |
| POST | `/tiago/action` | Execute stop, home_arms, open_gripper, close_gripper |
| POST | `/tiago/stop` | Stop base movement |

**Velocity command** (`POST /tiago/velocity`):

```json
{
  "linear_x": 0.0,  // -1 to 1 m/s, forward/backward
  "linear_y": 0.0,  // -1 to 1 m/s, strafe
  "angular": 0.0    // -1 to 1 rad/s, rotation
}
```

## Examples

### Python (requests)

```python
import requests

BASE = "http://localhost:8000"

# Mavic takeoff
r = requests.post(f"{BASE}/mavic/takeoff")
print(r.json())  # {"status": "ok", "action": "takeoff", "flying": True}

# Mavic move forward
requests.post(f"{BASE}/mavic/velocity", json={"pitch": -1.5})

# Mavic land
requests.post(f"{BASE}/mavic/land")

# Tiago move forward
requests.post(f"{BASE}/tiago/velocity", json={"linear_x": 0.5})

# Tiago stop
requests.post(f"{BASE}/tiago/stop")
```

### curl

```bash
# Mavic status
curl http://localhost:8000/mavic/status

# Mavic takeoff
curl -X POST http://localhost:8000/mavic/takeoff

# Mavic land
curl -X POST http://localhost:8000/mavic/land

# Tiago move forward
curl -X POST http://localhost:8000/tiago/velocity \
  -H "Content-Type: application/json" \
  -d '{"linear_x": 0.5}'

# Tiago stop
curl -X POST http://localhost:8000/tiago/stop
```

### JavaScript (fetch)

```javascript
const BASE = 'http://localhost:8000';

// Mavic takeoff
await fetch(`${BASE}/mavic/takeoff`, { method: 'POST' });

// Tiago velocity
await fetch(`${BASE}/tiago/velocity`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ linear_x: 0.5, angular: 0.2 })
});
```

## Integrating with Webots

The API currently stores commands in memory. To control the actual Webots simulation:

1. **Option A: Webots controller + HTTP client**  
   Run a Webots controller that periodically polls a queue or subscribes to commands from this API.

2. **Option B: Socket/ZeroMQ bridge**  
   Add a background task in this FastAPI app that forwards commands to a Webots controller over a socket or ZeroMQ.

3. **Option C: Webots supervisor**  
   Use a Webots supervisor controller that exposes an HTTP server or socket and forwards commands to robot nodes.

Update `app/routers/mavic.py` and `app/routers/tiago.py` to replace the `# TODO` sections with your integration logic.

## Project Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI app, CORS, routers
│   ├── schemas.py       # Pydantic models
│   └── routers/
│       ├── mavic.py     # Mavic endpoints
│       └── tiago.py     # Tiago endpoints
├── requirements.txt
└── README.md
```
