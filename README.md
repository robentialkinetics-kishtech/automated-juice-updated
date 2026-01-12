# ZKBot Juice Kiosk Controller v8

A complete Python-based control system for a 3-axis robotic arm that dispenses juice drinks. Features real-time manual jog control, program automation, order queue management, and serial communication with the robot hardware.

## 🎯 Features

- **Manual Jog Control** - Press-and-hold continuous movement on X, Y, Z axes with adjustable speed
- **Program Automation** - Record, save, and execute robot programs with step-by-step execution
- **Order Queue System** - Manage multiple drink orders with automatic execution
- **Real-time Monitoring** - Position display, E-stop status, progress tracking
- **Serial Communication** - Dual protocol support (Manual/Auto modes) via COM3
- **Teach Mode** - Record current positions and create programs by demonstration
- **Gripper Control** - Servo control for pick-and-place operations (DO0)

## 🔧 Hardware Requirements

- **Robot**: 3-axis robotic arm (ZKBot or compatible)
  - X-axis: -100 to +100 mm
  - Y-axis: -100 to +100 mm
  - Z-axis: 0 to +150 mm
- **Communication**: USB-to-Serial (CH340 chip) on COM3
- **Gripper**: Servo motor (0-180°)
- **E-stop Button**: Required for safety

## 📋 System Requirements

- Python 3.8+
- Windows 10/11 (tested)
- USB drivers for CH340 serial chip
- 50MB disk space (excluding virtual environment)

## ⚡ Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/robentialkinetics-kishtech/automated-juice-updated.git
cd automated-juice-updated
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Serial Port
Edit `config.py`:
```python
PORT = "COM3"  # Your robot's USB port
BAUD = 9600
```

### 5. Diagnose Connection
```bash
python diagnose_serial.py
```

### 6. Run Application
```bash
python gui.py
```

## 📖 Usage Guide

### Starting the Application
```bash
python gui.py
```

### Manual Jogging (Press & Hold)
1. Click **🕹️ Jog** button in Step Editor
2. Use directional buttons to move arm
3. Adjust **Jog Speed** slider (10-100%)
4. Release button to stop

### Creating a Program
1. Set coordinates: X, Y, Z, Feedrate (F), Delay
2. Click **Add** to add step
3. Click **Duplicate** to repeat step
4. Use **⬆ Up / ⬇ Down** to reorder steps
5. Click **Save** to save program

### Running a Program
1. Load program: **Open** button
2. Select execution mode:
   - **Normal**: Run all steps sequentially
   - **Step**: Run one step at a time with pause
3. Adjust speed override (50% = safe startup)
4. Click **Run Program**

### Order Queue
1. Click **Order** tab
2. Select juice flavor
3. Enter quantity
4. Add to queue
5. Click **Start Queue** to execute all orders

## 📁 Project Structure

```
zkbot_controller/
├── gui.py                    # Main GUI application
├── serial_comm.py           # Serial protocol layer
├── jog_control.py           # Manual jog control window
├── config.py                # Configuration (ports, limits)
├── models.py                # Data models (Step, Program)
├── order_queue.py           # Order management
├── order_runner.py          # Order execution
├── steps.py                 # Step definitions
├── diagnose_serial.py       # Serial port diagnostic tool
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── SETUP.md                # Detailed setup instructions
├── programs/               # Sample programs
│   ├── juices/
│   │   ├── orange.json
│   │   └── mango.json
│   ├── common/
│   │   └── pick_cup.json
│   └── orgin.json
└── images/                 # UI images
    ├── orange.jpeg
    ├── mango.jpeg
    └── lemon.jpeg
```

## 🔌 Serial Protocol

### Manual Mode (Jog Control)
```
Header:  0xff 0xfe
Command: 0x03-0x08 (X-, X+, Y-, Y+, Z-, Z+)
Speed:   F[value] (0-800)
Footer:  0xfd 0xfc
```

**Example**: Move X+ at speed 200
```
0xff 0xfe 0x04 F200 0xfd 0xfc
```

