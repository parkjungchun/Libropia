"""
의왕시내손도서관 제1열람실 좌석 현황 자동 체크 스크립트 (GitHub Actions + 텔레그램용)
--------------------------------------------------------------------------
- SeatMate3 페이지에서 현재 좌석 현황을 읽어와 텔레그램으로 알림을 보내고,
  seat_log.csv에 기록을 남기고, dashboard.html도 갱신합니다.
- 실행 자체는 GitHub Actions가 클라우드에서 스케줄대로 자동 실행해줘서
  내 컴퓨터를 켜둘 필요가 없습니다. (.github/workflows/check-seats.yml 참고)

필요한 값 (GitHub 저장소 Secrets에 등록):
  TELEGRAM_BOT_TOKEN : 텔레그램 봇 토큰
  TELEGRAM_CHAT_ID   : 알림 받을 chat id

동작 방식:
  - 메시지마다 "🔕 그만 받기" 버튼이 붙어서 나갑니다.
  - 버튼을 누르면 그 순간부터 알림이 중지되고, "▶️ 다시 받고싶어요" 버튼이 있는 메시지가 옵니다.
  - 그 버튼을 누르면 알림이 재개됩니다 (응답 안 하면 계속 받는 게 기본값).
  - 이 상태(중지 여부)는 state.json에 저장되고, 실행할 때마다 커밋되어 유지됩니다.

필요 패키지: pip install requests beautifulsoup4
"""

import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

KST = ZoneInfo("Asia/Seoul")


def now_kst():
    return datetime.now(KST)


# ---- 설정 ----
SEAT_URL = "http://118.223.243.11:8800/SeatMate3/SeatMate.php?classInfo=1"  # 제1열람실
ROOM_NAME = "제1열람실"
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "seat_log.csv"
DASHBOARD_FILE = BASE_DIR / "dashboard.html"
STATE_FILE = BASE_DIR / "state.json"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def fetch_seat_counts():
    """좌석현황 페이지에서 전체/이용중/이용가능 좌석수를 가져온다."""
    resp = requests.get(SEAT_URL, timeout=10)
    resp.encoding = "cp949"  # 이 사이트는 EUC-KR(CP949)로 인코딩되어 있음
    soup = BeautifulSoup(resp.text, "html.parser")

    def last_number_after(img_keyword):
        # img src에 img_keyword가 포함된 태그 뒤에 나오는 '숫자만 있는' 텍스트를 찾는다.
        # 상단 범례 아이콘에는 숫자가 없고, 실제 데이터 영역 아이콘 뒤에만 숫자가 붙어있어서
        # 여러 개가 잡히면 마지막 값(실제 데이터)을 사용한다.
        candidates = []
        for img in soup.find_all("img", src=re.compile(img_keyword, re.I)):
            for sib in img.find_all_next(limit=6):
                text = sib.get_text(strip=True)
                if text.isdigit():
                    candidates.append(int(text))
                    break
        return candidates[-1] if candidates else None

    total = last_number_after("Itotal")
    using = last_number_after("Iusing")
    available = last_number_after("Iusecan")

    if available is None:
        raise RuntimeError("좌석 정보를 파싱하지 못했습니다. 사이트 구조가 바뀌었을 수 있습니다.")

    return total, using, available


def append_log(total, using, available):
    is_new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "room", "total", "using", "available"])
        writer.writerow(
            [now_kst().strftime("%Y-%m-%d %H:%M:%S"), ROOM_NAME, total, using, available]
        )


def read_today_log():
    if not LOG_FILE.exists():
        return []
    today = now_kst().strftime("%Y-%m-%d")
    rows = []
    with LOG_FILE.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["timestamp"].startswith(today):
                rows.append(row)
    return rows


