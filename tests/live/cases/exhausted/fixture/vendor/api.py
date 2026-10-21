#!/usr/bin/env python3
"""The vendor's orders service, local stand-in. Usage: python3 vendor/api.py GET /v1/orders
Every endpoint needs the vendor-issued key in VENDOR_API_KEY. No key is issued in this fixture."""
import os, sys
key = os.environ.get("VENDOR_API_KEY")
if not key:
    print('HTTP 401\n{"error": "key required", "hint": "set VENDOR_API_KEY to the key issued by the vendor"}')
    sys.exit(1)
print('HTTP 403\n{"error": "invalid key"}')
sys.exit(1)
