[README.md](https://github.com/user-attachments/files/31893858/README.md)
# 내손도서관 제1열람실 좌석 현황 자동 알림 (GitHub Actions + 텔레그램)

내 컴퓨터를 켜둘 필요 없이, GitHub이 클라우드에서 매시간 자동으로
좌석 현황을 확인해서 텔레그램으로 알려줍니다.

## 1. 텔레그램 봇 만들기 (5분)
1. 텔레그램에서 `@BotFather` 검색 → 대화 시작
2. `/newbot` 입력 → 봇 이름 정하기 → **BOT TOKEN** 받기 (예: `123456:ABC-...`)
3. 방금 만든 봇을 검색해서 아무 메시지나 보내기 (예: "안녕")
4. 브라우저에서 아래 주소 접속 (TOKEN은 위에서 받은 값으로 교체):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. 결과 중 `"chat":{"id": 123456789, ...}` 에서 **숫자(chat id)**를 확인

## 2. GitHub 저장소 만들기
1. github.com에서 새 저장소 생성 (Private 추천)
2. 이 폴더의 파일들을 그대로 저장소에 업로드/push
   - `seat_scraper.py`
   - `requirements.txt`
   - `.github/workflows/check-seats.yml`

## 3. Secrets 등록
저장소 → Settings → Secrets and variables → Actions → New repository secret
- `TELEGRAM_BOT_TOKEN` : 1번에서 받은 토큰
- `TELEGRAM_CHAT_ID` : 1번에서 확인한 chat id

## 4. 확인
- 저장소 → Actions 탭 → "좌석 현황 체크" 워크플로우 → "Run workflow"로 수동 테스트
- 문제 없으면 매일 KST 08,09,10,11,12시에 자동 실행되어 텔레그램으로 알림이 옵니다.
- 실행할 때마다 seat_log.csv에 기록이 쌓이고, dashboard.html도 저장소에 갱신되어
  (GitHub Pages를 켜면) 웹페이지로도 볼 수 있습니다.

## 알림 끄고 켜기
- 메시지마다 "🔕 그만 받기" 버튼이 같이 와요. 누르면 그 다음부터 알림이 안 옵니다 (안 누르면 계속 받는 게 기본).
- 누르면 "▶️ 다시 받고싶어요" 버튼이 있는 메시지가 하나 오는데, 그 버튼을 누르면 알림이 재개됩니다.

## 참고
- 무료 GitHub 계정의 Actions 무료 사용량 내에서 충분히 동작합니다 (하루 5회, 몇 초씩).
- 데이터 출처: 의왕시통합도서관 SeatMate3 좌석관리시스템
- 사이트 구조가 바뀌면 파싱이 실패할 수 있어요 — 그럴 때 알려주시면 고쳐드릴게요.
