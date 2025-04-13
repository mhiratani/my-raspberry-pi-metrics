import subprocess
import os
import re
import requests
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
LICENSE_KEY = os.getenv("LICENSE_KEY")

# 環境変数の検証
if not ACCOUNT_ID or not LICENSE_KEY:
    logger.error("環境変数 ACCOUNT_ID または LICENSE_KEY が設定されていません")
    exit(1)

EVENT_API_URL = f"https://insights-collector.newrelic.com/v1/accounts/{ACCOUNT_ID}/events"

# ホスト名取得
try:
    HOSTNAME = subprocess.check_output("hostname", shell=True).decode().strip()
except subprocess.SubprocessError as e:
    logger.error(f"ホスト名取得エラー: {e}")
    HOSTNAME = "unknown"

def get_temperature():
    """Raspberry Piの温度を取得"""
    try:
        temp_output = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        # 'temp=45.6'C' のような出力から数値部分を抽出
        match = re.search(r'temp=(\d+\.\d+)', temp_output)
        if match:
            return float(match.group(1))
        logger.warning("温度データのパターンが一致しませんでした")
        return None
    except Exception as e:
        logger.error(f"温度取得エラー: {e}")
        return None

def get_fan_speed():
    """ファンの回転数を取得"""
    try:
        # 指定されたパスからファン回転数を読み取る
        fan_path_pattern = "/sys/devices/platform/cooling_fan/hwmon/*/fan1_input"
        fan_paths = subprocess.check_output(f"ls {fan_path_pattern}", shell=True).decode().strip().split('\n')
        
        if fan_paths and len(fan_paths) > 0:
            with open(fan_paths[0], 'r') as f:
                return int(f.read().strip())
        
        logger.warning("ファン回転数のパスが見つかりませんでした")
        return None
    except subprocess.SubprocessError as e:
        logger.error(f"ファンパス検索エラー: {e}")
        return None
    except Exception as e:
        logger.error(f"ファン回転数取得エラー: {e}")
        return None

def send_to_newrelic(temp, fan_speed):
    """データをNewRelicに送信"""
    if temp is None and fan_speed is None:
        logger.warning("送信するデータがありません")
        return False
    
    timestamp = datetime.now().isoformat()
    
    # イベントデータの作成
    event_data = {
        "eventType": "TempAndFanMetrics",
        "timestamp": timestamp,
        "hostname": HOSTNAME
    }
    
    if temp is not None:
        event_data["temperature"] = temp
    
    if fan_speed is not None:
        event_data["fanSpeed"] = fan_speed
    
    # NewRelicにデータ送信
    headers = {
        "Content-Type": "application/json",
        "X-Insert-Key": LICENSE_KEY
    }
    
    try:
        response = requests.post(
            EVENT_API_URL,
            headers=headers,
            data=json.dumps([event_data])
        )
        
        if response.status_code == 200:
            logger.info(f"データ送信成功: {event_data}")
            return True
        else:
            logger.error(f"データ送信失敗: ステータスコード {response.status_code}, レスポンス: {response.text}")
            return False
    except Exception as e:
        logger.error(f"データ送信エラー: {e}")
        return False

def main():
    """メイン処理"""
    logger.info("メトリクス収集開始")
    temp = get_temperature()
    fan_speed = get_fan_speed()
    
    logger.info(f"温度: {temp}°C, ファン回転数: {fan_speed if fan_speed else '不明'} RPM")
    # NewRelicにデータ送信
    result = send_to_newrelic(temp, fan_speed)
    if not result:
        logger.warning("NewRelicへのデータ送信に失敗しました")

if __name__ == "__main__":
    main()