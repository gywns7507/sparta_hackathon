# AX 해커톤 — [10] 마케팅 공통: 콘텐츠 성과 예측기

> **모든 작업물은 [`[10] 마케팅 공통/`](./%5B10%5D%20%EB%A7%88%EC%BC%80%ED%8C%85%20%EA%B3%B5%ED%86%B5/) 폴더 안에 있습니다.**
> 이 README는 저장소 루트 안내용이며, 실제 코드·데이터·리포트를 보려면 반드시 위 폴더로 들어가야 합니다.

---

## 1. 어떤 과제인가

콘텐츠 마케터가 콘텐츠를 발행하기 **직전** 흔히 하는 고민 —
"이거 올리면 반응이 어떨까?" — 를 감이 아니라 **과거 성과 데이터**로 진단하는 과제입니다.

- 트랙: 마케팅 (직무 공통) / 채용 TO: 콘텐츠 마케터·그로스 마케터
- 특정 기업에 종속되지 않은 마케터 직무 공통 시나리오 (인스타그램·블로그·유튜브에 카드뉴스·숏폼·블로그·인포그래픽을 발행하고 CTR·인게이지먼트율로 성과를 측정)
- **ML 예측 모델 과제가 아님**: 데이터가 70행뿐이라 학습 기반 예측은 과적합 위험이 큼 → 대신 "유사 콘텐츠의 실제 과거 성과"로 기대 범위를 제시하는 **패턴 기반 진단**을 수행

과제 원문 전체는 [`problem.md`](<./[10] 마케팅 공통/problem.md>), Claude Code 작업 지시문은 [`CLAUDE.md`](<./[10] 마케팅 공통/CLAUDE.md>)에 있습니다.

## 2. 문제 정의

마케터는 콘텐츠 발행 전 반응을 예측할 방법이 마땅치 않습니다.

- 발행 전 반응 예측을 **감(感)** 에 의존
- 과거 성과 데이터가 있어도 패턴을 분석해 적용하기 번거로움
- A/B 테스트는 발행 **후** 비교라 발행 **전** 방향을 검증할 수 없어 저성과 콘텐츠를 그대로 발행
- 유사 콘텐츠를 찾아 벤치마크하는 일을 매번 수동으로 반복

→ 결과적으로 저성과가 예상되는 콘텐츠를 거르지 못하고, 시간대·포맷·제목 선택이 데이터 근거 없이 반복됩니다.

**미션**: 신규 콘텐츠 5건(`data/new_content_info.csv`)을 입력받아, 과거 성과 69건(`data/past_content_performance.csv`, 중복 제거 기준)의 패턴을 근거로 ①예상 CTR 범위, ②유사 콘텐츠 TOP3 비교표, ③데이터 근거가 있는 개선 제안 2가지를 담은 리포트를 생성합니다.

## 3. 단계별 문제 해결 과정

작업은 `.claude/skills/`에 정의된 4단계 커스텀 명령(`/analyze` → `/insight` → `/generate` → `/review`)을 순서대로 밟아 진행했고, 각 단계의 중요한 판단은 전부 [`decisions.md`](<./[10] 마케팅 공통/decisions.md>)에 근거와 함께 기록했습니다.

| 단계 | 무엇을 했나 | 핵심 산출물 |
|---|---|---|
| **1. `/analyze`** (데이터 파악) | 결측치(C069 engagement_rate, C070 reach)·완전 중복행(C003) 탐지 및 처리 방침 결정, `has_emoji` 타입 확인, posting_hour·has_emoji·type×channel별 CTR 패턴 산출 | `scripts/analyze.py` |
| **2. `/insight`** (유사도 설계) | 유사도 기준을 "앵커(type+channel 필수 일치) + 서브점수(posting_hour·has_emoji·topic_category 가중치)" 방식으로 설계 → 이후 ANOVA·t-test·상관분석으로 가중치를 통계적으로 재검증하고 `topic_category` 가중치를 0으로 조정 | `scripts/insight.py` |
| **3. `/generate`** (리포트 생성 — Basic/Standard/Challenge) | Python(유사도·정렬 계산) + Claude(수치 해석·제안 문구) 역할 분담으로 신규 5건 진단 리포트 작성. Standard에서 전 과정을 재사용 가능한 파이프라인으로 코드화, Challenge에서 팀 차원 발행 전략 기획안을 자동 산출하는 로직까지 추가 | `scripts/pipeline.py`, `scripts/challenge_screen.py` |
| **4. `/review`** (자가 점검) | Basic/Standard/Challenge 채점 기준별 자가 점검, 소표본(n<2) 신뢰도 라벨 누락 등 보완 | `content_prediction_report.md` 최종본에 반영 |

과정 중 발견해 수정한 대표적인 이슈 (자세한 내용은 `decisions.md` 참고):
- 유사도 앵커를 `type`까지 완화하면 서로 다른 포맷이 섞여 비교되는 버그 → 완전히 새로운 더미 데이터(`scripts/_verify_gen_dummy.py`)로 스트레스 테스트해 발견·수정
- `topic_category` 가중치가 통계적으로 무근거임을 ANOVA로 확인 → 서브점수에서 제외하고 리포트 전체를 재계산
- 소표본(n<5) 지역 신호로 "이미 최적인 조건을 바꾸라"고 제안하는 노이즈 발생 → 억제 로직 추가

## 4. 폴더/파일 구조

