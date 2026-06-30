# Protocol Template

This is a starting template for creating new protocol plugins.

## Steps to Create Your Protocol

1. Copy this directory:
```bash
   cp -r protocols/template protocols/my_protocol
```

2. Edit `my_protocol/template.py`:
   - Rename class if desired
   - Implement `start_server()`
   - Implement `start_clients()`
   - Implement `send_data()` (if active mode)
   - Implement `stop()`

3. Create config file:
```bash
   cp configs/template.json configs/my_protocol.json
```

4. Edit the config with your protocol name and parameters

5. Run test:
```bash
   python -m stgen.main configs/my_protocol.json
```

## Mode Selection

- **Active mode**: STGen calls `send_data()` for each packet
- **Passive mode**: Your binaries run autonomously, STGen monitors

Set `"mode": "active"` or `"mode": "passive"` in your config.