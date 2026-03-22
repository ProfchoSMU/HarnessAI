# 🎭 카카오 이모티콘 자동 생성 하네스

사람 얼굴 이미지 한 장으로 **병맛 카카오 이모티콘 18종**을 자동 생성합니다.
Claude 멀티 에이전트(하네스) 시스템으로 `analyzer → designer → generator` 3단계 파이프라인이 순서대로 실행됩니다.

---

## 📁 파일 구조

```
kakao_emoticon_harness/
├── harness.py              ← 메인 실행 파일 (Python API 버전)
├── multi_agent_harness.py  ← Claude Code 네이티브 버전 프롬프트
├── CLAUDE.md               ← Claude Code 자동 읽기용 지시서
├── README.md               ← 이 파일
└── output/                 ← 생성 결과 (자동 생성)
    ├── analysis.json       ← 캐릭터 분석 결과
    ├── design_brief.json   ← 18종 이모티콘 기획서
    ├── prompts.json        ← 이미지 생성 프롬프트 (JSON)
    └── prompts.txt         ← 이미지 생성 프롬프트 (텍스트)
```

---

## 🚀 실행 방법

### 방법 1: Python 직접 실행

```bash
# 설치
pip install anthropic

# API 키 설정
export ANTHROPIC_API_KEY="sk-ant-..."

# 실행
python harness.py --image 내얼굴.jpg
python harness.py --image 내얼굴.jpg --style 병맛
python harness.py --image 내얼굴.jpg --style 귀여운
```

**스타일 옵션**: `병맛` / `귀여운` / `감성` / `폭발적`

---

### 방법 2: Claude Code (화면에서 본 그 방식!)

```bash
# Claude Code 설치
npm install -g @anthropic-ai/claude-code

# 프로젝트 폴더에서 실행
cd kakao_emoticon_harness
claude
```

Claude Code가 열리면:
```
> 내 얼굴 사진(face.jpg)으로 병맛 카카오 이모티콘 18종 만들어줘
```

Claude Code는 CLAUDE.md를 자동으로 읽고 harness.py를 실행합니다.

---

## 🤖 에이전트 역할

| 에이전트 | 역할 | 입력 | 출력 |
|---------|------|------|------|
| **analyzer** | 얼굴 특징·분위기 분석 | 이미지 파일 | analysis.json |
| **designer** | 18종 구도·표정·이펙트 기획 | analysis.json | design_brief.json |
| **generator** | 이미지 생성 프롬프트 완성 | 위 두 파일 | prompts.txt |

---

## 🎨 18종 이모티콘 슬롯

```
01 반가워     02 감사      03 화났어    04 눈물
05 당황       06 수줍      07 졸림      08 하트
09 파이팅     10 놀람      11 빵터짐    12 슬픔
13 부탁해     14 싫어      15 오케이    16 헉
17 어색       18 배고파
```

---

## 📤 최종 결과물 활용

`output/prompts.txt` 파일이 생성되면:

1. **DALL-E 3** — OpenAI API에 각 프롬프트 입력
2. **Midjourney** — Discord에서 `/imagine` + 프롬프트
3. **Stable Diffusion** — ComfyUI/A1111에 프롬프트 입력
4. **Adobe Firefly** — 웹에서 직접 붙여넣기

생성된 PNG 파일들을 **카카오 이모티콘 스튜디오**에 업로드하면 심사 신청 가능합니다.
→ https://emoticonstudio.kakao.com

---

## 💡 팁

- **병맛이 핵심**: analyzer가 과장 포인트를 찾아내므로 특징 있는 사진일수록 좋음
- **정면 사진 권장**: 분석 정확도 향상
- **고해상도 선호**: 최소 512×512px 이상
- **스타일 실험**: 같은 사진으로 `병맛`, `귀여운` 두 버전 만들어보기

---

## ⚠️ 주의사항

- `ANTHROPIC_API_KEY` 환경변수 필수
- 이미지 생성 단계는 별도 API (DALL-E 등) 필요
- 카카오 이모티콘 제출 시 원저작권 및 초상권 확인 필요
