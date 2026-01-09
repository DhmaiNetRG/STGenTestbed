#  STGen Documentation Index

**Last Updated**: January 10, 2026  
**Project Status**:  Production Ready  
**Size**: 1.3 GB (cleaned)

---

##  Start Here

### New to STGen?
1. Read: [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) - Everything you need
2. Run: `./start_all.sh` (or appropriate for your OS)
3. Open: http://localhost:3000

### Want to Deploy?
1. Read: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) - 30-second setup
2. Run: `docker-compose up -d`
3. Or read: [DOCKER.md](DOCKER.md) - Advanced options

### Just Run It?
```bash
./start_all.sh          # Linux/macOS
start_all.bat           # Windows
docker-compose up -d    # Any OS
```

---

## 📚 Documentation by Category

### Getting Started (Read First)
| File | Purpose | Read Time |
|------|---------|-----------|
| **[COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** | Comprehensive overview & quick start | 10 min |
| **[README.md](README.md)** | Original project README | 5 min |
| **[DOXYGEN_MAINPAGE.h](DOXYGEN_MAINPAGE.h)** | API documentation mainpage | 5 min |

### Platform-Specific Setup
| File | Purpose | For Whom |
|------|---------|----------|
| **[STARTUP_COMMANDS.md](STARTUP_COMMANDS.md)** | All startup methods (Linux, macOS, Windows) | Everyone |
| **[WINDOWS_GUIDE.md](WINDOWS_GUIDE.md)** | Windows-specific setup & troubleshooting | Windows users |
| **[DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)** | Docker in 30 seconds | Docker users |

### Deployment & Production
| File | Purpose | When |
|------|---------|------|
| **[DOCKER.md](DOCKER.md)** | Advanced Docker + cloud deployment | Production |
| **[APKO_GUIDE.md](APKO_GUIDE.md)** | Distroless containers for security | Security-conscious |
| **[DOCKERFILE_vs_APKO.md](DOCKERFILE_vs_APKO.md)** | Container comparison & migration | Deciding between options |
| **[docker-compose.yml](docker-compose.yml)** | Docker orchestration config | Docker users |
| **[Dockerfile](Dockerfile)** | Standard Docker image | Docker users |
| **[apko.yaml](apko.yaml)** | Distroless image config | Security-focused |

### Code & Documentation
| File | Purpose | For Whom |
|------|---------|----------|
| **[PROJECT_CLEANUP_SUMMARY.md](PROJECT_CLEANUP_SUMMARY.md)** | What was cleaned & why | Developers |
| **[Doxyfile](Doxyfile)** | API docs configuration | Developers |
| **[DOXYGEN_MAINPAGE.h](DOXYGEN_MAINPAGE.h)** | API documentation content | Developers |

### Startup Scripts (Ready to Use)
| File | OS | Usage |
|------|----|----|
| **[start_all.sh](start_all.sh)** | Linux/macOS | `./start_all.sh` |
| **[start_all.bat](start_all.bat)** | Windows (cmd) | `start_all.bat` |
| **[start_all.ps1](start_all.ps1)** | Windows (PowerShell) | `powershell -ExecutionPolicy Bypass -File start_all.ps1` |
| **[docker-run.sh](docker-run.sh)** | Docker | `./docker-run.sh build` |

---

## 🔍 Find What You Need

### "How do I start STGen?"
- Linux/macOS: [STARTUP_COMMANDS.md](STARTUP_COMMANDS.md) → bash section
- Windows: [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md)
- Docker: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
- Everything: [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)

### "How do I deploy to production?"
- Local: [STARTUP_COMMANDS.md](STARTUP_COMMANDS.md)
- Docker: [DOCKER.md](DOCKER.md)
- AWS/Cloud: [DOCKER.md](DOCKER.md) → Cloud section
- Distroless: [APKO_GUIDE.md](APKO_GUIDE.md)

### "What network profiles are available?"
- [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) → Network Profiles section
- [configs/network_conditions/](configs/network_conditions/) → Configuration files

### "What sensors can I use?"
- [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) → Sensor Types section
- [stgen/sensor_generator.py](stgen/sensor_generator.py) → Code

### "What protocols are supported?"
- [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) → Supported Protocols section
- [protocols/](protocols/) → Implementation files

### "How do I use the CLI?"
- [STARTUP_COMMANDS.md](STARTUP_COMMANDS.md) → CLI Usage section
- [stgen/main.py](stgen/main.py) → `python stgen/main.py --help`

### "I'm on Windows, what do I do?"
- [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md) - Complete guide
- Or [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) - General guide

### "I want to use Docker"
- Quick: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
- Detailed: [DOCKER.md](DOCKER.md)
- vs Dockerfile: [DOCKERFILE_vs_APKO.md](DOCKERFILE_vs_APKO.md)

### "How do I troubleshoot?"
- [STARTUP_COMMANDS.md](STARTUP_COMMANDS.md) → Troubleshooting section
- [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md) → Troubleshooting section
- [DOCKER.md](DOCKER.md) → Troubleshooting section

---

## 📊 Project Statistics

```
Total Size:        1.3 GB (after cleanup)
Space Saved:       ~330 MB
Files Cleaned:     1000+
Documentation:     9 comprehensive guides
Code Comments:     Doxygen format on 8 core files
Startup Scripts:   6 (bash, batch, powershell, docker)
Supported OS:      Linux, macOS, Windows, Docker
```

---

## 🚀 Quick Command Reference

### Start Everything
```bash
./start_all.sh          # Linux/macOS
start_all.bat           # Windows cmd
pwsh -NoP -C "& start_all.ps1"  # Windows PowerShell
docker-compose up -d    # Docker
```

### Stop Everything
```bash
./stop_all.sh           # Linux/macOS
stop_all.bat            # Windows
docker-compose down     # Docker
```

### View Logs
```bash
tail -f logs/backend.log        # Backend (Linux/macOS)
type logs\backend.log           # Backend (Windows)
docker logs -f stgen-web-ui     # Docker
```

### Generate API Docs
```bash
doxygen Doxyfile
open docs/doxygen/html/index.html
```

---

## 🎯 Access Points (After Running)

| Service | URL | Purpose |
|---------|-----|---------|
| Web UI | http://localhost:3000 | Create & monitor experiments |
| REST API | http://localhost:8000 | Programmatic access |
| API Docs | http://localhost:8000/docs | Interactive documentation |
| Results | `./results/ui_experiments/` | Experiment data |

---

## 📚 Full Documentation Map

```
STGen_Future_Present/
│
├── 🎯 START HERE
│   ├── COMPLETE_GUIDE.md ..................... Everything you need
│   ├── README.md ............................ Original README
│   └── DOXYGEN_MAINPAGE.h ................... API docs mainpage
│
├── 🚀 QUICK START
│   ├── STARTUP_COMMANDS.md ................. All startup methods
│   ├── WINDOWS_GUIDE.md ................... Windows setup
│   ├── DOCKER_QUICKSTART.md ............... Docker in 30 sec
│   ├── start_all.sh ....................... Startup (Linux/macOS)
│   ├── start_all.bat ...................... Startup (Windows)
│   ├── start_all.ps1 ...................... Startup (PowerShell)
│   ├── stop_all.sh ........................ Shutdown (Linux/macOS)
│   ├── stop_all.bat ....................... Shutdown (Windows)
│   └── stop_all.ps1 ....................... Shutdown (PowerShell)
│
├── 🐳 DEPLOYMENT
│   ├── DOCKER.md .......................... Advanced Docker
│   ├── APKO_GUIDE.md ...................... Distroless containers
│   ├── DOCKERFILE_vs_APKO.md ............. Container comparison
│   ├── docker-compose.yml ................. Docker orchestration
│   ├── docker-compose.apko.yml ........... Apko orchestration
│   ├── Dockerfile ......................... Docker image
│   ├── apko.yaml .......................... Distroless image
│   └── docker-run.sh ...................... Docker helper
│
├── 📖 DOCUMENTATION
│   ├── PROJECT_CLEANUP_SUMMARY.md ......... Cleanup details
│   ├── Doxyfile ........................... API docs config
│   ├── DOXYGEN_MAINPAGE.h ................. API docs content
│   └── (this file) INDEX.md ............... Documentation index
│
├── 💻 CORE FILES (Doxygen-documented)
│   ├── stgen/main.py ..................... CLI entry point
│   ├── stgen/orchestrator.py ............. Test orchestration
│   ├── stgen/sensor_generator.py ......... Sensor data generation
│   ├── stgen/network_emulator.py ......... Network simulation
│   ├── stgen/metrics_collector.py ........ Metrics collection
│   ├── stgen/failure_injector.py ......... Failure injection
│   ├── stgen/validator.py ................ Validation
│   └── stgen-ui/backend/stgen_controller.py  Web UI controller
│
├── ⚙️ CONFIGURATION
│   ├── configs/ ........................... Configuration files
│   ├── configs/network_conditions/ ....... Network profiles
│   ├── configs/scenarios/ ................ Test scenarios
│   └── requirements.txt ................... Python dependencies
│
└── 🌐 WEB UI
    └── stgen-ui/
        ├── backend/ ....................... FastAPI server
        └── frontend/ ...................... React dashboard
```

---

## ✨ What's New

### Cleanup (330 MB freed)
- ✓ Removed duplicate `venv/` directory
- ✓ Removed `tttt/` playground
- ✓ Cleaned old logs and cache
- ✓ Removed .pyc files

### Documentation (9 files)
- ✓ Doxygen comments on 8 core files
- ✓ Comprehensive guides for every scenario
- ✓ Platform-specific instructions
- ✓ Complete API documentation structure

### Cross-Platform
- ✓ Works on Linux, macOS, Windows
- ✓ Docker option for any OS
- ✓ Distroless container option

---

## 🎓 Learn More

### About STGen
- Read: [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)
- Run: [STARTUP_COMMANDS.md](STARTUP_COMMANDS.md)
- Deploy: [DOCKER.md](DOCKER.md)

### About Code
- API Docs: Generate with `doxygen Doxyfile`
- Source: [stgen/](stgen/) directory
- Protocols: [protocols/](protocols/) directory

### About Containers
- Standard Docker: [DOCKER.md](DOCKER.md)
- Distroless: [APKO_GUIDE.md](APKO_GUIDE.md)
- Compare: [DOCKERFILE_vs_APKO.md](DOCKERFILE_vs_APKO.md)

---

## 🆘 Need Help?

| Question | Answer |
|----------|--------|
| How to start? | See [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) |
| Windows issues? | See [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md) |
| Docker questions? | See [DOCKER.md](DOCKER.md) |
| All startup methods? | See [STARTUP_COMMANDS.md](STARTUP_COMMANDS.md) |
| API documentation? | Run `doxygen Doxyfile` |
| Troubleshooting? | See Troubleshooting in relevant guide |

---

## 📞 Quick Links

- **Web UI**: http://localhost:3000 (after starting)
- **API Docs**: http://localhost:8000/docs (after starting)
- **GitHub**: (your repo)
- **Issues**: (your issues page)

---

**Ready to start? Go to [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** 🚀

*Documentation complete • Project cleaned • Production ready*
