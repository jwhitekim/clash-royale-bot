# Clash Royale 클랜전 듀얼 봇

텔레그램 인라인 봇. 클랜전 중 상대 플레이어의 최근 듀얼 덱을 빠르게 조회.

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env
# .env에 토큰/키 입력
```

## 텔레그램 봇 설정 (@BotFather)

1. `/newbot` → 봇 이름/아이디 설정 → 토큰 발급
2. `/setinline` → 인라인 모드 활성화 (필수)
3. `/setinlinefeedback` → **Enable** 설정 (chosen_inline_result 핸들러 동작에 필수)

## Clash Royale API 키 발급

1. https://developer.clashroyale.com 접속 → 로그인
2. "Create New Key" → Key Name, Description 입력
3. **Allowed IP Addresses**에 현재 IP 입력
   - 로컬 맥북: `curl ifconfig.me`
   - Railway 배포 후: Railway 로그에서 확인
4. API 키 복사 → `.env`의 `CR_API_KEY`에 입력

## 실행 (로컬)

```bash
python bot.py
```

## 사용 방법

```
/register #태그          내 플레이어 태그 등록
/setdecks 덱1,...|덱2,...|덱3,...   내 듀얼 덱 3개 등록 (카드 8장, | 구분)
/mydecks                 저장된 내 덱 확인

채팅방에서: @봇이름 상대닉네임   상대 최근 듀얼 덱 조회
```

## Railway 배포

1. `.gitignore` 확인 후 GitHub에 push
2. https://railway.app → "New Project" → GitHub 레포 선택
3. Variables 설정:
   ```
   TELEGRAM_BOT_TOKEN=...
   CR_API_KEY=...
   MODE=webhook
   RAILWAY_DOMAIN=자동생성된도메인.railway.app
   ```
4. "Generate Domain"으로 도메인 발급 → `RAILWAY_DOMAIN`에 입력
5. Railway 로그에서 서버 IP 확인 → Clash Royale API 키에 등록
