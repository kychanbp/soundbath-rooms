#!/bin/zsh
# Start the web server. On this Mac open http://localhost:8000. On a phone on the same Wi-Fi use this Mac's address.
echo "This Mac:  http://localhost:8000"
echo "Phone:     http://$(ipconfig getifaddr en0 || ipconfig getifaddr en1):8000"
python3 "$(dirname "$0")/scripts/serve.py" 8000
