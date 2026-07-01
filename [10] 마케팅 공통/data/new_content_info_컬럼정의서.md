# new_content_info.csv 컬럼 정의서

- 파일 설명: 발행 전 신규 콘텐츠 5건의 속성 정보 (성과 예측 대상)
- 총 행 수: 5
- 총 컬럼 수: 7
- 식별자 컬럼(content_id) 없음 → 행 순서(1~5번째)로 구분

| # | 컬럼명 | 데이터 타입 | 설명 | 값 범위 / 예시 | 결측치 |
|---|---|---|---|---|---|
| 1 | title | string | 콘텐츠 제목 (한글) | "주니어 마케터 6개월 성장기" 등 | 없음 |
| 2 | type | string (범주형) | 콘텐츠 유형 | 숏폼 / 카드뉴스 / 블로그 / 인포그래픽 | 없음 |
| 3 | topic_category | string (범주형) | 콘텐츠 주제 카테고리 | 커리어 / 생산성 / 트렌드 / 후기 | 없음 |
| 4 | channel | string (범주형) | 발행 예정 채널 | 유튜브 / 인스타그램 / 블로그 | 없음 |
| 5 | headline_length | integer | 제목(헤드라인) 글자 수 | 15 ~ 34 | 없음 |
| 6 | has_emoji | boolean | 제목에 이모지 포함 여부 | True / False | 없음 |
| 7 | posting_hour | integer | 게시 예정 시각 (24시간제, 시 단위) | 8 / 12 / 18 / 20 | 없음 |

## 비고
- past_content_performance.csv와 비교했을 때 `content_id`, `ctr`, `engagement_rate`, `reach` 컬럼이 없음 — 이는 아직 발행 전이라 성과가 존재하지 않기 때문(예측 대상).
- 나머지 7개 컬럼은 past_content_performance.csv와 이름·타입·값의 범주가 동일하여 유사 콘텐츠 매칭의 기준 피처로 사용 가능.
