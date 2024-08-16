#!/bin/bash
set -e

# cd to script directory
cd "$(dirname "$0")"

sudo ln -s $(realpath ./lostbot.service) /etc/systemd/system/lostbot.service

sudo systemctl daemon-reload
sudo systemctl enable --now lostbot
sudo systemctl status lostbot
