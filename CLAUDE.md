# 카카오 이모티콘 자동 생성 하네스

## 프로젝트 설명
사람 이미지를 입력받아 병맛 카카오톡 이모티콘 18종을 자동으로 생성하는 멀티 에이전트 시스템.

## 에이전트 구조
1. **analyzer** - 이미지에서 얼굴 특징·표정·분위기를 분석하고 JSON으로 요약
2. **designer** - 분석 결과를 바탕으로 18종 이모티콘 시나리오·구도·표정을 기획
3. **generator** - 각 이모티콘의 이미지 생성 프롬프트를 완성하고 파일로 저장

## 실행
```
python harness.py --image path/to/face.jpg
```

## 출력
- `output/emoticons/` 폴더에 PNG 18장
- `output/design_brief.json` — 기획서
- `output/prompts.txt` — 각 이미지 생성에 사용한 프롬프트 목록
