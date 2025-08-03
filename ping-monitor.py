import subprocess
import requests
import platform
import socket # ホスト名を取得するために追加
import os
from dotenv import load_dotenv
# 環境変数の読み込み
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_TO_ID = os.getenv("LINE_TO_ID")
LINE_API_URL = os.getenv("LINE_API_URL")

TARGET_IP = "192.168.30.4" # 監視対象のIPアドレス

def get_hostname():
    """現在のホスト名を取得します。"""
    return socket.gethostname()

def send_line_message(message_text):
    """
    LINE Messaging APIを使用してメッセージを送信します。
    ホスト名をメッセージに含めます。
    """
    hostname = get_hostname()
    full_message_text = f"[{hostname}] {message_text}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_TO_ID,
        "messages": [
            {
                "type": "text",
                "text": full_message_text
            }
        ]
    }
    try:
        response = requests.post(LINE_API_URL, headers=headers, json=payload)
        response.raise_for_status() # HTTPエラーが発生した場合に例外を発生させる
        print(f"LINEメッセージ送信結果: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"LINEメッセージ送信エラー: {e}")

def check_ping(ip_address):
    """
    指定されたIPアドレスへのPingを実行し、成否を返します。
    OSによってPingコマンドのオプションを調整します。
    """
    param = '-n 1' if platform.system().lower() == 'windows' else '-c 1'
    command = ['ping', param, ip_address]

    try:
        # Pingコマンドを実行し、出力をキャプチャ
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        # returncodeが0なら成功
        if result.returncode == 0:
            print(f"{ip_address} へのPingは成功しました。")
            return True
        else:
            print(f"{ip_address} へのPingは失敗しました。")
            print(f"Ping出力:\n{result.stdout}\n{result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"{ip_address} へのPingがタイムアウトしました。")
        return False
    except Exception as e:
        print(f"Ping実行中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    if not check_ping(TARGET_IP):
        message = f"{TARGET_IP} へのPingが失敗しました。ネットワーク接続を確認してください。"
        send_line_message(message)
    else:
        # Ping成功時には特に通知しないが、必要であればここにもメッセージ送信を追加できる
        pass
