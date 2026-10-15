#!/usr/bin/env python3
"""Compatibility shim: v2 moved the hooks; sessions started earlier still call this path. Fails open. Delete after the v2 merge."""
import sys
sys.exit(0)
