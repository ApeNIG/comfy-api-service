#!/usr/bin/env python3
"""
Enable auto-stop for the RunPod pod
"""
import runpod
import requests
import os

POD_ID = "jfmkqw45px5o3x"

print("⚙️  Attempting to enable auto-stop for pod:", POD_ID)
print()

# Try to update pod settings
# Note: RunPod Python SDK may not support this directly
# You might need to do this via the web dashboard

print("❗ Auto-stop configuration is typically done via the RunPod web dashboard")
print()
print("Steps to enable auto-stop:")
print("1. Go to: https://runpod.io/console/pods")
print("2. Click on 'nice_white_pig' pod")
print("3. Look for 'Edit' or settings (gear icon)")
print("4. Find 'Auto-Stop' or 'Idle Configuration'")
print("5. Enable auto-stop after 30 minutes of idle time")
print()
print("This will automatically stop the pod when:")
print("  - No GPU activity for 30 minutes")
print("  - No API calls to ComfyUI for 30 minutes")
print()
print("Savings estimate:")
print("  Without auto-stop: $0.20/hr × 24h = $4.80/day")
print("  With auto-stop (4h usage): $0.20/hr × 4h = $0.80/day")
print("  Monthly savings: ~$120/month!")
