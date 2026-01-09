# STGen - Windows Startup Guide

## Quick Start (Choose One)

### **OPTION 1: Docker (RECOMMENDED) ⭐ No local setup needed!**

```batch
docker-startup.bat
```

This starts everything in isolated Docker containers. **No Python/Node.js installation required.**

**What you need:**
- Docker Desktop installed: https://www.docker.com/products/docker-desktop

**Benefits:**
- ✅ No dependency conflicts
- ✅ Works exactly like Linux/macOS
- ✅ Easy to deploy to cloud
- ✅ Reproducible environment

---

### **OPTION 2: Local Python Setup**

```batch
start_all.bat
```

This runs STGen on your local machine using Python and Node.js.

**What you need:**
- Python 3.12+: https://www.python.org/downloads/
  - **IMPORTANT**: Check "Add Python to PATH" during installation
- Node.js 18+: https://nodejs.org/

**Benefits:**
- ✅ Direct access to code for debugging
- ✅ Faster startup (no container overhead)
- ✅ Easier to modify and develop

---

## Recommended Workflow

| Scenario | Use |
|----------|-----|
| **Production / Deployment** | Docker (`docker-startup.bat`) |
| **Testing / Demos** | Docker (`docker-startup.bat`) |
| **Development / Debugging** | Local (`start_all.bat`) |
| **No Python installed** | Docker (`docker-startup.bat`) |
| **Python already installed** | Local (`start_all.bat`) |

---

## Docker Commands (For Reference)

```batch
REM Start containers
docker-compose up -d

REM Stop containers
docker-compose down

REM View logs
docker-compose logs -f

REM Run CLI inside container
docker exec stgen python -m stgen.main --help

REM Run tests inside container
docker exec stgen python run_comparison_test.py

REM Rebuild image
docker-compose build

REM View container status
docker ps
```

---

## Troubleshooting

### Docker says "port already in use"
```batch
docker-compose down
docker-compose up -d
```

### Python script says "module not found"
You're mixing Docker and local Python. Choose ONE:
- **Use Docker**: Run `docker-startup.bat`
- **Use Local**: Install dependencies: `pip install -r requirements.txt`

### Docker not found
Install Docker Desktop: https://www.docker.com/products/docker-desktop

---

## System Architecture

```
STGen_Future_Present/
├── start_all.bat          ← Local Python setup
├── docker-startup.bat     ← Docker setup (RECOMMENDED)
├── docker-compose.yml     ← Container configuration
├── Dockerfile             ← Container image definition
├── stgen/                 ← Core framework
├── stgen-ui/              ← Web dashboard
└── protocols/             ← Protocol implementations
```

---

## Environment Comparison

| Aspect | Docker | Local |
|--------|--------|-------|
| Setup Time | ~2 min | ~5 min (install deps) |
| Isolation | ✅ Complete | ❌ Shared system |
| Reproducibility | ✅ Guaranteed | ⚠️ May vary |
| Debugging | ⚠️ Container shell | ✅ Direct IDE |
| Deployment | ✅ Direct to cloud | ⚠️ Manual setup |
| Dependencies | ✅ In container | ❌ System-wide |

---

## Questions?

See main README.md for complete documentation.
