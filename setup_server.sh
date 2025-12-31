#!/bin/bash
set -e

# Kolory do komunikatów
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Rozpoczynam automatyczną instalację Gym Tracker...${NC}"

# 1. Aktualizacja systemu
echo -e "${BLUE}📦 Aktualizuję system i instaluję zależności...${NC}"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# 2. Tworzenie wirtualnego środowiska
echo -e "${BLUE}🐍 Konfiguruję środowisko Python...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Aktywacja venv i instalacja bibliotek
source venv/bin/activate
pip install -r requirements.txt

# 3. Konfiguracja Systemd (autostart)
echo -e "${BLUE}⚙️ Konfiguruję usługę systemową (autostart)...${NC}"
SERVICE_FILE=/etc/systemd/system/gym-tracker.service
CURRENT_DIR=$(pwd)
USER_NAME=$(whoami)

# Tworzenie pliku usługi
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Gym Tracker App
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$CURRENT_DIR
Environment="PATH=$CURRENT_DIR/venv/bin"
ExecStart=$CURRENT_DIR/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 app:app
Restart=always
RestartSec=10
RuntimeMaxSec=28800

[Install]
WantedBy=multi-user.target
EOF

# 4. Uruchomienie usługi
echo -e "${BLUE}🔥 Uruchamiam aplikację...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable gym-tracker
sudo systemctl restart gym-tracker

# 5. Otwarcie portu w firewallu systemu (netfilter-persistent)
if command -v ufw > /dev/null; then
    sudo ufw allow 5000
fi

echo -e "${GREEN}✅ Zakończono pomyślnie!${NC}"
echo -e "Aplikacja działa w tle."
echo -e "Możesz sprawdzić status komendą: ${BLUE}sudo systemctl status gym-tracker${NC}"
echo -e "Strona dostępna pod adresem: http://$(curl -s ifconfig.me):5000"