### Auto Mode (Program Execution)
```
Header:  0x550xAA
G-code:  G01 X[mm] Y[mm] Z[mm] F[mm/min]
Footer:  0xAA0x55
```

**Example**: Move to X10, Y20, Z50 at 200 mm/min
```
0x550xAA G01 X10 Y20 Z50 F200 0xAA0x55
```

## ⚙️ Configuration

### config.py
```python
# Serial Connection
PORT = "COM3"              # Robot USB port
BAUD = 9600               # Baud rate
TIMEOUT = 2               # Connection timeout (seconds)

# Workspace Limits
WORKSPACE_LIMITS = {
    'X': {'min': -100, 'max': 100},
    'Y': {'min': -100, 'max': 100},
    'Z': {'min': 0, 'max': 150}
}

# Speed Control
SPEED_OVERRIDE_PERCENT = 50  # Default startup speed (safe)
```

## 🐛 Troubleshooting

### Serial Port Errors
**Error**: `PermissionError: could not open port 'COM3'`

**Solution**:
1. Close Arduino IDE Serial Monitor
2. Close other terminal applications
3. Run `diagnose_serial.py` to verify port
4. Restart the application

### Port Not Found
**Error**: `FileNotFoundError: could not open port 'COM3'`

**Solution**:
1. Check USB cable connection
2. Open Device Manager (`Win + X` → Device Manager)
3. Look for "USB-SERIAL CH340" under Ports
4. Update port in `config.py`
5. Run `diagnose_serial.py` to find correct port

### Robot Not Responding
**Error**: No movement when pressing jog buttons

**Solution**:
1. Check E-stop button (must be released)
2. Verify USB connection
3. Run `diagnose_serial.py` to test communication
4. Check robot power supply
5. Verify config.py baud rate matches robot (usually 9600)

### Program Execution Stalls
**Solution**:
1. Ensure all steps have valid coordinates
2. Check feedrate (F) is between 1-500
3. Verify no workspace limit violations
4. Release E-stop if triggered

## 🛠️ Development

### Running Diagnostics
```bash
python diagnose_serial.py
```

Outputs:
- Available COM ports
- Port connectivity test
- Configuration verification
- Suggested fixes

### Code Structure

**serial_comm.py** - Hardware interface
- `open_port()` - Open USB connection
- `send_command()` - Send G-code to robot
- `query_position()` - Get current coordinates
- `StepExecutor` - Step-by-step execution

**jog_control.py** - Manual control
- `JogControlWindow` - Press-and-hold jog interface
- `continuous_move_loop()` - Smooth movement thread
- `send_protocol()` - Protocol command sender

**gui.py** - Main application
- Step editor (Add, Update, Delete)
- Program manager (Open, Save, Run)
- Order queue system
- Position monitoring

## 📦 Dependencies

```
pyserial==3.5           # Serial communication
pyperclip==1.8.2        # Clipboard support (optional)
```

See `requirements.txt` for full list.

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open Pull Request

## 📞 Support

For issues and questions:
1. Run `diagnose_serial.py` to check system status
2. Check [SETUP.md](SETUP.md) for detailed instructions
3. Review error logs in terminal output
4. Open an issue on GitHub with diagnostic output

## 🎯 Roadmap

- [ ] Network-based control (TCP/IP)
- [ ] Web interface dashboard
- [ ] Machine learning for motion optimization
- [ ] Collision detection system
- [ ] Multi-arm support
- [ ] ROS integration

## 📝 Changelog

### v8.0 (2026-01-12)
- ✅ Complete jog control with press-and-hold
- ✅ Order queue system
- ✅ Continuous movement with retry logic
- ✅ Serial port diagnostics
- ✅ Thread-safe program execution
- ✅ E-stop and safety mechanisms

## 👨‍💻 Author

**ZKBot Development Team**  
Robential Kinematics - Kishtech

---

**Last Updated**: January 12, 2026  
**Version**: 8.0  
**Status**: Production Ready ✅
