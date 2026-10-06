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
| 환경변수 | Claude 연결: `ANTHROPIC_VERTEX_PROJECT_ID` (Vertex AI, ADC 로그인) 또는 `ANTHROPIC_API_KEY` |
| 환경변수 | `CLOUD_ML_REGION` (Vertex AI 리전, 선택, 기본값 `global`) |
| 환경변수 | `OPENAI_MODEL` (선택, 기본값 `gpt-5`) |

두 API는 ChatGPT Plus, Claude Pro 구독과 별도로 사용량만큼 과금됩니다.

### 사용법

```bash
pip install -r requirements.txt
python3 ai_pipeline.py check                      # 두 API 연결 점검 (짧은 호출 2회)
python3 ai_pipeline.py draft "퇴사 후 1년 회고" 5  # 초안 5개 → 검수 → 저장
```

### 내 Windows PC에서 Vertex AI(ADC)로 실행

PowerShell에서 순서대로 실행합니다.

```powershell
winget install Google.CloudSDK Python.Python.3.12 Git.Git   # 설치 후 PowerShell 새로 열기
gcloud init                                       # 로그인하고 프로젝트 선택
gcloud auth application-default login             # ADC 로그인 (PC 전역에 저장)
gcloud services enable aiplatform.googleapis.com  # Vertex AI API 켜기
setx ANTHROPIC_VERTEX_PROJECT_ID (gcloud config get-value project)
setx CLOUD_ML_REGION global
setx OPENAI_API_KEY "sk-..."                      # 설정 후 PowerShell 새로 열기
git clone -b claude/practical-edison-bw7wi5 https://github.com/dmsk1111-gif/claude-test.git
cd claude-test
pip install -r requirements.txt
python ai_pipeline.py check
```

Google Cloud 콘솔의 Vertex AI → Model Garden에서 Claude 모델 사용 신청(Enable)을 먼저 해야 합니다.
