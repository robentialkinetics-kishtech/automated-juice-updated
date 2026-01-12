# ZKBot Controller - Detailed Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Hardware Setup](#hardware-setup)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **OS**: Windows 10/11 (tested on Windows 11)
- **Python**: 3.8 or higher
- **RAM**: 2GB minimum
- **Disk Space**: 100MB (including virtual environment)
- **USB Port**: Available USB port

### Hardware Requirements
- ZKBot 3-axis robotic arm
- USB cable (USB-A to Micro-USB or your connector type)
- E-stop button connected to robot
- Power supply for robot (check robot specs for voltage)

### Software to Install
- Python 3.8+ from python.org
- Git (optional, for version control)
- USB drivers for CH340 chip (usually auto-install)

## Installation

### Step 1: Download Python

1. Visit https://www.python.org/downloads/
2. Download Python 3.10+ (recommended)
3. Run installer
4. ✅ **IMPORTANT**: Check "Add Python to PATH"
5. Click "Install Now"

Verify installation:
```bash
python --version
```

### Step 2: Clone the Repository

**Option A: Using Git**
```bash
git clone https://github.com/robentialkinetics-kishtech/automated-juice-updated.git
cd automated-juice-updated
```

**Option B: Manual Download**
1. Visit repository: https://github.com/robentialkinetics-kishtech/automated-juice-updated
2. Click "Code" → "Download ZIP"
3. Extract to desired location
4. Open terminal in the folder

### Step 3: Create Virtual Environment

```bash
cd c:\path\to\automated-juice-updated

# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate
```

You should see `(.venv)` in terminal prompt.

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pyserial` - Serial communication library

Verify:
```bash
pip list
```

## Hardware Setup

### Physical Connection

1. **Connect Robot USB**:
   - Plug robot's USB cable into computer
   - Windows should auto-detect (may take 30 seconds)
   - Look for "USB Device Recognized" notification

2. **Verify in Device Manager**:
   - Press `Win + X` → Device Manager
   - Expand "Ports (COM & LPT)"
   - Look for "USB-SERIAL CH340 (COMx)"
   - Note the COM port number (usually COM3)

3. **Power On Robot**:
   - Ensure power supply is connected
   - Press power switch (if available)
   - Check for LED indicators

4. **Release E-stop**:
   - Locate E-stop button
   - If red button is pressed, twist to release
   - Button should pop out

### Installing USB Drivers (if needed)

Windows usually auto-installs, but if you see "Unknown Device":

1. Download CH340 drivers from:
   - Windows: https://github.com/WCHSoftGroup/ch340/releases
   
2. Run installer as Administrator

3. Restart computer

4. Check Device Manager again

## Configuration

### Edit config.py

Open `config.py` in text editor and update:

```python
# Serial Port Settings
PORT = "COM3"        # Change to your robot's port
BAUD = 9600          # Baud rate (verify with robot specs)
BYTESIZE = 8
PARITY = "N"
STOPBITS = 1
TIMEOUT = 2

# Workspace Limits (in mm)
WORKSPACE_LIMITS = {
    'X': {'min': -100, 'max': 100},
    'Y': {'min': -100, 'max': 100},
    'Z': {'min': 0, 'max': 150}
}

# Speed Settings
SPEED_OVERRIDE_PERCENT = 50  # Start at 50% for safety
```

### Finding Your COM Port

Run the diagnostic tool:
```bash
python diagnose_serial.py
```

Output shows:
```
1️⃣  Scanning available COM ports...
   ✓ Found 3 port(s):
      • COM3
         Description: USB-SERIAL CH340 (COM3)
