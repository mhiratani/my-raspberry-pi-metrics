import subprocess
import json
import requests
import os
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

def run_speedtest():
    """speedtestを実行して速度テスト結果を取得"""
    try:
        # speedtestをJSON形式で実行
        logger.info("速度テスト実行中...")
        result = subprocess.run(['speedtest', '-f', 'json'], capture_output=True, text=True, check=True)
        
        try:
            data = json.loads(result.stdout)
            
            # バンド幅をbyte/sからMbpsに変換 (byte/s ÷ 125000 = Mbps)
            download_speed = data['download']['bandwidth'] / 125000
            upload_speed = data['upload']['bandwidth'] / 125000
            ping = data['ping']['latency']
            
            logger.info(f"速度テスト完了: ダウンロード {download_speed:.2f} Mbps, アップロード {upload_speed:.2f} Mbps, Ping {ping:.2f} ms")
            
            jitter = data['ping']['jitter']
            packet_loss = data.get('packetLoss', 0)
            isp = data.get('isp', 'Unknown')
            
            return {
                "download_mbps": download_speed,
                "upload_mbps": upload_speed,
                "ping_ms": ping,
                "jitter_ms": jitter,
                "packet_loss": packet_loss,
                "isp": isp,
                "timestamp": datetime.now().isoformat(),
                "hostname": HOSTNAME
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            logger.debug(f"受信したデータ: {result.stdout}")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"speedtest実行エラー: {e}")
        if e.stderr:
            logger.error(f"エラー出力: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"速度テスト実行中の予期しないエラー: {e}")
        return None

def send_to_newrelic(data):
    """テスト結果をNewRelicに送信"""
    if not data:
        logger.warning("送信するデータがありません")
        return False
    
    # NewRelicのイベントデータ形式に変換
    event_data = {
        "eventType": "NetworkSpeedTest",
        "downloadSpeed": data["download_mbps"],
        "uploadSpeed": data["upload_mbps"],
        "pingLatency": data["ping_ms"],
        "jitter": data["jitter_ms"],
        "packetLoss": data["packet_loss"],
        "isp": data["isp"],
        "timestamp": data["timestamp"],
        "hostname": data["hostname"]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Insert-Key": LICENSE_KEY
    }
    
    try:
        response = requests.post(EVENT_API_URL, headers=headers, json=[event_data])
        if response.status_code == 200:
            logger.info("NewRelicへのデータ送信に成功しました")
            return True
        else:
            logger.error(f"データ送信失敗: ステータスコード {response.status_code}, レスポンス: {response.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"NewRelicへのリクエストエラー: {e}")
        return False
    except Exception as e:
        logger.error(f"NewRelicへのデータ送信中の予期しないエラー: {e}")
        return False

def main():
    """メイン処理"""
    logger.info("ネットワーク速度テスト開始")
    speed_data = run_speedtest()
    
    if speed_data:
        result = send_to_newrelic(speed_data)
        if result:
            logger.info("処理が正常に完了しました")
        else:
            logger.warning("NewRelicへのデータ送信に失敗しました")
    else:
        logger.error("速度テストの実行に失敗しました")
    
    logger.info("ネットワーク速度テスト終了")

if __name__ == "__main__":
    main()