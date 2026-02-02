# Bin Scripts

Utility scripts for managing the Trender application.

## local_dev.py

Orchestrator script for local workflow development and testing.

### Quick Start

```bash
# Install dependencies first (if not already done)
pip install -r requirements.txt           # For bin scripts
pip install -r workflows/requirements.txt  # For workflow tasks
pip install -r trigger/requirements.txt    # For trigger script

# Or install all at once
pip install -r requirements.txt -r workflows/requirements.txt -r trigger/requirements.txt

# Run with one command
python bin/local_dev.py
```

### What It Does

1. ✅ Validates your `.env` configuration
2. ✅ Starts local task server on port 8120
3. ✅ Waits for server health check
4. ✅ Triggers workflow against local server
5. ✅ Streams logs from both processes
6. ✅ Graceful cleanup on Ctrl+C

### Usage Examples

```bash
# Default: Full workflow (server + trigger)
python bin/local_dev.py

# Server only (for manual testing)
python bin/local_dev.py --server-only

# Trigger only (assumes server already running)
python bin/local_dev.py --trigger-only

# Custom port
python bin/local_dev.py --port 8121

# Skip health check (start immediately)
python bin/local_dev.py --no-wait
```

### Requirements

- Render CLI v2.4.2+ (installed and configured)
- Python 3.8+
- Valid `.env` file with required variables:
  - `DATABASE_URL`
  - `GITHUB_ACCESS_TOKEN`
  - `RENDER_API_KEY`
  - `RENDER_WORKFLOW_SLUG`
  - `RENDER_USE_LOCAL_DEV=true`
  - `RENDER_LOCAL_DEV_URL=http://localhost:8120`

### Environment Variables

The script automatically loads variables from `.env` in the project root. See `env.example` for all configuration options.

**Key variables for local development:**

```bash
# Enable local dev mode
RENDER_USE_LOCAL_DEV=true
RENDER_LOCAL_DEV_URL=http://localhost:8120

# Optional: Faster testing
DEV_MODE=true
DEV_REPO_LIMIT=5
```

### Colored Output

The script uses ANSI colors to distinguish between different log sources:

- 🔵 **[SERVER]** - Task server logs (blue)
- 🟢 **[TRIGGER]** - Trigger process logs (green)
- ✓ Success messages (green)
- ✗ Error messages (red)
- ℹ Info messages (cyan)
- ⚠ Warning messages (yellow)

### Troubleshooting

**"Server appears to hang"**: This is normal! The task server runs indefinitely. Use Ctrl+C to stop.

**"Connection refused"**: Ensure no other process is using port 8120, or use `--port` to specify a different port.

**"Missing environment variables"**: Run the script to see which variables need configuration. Update your `.env` file.

**"Module not found"**: Install Python dependencies:
```bash
pip install -r requirements.txt -r workflows/requirements.txt -r trigger/requirements.txt
```

## db_setup.sh

Database initialization script. Sets up PostgreSQL schema for Trender.

```bash
./bin/db_setup.sh
```

## preview.sh

Preview script for testing the dashboard locally.

```bash
./bin/preview.sh
```

---

For more information, see [LOCAL_TESTING.md](../LOCAL_TESTING.md) in the project root.

