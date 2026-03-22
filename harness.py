"""
카카오 이모티콘 자동 생성 하네스 v7

사용법:
  python harness.py --image sangi.jpg --style 병맛   (풀 파이프라인)
  python harness.py --gallery-only                   (갤러리+push만)
"""

import anthropic
import base64
import json
import argparse
import os
import sys
import time
import urllib.request
import subprocess
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

DESIGNS = [
    {"slot_id": "01_hi",       "emotion": "인사/안녕",   "expression": "눈을 크게 뜨고 활짝 웃음",       "body_action": "한 손을 높이 들어 흔들기",        "effects": "반짝이 효과"},
    {"slot_id": "02_thanks",   "emotion": "감사/고마워", "expression": "눈이 초승달 모양, 입꼬리 올라감", "body_action": "두 손을 가슴 앞에 모으기",        "effects": "하트 여러 개"},
    {"slot_id": "03_love",     "emotion": "사랑/좋아해", "expression": "눈이 하트 모양, 볼에 홍조",       "body_action": "두 팔로 하트 만들기",              "effects": "큰 하트 가득"},
    {"slot_id": "04_cry",      "emotion": "울음/슬픔",   "expression": "눈썹 팔자, 눈물 폭포",            "body_action": "고개 숙이고 어깨 떨기",            "effects": "눈물 방울 큼직"},
    {"slot_id": "05_angry",    "emotion": "분노/화남",   "expression": "눈썹 강하게 내려감, 눈 부릅뜸",   "body_action": "주먹 쥐고 부들부들",              "effects": "머리 위 연기, 얼굴 빨개짐"},
    {"slot_id": "06_surprise", "emotion": "놀람/충격",   "expression": "눈 최대로 크게, 입 크게 벌림",    "body_action": "두 손으로 뺨 잡기",               "effects": "번개 효과, 별 튀김"},
    {"slot_id": "07_lol",      "emotion": "웃음/ㅋㅋ",  "expression": "눈 반달, 입 크게 열려 이 보임",   "body_action": "배 잡고 앞으로 구부리기",          "effects": "웃음 파동"},
    {"slot_id": "08_ok",       "emotion": "좋아요/엄지", "expression": "한쪽 눈 윙크, 입꼬리 올림",       "body_action": "엄지 척 올리기",                  "effects": "반짝이, OK 심볼"},
    {"slot_id": "09_sorry",    "emotion": "미안/죄송",   "expression": "눈썹 팔자, 눈 아래로",            "body_action": "두 손 합장하고 고개 숙이기",       "effects": "땀방울"},
    {"slot_id": "10_party",    "emotion": "축하/파티",   "expression": "눈 반달, 입 크게 벌리고 환호",    "body_action": "두 팔 번쩍 들기",                 "effects": "폭죽, 색종이 가루"},
    {"slot_id": "11_tired",    "emotion": "피곤/지침",   "expression": "눈 반쯤 감김, 입 힘없이 내려감",  "body_action": "몸 한쪽으로 기울고 늘어짐",        "effects": "ZZZ, 다크서클"},
    {"slot_id": "12_no",       "emotion": "거부/싫어",   "expression": "눈썹 찌푸림, 눈 가늘게",          "body_action": "양손 X자로 교차하며 거절",         "effects": "빨간 X"},
    {"slot_id": "13_work",     "emotion": "출근/좀비",   "expression": "눈 초점 없음, 무표정",            "body_action": "가방 들고 비틀비틀 걷기",          "effects": "좀비 오라, 파리 날림"},
    {"slot_id": "14_off",      "emotion": "퇴근/해방",   "expression": "눈 반달로 활짝, 입 크게 웃음",    "body_action": "가방 집어 던지며 점프",            "effects": "무지개, 빛 폭발"},
    {"slot_id": "15_eat",      "emotion": "밥먹자",      "expression": "눈 초롱초롱, 침 흘림",            "body_action": "숟가락 들고 밥그릇 앞에",          "effects": "김 모락모락, 하트"},
    {"slot_id": "16_coffee",   "emotion": "커피/카페인", "expression": "눈 번쩍 뜨임, 에너지 넘침",       "body_action": "커피잔 들고 원샷",                 "effects": "카페인 번개"},
    {"slot_id": "17_sleep",    "emotion": "잠/졸림",     "expression": "눈 완전히 감김, 입 살짝 벌림",    "body_action": "고개 꾸벅꾸벅",                   "effects": "ZZZ 크게, 달과 별"},
    {"slot_id": "18_fighting", "emotion": "응원/파이팅", "expression": "눈 빛남, 투지 넘치는 표정",        "body_action": "주먹 꽉 쥐고 앞으로",             "effects": "파이팅, 불꽃"},
]


