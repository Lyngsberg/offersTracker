#!/bin/bash
set -e # Stop script immediately if any command fails

# --- PART 1: AUTO-INSTALL BUILDX CLI (If missing) ---
# We check if 'docker buildx' works. If not, we download it automatically.
if ! docker buildx version > /dev/null 2>&1; then
    echo "❌ Buildx CLI plugin not found. Installing it now..."
    mkdir -p ~/.docker/cli-plugins
    # Download the binary (Using v0.12.0 which is stable)
    wget -q https://github.com/docker/buildx/releases/download/v0.12.0/buildx-v0.12.0.linux-amd64 -O ~/.docker/cli-plugins/docker-buildx
    chmod +x ~/.docker/cli-plugins/docker-buildx
    echo "✅ Buildx CLI installed."
else
    echo "✅ Buildx CLI is ready."
fi

# --- PART 2: SETUP BUILDER INSTANCE ---
# We look for a builder named 'armbuilder'. 
# If it exists, we use it. If not, we create it.
if ! docker buildx inspect armbuilder > /dev/null 2>&1; then
    echo "⚙️  Creating new builder: armbuilder..."
    docker buildx create --name armbuilder --use --driver docker-container
else
    echo "⚙️  Using existing builder: armbuilder"
    docker buildx use armbuilder
fi

# Ensure the builder is running
docker buildx inspect --bootstrap > /dev/null

# --- PART 3: ENABLE ARM EMULATION (QEMU) ---
# This fixes "exec format error" when building ARM on Intel
echo "🔧 Checking QEMU emulators..."
docker run --privileged --rm tonistiigi/binfmt --install all > /dev/null 2>&1

# --- PART 4: THE ACTUAL BUILD ---
echo "🚀 Starting Build for Linux/ARM64..."

docker buildx build \
  --platform linux/arm64 \
  -f Dockerfile_rema_scraper \
  -t lyngsberg/rema-scraper:latest \
  --push \
  .

echo "✅ Success! Image pushed to Docker Hub."