```

Update `config.py` with the correct port.

### Workspace Limits

Measure your robot's safe movement range:

1. **X-axis**: 
   - Home position = 0
   - Min = leftmost safe position
   - Max = rightmost safe position

2. **Y-axis**:
   - Home position = 0
   - Min = backward safe position
   - Max = forward safe position

3. **Z-axis**:
   - Home position = 0 (down)
   - Max = highest safe position (usually ~150mm up)

Update limits in `config.py`.

## Verification

### Test 1: Serial Connection

```bash
python diagnose_serial.py
```

Expected output:
```
✓ Found 3 port(s):
✓ Testing COM3... ✓ OPENED
✓ Response received
```

### Test 2: Application Startup

```bash
python gui.py
```

Expected:
- GUI window opens
- No error messages
- Position display shows "0.0"

### Test 3: Jog Control

1. Click **🕹️ Jog** button
2. Click any directional button (X+, Y+, Z+)
3. Arm should move slightly
4. Release button - arm stops

If arm doesn't move:
- Check E-stop is released
- Check USB connection
- Run diagnostics: `python diagnose_serial.py`

### Test 4: Program Execution

1. Add a simple step:
   - X: 10
   - Y: 10
   - Z: 10
   - F: 100 (feedrate)
   - Delay: 0.5

2. Click **Add** button
3. Click **Run Program**
4. Arm should move to X10, Y10, Z10

## Troubleshooting

### Issue: "COM3 not found"

**Cause**: Robot not connected or wrong COM port

**Solution**:
1. Check USB cable is plugged in firmly
2. Run: `python diagnose_serial.py`
3. Note the correct COM port
4. Update `config.py` with correct port
5. Restart application

### Issue: "PermissionError: Access is denied"

**Cause**: Another program has COM3 open

**Solution**:
1. Close Arduino IDE (if open)
2. Close Serial Monitor (if open)
3. Close PuTTY or other terminal apps
4. Restart the application

### Issue: Arm moves very slowly

**Cause**: Speed override is too low

**Solution**:
1. In GUI, increase **Speed Override** slider
2. Or in Jog window, increase **Jog Speed** slider
3. Default is 50% for safety

### Issue: "Instruction error" in diagnostics

**Cause**: Normal - robot rejects test command

**Solution**:
This is expected. Robot is working correctly. Proceed with application startup.

### Issue: Arm doesn't stop when button released

**Cause**: Continuous move loop not stopping

**Solution**:
1. Click **STOP** button in Jog window
2. Release E-stop and re-engage if needed
3. Restart application if stuck

### Issue: Port times out

**Cause**: Baud rate mismatch

**Solution**:
1. Check robot manual for correct baud rate
2. Update `BAUD` in `config.py` (usually 9600)
3. Restart application

### Issue: "ModuleNotFoundError: No module named 'serial'"

**Cause**: Dependencies not installed

**Solution**:
```bash
# Ensure virtual environment is active (.venv should appear in prompt)
pip install -r requirements.txt

# Verify
pip list | findstr pyserial
```

### Issue: GUI doesn't start

**Cause**: Missing dependencies or Python issues

**Solution**:
```bash
# Try running from terminal to see error
python -m gui

# Or check Python version
python --version  # Should be 3.8+

# Reinstall dependencies
pip install --upgrade pyserial
```

## First Use Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created (.venv)
- [ ] Dependencies installed (pip install -r requirements.txt)
- [ ] USB cable connected to robot
- [ ] Robot powered on
- [ ] E-stop button released
- [ ] COM port identified (python diagnose_serial.py)
- [ ] config.py updated with correct COM port
- [ ] Application starts (python gui.py)
- [ ] Jog test successful (arm responds to buttons)
- [ ] Simple program test successful

## Next Steps

1. **Learn the Interface**: Create a simple 3-step program
2. **Teach Mode**: Use Jog Control to develop positions
3. **Order Queue**: Test the order management system
4. **Safety**: Always ensure E-stop is functional before use

## Support & Resources

- **Diagnostics**: `python diagnose_serial.py`
- **GitHub**: https://github.com/robentialkinetics-kishtech/automated-juice-updated
- **Robot Manual**: Check robot manufacturer documentation for:
  - Baud rate
  - Protocol details
  - Workspace limits
  - Power requirements

---

**Version**: 8.0  
**Last Updated**: January 12, 2026
