#!/bin/bash
set -e

# cd to script directory
cd "$(dirname "$0")"

sudo ln -sf $(realpath ./lostbot.service) /etc/systemd/system/lostbot.service

sudo systemctl daemon-reload
sudo systemctl enable --now lostbot
sudo systemctl status lostbot