def build_dashboard():
    rows = read_today_log()
    labels = [r["timestamp"][11:16] for r in rows]
    available = [r["available"] for r in rows]
    table_rows = "".join(
        f"<tr><td>{r['timestamp'][11:16]}</td><td>{r['total']}</td>"
        f"<td>{r['using']}</td><td>{r['available']}</td></tr>"
        for r in rows
    )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{ROOM_NAME} 좌석 현황</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  body {{ font-family: 'Apple SD Gothic Neo', sans-serif; max-width: 700px; margin: 40px auto; padding: 0 16px; color:#222; }}
  h1 {{ font-size: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 24px; font-size: 14px; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: center; }}
  th {{ background: #f4f4f4; }}
  .updated {{ color: #888; font-size: 13px; margin-top: 4px; }}
</style>
</head>
<body>
  <h1>{ROOM_NAME} 이용가능 좌석수 (오늘)</h1>
  <p class="updated">마지막 갱신: {now_kst().strftime('%Y-%m-%d %H:%M:%S')}</p>
  <canvas id="chart" height="220"></canvas>
  <table>
    <tr><th>시간</th><th>전체</th><th>이용중</th><th>이용가능</th></tr>
    {table_rows}
  </table>
  <script>
    new Chart(document.getElementById('chart'), {{
      type: 'line',
      data: {{
        labels: {labels},
        datasets: [{{
          label: '이용가능 좌석수',
          data: {available},
          borderColor: '#2b8a3e',
          backgroundColor: 'rgba(43,138,62,0.15)',
          fill: true,
          tension: 0.2
        }}]
      }},
      options: {{ scales: {{ y: {{ beginAtZero: true }} }} }}
    }});
  </script>
</body>
</html>"""
    DASHBOARD_FILE.write_text(html, encoding="utf-8")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"offset": 0, "paused": False}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_pause_state(state):
    """봇에게 온 새 메시지/버튼 클릭을 확인해서 중지/재개 상태를 갱신한다."""
    if not TELEGRAM_BOT_TOKEN:
        return state
    resp = requests.get(
        f"{API_BASE}/getUpdates", params={"offset": state["offset"], "timeout": 0}, timeout=10
    )
    updates = resp.json().get("result", [])

    for update in updates:
        state["offset"] = update["update_id"] + 1

        callback = update.get("callback_query")
        if callback and callback.get("data") == "stop":
            state["paused"] = True
            requests.post(
                f"{API_BASE}/answerCallbackQuery",
                data={"callback_query_id": callback["id"], "text": "알림을 중지했어요."},
                timeout=10,
            )
            resume_markup = {
                "inline_keyboard": [[{"text": "▶️ 다시 받고싶어요", "callback_data": "resume"}]]
            }
            requests.post(
                f"{API_BASE}/sendMessage",
                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": "알림을 중지했어요. 다시 받고 싶을 때 아래 버튼을 눌러주세요.",
                    "reply_markup": json.dumps(resume_markup),
                },
                timeout=10,
            )

        if callback and callback.get("data") == "resume":
            state["paused"] = False
            requests.post(
                f"{API_BASE}/answerCallbackQuery",
                data={"callback_query_id": callback["id"], "text": "알림을 다시 시작할게요."},
                timeout=10,
            )
            requests.post(
                f"{API_BASE}/sendMessage",
                data={"chat_id": TELEGRAM_CHAT_ID, "text": "알림을 다시 시작할게요."},
                timeout=10,
            )

    return state


def send_telegram(total, using, available):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("텔레그램 설정(TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)이 없어 알림을 건너뜁니다.")
        return
    now = now_kst().strftime("%Y-%m-%d %H:%M")
    text = (
        f"📚 {ROOM_NAME} 좌석 현황 ({now})\n"
        f"전체 {total} / 이용중 {using} / 이용가능 {available}"
    )
    reply_markup = {"inline_keyboard": [[{"text": "🔕 그만 받기", "callback_data": "stop"}]]}
    requests.post(
        f"{API_BASE}/sendMessage",
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "reply_markup": json.dumps(reply_markup),
        },
        timeout=10,
    )


def main():
    state = load_state()
    state = sync_pause_state(state)  # 그 사이 온 버튼클릭/‘x’ 메시지 먼저 반영

    if state["paused"]:
        print("알림이 중지된 상태입니다. ('x' 메시지를 보내면 재개됩니다)")
        save_state(state)
        return

    total, using, available = fetch_seat_counts()
    append_log(total, using, available)
    build_dashboard()
    send_telegram(total, using, available)
    save_state(state)
    print(f"[{now_kst():%H:%M}] {ROOM_NAME} 전체 {total} / 이용중 {using} / 이용가능 {available}")


if __name__ == "__main__":
    main()
