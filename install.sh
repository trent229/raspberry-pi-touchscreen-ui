#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/touchscreen-ui.desktop"

echo "Checking Python touchscreen dependencies..."
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3-tk
fi

python3 -m py_compile "$PROJECT_DIR/app.py"
mkdir -p "$AUTOSTART_DIR"

cat > "$AUTOSTART_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Touchscreen Control Center
Comment=Launch the touchscreen user interface
Exec=/usr/bin/python3 $PROJECT_DIR/app.py
Path=$PROJECT_DIR
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

chmod +x "$PROJECT_DIR/app.py"

echo "Installation complete."
echo "Run now with: python3 $PROJECT_DIR/app.py"
echo "The interface will start automatically at the next desktop login."
