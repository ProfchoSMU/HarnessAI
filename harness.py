"""
카카오 이모티콘 자동 생성 하네스 v5
- analyzer: Claude로 얼굴 분석
- designer: 하드코딩 (JSON 에러 없음)
- generator: DALL-E 3로 이미지 생성

사용법:
  python harness.py --image sangi.jpg --style 병맛
"""

import anthropic
import base64
import json
import argparse
import os
import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    print("openai 없음. 실행하세요: pip install openai")
    sys.exit(1)

MODEL        = "claude-opus-4-6"
OUTPUT_DIR   = Path("output")
EMOTICON_DIR = OUTPUT_DIR / "emoticons"
STYLES       = ["병맛", "귀여운", "감성", "폭발적"]

# ── 18종 고정 기획 (JSON 에러 없음) ──────────────
DESIGNS = [
    {"slot_id": "01_hi",       "emotion": "인사/안녕",   "expression": "눈을 크게 뜨고 활짝 웃음, 눈썹 올라감",           "body_action": "한 손을 높이 들어 흔들기",          "effects": "반짝이 효과, 밝은 빛"},
    {"slot_id": "02_thanks",   "emotion": "감사/고마워", "expression": "눈이 초승달 모양, 입꼬리 최대로 올라감",           "body_action": "두 손을 가슴 앞에 모으기",          "effects": "하트 여러 개 떠오름"},
    {"slot_id": "03_love",     "emotion": "사랑/좋아해", "expression": "눈이 하트 모양, 볼에 홍조",                       "body_action": "두 팔로 하트 만들기",               "effects": "큰 하트, 작은 하트 가득"},
    {"slot_id": "04_cry",      "emotion": "울음/슬픔",   "expression": "눈썹 팔자, 입꼬리 내려감, 눈물 폭포",             "body_action": "고개 숙이고 어깨 떨기",             "effects": "눈물 방울 큼직하게"},
    {"slot_id": "05_angry",    "emotion": "분노/화남",   "expression": "눈썹 강하게 내려감, 눈 부릅뜸, 이 악물기",        "body_action": "주먹 쥐고 부들부들 떨기",           "effects": "머리 위 연기, 얼굴 빨개짐, 분노 심볼"},
    {"slot_id": "06_surprise", "emotion": "놀람/충격",   "expression": "눈 최대로 크게, 입 크게 벌림, 눈썹 하늘로",       "body_action": "두 손으로 뺨 잡기",                 "effects": "번개 효과, 별 튀김"},
    {"slot_id": "07_lol",      "emotion": "웃음/ㅋㅋ",  "expression": "눈 반달 모양, 입 크게 열려 이 보임, 눈물",         "body_action": "배 잡고 앞으로 구부리기",            "effects": "ㅋㅋㅋ 텍스트 효과, 웃음 파동"},
    {"slot_id": "08_ok",       "emotion": "좋아요/엄지", "expression": "한쪽 눈 윙크, 입꼬리 올림",                       "body_action": "엄지 척 올리기",                    "effects": "반짝이, OK 심볼"},
    {"slot_id": "09_sorry",    "emotion": "미안/죄송",   "expression": "눈썹 팔자, 눈 아래로, 입 꾹 다물기",              "body_action": "두 손 합장하고 고개 90도 숙이기",   "effects": "땀방울, 죄송 오라"},
    {"slot_id": "10_party",    "emotion": "축하/파티",   "expression": "눈 반달, 입 크게 벌리고 환호",                    "body_action": "두 팔 번쩍 들기",                   "effects": "폭죽, 색종이 가루, 별"},
    {"slot_id": "11_tired",    "emotion": "피곤/지침",   "expression": "눈 반쯤 감김, 입 힘없이 내려감",                  "body_action": "몸 한쪽으로 기울고 늘어짐",         "effects": "ZZZ, 다크서클, 기력 없는 선"},
    {"slot_id": "12_no",       "emotion": "거부/싫어",   "expression": "눈썹 찌푸림, 눈 가늘게, 입 일자",                 "body_action": "양손 X자로 교차하며 거절",           "effects": "NO 심볼, 빨간 X"},
    {"slot_id": "13_work",     "emotion": "출근/좀비",   "expression": "눈 초점 없음, 입 반쯤 열림, 무표정",              "body_action": "가방 들고 비틀비틀 걷기",            "effects": "해골, 좀비 오라, 파리 날림"},
    {"slot_id": "14_off",      "emotion": "퇴근/해방",   "expression": "눈 반달로 활짝, 입 크게 웃음",                    "body_action": "가방 집어 던지며 점프",              "effects": "자유 텍스트, 무지개, 빛 폭발"},
    {"slot_id": "15_eat",      "emotion": "밥먹자",      "expression": "눈 초롱초롱, 침 흘림, 기대 가득한 표정",           "body_action": "숟가락 들고 밥그릇 앞에",            "effects": "김 모락모락, 하트, 식욕 오라"},
    {"slot_id": "16_coffee",   "emotion": "커피/카페인", "expression": "눈 번쩍 뜨임, 동공 작아짐, 에너지 넘침",           "body_action": "커피잔 들고 원샷",                   "effects": "카페인 번개, 에너지 파동"},
    {"slot_id": "17_sleep",    "emotion": "잠/졸림",     "expression": "눈 완전히 감김, 입 살짝 벌림",                    "body_action": "고개 꾸벅꾸벅",                     "effects": "ZZZ 크게, 달과 별, 수면 구름"},
    {"slot_id": "18_fighting", "emotion": "응원/파이팅", "expression": "눈 빛남, 이 악물기, 투지 넘치는 표정",             "body_action": "주먹 꽉 쥐고 앞으로",               "effects": "파이팅 텍스트, 불꽃, 에너지 광선"},
]


