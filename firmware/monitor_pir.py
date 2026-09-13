#!/usr/bin/env python3
import serial
import time
import sys

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
    print(f"Opening {port} at 115200 baud...")
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return

    print("=" * 60)
    print(" AgriVerde Live PIR & Sensor Monitor")
    print("=" * 60)
    print("Press Ctrl+C to stop.\n")

    last_pir_pin = None
    try:
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            # Highlight PIR events
            if "MOTION DETECTED" in line:
                print(f"\033[91;1m[!] {line}\033[0m", flush=True)
            elif "MOTION CLEARED" in line:
                print(f"\033[92;1m[✓] {line}\033[0m", flush=True)
            elif "[DIAG]" in line:
                # Check pin state
                if "Pin 14: 1" in line:
                    state_str = "\033[91mPin 14: HIGH (Object / Triggered)\033[0m"
                else:
                    state_str = "\033[92mPin 14: LOW (Clear / Idle)\033[0m"
                print(f"[DIAG] {state_str} | {line.split('|', 1)[-1].strip() if '|' in line else line}", flush=True)
            elif "PUMP" in line or "Live telemetry" in line or "Manual" in line:
                print(f"[*] {line}", flush=True)
    except KeyboardInterrupt:
        print("\nExiting monitor.")
    finally:
        ser.close()

if __name__ == '__main__':
    main()
