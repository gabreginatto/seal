# Seal - Startup Guide

## What Went Wrong During Initial Startup Attempts

During the initial startup attempts, there were **4-5 failed attempts** due to Python module import issues. Here's what happened:

### Failed Attempts and Why They Failed:

1. **Attempt 1-2**: `python src/lacre/main_lacre.py`
   - **Error**: `ImportError: attempted relative import with no known parent package`
   - **Why**: Running the script directly caused Python to treat it as a standalone script, breaking relative imports like `from .config_lacre import ...`

2. **Attempt 3**: `python -m src.lacre.main_lacre`
   - **Error**: `ModuleNotFoundError: No module named 'config'`
   - **Why**: The module path was correct, but `config_lacre.py` tried to import `from config import ...` (looking for `/Users/.../Desktop/Code/Seal/src/config.py`), which requires proper Python path setup

3. **Attempt 4-5**: Various combinations with environment variables
   - **Issue**: Inconsistent working directory and Python path setup

### What Finally Worked:

**Attempt 6**: `python main.py --start-date 20251001 --end-date 20251031 --states SP --discovery-only`
- **Why it worked**:
  - `main.py` is the proper entry point that sets up Python path correctly
  - It adds `src/` to `sys.path` before importing: `sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))`
  - Must be run from the Seal root directory

## Root Cause Analysis

The project has a specific architecture:
```
Seal/
├── main.py                    # ✓ Correct entry point (sets up sys.path)
├── src/
│   ├── config.py             # Imported by config_lacre.py
│   ├── lacre/
│   │   ├── main_lacre.py     # ✗ Cannot be run directly (relative imports)
│   │   ├── config_lacre.py   # Imports from config (needs sys.path setup)
│   │   └── ...
```

**Key Lesson**: Always use `main.py` as the entry point, not the internal module files.

---

## How to Start the Script (3 Methods)

### Method 1: Using the Startup Script (RECOMMENDED)

The easiest and most reliable way:

```bash
cd /Users/gabrielreginatto/Desktop/Code/Seal
./run_lacre_discovery.sh --start-date 20251001 --end-date 20251031 --states SP --discovery-only
```

**Benefits**:
- Automatically sets working directory
- Validates credentials path
- Creates logs directory
- Provides clear PID and monitoring instructions
- Handles all path setup

### Method 2: Direct Python Command

If you need more control:

```bash
cd /Users/gabrielreginatto/Desktop/Code/Seal
export GOOGLE_APPLICATION_CREDENTIALS="/Users/gabrielreginatto/Desktop/Code/Seal/setup/pncp-key.json"
nohup python main.py --start-date 20251001 --end-date 20251031 --states SP --discovery-only > /tmp/seal_output.log 2>&1 &
echo "PID: $!"
```

**Important**:
- ✅ Must run from Seal directory
- ✅ Must use `python main.py` (not `python src/lacre/main_lacre.py`)
- ✅ Must set `GOOGLE_APPLICATION_CREDENTIALS`

### Method 3: Foreground Execution (for testing)

To see output in real-time:

```bash
cd /Users/gabrielreginatto/Desktop/Code/Seal
export GOOGLE_APPLICATION_CREDENTIALS="/Users/gabrielreginatto/Desktop/Code/Seal/setup/pncp-key.json"
python main.py --start-date 20251001 --end-date 20251031 --states SP --discovery-only
```

**Use this when**:
- Testing configuration changes
- Debugging issues
- Short test runs

---

## Common Arguments

```bash
--start-date YYYYMMDD          # Start date (e.g., 20251001 for Oct 1, 2025)
--end-date YYYYMMDD            # End date (e.g., 20251031 for Oct 31, 2025)
--states XX                    # State code (e.g., SP, RJ, MG) or comma-separated "SP,RJ,MG"
--discovery-only               # Only run discovery (don't process results)
```

### Examples:

```bash
# October 2025 for São Paulo (discovery only)
./run_lacre_discovery.sh --start-date 20251001 --end-date 20251031 --states SP --discovery-only

# Q4 2025 for multiple states
./run_lacre_discovery.sh --start-date 20251001 --end-date 20251231 --states "SP,RJ,MG"

# Full year 2025 for São Paulo
./run_lacre_discovery.sh --start-date 20250101 --end-date 20251231 --states SP
```

---

## Monitoring and Management

### Check if process is running:
```bash
ps aux | grep "python main.py"
```

### Monitor progress:
```bash
# Check the timestamped log from startup script
tail -f logs/seal_run_*.log

# Or check the main processing log
tail -f logs/pncp_lacre_*.log
```

### Check for rate limiting (should only show per-minute, NOT hourly):
```bash
grep "Rate limit" logs/pncp_lacre_*.log
# Should see: "Rate limit reached, sleeping for X seconds" where X <= 60
# Should NOT see: "Hourly rate limit reached, sleeping for 2394 seconds"
```

### Kill the process:
```bash
# Find PID
ps aux | grep "python main.py" | grep -v grep

# Kill it
kill <PID>
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'config'`
**Solution**: Make sure you're using `python main.py`, not `python src/lacre/main_lacre.py`

### Issue: `ImportError: attempted relative import`
**Solution**: Run from Seal directory and use `python main.py`

### Issue: Can't find credentials
**Solution**: Verify `setup/pncp-key.json` exists and `GOOGLE_APPLICATION_CREDENTIALS` is set

### Issue: Script sleeping for 40 minutes
**Solution**: This was fixed by removing artificial hourly rate limits from:
- `src/pncp_api.py` (lines 50-85)
- `src/lacre/optimized_lacre_discovery.py` (RateLimitTracker class)

The script now only has per-minute rate limiting (max 60-second sleep).

---

## Quick Reference Card

| Task | Command |
|------|---------|
| **Start Script** | `./run_lacre_discovery.sh --start-date 20251001 --end-date 20251031 --states SP --discovery-only` |
| **Check Status** | `ps aux \| grep "python main.py"` |
| **Monitor Logs** | `tail -f logs/pncp_lacre_*.log` |
| **Kill Process** | `kill <PID>` |
| **Test Run** | `python main.py --start-date 20251001 --end-date 20251031 --states SP --discovery-only` |

---

## Rate Limiting (Fixed)

✅ **Current (Correct)**:
- Per-minute rate limiting: 60 requests/minute
- Max sleep time: 60 seconds (rolling window)
- No artificial hourly limits

❌ **Previous (Incorrect)**:
- Had artificial hourly rate limit (1000 requests/hour)
- Would sleep for 2,394 seconds (~40 minutes)
- Not enforced by PNCP API (was artificial)

The PNCP API only has per-minute rate limiting, confirmed by the Medical project which runs all night without hourly limits.