claude_client = anthropic.Anthropic()
openai_client = OpenAI()


def load_image_base64(path: str):
    ext = Path(path).suffix.lower()
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png", ".webp": "image/webp"}
    media_type = media_map.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode(), media_type


def log(agent: str, msg: str):
    colors = {"harness": "\033[32m", "analyzer": "\033[35m",
              "designer": "\033[36m", "generator": "\033[33m"}
    c = colors.get(agent, "")
    r = "\033[0m"
    print(f"{c}[{agent}]{r}  {msg}")


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── 에이전트 1: analyzer ──────────────────────────
def run_analyzer(image_path: str, style: str) -> dict:
    log("analyzer", "이미지 분석 시작...")
    img_data, media_type = load_image_base64(image_path)

    prompt = """이 인물 사진을 분석해서 아래 항목을 영어로 간단히 답하세요.
각 항목을 한 줄씩, 콜론(:) 뒤에 답변:

face_shape: 
hair_color_style: 
eye_features: 
glasses: 
skin_tone: 
outfit: 
distinctive: 
vibe: """

    response = claude_client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": media_type, "data": img_data
                }},
                {"type": "text", "text": prompt}
            ]
        }]
    )

    # 줄 파싱 (JSON 아님 → 에러 없음)
    result = {}
    for line in response.content[0].text.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()

    log("analyzer", f"완료 → {result.get('vibe', '분석 완료')}")
    return result


# ── 에이전트 2: designer (하드코딩) ──────────────
def run_designer() -> list:
    log("designer", "18종 기획 로드 완료 (하드코딩)")
    return DESIGNS


