# 스레드 자동화

Threads 공식 API로 글 발행, 댓글 관리, 성과 수집을 자동화하는 도구입니다.

## 환경 준비 (Claude Code 클라우드 환경 `스레드자동화`)

세션 제목 표시줄의 클라우드 환경 메뉴 → Edit에서 설정합니다. 바꾼 뒤에는 새 세션을 열어야 반영됩니다.

| 설정 | 값 |
|---|---|
| Network access | 허용 도메인에 `graph.threads.net` 추가 |
| 환경변수 | `THREADS_ACCESS_TOKEN` (필수) |
| 환경변수 | `THREADS_APP_SECRET` (장기 토큰 변환용, 선택) |

## 기능 범위

| 기능 | 지원 | 권한 |
|---|---|---|
| 내 글 발행 | O | `threads_content_publish` |
| 댓글 읽기 | O | `threads_read_replies` |
| 댓글에 답글, 숨기기 | O | `threads_manage_replies` |
| 성과 조회 | O | `threads_manage_insights` |
| 좋아요, 팔로우 | X | 공식 API에 없음 |

## 사용법

```bash
python3 threads.py check        # 먼저 실행: 토큰, 네트워크, 권한 점검
python3 threads.py exchange     # 단기 토큰 → 60일 장기 토큰
python3 threads.py post "본문"
python3 threads.py replies <글ID>
python3 threads.py reply <글ID> "본문"
python3 threads.py insights <글ID>
```

전체 명령은 `python3 threads.py`로 확인합니다.

## ChatGPT → Claude 연결 (`ai_pipeline.py`)

ChatGPT가 스레드 초안을 여러 개 쓰고, Claude가 후킹 점수, 문제점, 수정본, 추천 초안을 정리합니다. 결과는 `output/날짜-시간.md`에 저장됩니다.

### 환경 준비

| 설정 | 값 |
|---|---|
| Network access | 허용 도메인에 `api.openai.com`, `api.anthropic.com` 추가 |
| 환경변수 | `OPENAI_API_KEY` (platform.openai.com에서 발급, 필수) |
| 환경변수 | `ANTHROPIC_API_KEY` (console.anthropic.com에서 발급, 필수) |
| 환경변수 | `OPENAI_MODEL` (선택, 기본값 `gpt-5`) |

두 API는 ChatGPT Plus, Claude Pro 구독과 별도로 사용량만큼 과금됩니다.

### 사용법

```bash
pip install -r requirements.txt
python3 ai_pipeline.py check                      # 두 API 연결 점검 (짧은 호출 2회)
python3 ai_pipeline.py draft "퇴사 후 1년 회고" 5  # 초안 5개 → 검수 → 저장
```