def log(agent: str, msg: str):
    colors = {"harness": "\033[32m", "analyzer": "\033[35m",
              "designer": "\033[36m", "generator": "\033[33m",
              "gallery": "\033[34m", "github": "\033[33m"}
    c = colors.get(agent, "")
    r = "\033[0m"
    print(f"{c}[{agent}]{r}  {msg}")


def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_image_base64(path: str):
    ext = Path(path).suffix.lower()
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png", ".webp": "image/webp"}
    media_type = media_map.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode(), media_type


def run_analyzer(image_path: str) -> dict:
    log("analyzer", "이미지 분석 시작...")
    claude_client = anthropic.Anthropic()
    img_data, media_type = load_image_base64(image_path)
    prompt = """이 인물 사진을 분석해서 아래 항목을 영어로 간단히 답하세요.
각 항목을 한 줄씩, 콜론(:) 뒤에 답변:

face_shape: 
hair_color_style: 
eye_features: 
glasses: 
skin_tone: 
outfit: 
vibe: """

    response = claude_client.messages.create(
        model=MODEL, max_tokens=400,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_data}},
            {"type": "text", "text": prompt}
        ]}]
    )
    result = {}
    for line in response.content[0].text.strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    log("analyzer", f"완료 → {result.get('vibe', '분석 완료')}")
    return result


def run_generator(analysis: dict, style: str) -> list:
    log("generator", "프롬프트 작성 중...")
    style_map = {
        "병맛":   "absurdist Korean webtoon sticker, thick black outlines, flat bold colors, exaggerated funny expression",
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
        f"{glasses_desc}, {analysis.get('outfit','casual clothes')}"
    )
    results = []
    for i, design in enumerate(DESIGNS, 1):
        prompt = (
            f"{style_desc}. Character: {char_base}. "
            f"Emotion: {design['emotion']}. Expression: {design['expression']}. "
            f"Action: {design['body_action']}. Effects: {design['effects']}. "
            f"Pure white background, square, single character centered, no text, kakao emoticon style."
        )
        results.append({"slot_id": design["slot_id"], "filename": f"{design['slot_id']}.png",
                        "emotion": design["emotion"], "prompt": prompt})
        log("generator", f"  [{i:02d}/18] {design['slot_id']} — {design['emotion']}")
    return results


def generate_images(prompts: list):
    openai_client = OpenAI()
    log("generator", "DALL-E 3 이미지 생성 시작... (약 4분 소요)")
    EMOTICON_DIR.mkdir(parents=True, exist_ok=True)
    total = len(prompts)
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
                model="dall-e-3", prompt=item["prompt"],
                size="1024x1024", quality="standard", n=1)
            urllib.request.urlretrieve(response.data[0].url, out_path)
            log("generator", f"  OK  {item['filename']} 저장 완료")
            success += 1
        except Exception as e:
            log("generator", f"  FAIL {item['slot_id']} 실패: {e}")
        if i < total:
            time.sleep(13)
    log("generator", f"완료 → {success}/{total}장 생성")


