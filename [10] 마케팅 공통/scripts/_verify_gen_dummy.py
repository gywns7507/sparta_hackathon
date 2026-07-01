"""
파이프라인 검증용 더미 데이터 생성기 (제출물 아님, 검증 전용)
past_content_performance.csv / new_content_info.csv와 동일한 스키마로 완전히 새로운 값을 채운
더미 데이터를 만들어 scripts/pipeline.py가 다른 데이터셋에도 정상 동작하는지 확인한다.
"""
import random
import pandas as pd

random.seed(42)

TYPES_CHANNELS_N = [
    ("카드뉴스", 16),
    ("숏폼", 16),
    ("블로그", 16),
    ("인포그래픽", 2),  # 의도적으로 희소하게 -> "type까지 완화" fallback을 유도
]
TOPICS = ["생산성", "커리어", "트렌드", "후기"]
HOURS = [8, 12, 18, 20]

TYPE_CHANNEL_BIAS = {
    "카드뉴스": {"인스타그램": 0.7, "유튜브": 0.1, "블로그": 0.2},
    "숏폼": {"유튜브": 0.6, "인스타그램": 0.35, "블로그": 0.05},
    "블로그": {"블로그": 0.9, "유튜브": 0.05, "인스타그램": 0.05},
    "인포그래픽": {"인스타그램": 0.5, "블로그": 0.3, "유튜브": 0.2},
}

BASE_CTR = {"카드뉴스": 3.5, "숏폼": 4.0, "블로그": 2.8, "인포그래픽": 2.9}
HOUR_BONUS = {8: -0.6, 12: -0.2, 18: 0.4, 20: 0.7}
EMOJI_BONUS = 0.9
CHANNEL_BONUS = {"유튜브": 0.3, "인스타그램": 0.1, "블로그": -0.1}

rows = []
cid = 1
for type_, n in TYPES_CHANNELS_N:
    channels = list(TYPE_CHANNEL_BIAS[type_].keys())
    weights = list(TYPE_CHANNEL_BIAS[type_].values())
    for i in range(n):
        channel = random.choices(channels, weights=weights)[0]
        topic = random.choice(TOPICS)
        hour = random.choice(HOURS)
        emoji = random.random() < 0.65
        length = random.randint(10, 32)

        ctr = (BASE_CTR[type_] + HOUR_BONUS[hour] + CHANNEL_BONUS[channel]
               + (EMOJI_BONUS if emoji else 0) + random.gauss(0, 0.3))
        ctr = max(0.5, round(ctr, 1))
        engagement = round(max(0.5, ctr * 1.6 + random.gauss(0, 0.5)), 1)
        reach = random.randint(4000, 48000)

        rows.append({
            "content_id": f"D{cid:03d}",
            "title": f"[검증용] {type_}-{topic}-{channel}-{hour}시 샘플 {cid}",
            "type": type_, "topic_category": topic, "channel": channel,
            "ctr": ctr, "engagement_rate": engagement, "reach": reach,
            "headline_length": length, "has_emoji": emoji, "posting_hour": hour,
        })
        cid += 1

# 완전 중복행 1건 추가 (D003 복제 -> 원본 C003 중복 케이스 재현)
rows.append(dict(rows[2]))

# 결측 2건 재현: 마지막-1행 engagement_rate 결측, 마지막행 reach 결측
rows[-2] = {**rows[-2], "engagement_rate": ""}
rows[-1] = {**rows[-1], "reach": ""}

past_df = pd.DataFrame(rows)
past_df.to_csv("output/_verify/dummy_past_content_performance.csv", index=False)

new_rows = [
    {"title": "퇴근길에 듣는 생산성 꿀팁", "type": "숏폼", "topic_category": "생산성",
     "channel": "유튜브", "headline_length": 14, "has_emoji": True, "posting_hour": 20},
    {"title": "블로그에서 보는 이번주 트렌드 카드", "type": "카드뉴스", "topic_category": "트렌드",
     "channel": "블로그", "headline_length": 28, "has_emoji": False, "posting_hour": 12},
    {"title": "후기 모아보는 인포그래픽 한장 정리", "type": "인포그래픽", "topic_category": "후기",
     "channel": "인스타그램", "headline_length": 16, "has_emoji": True, "posting_hour": 18},
    {"title": "유튜브에 올리는 커리어 블로그 아티클", "type": "블로그", "topic_category": "커리어",
     "channel": "유튜브", "headline_length": 30, "has_emoji": False, "posting_hour": 8},
    {"title": "점심시간 트렌드 숏폼 요약", "type": "숏폼", "topic_category": "트렌드",
     "channel": "인스타그램", "headline_length": 20, "has_emoji": False, "posting_hour": 12},
    {"title": "생산성 카드뉴스 저녁 발행", "type": "카드뉴스", "topic_category": "생산성",
     "channel": "인스타그램", "headline_length": 10, "has_emoji": True, "posting_hour": 20},
]
new_df = pd.DataFrame(new_rows)
new_df.to_csv("output/_verify/dummy_new_content_info.csv", index=False)

print(f"past rows: {len(past_df)} (dedup 전), type별 개수:\n{past_df['type'].value_counts()}")
print(f"\nnew rows: {len(new_df)}")
