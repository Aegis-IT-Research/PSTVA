#!/bin/zsh

# Setup Script for Aegis Security Assessment Toolkit

# Exit on error
set -e

# Step 1: Install docker

if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    sudo apt update && sudo apt install -y docker.io
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Installing Docker Compose..."
    sudo apt update && sudo apt install -y docker-compose
fi

# Check if user has Docker permissions
if ! groups | grep -q '\bdocker\b'; then
    echo "Adding user to the Docker group for permissions..."
    sudo usermod -aG docker $USER
    echo "Please log out and log back in for Docker group changes to take effect, or run this script with sudo."
    exit 1
fi

# Setup completed
echo "Setup completed successfully."
