# How to Run the Mock AHS Generator

## Quick Start (3 Steps)

### Step 1: Save the Generator Script

Save the mock AHS generator code as a file in your project:

**Location**: `Parser_Tool/scripts/mock_ahs_generator.py`

If the `scripts/` directory doesn't exist, create it:
```bash
mkdir scripts
```

Then paste the generator code into `scripts/mock_ahs_generator.py`

---

## Step 2: Run the Generator

### Option A: Run from Project Root (Recommended)

```bash
# Navigate to your project directory
cd Parser_Tool

# Run the generator script
python scripts/mock_ahs_generator.py
```

### Option B: Run with Python Module

```bash
cd Parser_Tool
python -m scripts.mock_ahs_generator
```

### Option C: Run on Windows PowerShell

```powershell
cd Parser_Tool
python.exe scripts/mock_ahs_generator.py
```

---

## Step 3: Verify Test Files Were Created

The script will output something like:

```
🔧 Mock AHS File Generator
==================================================

✓ Generating valid_demo.ahs...
  Created: tests/fixtures/valid_demo.ahs

✓ Generating with_faults_demo.ahs...
  Created: tests/fixtures/with_faults_demo.ahs

✓ Generating minimal.ahs...
  Created: tests/fixtures/minimal.ahs

==================================================
✅ Mock AHS files generated successfully!

Test files created in: tests/fixtures/

Usage:
  python -m ahsdp.cli --in tests/fixtures/valid_demo.ahs --out ./exports/report.md
  python run_app.py  # Launch GUI to test with generated files
```

**Check the files were created:**
```bash
ls -la tests/fixtures/
# or on Windows:
dir tests\fixtures\
```

You should see:
- `valid_demo.ahs` (50-100 KB)
- `with_faults_demo.ahs` (50-100 KB)
- `minimal.ahs` (1-2 KB)

---

## Now Test Your Parser

### Test with CLI:

```bash
# Test parsing the valid demo file
python -m ahsdp.cli --in tests/fixtures/valid_demo.ahs --out ./exports/report.md

# Check the output
cat ./exports/report.md
```

### Test with GUI:

```bash
# Launch the GUI
python run_app.py
```

Then in the GUI:
1. Click **Browse** next to "Input AHS Bundle"
2. Select `tests/fixtures/valid_demo.ahs`
3. Choose output location
4. Click **PARSE**
5. Verify report is generated

### Test with Fault Detection:

```bash
# Enable fault detection and parse file with faults
AHS_FAULTS=1 python -m ahsdp.cli --in tests/fixtures/with_faults_demo.ahs --out ./exports/faults_report.md
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'scripts'`

**Solution**: Make sure you're in the `Parser_Tool` directory:
```bash
cd Parser_Tool
python scripts/mock_ahs_generator.py
```

### Issue: `FileNotFoundError: [Errno 2] No such file or directory: 'tests/fixtures'`

**Solution**: The script creates the directory automatically, but if it fails:
```bash
mkdir -p tests/fixtures
python scripts/mock_ahs_generator.py
```

### Issue: Script runs but no files are created

**Solution**: Check permissions and disk space:
```bash
# Verify you can write to the directory
touch tests/fixtures/test.txt
rm tests/fixtures/test.txt

# Then try again
python scripts/mock_ahs_generator.py
```

### Issue: `Permission denied` on Linux/Mac

**Solution**: Make the script executable and run it:
```bash
chmod +x scripts/mock_ahs_generator.py
python scripts/mock_ahs_generator.py
```

---

## What Each Test File Does

| File | Purpose | Use Case |
|------|---------|----------|
| **valid_demo.ahs** | Normal, healthy ProLiant server | Test happy path, parsing works |
| **with_faults_demo.ahs** | Server with fault indicators | Test fault detection heuristics |
| **minimal.ahs** | Minimal ZIP structure | Test error handling for incomplete data |

---

## One-Time Setup: Create Script Shortcut (Optional)

### Windows (PowerShell)

Create a file `generate_test_data.ps1`:
```powershell
python scripts/mock_ahs_generator.py
```

Then run anytime with:
```powershell
.\generate_test_data.ps1
```

### Linux/Mac (Bash)

Create a file `generate_test_data.sh`:
```bash
#!/bin/bash
python scripts/mock_ahs_generator.py
```

Make it executable and run:
```bash
chmod +x generate_test_data.sh
./generate_test_data.sh
```

---

## Verify Installation Works End-to-End

Run this complete test sequence:

```bash
# 1. Generate test data
python scripts/mock_ahs_generator.py

# 2. Verify files exist
ls tests/fixtures/*.ahs

# 3. Test CLI parsing
python -m ahsdp.cli --in tests/fixtures/valid_demo.ahs --out ./exports/report.md

# 4. Verify report was created
cat ./exports/report.md

# 5. Launch GUI
python run_app.py
```

If all these steps complete without errors, your MVP testing environment is ready! ✅
