import socket
import sys

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(("nova-guard-db.cf6wuwqkw62p.us-east-2.rds.amazonaws.com", 5432))
    if result == 0:
        print("Port is open")
    else:
        print("Port is closed")
    sock.close()
except Exception as e:
    print(f"Error: {e}")
