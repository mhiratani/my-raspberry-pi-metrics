#!/bin/bash

# 現在のユーザー名を取得
CURRENT_USER=$(whoami)
METRICS_NAME="${METRICS_NAME}"
HOME_DIR="/home/$CURRENT_USER"
PROJECT_DIR="$HOME_DIR/my-raspberry-pi-metrics"
VENV_DIR="$PROJECT_DIR/venv"

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# systemdサービスファイルの内容
SERVICE_CONTENT="[Unit]
Description=Raspberry Pi Metrics About Temp And Fan Speed NewRelic
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/fan_and_temp_monitor.py

Restart=always
RestartSec=60
User=$CURRENT_USER
Group=$CURRENT_USER
Environment=PYTHONUNBUFFERED=1
WorkingDirectory=$PROJECT_DIR

[Install]
WantedBy=multi-user.target"

# systemdタイマーファイルの内容
TIMER_CONTENT="[Unit]
Description=Raspberry Pi Metrics About Temp And Fan Speed NewRelic Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min
Unit=fan-and-temp-monitor.service

[Install]
WantedBy=timers.target"

# スクリプトに実行権限を付与
chmod +x "$PROJECT_DIR/fan_and_temp_monitor.py"
echo -e "${GREEN}スクリプトに実行権限を付与しました。${NC}"

# .envファイルのパーミッション設定
chmod 600 "$PROJECT_DIR/.env"
echo -e "${GREEN}.envファイルのパーミッションを設定しました。${NC}"

# 仮想環境の確認と作成
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}仮想環境は既に存在します。${NC}"
    read -p "再作成しますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        echo -e "${GREEN}既存の仮想環境を削除しました。${NC}"
        python3 -m venv "$VENV_DIR"
        echo -e "${GREEN}新しい仮想環境を作成しました。${NC}"
    fi
else
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}仮想環境を作成しました。${NC}"
fi

# パッケージのインストール
echo -e "${GREEN}必要なパッケージをインストールしています...${NC}"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"
deactivate
echo -e "${GREEN}パッケージのインストールが完了しました。${NC}"

# systemdサービスファイルの作成
if [ -f "/etc/systemd/system/${METRICS_NAME}.service" ]; then
    echo -e "${YELLOW}systemdサービスファイルは既に存在します。${NC}"
    read -p "上書きしますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo bash -c "echo '$SERVICE_CONTENT' > /etc/systemd/system/${METRICS_NAME}.service"
        echo -e "${GREEN}systemdサービスファイルを更新しました。${NC}"
    fi
else
    sudo bash -c "echo '$SERVICE_CONTENT' > /etc/systemd/system/${METRICS_NAME}.service"
    echo -e "${GREEN}systemdサービスファイルを作成しました。${NC}"
fi

# systemdタイマーファイルの作成
if [ -f "/etc/systemd/system/${METRICS_NAME}.timer" ]; then
    echo -e "${YELLOW}systemdタイマーファイルは既に存在します。${NC}"
    read -p "上書きしますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo bash -c "echo '$TIMER_CONTENT' > /etc/systemd/system/${METRICS_NAME}.timer"
        echo -e "${GREEN}systemdタイマーファイルを更新しました。${NC}"
    fi
else
    sudo bash -c "echo '$TIMER_CONTENT' > /etc/systemd/system/${METRICS_NAME}.timer"
    echo -e "${GREEN}systemdタイマーファイルを作成しました。${NC}"
fi

echo -e "\n${GREEN}セットアップが完了しました。${NC}"
echo -e "1. ${YELLOW}$PROJECT_DIR/.env${NC} ファイルを編集して、NewRelicの情報を設定してください。"
echo -e "2. 以下のコマンドでサービスを有効化・開始してください："
echo -e "   ${YELLOW}sudo systemctl daemon-reload${NC}"
echo -e "   ${YELLOW}sudo systemctl enable ${METRICS_NAME}.timer${NC}"
echo -e "   ${YELLOW}sudo systemctl start ${METRICS_NAME}.timer${NC}"