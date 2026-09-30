#!/usr/bin/env python3
"""Threads API 자동화 도구 (표준 라이브러리만 사용).

필요한 환경변수
  THREADS_ACCESS_TOKEN  Threads 사용자 액세스 토큰 (필수)
  THREADS_APP_SECRET    앱 시크릿 (단기 토큰 → 장기 토큰 변환 시에만 필요)

사용법
  python3 threads.py check                     토큰, 네트워크, 권한별 동작 여부 점검
  python3 threads.py exchange                  단기 토큰을 60일 장기 토큰으로 변환
  python3 threads.py refresh                   장기 토큰 기간 연장
  python3 threads.py me                        내 계정 정보
  python3 threads.py posts [개수]              내 최근 글 목록
  python3 threads.py post "본문"               텍스트 글 발행
  python3 threads.py replies <글ID>            글에 달린 댓글 목록
  python3 threads.py reply <글ID> "본문"       댓글(답글) 달기
  python3 threads.py hide <댓글ID>             댓글 숨기기
  python3 threads.py unhide <댓글ID>           댓글 숨김 해제
  python3 threads.py insights <글ID>           글 성과(조회, 좋아요, 댓글, 리포스트, 인용)

좋아요 누르기와 팔로우는 Threads 공식 API에 엔드포인트가 없어서 지원하지 않습니다.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://graph.threads.net"
VERSION = "v1.0"


class ThreadsError(Exception):
    pass


def _token():
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    if not token:
        raise ThreadsError("THREADS_ACCESS_TOKEN 환경변수가 없습니다.")
    return token


def call(method, path, params=None, versioned=True):
    params = dict(params or {})
    params.setdefault("access_token", _token())
    url = f"{BASE}/{VERSION}/{path}" if versioned else f"{BASE}/{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            msg = json.loads(body).get("error", {}).get("message", body)
        except ValueError:
            msg = body
        raise ThreadsError(f"HTTP {e.code}: {msg}") from None
    except urllib.error.URLError as e:
        raise ThreadsError(f"네트워크 오류: {e.reason} (graph.threads.net 허용 여부 확인)") from None


def me():
    return call("GET", "me", {"fields": "id,username,name,threads_biography"})


def posts(limit=10):
    return call("GET", "me/threads", {
        "fields": "id,text,timestamp,permalink,media_type",
        "limit": limit,
    }).get("data", [])


def _publish(params):
    user_id = me()["id"]
    container = call("POST", f"{user_id}/threads", params)["id"]
    # 컨테이너 처리가 끝나기 전에 발행하면 실패할 수 있어 잠시 기다린다.
    for _ in range(10):
        status = call("GET", container, {"fields": "status,error_message"})
        if status.get("status") == "FINISHED":
            break
        if status.get("status") == "ERROR":
            raise ThreadsError(f"컨테이너 오류: {status.get('error_message')}")
        time.sleep(3)
    return call("POST", f"{user_id}/threads_publish", {"creation_id": container})


def post(text):
    return _publish({"media_type": "TEXT", "text": text})


def reply(media_id, text):
    return _publish({"media_type": "TEXT", "text": text, "reply_to_id": media_id})


def replies(media_id):
    return call("GET", f"{media_id}/replies", {
        "fields": "id,text,username,timestamp,hide_status",
    }).get("data", [])


def hide(reply_id, value=True):
    return call("POST", f"{reply_id}/manage_reply", {"hide": "true" if value else "false"})


def insights(media_id):
    data = call("GET", f"{media_id}/insights", {
        "metric": "views,likes,replies,reposts,quotes",
    }).get("data", [])
    return {m["name"]: m["values"][0]["value"] for m in data if m.get("values")}


def exchange():
    secret = os.environ.get("THREADS_APP_SECRET")
    if not secret:
        raise ThreadsError("THREADS_APP_SECRET 환경변수가 없습니다.")
    return call("GET", "access_token", {
        "grant_type": "th_exchange_token",
        "client_secret": secret,
    }, versioned=False)


def refresh():
    return call("GET", "refresh_access_token", {"grant_type": "th_refresh_token"}, versioned=False)


def check():
    """읽기 전용 호출만으로 권한별 동작 여부를 점검한다. 글을 올리지 않는다."""
    rows = []

    def run(label, fn):
        try:
            result = fn()
            rows.append((label, "OK", result))
            return result
        except ThreadsError as e:
            rows.append((label, "실패", str(e)))
            return None

    account = run("계정 조회 (threads_basic)", me)
    if account is None:
        _print_rows(rows)
        return
    recent = run("내 글 목록 (threads_basic)", lambda: f"{len(posts(5))}개 조회")
    latest = posts(1) if recent else []
    if latest:
        mid = latest[0]["id"]
        run("댓글 읽기 (threads_read_replies)", lambda: f"{len(replies(mid))}개 조회")
        run("성과 조회 (threads_manage_insights)", lambda: insights(mid))
    else:
        rows.append(("댓글 읽기 / 성과 조회", "건너뜀", "올린 글이 없어 점검 불가"))
    rows.append(("글 발행 / 댓글 달기 (threads_content_publish, threads_manage_replies)",
                 "미점검", "실제 글이 올라가므로 post 명령으로 직접 테스트"))
    _print_rows(rows)


def _print_rows(rows):
    for label, state, detail in rows:
        if not isinstance(detail, str):
            detail = json.dumps(detail, ensure_ascii=False)
        print(f"[{state}] {label}\n        {detail}")


COMMANDS = {
    "check": (check, 0),
    "exchange": (exchange, 0),
    "refresh": (refresh, 0),
    "me": (me, 0),
    "posts": (lambda n="10": posts(int(n)), None),
    "post": (post, 1),
    "replies": (replies, 1),
    "reply": (reply, 2),
    "hide": (hide, 1),
    "unhide": (lambda rid: hide(rid, False), 1),
    "insights": (insights, 1),
}


def main(argv):
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    fn, nargs = COMMANDS[argv[1]]
    args = argv[2:]
    if nargs is not None and len(args) != nargs:
        print(__doc__)
        return 1
    try:
        result = fn(*args)
    except ThreadsError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
