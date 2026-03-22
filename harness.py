"""
카카오 이모티콘 자동 생성 하네스 v8
- AndyBoy 스타일 갤러리 페이지 생성

사용법:
  python harness.py --image sangi.jpg --style 병맛 --name 홍길동
  python harness.py --gallery-only --name 홍길동
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
    {"slot_id": "03_love",     "emotion": "사랑/좋아해", "expression": "눈이 하트 모양, 볼에 홍조",       "body_action": "두 팔로 하트 만들기",             "effects": "큰 하트 가득"},
    {"slot_id": "04_cry",      "emotion": "울음/슬픔",   "expression": "눈썹 팔자, 눈물 폭포",            "body_action": "고개 숙이고 어깨 떨기",           "effects": "눈물 방울 큼직"},
    {"slot_id": "05_angry",    "emotion": "분노/화남",   "expression": "눈썹 강하게 내려감, 눈 부릅뜸",   "body_action": "주먹 쥐고 부들부들",             "effects": "머리 위 연기, 얼굴 빨개짐"},
    {"slot_id": "06_surprise", "emotion": "놀람/충격",   "expression": "눈 최대로 크게, 입 크게 벌림",    "body_action": "두 손으로 뺨 잡기",              "effects": "번개 효과, 별 튀김"},
    {"slot_id": "07_lol",      "emotion": "웃음/ㅋㅋ",  "expression": "눈 반달, 입 크게 열려 이 보임",   "body_action": "배 잡고 앞으로 구부리기",         "effects": "웃음 파동"},
    {"slot_id": "08_ok",       "emotion": "좋아요/엄지", "expression": "한쪽 눈 윙크, 입꼬리 올림",       "body_action": "엄지 척 올리기",                 "effects": "반짝이, OK 심볼"},
    {"slot_id": "09_sorry",    "emotion": "미안/죄송",   "expression": "눈썹 팔자, 눈 아래로",            "body_action": "두 손 합장하고 고개 숙이기",      "effects": "땀방울"},
    {"slot_id": "10_party",    "emotion": "축하/파티",   "expression": "눈 반달, 입 크게 벌리고 환호",    "body_action": "두 팔 번쩍 들기",                "effects": "폭죽, 색종이 가루"},
    {"slot_id": "11_tired",    "emotion": "피곤/지침",   "expression": "눈 반쯤 감김, 입 힘없이 내려감",  "body_action": "몸 한쪽으로 기울고 늘어짐",       "effects": "ZZZ, 다크서클"},
    {"slot_id": "12_no",       "emotion": "거부/싫어",   "expression": "눈썹 찌푸림, 눈 가늘게",          "body_action": "양손 X자로 교차하며 거절",        "effects": "빨간 X"},
    {"slot_id": "13_work",     "emotion": "출근/좀비",   "expression": "눈 초점 없음, 무표정",            "body_action": "가방 들고 비틀비틀 걷기",         "effects": "좀비 오라, 파리 날림"},
    {"slot_id": "14_off",      "emotion": "퇴근/해방",   "expression": "눈 반달로 활짝, 입 크게 웃음",    "body_action": "가방 집어 던지며 점프",           "effects": "무지개, 빛 폭발"},
    {"slot_id": "15_eat",      "emotion": "밥먹자",      "expression": "눈 초롱초롱, 침 흘림",            "body_action": "숟가락 들고 밥그릇 앞에",         "effects": "김 모락모락, 하트"},
    {"slot_id": "16_coffee",   "emotion": "커피/카페인", "expression": "눈 번쩍 뜨임, 에너지 넘침",       "body_action": "커피잔 들고 원샷",               "effects": "카페인 번개"},
    {"slot_id": "17_sleep",    "emotion": "잠/졸림",     "expression": "눈 완전히 감김, 입 살짝 벌림",    "body_action": "고개 꾸벅꾸벅",                  "effects": "ZZZ 크게, 달과 별"},
    {"slot_id": "18_fighting", "emotion": "응원/파이팅", "expression": "눈 빛남, 투지 넘치는 표정",        "body_action": "주먹 꽉 쥐고 앞으로",            "effects": "파이팅, 불꽃"},
]


def log(agent, msg):
    colors = {"harness": "\033[32m", "analyzer": "\033[35m",
              "designer": "\033[36m", "generator": "\033[33m",
              "gallery": "\033[34m", "github": "\033[33m"}
    c = colors.get(agent, ""); r = "\033[0m"
    print(f"{c}[{agent}]{r}  {msg}")


def save_json(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_image_base64(path):
    ext = Path(path).suffix.lower()
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png", ".webp": "image/webp"}
    media_type = media_map.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode(), media_type


def run_analyzer(image_path):
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


def run_generator(analysis, style):
    log("generator", "프롬프트 작성 중...")

    # 캐릭터 고정 묘사 (분석 결과 반영)
    glasses_desc = ""
    g = analysis.get("glasses", "none")
    if g and "none" not in g.lower() and "no " not in g.lower():
        glasses_desc = f", {g}"

    char_base = (
        f"{analysis.get('hair_color_style','black short hair')}, "
        f"{analysis.get('eye_features','small dark eyes')}"
        f"{glasses_desc}, {analysis.get('outfit','dark suit')}"
    )

    # 스타일 고정: 카카오 병맛 이모티콘 — 표정 극대화, 배경 완전 흰색
    BASE_STYLE = (
        "Korean kakao talk emoticon sticker, "
        "cute chubby chibi character, big round head, tiny body, "
        "short stubby arms and legs, "
        "thick black outlines, clean flat 2D illustration, "
        "PURE WHITE BACKGROUND with absolutely nothing else, "
        "no background elements, no patterns, no shadows, no gradients, "
        "no decorations behind character, only solid white, "
        "ONE single character only, full body centered, "
        "character takes up 70 percent of frame, "
        "no text, no words, no letters"
    )

    # 표정별 감정 강조 키워드
    EMOTION_BOOST = {
        "01_hi":       "bright happy smiling eyes, wide grin, cheerful",
        "02_thanks":   "grateful teary eyes, warm smile, touched expression",
        "03_love":     "heart shaped eyes, blushing cheeks, lovesick face",
        "04_cry":      "crying face, rivers of tears, sad frowning mouth, puffy eyes",
        "05_angry":    "furious red face, steam from head, angry eyebrows, clenched teeth",
        "06_surprise": "shocked wide eyes, dropped jaw, eyebrows flying up",
        "07_lol":      "laughing so hard, tears of joy, mouth wide open, crescent eyes",
        "08_ok":       "winking one eye, thumbs up, confident smirk",
        "09_sorry":    "deeply apologetic, puppy eyes, trembling lip",
        "10_party":    "ecstatic expression, eyes sparkling, huge smile",
        "11_tired":    "exhausted half-closed eyes, drooping mouth, dark circles",
        "12_no":       "stern refusing face, sharp eyes, firm closed mouth",
        "13_work":     "zombie blank stare, empty eyes, expressionless",
        "14_off":      "overjoyed relief expression, jumping happily, eyes shining",
        "15_eat":      "drooling hungry eyes, excited expression, mouth watering",
        "16_coffee":   "energized wide awake eyes, buzzing with energy",
        "17_sleep":    "peacefully sleeping face, closed eyes, slight smile",
        "18_fighting": "determined fierce eyes, clenched fist, fired up expression",
    }

    results = []
    for i, design in enumerate(DESIGNS, 1):
        emotion_detail = EMOTION_BOOST.get(design["slot_id"], "")
        prompt = (
            f"{BASE_STYLE}. "
            f"Character: {char_base}. "
            f"Emotion: {design['emotion']}. "
            f"Expression detail: {emotion_detail}. "
            f"Exaggerated face: {design['expression']}. "
            f"Body pose: {design['body_action']}. "
            f"Effects: {design['effects']}. "
            f"CRITICAL: solid pure white background only, nothing else in background. "
            f"CRITICAL: only ONE single character in the image."
        )
        results.append({
            "slot_id":  design["slot_id"],
            "filename": f"{design['slot_id']}.png",
            "emotion":  design["emotion"],
            "prompt":   prompt
        })
        log("generator", f"  [{i:02d}/18] {design['slot_id']} — {design['emotion']}")
    return results


def clean_background(img_path: Path):
    """이미지 가장자리 흰색 영역 감지 후 배경을 순수 흰색으로 교체"""
    from PIL import Image
    import numpy as np

    img = Image.open(img_path).convert("RGBA")
    data = np.array(img)

    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]

    # 밝은 색 (240 이상) = 배경으로 판단 → 완전 흰색으로
    is_bg = (r > 230) & (g > 230) & (b > 230)
    data[is_bg] = [255, 255, 255, 255]

    result = Image.fromarray(data).convert("RGB")
    result.save(img_path, "PNG")


def generate_images(prompts):
    openai_client = OpenAI()
    log("generator", "DALL-E 3 이미지 생성 시작... (약 4분 소요)")
    EMOTICON_DIR.mkdir(parents=True, exist_ok=True)
    total = len(prompts); success = 0
    for i, item in enumerate(prompts, 1):
        out_path = EMOTICON_DIR / item["filename"]
        if out_path.exists():
            log("generator", f"  [{i:02d}/{total}] 이미 존재, 스킵")
            success += 1; continue
        log("generator", f"  [{i:02d}/{total}] {item['slot_id']} 생성 중...")
        try:
            response = openai_client.images.generate(
                model="dall-e-3", prompt=item["prompt"],
                size="1024x1024", quality="standard", n=1)
            urllib.request.urlretrieve(response.data[0].url, out_path)
            # 배경을 완전 흰색으로 강제 처리
            clean_background(out_path)
            log("generator", f"  OK  {item['filename']} 저장 완료")
            success += 1
        except Exception as e:
            log("generator", f"  FAIL {item['slot_id']}: {e}")
        if i < total:
            time.sleep(13)
    log("generator", f"완료 → {success}/{total}장")


# ── AndyBoy 스타일 갤러리 생성 ────────────────────
def make_gallery(name="나", style="병맛"):
    log("gallery", "gallery.html 생성 중...")
    png_files = sorted(EMOTICON_DIR.glob("*.png"))
    total = len(png_files)

    # 첫 번째 이미지를 대표 이미지로
    main_img = f"emoticons/{png_files[0].name}" if png_files else ""

    # 이모티콘 카드 HTML (4열 그리드)
    cards = ""
    for png in png_files:
        slot_id = png.stem
        num = slot_id.split("_")[0]  # "01"
        emotion = slot_id
        for d in DESIGNS:
            if d["slot_id"] == slot_id:
                emotion = d["emotion"]
                break
        cards += f"""
            <div class="emoti-card" onclick="openModal('emoticons/{png.name}')">
                <div class="emoti-num">{num}</div>
                <img src="emoticons/{png.name}" alt="{emotion}">
                <div class="emoti-label">{emotion}</div>
            </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} 이모티콘</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Apple SD Gothic Neo','Noto Sans KR',sans-serif; background:#f0ede6; color:#222; }}

  /* 상단 네비 */
  nav {{
    background:#2b1d0e;
    display:flex; align-items:center; justify-content:space-between;
    padding:0 32px; height:44px;
  }}
  nav .nav-title {{ color:#f5c518; font-weight:700; font-size:1rem; letter-spacing:1px; }}
  nav .nav-name  {{ color:#fff; font-size:.9rem; }}
  nav .nav-center {{ color:#fff; font-size:.9rem; font-weight:600; }}

  /* 노란 헤더 */
  .hero {{
    background:#f5c518;
    text-align:center;
    padding:28px 20px 24px;
    border-bottom:3px solid #2b1d0e;
  }}
  .hero h1 {{ font-size:2rem; font-weight:900; color:#1a1200; margin-bottom:6px; }}
  .hero p  {{ font-size:.9rem; color:#4a3800; }}

  /* 대표 이미지 영역 */
  .profile-area {{
    text-align:center; padding:32px 20px 16px;
  }}
  .profile-circle {{
    width:120px; height:120px; border-radius:50%;
    border:3px solid #ddd; background:#fff;
    display:inline-flex; align-items:center; justify-content:center;
    overflow:hidden; margin-bottom:16px;
    box-shadow: 0 2px 12px rgba(0,0,0,.1);
  }}
  .profile-circle img {{ width:100%; height:100%; object-fit:cover; }}
  .profile-meta {{
    display:flex; gap:24px; justify-content:center;
    font-size:.82rem; color:#888; margin-top:4px;
  }}
  .profile-meta span {{ display:flex; align-items:center; gap:4px; }}

  /* SPECIAL 섹션 */
  .section-label {{
    text-align:center; font-size:.75rem; font-weight:700;
    letter-spacing:2px; color:#aaa; margin:24px 0 16px;
  }}
  .special-cards {{
    display:flex; gap:16px; justify-content:center;
    padding:0 20px 8px;
  }}
  .special-card {{
    background:#fff; border-radius:14px; padding:16px;
    text-align:center; width:160px;
    box-shadow:0 2px 8px rgba(0,0,0,.08); cursor:pointer;
  }}
  .special-card img {{ width:100%; aspect-ratio:1; object-fit:cover; border-radius:8px; }}
  .special-card .sc-label {{ font-size:.8rem; font-weight:700; color:#333; margin-top:10px; }}
  .special-card .sc-size  {{ font-size:.72rem; color:#aaa; margin-top:2px; }}

  /* EMOTICONS 그리드 */
  .emoti-grid {{
    display:grid;
    grid-template-columns:repeat(4, 1fr);
    gap:12px;
    padding:8px 24px 40px;
    max-width:900px; margin:0 auto;
  }}
  .emoti-card {{
    background:#fff; border-radius:14px; padding:12px 8px 10px;
    text-align:center; position:relative; cursor:pointer;
    box-shadow:0 2px 8px rgba(0,0,0,.07);
    transition:transform .15s, box-shadow .15s;
  }}
  .emoti-card:hover {{ transform:translateY(-3px); box-shadow:0 6px 18px rgba(0,0,0,.13); }}
  .emoti-num {{
    position:absolute; top:8px; left:10px;
    font-size:.68rem; color:#bbb; font-weight:600;
  }}
  .emoti-card img {{ width:100%; aspect-ratio:1; object-fit:cover; border-radius:8px; }}
  .emoti-label {{ font-size:.78rem; color:#555; margin-top:8px; font-weight:500; }}

  /* 모달 */
  .modal {{
    display:none; position:fixed; inset:0;
    background:rgba(0,0,0,.78); z-index:200;
    align-items:center; justify-content:center;
  }}
  .modal.show {{ display:flex; }}
  .modal img {{
    max-width:82vw; max-height:82vh;
    border-radius:16px; box-shadow:0 8px 40px rgba(0,0,0,.5);
  }}
  .modal-close {{
    position:fixed; top:18px; right:26px;
    color:#fff; font-size:2.2rem; cursor:pointer; font-weight:300; line-height:1;
  }}

  footer {{
    text-align:center; padding:24px;
    font-size:.78rem; color:#aaa;
    border-top:1px solid #ddd;
  }}
</style>
</head>
<body>

<!-- 네비게이션 -->
<nav>
  <span class="nav-title">Harness AI</span>
  <span class="nav-center">{name}</span>
  <span class="nav-name">{style} 스타일</span>
</nav>

<!-- 노란 헤더 -->
<div class="hero">
  <h1>{name}</h1>
  <p>{style} 이모티콘 {total}종 세트</p>
</div>

<!-- 대표 이미지 -->
<div class="profile-area">
  <div class="profile-circle">
    {"<img src='" + main_img + "' alt='대표'>" if main_img else ""}
  </div>
  <div class="profile-meta">
    <span>🎭 {total}개 이모티콘</span>
    <span>📐 1024 x 1024px</span>
    <span>🖼 PNG</span>
  </div>
</div>

<!-- SPECIAL -->
<div class="section-label">SPECIAL</div>
<div class="special-cards">
  {"".join([f'''
  <div class="special-card" onclick="openModal('emoticons/{png_files[i].name}')">
    <img src="emoticons/{png_files[i].name}" alt="스페셜">
    <div class="sc-label">{"메인 이미지" if i==0 else "탭 이미지"}</div>
    <div class="sc-size">{"240 x 240px" if i==0 else "96 x 74px"}</div>
  </div>''' for i in range(min(2, len(png_files)))])}
</div>

<!-- EMOTICONS -->
<div class="section-label">EMOTICONS</div>
<div class="emoti-grid">
  {cards}
</div>

<footer>
  Made with Claude + DALL-E 3 &nbsp;|&nbsp; {datetime.now().strftime('%Y.%m.%d')}
</footer>

<!-- 모달 -->
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


# ── GitHub push ───────────────────────────────────
def git_push():
    log("github", "GitHub push 시작...")
    cmds = ["git add output/", 'git commit -m "emoticon update"', "git push origin main"]
    for cmd in cmds:
        result = subprocess.run(cmd, shell=True, capture_output=True, encoding="utf-8", errors="replace")
        if result.stdout.strip(): log("github", f"  {result.stdout.strip()}")
        if result.returncode != 0 and result.stderr.strip():
            log("github", f"  {result.stderr.strip()}")
    log("github", "push 완료!")
    log("github", "주소: https://ProfchoSMU.github.io/HarnessAI/output/gallery.html")


# ── 메인 ─────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image",        default=None)
    parser.add_argument("--style",        default="병맛", choices=STYLES)
    parser.add_argument("--name",         default="나만의 이모티콘")
    parser.add_argument("--gallery-only", action="store_true")
    args = parser.parse_args()

    # 갤러리 + push만
    if args.gallery_only:
        make_gallery(name=args.name, style=args.style)
        print()
        git_push()
        sys.exit(0)

    # 풀 파이프라인
    if not args.image:
        print("사용법: python harness.py --image 파일명.jpg --name 이름")
        print("       python harness.py --gallery-only --name 이름")
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
    log("harness", f"파이프라인 시작 — {args.name} / {args.style}")
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

    make_gallery(name=args.name, style=args.style)
    print()

    git_push()
    print()

    png_count = len(list(EMOTICON_DIR.glob("*.png")))
    log("harness", "=" * 50)
    log("harness", f"완료! 총 {png_count}장 생성")
    log("harness", "주소: https://ProfchoSMU.github.io/HarnessAI/output/gallery.html")
    log("harness", "=" * 50)