```
[10] 마케팅 공통/
├── problem.md                  # 과제 원문 (문제 정의·미션·채점 기준)
├── CLAUDE.md                   # Claude Code용 작업 진행 가이드
├── design-conversation.md      # (참고) 과제 설계자의 문제 설계 배경 기록
├── decisions.md                # ★ 전 과정 의사결정 로그 — 판단 근거를 확인하려면 여기
├── streamlit_app.py             # ★ HTML 대시보드(sample-final.html) 배포용 Streamlit 앱
├── requirements.txt             # 실행 의존성 (pandas·numpy·scipy·streamlit 등)
│
├── .claude/skills/              # 커스텀 슬래시 명령 정의
│   ├── analyze.md               #   /analyze  — 데이터 파악
│   ├── insight.md                #   /insight  — 유사도 기준 설계
│   ├── generate.md               #   /generate — 리포트 생성
│   └── review.md                 #   /review   — 제출 전 자가 점검
│
├── context/                     # 도메인 지식 (힌트 자료)
│   ├── company-info.md          #   유사 콘텐츠 TOP3 찾는 법·개선 제안 방법론
│   └── industry-news.md         #   시간대·채널별 CTR 업계 통설
│
├── data/                        # 입력 데이터
│   ├── past_content_performance.csv          # 과거 성과 70건 (중복 1·결측 2건 포함)
│   ├── past_content_performance_컬럼정의서.md
│   ├── new_content_info.csv                  # 진단 대상 신규 콘텐츠 5건
│   └── new_content_info_컬럼정의서.md
│
├── scripts/                      # 실행 코드
│   ├── analyze.py                 #   1단계: 결측·중복·성과 패턴 탐색
│   ├── insight.py                 #   2단계: 유사도 기준 검증용 스크립트
│   ├── generate.py                #   3단계 초안: 신규 5건 TOP3·CTR 범위 계산
│   ├── pipeline.py                #   ★ 최종 재사용 파이프라인 (Basic~Challenge 전체 재현)
│   ├── challenge_screen.py        #   Challenge: 팀 차원 전략 후보 스크리닝
│   └── _verify_gen_dummy.py       #   (검증 전용) 파이프라인 검증용 더미 데이터 생성기
│
└── output/                       # 산출물
    ├── content_prediction_report.md            # ★★ 최종 제출 리포트 (Basic+Standard+Challenge 통합)
    ├── content_prediction_report_pipeline_sample.md  # pipeline.py 원본 산출값 (재현성 검증용)
    ├── example_new_content_alt.csv / example_report_alt.md  # 다른 입력 3건으로 재현성 검증한 결과
    ├── sample-basic.html / sample-standard.html / sample-challenge.html  # 단계별 HTML 시각화
    ├── sample-final.html                       # ★★ 최종 통합 HTML 시각화 리포트
    ├── template.md                             # (참고) 과제 제공 제출 템플릿, 작업물 아님
    ├── my_test_report.md                       # 개발 중 테스트용 산출물
    └── _verify/                                # 더미 데이터 스트레스 테스트 산출물 (검증 전용)
```

## 5. 최종 결과물을 확인하는 방법

가장 빠르게 확인하려면 아래 순서를 권장합니다.

1. **웹 대시보드로 보기 (Streamlit 배포)**
   ```bash
   cd "[10] 마케팅 공통"
   pip install -r requirements.txt
   streamlit run streamlit_app.py
   ```
   [`streamlit_app.py`](<./[10] 마케팅 공통/streamlit_app.py>)가 `output/sample-final.html`을 그대로 불러와 브라우저 대시보드로 띄웁니다. 로컬 확인용이며, Streamlit Community Cloud 등에 그대로 배포해 URL로 공유할 수도 있습니다(레포지토리·`streamlit_app.py` 경로·`requirements.txt`만 지정하면 됨).

2. **파일만 빠르게 보기 (배포 없이)**
   - [`output/sample-final.html`](<./[10] 마케팅 공통/output/sample-final.html>)을 브라우저로 직접 열기 — 진단 결과·비교표·전략 기획안을 시각화한 최종 통합 리포트
   - 텍스트로 보려면 [`output/content_prediction_report.md`](<./[10] 마케팅 공통/output/content_prediction_report.md>) 확인 (제출 기준 최종 리포트, Basic 필수 항목 + Standard 파이프라인 설명 + Challenge 전략 기획안 포함)

3. **판단 근거를 확인하고 싶다면**
   - [`decisions.md`](<./[10] 마케팅 공통/decisions.md>)에서 유사도 기준, 결측·중복 처리, 통계 검증(ANOVA·t-test), 버그 수정 이력을 시간순으로 확인

4. **파이프라인을 직접 재현해보고 싶다면** (Python 3 + `pip install -r requirements.txt` 필요)
   ```bash
   cd "[10] 마케팅 공통"
   pip install -r requirements.txt

   # 기본 실행 (data/의 기본 CSV로 리포트 재생성)
   py scripts/pipeline.py

   # 다른 신규 콘텐츠 CSV로 재현성 검증
   py scripts/pipeline.py --new data/new_content_info.csv --out output/content_prediction_report.md

   # Challenge: 발행 전략 기획안 섹션까지 포함
   py scripts/pipeline.py --strategy
   ```
   `--new`에 동일한 컬럼 구조(`title/type/topic_category/channel/headline_length/has_emoji/posting_hour`)의 다른 CSV 경로를 넣으면, 몇 건이든 동일한 절차(정제 → 유사 TOP3 → CTR 범위 → 개선 제안 → 리포트)로 새 리포트가 생성됩니다. 이미 다른 입력으로 검증한 결과는 `output/example_report_alt.md`, 극단적인 더미 데이터로 검증한 결과는 `output/_verify/dummy_report.md`에서 확인할 수 있습니다.
