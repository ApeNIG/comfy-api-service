# Windows Cleanup Guide - Remove ComfyUI API Service Files

**What you downloaded:** Docker images, models, and cached data totaling ~**53GB**

---

## 📊 What's Taking Up Space

Based on your system scan:

| Item | Size | Location |
|------|------|----------|
| **ComfyUI Models** | 4.27 GB | Docker volume |
| **ComfyUI Image** | 23.8 GB | Docker image |
| **API/Worker Images** | 440 MB each | Docker images |
| **Build Cache** | 5.71 GB | Docker cache |
| **Dev Container** | 24.7 GB | VSCode dev container |
| **Other Images** | ~16 GB | CUDA, Redis, MinIO, etc. |
| **Total** | ~53 GB | |

---

## 🧹 Cleanup Options

### Option 1: Remove Everything (Recommended - Frees ~53GB)

Run these commands in **PowerShell** (as Administrator):

```powershell
# Navigate to project directory
cd C:\Users\sibag\desktop\BUILD\comfy-api-service

# Stop all running containers
docker compose down

# Remove ALL Docker data (images, containers, volumes, networks, cache)
docker system prune -a --volumes

# When prompted, type: y
```

**What this removes:**
- ✅ All Docker images (~40GB)
- ✅ ComfyUI models (4.27GB)
- ✅ All containers
- ✅ All volumes (Redis data, MinIO data, models)
- ✅ Build cache (5.71GB)
- ✅ Unused networks

**What this keeps:**
- ✅ Your source code
- ✅ Git repository
- ✅ .env file
- ✅ Documentation

---

### Option 2: Keep System, Remove Project Only (Frees ~30GB)

If you want to keep Docker for other projects:

```powershell
cd C:\Users\sibag\desktop\BUILD\comfy-api-service

# Stop and remove containers
docker compose down -v

# Remove project images only
docker rmi comfy-api-service-worker comfy-api-service-api comfy-api-service-comfyui

# Remove project volumes
docker volume rm comfy-api-service_comfyui_models
docker volume rm comfy-api-service_comfyui_output
docker volume rm comfy-api-service_minio_data
docker volume rm comfy-api-service_redis_data
docker volume rm comfy-api-service_minio_dev_data
docker volume rm comfy-api-service_redis_dev_data
```

---

### Option 3: Remove Models Only (Frees 4.27GB)

If you want to keep the system but just remove the big model files:

```powershell
# Remove the models volume
docker volume rm comfy-api-service_comfyui_models
```

---

## 📂 Where Files Are Stored on Windows

Docker stores everything in a virtual disk on Windows:

### WSL2 Backend (Most Common)
```
Location: C:\Users\sibag\AppData\Local\Docker\wsl\data\ext4.vhdx
Type: Virtual Hard Disk
What's inside: All Docker images, containers, volumes
```

This is a **single file** that contains everything Docker-related.

### Specific Locations:

1. **Docker Images & Containers:**
   - Stored inside: `ext4.vhdx` virtual disk
   - Not directly accessible from Windows Explorer

2. **ComfyUI Models (4.27GB):**
   - Docker Volume: `comfy-api-service_comfyui_models`
   - Inside: `ext4.vhdx` → `/var/lib/docker/volumes/comfy-api-service_comfyui_models/_data`
   - File: `v1-5-pruned-emaonly.safetensors` (4GB)

3. **Redis/MinIO Data:**
   - Docker Volumes: `comfy-api-service_redis_data`, `comfy-api-service_minio_data`
   - Inside: `ext4.vhdx`

4. **Build Cache (5.71GB):**
   - Inside: `ext4.vhdx` → `/var/lib/docker/buildx/cache`

5. **Your Source Code:**
   - `C:\Users\sibag\desktop\BUILD\comfy-api-service\` ← This is safe!

---

## 🔍 Files You Likely Downloaded via PowerShell

Based on typical setup, you probably downloaded:

### 1. Docker Images (via `docker pull` or `docker compose up`)
```powershell
# These were downloaded automatically:
ghcr.io/ai-dock/comfyui:latest          # 4.22 GB
nvidia/cuda:12.8.1-cudnn-devel          # 16.4 GB
redis:7-alpine                          # 60.7 MB
minio/minio:latest                      # 241 MB
python:3.11-slim                        # 213 MB (for API/Worker)

# Total: ~21 GB downloaded from internet
```

### 2. ComfyUI Model (auto-downloaded on first run)
```
Model: v1-5-pruned-emaonly.safetensors
Size: 4.0 GB
Downloaded to: Docker volume comfyui_models
```

### 3. Python Dependencies (via Poetry/pip)
```
Location: Inside Docker images
Size: ~500 MB (FastAPI, Redis, etc.)
```

---

## ✅ Recommended Cleanup Steps

**If you want to start fresh:**

```powershell
# 1. Open PowerShell as Administrator
# 2. Navigate to project
cd C:\Users\sibag\desktop\BUILD\comfy-api-service

# 3. Stop everything
docker compose down

# 4. Remove everything Docker (NUCLEAR OPTION)
docker system prune -a --volumes

# Confirm with: y

# 5. (Optional) Remove project folder
cd ..
rmdir /s comfy-api-service
```

**What you'll free up:**
- ~53 GB of disk space
- All Docker images and containers
- All cached build layers
- All volumes with data

**What survives:**
- If you keep the project folder:
  - ✅ Source code
  - ✅ Git history
  - ✅ Documentation
  - ✅ Configuration files

---

## 🎯 Quick Commands Reference

### Check what's using space
```powershell
docker system df -v
```

### See all volumes
```powershell
docker volume ls
```

### See volume size
```powershell
docker system df -v | findstr comfyui
```

### Remove specific volume
```powershell
docker volume rm <volume_name>
```

### Remove all unused images
```powershell
docker image prune -a
```

### Remove all unused volumes
```powershell
docker volume prune
```

### Remove build cache
```powershell
docker builder prune -a
```

---

## ⚠️ Important Notes

1. **Before cleanup:** Make sure you've committed any important changes to Git
   ```powershell
   git status
   git add .
   git commit -m "Save my work"
   git push
   ```

2. **Docker Desktop:** After cleanup, you might need to restart Docker Desktop

3. **WSL2 Disk:** After removing Docker data, the `ext4.vhdx` file might not shrink immediately. To reclaim space:
   ```powershell
   # Shut down WSL
   wsl --shutdown

   # Compact the disk (in PowerShell as Admin)
   Optimize-VHD -Path "C:\Users\sibag\AppData\Local\Docker\wsl\data\ext4.vhdx" -Mode Full
   ```

4. **Keep your code!** The cleanup commands above only remove Docker data, not your source code in `C:\Users\sibag\desktop\BUILD\comfy-api-service\`

---

## 🔄 If You Want to Start Over Later

After cleanup, to rebuild:

```powershell
cd C:\Users\sibag\desktop\BUILD\comfy-api-service
docker compose up -d
```

Everything will be re-downloaded and rebuilt automatically (~10-15 minutes).

---

## ❓ Need Help?

If something goes wrong:
1. Check Docker Desktop is running
2. Check WSL2 is running: `wsl --status`
3. Restart Docker Desktop
4. Restart your computer

---

**Summary:** Run `docker system prune -a --volumes` to remove everything (~53GB) while keeping your source code safe.
