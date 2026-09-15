import subprocess
result = subprocess.run(['bluetoothctl', 'scan', 'on'], capture_output=True)
print(result)
