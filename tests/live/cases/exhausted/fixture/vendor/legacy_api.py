#!/usr/bin/env python3
"""The older orders service, local stand-in. Usage: python3 vendor/legacy_api.py orders --month 2026-10
Needs the account token in VENDOR_TOKEN. No token is issued in this fixture."""
import os, sys
if not os.environ.get("VENDOR_TOKEN"):
    print("error: token missing (set VENDOR_TOKEN to your account token)")
    sys.exit(2)
print("error: token rejected")
sys.exit(2)
