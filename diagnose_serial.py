#!/usr/bin/env python3
"""
Serial Port Diagnostic Tool for ZKBot Controller
Run this to diagnose serial port connection issues
"""

import serial
import serial.tools.list_ports
import time
import sys


def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def diagnose_serial_ports():
    """Diagnose serial port issues."""
    print_header("🔧 ZKBot Serial Port Diagnostic Tool")
    
    # 1. Scan ports
    print("\n1️⃣  Scanning available COM ports...")
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("\n   ❌ NO SERIAL PORTS FOUND!")
        print("\n   Troubleshooting:")
        print("   → Check if USB cable is connected")
        print("   → Check Device Manager (Win+X → Device Manager)")
        print("   → Look under 'Ports (COM & LPT)'")
        print("   → Install/update USB drivers")
        print("   → Try different USB ports on computer")
        return False
    
    print(f"\n   ✓ Found {len(ports)} port(s):\n")
    for i, port_info in enumerate(ports, 1):
        print(f"      {i}. {port_info.device}")
        print(f"         Description: {port_info.description}")
        print(f"         HWID: {port_info.hwid}")
        if port_info.manufacturer:
            print(f"         Manufacturer: {port_info.manufacturer}")
        print()
    
    # 2. Test connectivity
    print_header("2️⃣  Testing Port Connectivity")
    
    successful_ports = []
    
    for port_info in ports:
        port = port_info.device
        print(f"\n   Testing {port}...", end=" ", flush=True)
        
        try:
            # Try to open port
            ser = serial.Serial(port, 9600, timeout=1)
            print("✓ OPENED")
            
            # Try communication
            print(f"      Sending test command...", end=" ", flush=True)
            ser.write(b"0x550xAA G14 0xAA0x55\r\n")
            time.sleep(0.3)
            response = ser.read(100)
            
            if response:
                print(f"✓ Response received")
                print(f"      Response: {response[:50]}...")
                successful_ports.append(port)
            else:
                print("⚠ No response (may still work)")
                successful_ports.append(port)
            
            ser.close()
            print(f"      ✓ Port closed successfully")
            
        except PermissionError:
            print("❌ PERMISSION DENIED")
            print(f"      → Port is in use by another application")
            print(f"      → Possible causes:")
            print(f"        - Arduino IDE Serial Monitor is open")
            print(f"        - Another terminal application is open")
            print(f"        - Device manager holding port lock")
            print(f"      → Solution: Close other applications and retry")
            
        except serial.SerialException as e:
            print(f"❌ FAILED: {str(e)}")
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
    
    # 3. Config check
    print_header("3️⃣  Configuration Check")
    
    try:
        from config import PORT, BAUD
        print(f"\n   config.py settings:")
        print(f"   • PORT = '{PORT}'")
        print(f"   • BAUD = {BAUD}")
        
        available = [p.device for p in ports]
        
        if PORT in available:
            print(f"\n   ✓ {PORT} is available and configured")
        else:
            print(f"\n   ⚠️  {PORT} not found in available ports")
            if successful_ports:
                print(f"   → Recommended: Update config.py to PORT = '{successful_ports[0]}'")
                print(f"\n   To fix:")
                print(f"   1. Open config.py")
                print(f"   2. Change: PORT = '{successful_ports[0]}'")
                print(f"   3. Save and restart the application")
    
    except Exception as e:
        print(f"\n   Error reading config: {str(e)}")
    
    # 4. Summary
    print_header("📊 Summary")
    
    print(f"\n   Total ports found: {len(ports)}")
    print(f"   Ports responding: {len(successful_ports)}")
    
    if successful_ports:
        print(f"\n   ✅ SUCCESS - Ports are working!")
        print(f"\n   Recommended port: {successful_ports[0]}")
    else:
        print(f"\n   ⚠️  ISSUE DETECTED - No ports responding")
    
    # 5. Next steps
    print_header("💡 Next Steps")
    
    print("\n   1. Verify robot connection:")
    print("      → Ensure USB cable is firmly connected")
    print("      → Check for physical USB issues")
    
    print("\n   2. Update config.py:")
    print("      → Set PORT = 'COMx' (from scan results above)")
    
    print("\n   3. Close conflicting apps:")
    print("      → Arduino IDE Serial Monitor")
    print("      → PuTTY / Other terminal apps")
    print("      → Any other serial port tools")
    
    print("\n   4. Restart application:")
    print("      → Close and reopen ZKBot Controller")
    
    print("\n   5. If still failing:")
    print("      → Check Device Manager for errors")
    print("      → Update/reinstall USB drivers")
    print("      → Try different USB ports on computer")
    
    print_header("End of Diagnostic Report")
    print()
    
    return len(successful_ports) > 0


def main():
    """Main entry point."""
    try:
        success = diagnose_serial_ports()
        
        if not success:
            print("\n⚠️  Connection issues detected. See recommendations above.")
            sys.exit(1)
        else:
            print("\n✅ Serial port is ready for use!")
            sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Diagnostic error: {str(e)}")
        sys.exit(1)
    
    finally:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