# ── 에이전트 3: generator ─────────────────────────
def run_generator(analysis: dict, designs: list, style: str) -> list:
    log("generator", "프롬프트 작성 중...")

    style_map = {
        "병맛":   "absurdist Korean webtoon sticker, thick black outlines, flat bold colors, over-the-top exaggerated funny expression",
        "귀여운": "cute chibi Korean kakao emoticon, soft rounded lines, pastel colors, big sparkling eyes",
        "감성":   "soft emotional Korean illustration sticker, gentle lines, muted warm tones",
        "폭발적": "explosive energetic Korean cartoon sticker, bold dynamic lines, vivid saturated colors",
    }
    style_desc = style_map.get(style, style_map["병맛"])

    glasses_desc = ""
    g = analysis.get("glasses", "none")
    if g and "none" not in g.lower() and "no " not in g.lower():
        glasses_desc = f", wearing {g}"

    char_base = (
        f"{analysis.get('face_shape','round')} face, "
        f"{analysis.get('hair_color_style','dark short hair')}, "
        f"{analysis.get('eye_features','dark eyes')} eyes"
        f"{glasses_desc}, "
        f"{analysis.get('outfit','casual clothes')}"
    )

    results = []
    for i, design in enumerate(designs, 1):
        prompt = (
            f"{style_desc}. "
            f"Character: {char_base}. "
            f"Emotion: {design['emotion']}. "
            f"Expression: {design['expression']}. "
            f"Action: {design['body_action']}. "
            f"Effects: {design['effects']}. "
            f"Pure white background, square composition, "
            f"single character centered, no text no words, "
            f"kakao emoticon sticker style."
        )
        results.append({
            "slot_id":  design["slot_id"],
            "filename": f"{design['slot_id']}.png",
            "emotion":  design["emotion"],
            "prompt":   prompt,
        })
        log("generator", f"  [{i:02d}/18] {design['slot_id']} — {design['emotion']}")

    return results


# ── DALL-E 3 이미지 생성 ──────────────────────────
def generate_images(prompts: list):
    log("generator", "DALL-E 3 이미지 생성 시작... (약 4분 소요)")
    EMOTICON_DIR.mkdir(parents=True, exist_ok=True)

    total   = len(prompts)
    success = 0

    for i, item in enumerate(prompts, 1):
        out_path = EMOTICON_DIR / item["filename"]

        if out_path.exists():
            log("generator", f"  [{i:02d}/{total}] 이미 존재, 스킵")
            success += 1
            continue

        log("generator", f"  [{i:02d}/{total}] {item['slot_id']} 생성 중...")

        try:
            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=item["prompt"],
                size="1024x1024",
                quality="standard",
                n=1,
            )
            url = response.data[0].url
            urllib.request.urlretrieve(url, out_path)
            log("generator", f"  OK  {item['filename']} 저장 완료")
            success += 1

        except Exception as e:
            log("generator", f"  FAIL {item['slot_id']} 실패: {e}")

        if i < total:
            time.sleep(13)  # DALL-E rate limit 방지

    log("generator", f"완료 → {success}/{total}장 생성")


# ── 메인 파이프라인 ───────────────────────────────
def run_pipeline(image_path: str, style: str):
    start = datetime.now()
    print()
    log("harness", "=" * 50)
    log("harness", f"파이프라인 시작 — 스타일: {style}")
    log("harness", "=" * 50)
    print()

    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1단계: 이미지 분석
    analysis = run_analyzer(image_path, style)
    save_json(analysis, OUTPUT_DIR / "analysis.json")
    print()

    # 2단계: 기획 로드 (하드코딩)
    designs = run_designer()
    print()

    # 3단계: 프롬프트 생성
    prompts = run_generator(analysis, designs, style)
    save_json(prompts, OUTPUT_DIR / "prompts.json")
    with open(OUTPUT_DIR / "prompts.txt", "w", encoding="utf-8") as f:
        f.write(f"# 카카오 이모티콘 — {style} 스타일\n\n")
        for p in prompts:
            f.write(f"## {p['slot_id']} — {p['emotion']}\n{p['prompt']}\n\n")
    print()

    # 4단계: 이미지 생성
    generate_images(prompts)

    elapsed   = (datetime.now() - start).seconds
    png_count = len(list(EMOTICON_DIR.glob("*.png")))
    print()
    log("harness", "=" * 50)
    log("harness", f"완료! ({elapsed}초 소요)")
    log("harness", f"이미지 위치: {EMOTICON_DIR.absolute()}")
    log("harness", f"총 {png_count}장 생성됨")
    log("harness", "=" * 50)
    print()


# ── CLI ──────────────────────────────────────────
if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY 가 없습니다.")
        print('PowerShell: $env:ANTHROPIC_API_KEY = "sk-ant-..."')
        sys.exit(1)
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 가 없습니다.")
        print('PowerShell: $env:OPENAI_API_KEY = "sk-proj-..."')
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--style", default="병맛", choices=STYLES)
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"이미지 파일을 찾을 수 없습니다: {args.image}")
        sys.exit(1)

    run_pipeline(args.image, args.style)