def make_gallery():
    log("gallery", "gallery.html 생성 중...")
    png_files = sorted(EMOTICON_DIR.glob("*.png"))
    cards_html = ""
    for png in png_files:
        slot_id = png.stem
        emotion = slot_id
        for d in DESIGNS:
            if d["slot_id"] == slot_id:
                emotion = d["emotion"]
                break
        cards_html += f"""
        <div class="card" onclick="openModal('emoticons/{png.name}')">
            <img src="emoticons/{png.name}" alt="{emotion}">
            <p>{emotion}</p>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>나만의 이모티콘</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Apple SD Gothic Neo','Noto Sans KR',sans-serif; background:#fff8f0; }}
  header {{ background:linear-gradient(135deg,#ff6b6b,#ffd93d); padding:40px 20px; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,.1); }}
  header h1 {{ font-size:2rem; color:white; text-shadow:2px 2px 4px rgba(0,0,0,.2); margin-bottom:8px; }}
  header p {{ color:rgba(255,255,255,.9); font-size:.95rem; }}
  .badge {{ display:inline-block; background:white; color:#ff6b6b; border-radius:20px; padding:4px 14px; font-size:.85rem; font-weight:bold; margin-top:12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:16px; padding:32px 24px; max-width:900px; margin:0 auto; }}
  .card {{ background:white; border-radius:16px; padding:16px 12px 12px; text-align:center; box-shadow:0 2px 12px rgba(0,0,0,.08); transition:transform .2s,box-shadow .2s; cursor:pointer; }}
  .card:hover {{ transform:translateY(-4px); box-shadow:0 8px 24px rgba(0,0,0,.14); }}
  .card img {{ width:100%; aspect-ratio:1; object-fit:cover; border-radius:10px; margin-bottom:10px; }}
  .card p {{ font-size:.82rem; color:#666; font-weight:500; }}
  footer {{ text-align:center; padding:32px; color:#aaa; font-size:.82rem; }}
  .modal {{ display:none; position:fixed; inset:0; background:rgba(0,0,0,.75); z-index:100; align-items:center; justify-content:center; }}
  .modal.show {{ display:flex; }}
  .modal img {{ max-width:80vw; max-height:80vh; border-radius:16px; }}
  .modal-close {{ position:fixed; top:20px; right:28px; color:white; font-size:2rem; cursor:pointer; font-weight:bold; }}
</style>
</head>
<body>
<header>
  <h1>🎭 나만의 이모티콘</h1>
  <p>AI가 만든 나만의 카카오 이모티콘</p>
  <span class="badge">✨ {len(png_files)}종 세트</span>
</header>
<div class="grid">{cards_html}</div>
<footer>Made with Claude + DALL-E 3 &nbsp;|&nbsp; {datetime.now().strftime('%Y.%m.%d')}</footer>
<div class="modal" id="modal" onclick="closeModal()">
  <span class="modal-close">&times;</span>
  <img id="modal-img" src="" alt="">
</div>
<script>
  function openModal(src) {{
    document.getElementById('modal-img').src = src;
    document.getElementById('modal').classList.add('show');
  }}
  function closeModal() {{
    document.getElementById('modal').classList.remove('show');
  }}
  document.addEventListener('keydown', e => {{ if(e.key==='Escape') closeModal(); }});
</script>
</body>
</html>"""

    gallery_path = OUTPUT_DIR / "gallery.html"
    gallery_path.write_text(html, encoding="utf-8")
    log("gallery", f"완료 → {gallery_path.absolute()}")


def git_push():
    log("github", "GitHub push 시작...")
    cmds = [
        "git add output/",
        'git commit -m "이모티콘 업데이트"',
        "git push origin main"
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        out = result.stdout.strip()
        err = result.stderr.strip()
        if out: log("github", f"  {out}")
        if result.returncode != 0 and err:
            log("github", f"  {err}")
    log("github", "push 완료!")
    log("github", "주소: https://ProfchoSMU.github.io/HarnessAI/output/gallery.html")


# ── 메인 ─────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image",        default=None)
    parser.add_argument("--style",        default="병맛", choices=STYLES)
    parser.add_argument("--gallery-only", action="store_true")
    args = parser.parse_args()

    # 갤러리 + push만
    if args.gallery_only:
        make_gallery()
        print()
        git_push()
        sys.exit(0)

    # 풀 파이프라인
    if not args.image:
        print("사용법: python harness.py --image 파일명.jpg")
        print("       python harness.py --gallery-only")
        sys.exit(1)
    if not Path(args.image).exists():
        print(f"이미지를 찾을 수 없습니다: {args.image}")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print('ANTHROPIC_API_KEY 없음. $env:ANTHROPIC_API_KEY = "sk-ant-..."')
        sys.exit(1)
    if not os.environ.get("OPENAI_API_KEY"):
        print('OPENAI_API_KEY 없음. $env:OPENAI_API_KEY = "sk-proj-..."')
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    print()
    log("harness", "=" * 50)
    log("harness", f"파이프라인 시작 — 스타일: {args.style}")
    log("harness", "=" * 50)
    print()

    analysis = run_analyzer(args.image)
    save_json(analysis, OUTPUT_DIR / "analysis.json")
    print()

    prompts = run_generator(analysis, args.style)
    save_json(prompts, OUTPUT_DIR / "prompts.json")
    print()

    generate_images(prompts)
    print()

    make_gallery()
    print()

    git_push()
    print()

    png_count = len(list(EMOTICON_DIR.glob("*.png")))
    log("harness", "=" * 50)
    log("harness", f"완료! 총 {png_count}장 생성")
    log("harness", "주소: https://ProfchoSMU.github.io/HarnessAI/output/gallery.html")
    log("harness", "=" * 50)
