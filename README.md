# ラズベリーパイで通信速度をモニタリングしNewRelicでグラフ化するシステム

## セットアップ手順

### 1. プロジェクトディレクトリの作成

```bash
mkdir -p ~/speedtest
cd ~/speedtest
```

### 2. 通信速度測定スクリプトの作成

`speedtest_monitor.py`という名前で以下のスクリプトを作成します：

```python
#!/usr/bin/env python3
import subprocess
import json
import time
import requests
import datetime
import logging
import sys

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('speedtest_monitor')

# 起動メッセージ
logger.info("Speed test monitoring service started")

# NewRelicの設定
LICENSE_KEY = "あなたのNewRelicライセンスキー"
ACCOUNT_ID = "あなたのNewRelicアカウントID"
EVENT_API_URL = f"https://insights-collector.newrelic.com/v1/accounts/{ACCOUNT_ID}/events"

def run_speedtest():
    try:
        # speedtest-cliをJSON形式で実行
        logger.info("Starting speed test...")
        result = subprocess.run(['speedtest-cli', '--json'], capture_output=True, text=True)
        logger.info("Speed test completed, processing results...")
        data = json.loads(result.stdout)
        
        # 必要なデータを抽出
        download_speed = data['download'] / 1000000  # bpsをMbpsに変換
        upload_speed = data['upload'] / 1000000      # bpsをMbpsに変換
        ping = data['ping']
        
        return {
            "download_mbps": download_speed,
            "upload_mbps": upload_speed,
            "ping_ms": ping,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error running speedtest: {e}")
        return None

def send_to_newrelic(data):
    if not data:
        return
    
    # NewRelicのイベントデータ形式に変換
    event_data = {
        "eventType": "NetworkSpeedTest",
        "downloadSpeed": data["download_mbps"],
        "uploadSpeed": data["upload_mbps"],
        "pingLatency": data["ping_ms"],
        "timestamp": data["timestamp"]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Insert-Key": LICENSE_KEY
    }
    
    try:
        logger.info("Sending data to New Relic...")
        response = requests.post(EVENT_API_URL, headers=headers, json=[event_data])
        if response.status_code == 200:
            logger.info(f"Data sent to New Relic successfully: {data}")
        else:
            logger.error(f"Failed to send data: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending data to New Relic: {e}")

if __name__ == "__main__":
    while True:
        logger.info("Running speed test cycle...")
        speed_data = run_speedtest()
        send_to_newrelic(speed_data)
        logger.info(f"Waiting for next test cycle (30 seconds)...")
        time.sleep(30)  # 30秒ごとに実行（必要に応じて調整）
```

### 3. スクリプトの実行権限を設定

```bash
chmod +x ~/speedtest/speedtest_monitor.py
```

### 4. systemdサービスの設定

以下のコマンドでサービスファイルを作成します：

```bash
sudo nano /etc/systemd/system/speedtest-monitor.service
```

以下の内容を記述（ユーザー名を実際のものに置き換えてください）：

```
[Unit]
Description=Network Speed Test Monitor
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/ユーザー名/speedtest/speedtest_monitor.py
WorkingDirectory=/home/ユーザー名/speedtest
Restart=always
User=ユーザー名
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 5. サービスの有効化と起動

```bash
sudo systemctl daemon-reload
sudo systemctl enable speedtest-monitor
sudo systemctl start speedtest-monitor
```

### 6. サービスの状態確認

```bash
sudo systemctl status speedtest-monitor
```

## 動作確認

### ログの確認

```bash
sudo journalctl -u speedtest-monitor -f
```

### speedtest-cliの動作確認

```bash
speedtest-cli --json
```
注意: このコマンドは完了までに30秒〜1分程度かかることがあります。

## NewRelicでのダッシュボード設定

1. NewRelicのウェブインターフェースにログイン
2. 「Dashboards」→「Create a dashboard」を選択
3. 「Add a widget」→「NRQL」を選択
4. 以下のようなクエリを作成：

```sql
SELECT average(downloadSpeed), average(uploadSpeed) FROM NetworkSpeedTest TIMESERIES
```

5. ダッシュボードを保存して完了

## カスタマイズ

### 測定間隔の変更

スクリプト内の`time.sleep(30)`の値を変更することで、測定間隔を調整できます。例えば、5分ごとに測定する場合は`time.sleep(300)`とします。

変更後はサービスを再起動してください：

```bash
sudo systemctl restart speedtest-monitor
```

### アラートの設定

NewRelicのアラート機能を使用して、通信速度が特定の閾値を下回った場合に通知を受け取ることができます。

## トラブルシューティング

### サービスが起動しない場合

1. ユーザー名が正しいか確認：
```bash
whoami
```

2. パスが正しいか確認：
```bash
ls -l ~/speedtest/speedtest_monitor.py
```

3. ログを確認：
```bash
sudo journalctl -u speedtest-monitor
```

### データがNewRelicに表示されない場合

1. NewRelicのライセンスキーとアカウントIDが正しいか確認
2. スクリプトのログを確認して、データが正常に送信されているか確認
3. インターネット接続が正常か確認
