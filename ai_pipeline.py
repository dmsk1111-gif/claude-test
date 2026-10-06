#!/usr/bin/env python3
"""ChatGPT 초안 → Claude 검수 파이프라인.

ChatGPT가 스레드 초안을 여러 개 쓰고, Claude가 후킹과 문장을 검수해
수정본까지 만든 뒤 결과를 output/ 폴더에 마크다운으로 저장한다.

필요한 환경변수
  OPENAI_API_KEY      OpenAI API 키 (필수)
  ANTHROPIC_API_KEY   Anthropic API 키 (필수)
  OPENAI_MODEL        ChatGPT 모델 이름 (선택, 기본값 gpt-5)

사용법
  python3 ai_pipeline.py check                 두 API 키와 연결을 짧은 호출로 점검
  python3 ai_pipeline.py draft "주제" [개수]    초안 생성(기본 5개) → 검수 → 저장
"""
import datetime
import os
import pathlib
import sys

import anthropic
import openai

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")
CLAUDE_MODEL = "claude-opus-5-5"
OUTPUT_DIR = pathlib.Path(__file__).parent / "output"

DRAFT_INSTRUCTIONS = """너는 Threads 콘텐츠 작가다.
주어진 주제로 서로 다른 후킹 방식을 쓴 스레드 초안을 요청한 개수만큼 쓴다.
- 각 초안은 500자 이내, 첫 줄은 스크롤을 멈추게 하는 후킹 문장
- 번역투, 감탄사, 말줄임표 금지
- 초안마다 '## 초안 N' 제목을 붙이고 본문만 쓴다"""

REVIEW_SYSTEM = """너는 Threads 전문 마케터이자 꼼꼼한 편집자다.
받은 초안 각각에 대해 다음 형식으로 검수한다.

## 초안 N
- 후킹 점수: 10점 만점 점수와 근거 한 줄
- 문제점: 구체적으로 (번역투, 감탄사, 말줄임표, 늘어지는 문장, 약한 첫 줄)
- 수정본: 바로 올릴 수 있는 완성 원고

마지막에 '## 추천'으로 가장 반응이 좋을 초안 하나와 이유를 쓴다.
금지 표현: 결론적으로, 중요한 것은, 혁신적인, 소중한, 함께하는, 이유가 단순하다, 핵심은 다음과 같다.
수정본에도 금지 표현, 감탄사, 말줄임표를 쓰지 않는다."""


class PipelineError(Exception):
    pass


def _require(name):
    if not os.environ.get(name):
        raise PipelineError(f"{name} 환경변수가 없습니다.")


def chatgpt(instructions, prompt):
    _require("OPENAI_API_KEY")
    try:
        res = openai.OpenAI().responses.create(
            model=OPENAI_MODEL, instructions=instructions, input=prompt,
        )
    except openai.APIConnectionError:
        raise PipelineError("OpenAI 연결 실패 (api.openai.com 허용 여부 확인)") from None
    except openai.APIStatusError as e:
        raise PipelineError(f"OpenAI HTTP {e.status_code}: {e.message}") from None
    return res.output_text


def claude(system, prompt, max_tokens=16000):
    _require("ANTHROPIC_API_KEY")
    try:
        # 안전 분류기가 거절하면 서버가 다른 Claude 모델로 자동 재시도한다.
        res = anthropic.Anthropic().beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIConnectionError:
        raise PipelineError("Anthropic 연결 실패 (api.anthropic.com 허용 여부 확인)") from None
    except anthropic.APIStatusError as e:
        raise PipelineError(f"Anthropic HTTP {e.status_code}: {e.message}") from None
    if res.stop_reason == "refusal":
        raise PipelineError("Claude가 요청을 거절했습니다. 주제를 바꿔 다시 시도하세요.")
    text = "".join(b.text for b in res.content if b.type == "text")
    if res.stop_reason == "max_tokens":
        text += "\n\n(출력 길이 한도에 걸려 일부가 잘렸습니다)"
    return text


def draft(topic, count="5"):
    count = int(count)
    print(f"1/2 ChatGPT({OPENAI_MODEL})가 초안 {count}개 작성 중", file=sys.stderr)
    drafts = chatgpt(DRAFT_INSTRUCTIONS, f"주제: {topic}\n초안 개수: {count}")
    print(f"2/2 Claude({CLAUDE_MODEL})가 검수 중", file=sys.stderr)
    review = claude(REVIEW_SYSTEM, f"주제: {topic}\n\n{drafts}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{datetime.datetime.now():%Y%m%d-%H%M%S}.md"
    path.write_text(
        f"# {topic}\n\n# ChatGPT 초안\n\n{drafts}\n\n# Claude 검수\n\n{review}\n",
        encoding="utf-8",
    )
    print(review)
    print(f"\n저장: {path}", file=sys.stderr)


def check():
    for label, fn in [
        (f"ChatGPT ({OPENAI_MODEL})", lambda: chatgpt("한 단어로 답한다.", "연결 확인. '정상'이라고 답해.")),
        (f"Claude ({CLAUDE_MODEL})", lambda: claude("한 단어로 답한다.", "연결 확인. '정상'이라고 답해.", 2000)),
    ]:
        try:
            print(f"[OK] {label}: {fn().strip()}")
        except PipelineError as e:
            print(f"[실패] {label}: {e}")


COMMANDS = {"check": (check, (0, 0)), "draft": (draft, (1, 2))}


def main(argv):
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    fn, (lo, hi) = COMMANDS[argv[1]]
    args = argv[2:]
    if not lo <= len(args) <= hi:
        print(__doc__)
        return 1
    try:
        fn(*args)
    except PipelineError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
