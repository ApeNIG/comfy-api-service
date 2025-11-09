#!/usr/bin/env python3
"""
Manage RunPod pod - Start, Stop, and Check Status

Usage:
    python manage_runpod.py stop
    python manage_runpod.py start
    python manage_runpod.py status
"""

import sys
import json
import subprocess
from pathlib import Path

POD_ID = "jfmkqw45px5o3x"
API_KEY_FILE = Path.home() / ".runpod" / "config.toml"

def get_api_key():
    """Read API key from RunPod config"""
    if not API_KEY_FILE.exists():
        print("❌ RunPod config not found. Please run: runpod config")
        sys.exit(1)

    with open(API_KEY_FILE) as f:
        for line in f:
            if "api_key" in line:
                return line.split('"')[1]

    print("❌ API key not found in config")
    sys.exit(1)

def graphql_query(query):
    """Execute GraphQL query against RunPod API"""
    api_key = get_api_key()

    cmd = [
        "curl", "-s", "-X", "POST",
        "https://api.runpod.io/graphql",
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {api_key}",
        "-d", json.dumps({"query": query})
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Request failed: {result.stderr}")
        sys.exit(1)

    return json.loads(result.stdout)

def stop_pod():
    """Stop the pod"""
    print(f"🛑 Stopping pod {POD_ID}...")

    query = f'mutation {{ podStop(input: {{podId: "{POD_ID}"}}) {{ id desiredStatus }} }}'
    result = graphql_query(query)

    if "errors" in result:
        print(f"❌ Error: {result['errors']}")
        sys.exit(1)

    pod = result["data"]["podStop"]
    print(f"✅ Pod stopped!")
    print(f"   Status: {pod['desiredStatus']}")
    print(f"\n💰 Pod is now stopped and not billing")

def start_pod():
    """Start the pod"""
    print(f"▶️  Starting pod {POD_ID}...")

    query = f'mutation {{ podResume(input: {{podId: "{POD_ID}", gpuCount: 1}}) {{ id desiredStatus }} }}'
    result = graphql_query(query)

    if "errors" in result:
        print(f"❌ Error: {result['errors']}")
        sys.exit(1)

    pod = result["data"]["podResume"]
    print(f"✅ Pod starting...")
    print(f"   Status: {pod['desiredStatus']}")
    print(f"\n⏳ Wait ~1-2 minutes for pod to boot up")
    print(f"💡 Check status with: python {__file__} status")

def check_status():
    """Check pod status"""
    query = f'query {{ pod(input: {{podId: "{POD_ID}"}}) {{ id name desiredStatus runtime {{ uptimeInSeconds }} }} }}'
    result = graphql_query(query)

    if "errors" in result:
        print(f"❌ Error: {result['errors']}")
        sys.exit(1)

    pod = result["data"]["pod"]

    print(f"\n{'='*60}")
    print(f"Pod Status: {pod['name']}")
    print(f"{'='*60}")
    print(f"ID: {pod['id']}")
    print(f"Status: {pod['desiredStatus']}")

    if pod['runtime']:
        uptime = pod['runtime']['uptimeInSeconds']
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        print(f"Uptime: {hours}h {minutes}m")
    else:
        print(f"Uptime: Stopped")

    print(f"{'='*60}\n")

    if pod['desiredStatus'] == 'RUNNING':
        print("✅ Pod is RUNNING")
        print("💰 Pod is billing")
        print("\n🔗 ComfyUI URL: https://jfmkqw45px5o3x-8188.proxy.runpod.net")
        print("\n💡 Test connection:")
        print("   docker exec comfyui-api curl -s http://localhost:8000/health | python -m json.tool")
    elif pod['desiredStatus'] == 'EXITED':
        print("🛑 Pod is STOPPED")
        print("💰 Pod is NOT billing")
        print(f"\n💡 Start with: python {__file__} start")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['start', 'stop', 'status']:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    if action == 'stop':
        stop_pod()
    elif action == 'start':
        start_pod()
    elif action == 'status':
        check_status()

if __name__ == "__main__":
    main()
