# STGen Web UI

Professional web dashboard for STGen IoT Protocol Testing Framework.

## Features

-  Modern, responsive UI with dark/light themes
-  Real-time experiment monitoring
-  One-click experiment launch
-  Live metrics visualization
-  Visual configuration builder
-  Results browser with analysis
-  Distributed deployment manager
-  Background process management (no manual terminals)

## Tech Stack

**Backend:**
- FastAPI (Python async web framework)
- WebSocket for real-time updates
- Background task management

**Frontend:**
- React 18
- Material-UI (MUI) for components
- Recharts for visualization
- Axios for API calls

## Quick Start

### 1. Install Dependencies

```bash
cd stgen-ui

# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Run the Application

#### Option A: Development Mode (Two terminals)

**Terminal 1 - Backend:**
```bash
cd backend
python app.py
# Runs on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
# Runs on http://localhost:3000
```

#### Option B: Production Mode (Single command)

```bash
./start.sh
```

### 3. Access Dashboard

Open browser: **http://localhost:3000**

## Usage

1. **Create Experiment**: Configure protocol, sensors, network conditions
2. **Launch**: Click "Run Experiment" - everything runs in background
3. **Monitor**: Watch real-time metrics and logs
4. **Analyze**: View results with interactive charts
5. **Export**: Download reports and data

## Architecture

```
stgen-ui/
├── backend/           # FastAPI server
│   ├── app.py        # Main API server
│   ├── stgen_controller.py  # STGen wrapper
│   └── requirements.txt
├── frontend/          # React app
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── pages/
│   └── package.json
└── start.sh          # Launch script
```

## API Endpoints

- `GET /api/experiments` - List all experiments
- `POST /api/experiments` - Create new experiment
- `POST /api/experiments/{id}/start` - Start experiment
- `POST /api/experiments/{id}/stop` - Stop experiment
- `GET /api/experiments/{id}/status` - Get status
- `WS /ws/{id}` - Real-time updates

## Configuration

Backend config: `backend/config.json`
```json
{
  "stgen_path": "../",
  "results_path": "../results",
  "max_concurrent": 5
}
```

## Development

- Backend hot-reload: `uvicorn app:app --reload`
- Frontend hot-reload: `npm start` (automatic)

## License

Same as STGen
