import pandas as pd

past = pd.read_csv("data/past_content_performance.csv")
new = pd.read_csv("data/new_content_info.csv")

# 중복 제거 (C003) -> 69건 기준
clean = past.drop_duplicates(subset="content_id", keep="first").copy()

print("=== 1. 유사도 기준 검증: 신규 5건별 앵커 그룹(type+channel 일치) 크기 ===")
for i, row in new.iterrows():
    anchor = clean[(clean["type"] == row["type"]) & (clean["channel"] == row["channel"])]
    print(f"\n신규 {i+1}. [{row['title']}]")
    print(f"  조건: type={row['type']}, topic_category={row['topic_category']}, channel={row['channel']}, "
          f"posting_hour={row['posting_hour']}, has_emoji={row['has_emoji']}, headline_length={row['headline_length']}")
    print(f"  앵커(type+channel 일치) 후보 수: {len(anchor)}건 -> {'3건 이상, 완화 불필요' if len(anchor) >= 3 else '⚠ 3건 미달, 완화 필요'}")

    # 서브 점수: topic_category 일치(+1), posting_hour 일치(+2), has_emoji 일치(+1)
    sub = anchor.copy()
    sub["score"] = (
        (sub["topic_category"] == row["topic_category"]).astype(int) * 1
        + (sub["posting_hour"] == row["posting_hour"]).astype(int) * 2
        + (sub["has_emoji"] == row["has_emoji"]).astype(int) * 1
    )
    top3 = sub.sort_values(["score", "content_id"], ascending=[False, True]).head(3)
    print("  TOP3 후보:")
    for _, t in top3.iterrows():
        print(f"    {t['content_id']} score={t['score']} ctr={t['ctr']}% engagement={t['engagement_rate']} title={t['title']}")

print("\n=== 2. C069/C070(결측 행)이 앵커 그룹에 걸리는지 확인 ===")
for cid in ["C069", "C070"]:
    r = past[past["content_id"] == cid].iloc[0]
    print(f"  {cid}: type={r['type']}, channel={r['channel']}, topic_category={r['topic_category']}, "
          f"posting_hour={r['posting_hour']}, has_emoji={r['has_emoji']}, ctr={r['ctr']}, "
          f"engagement_rate={r['engagement_rate']}, reach={r['reach']}")

print("\n=== 3. 제목 길이 효과 검증 (소셜 채널 = 인스타그램/유튜브, 블로그 제외) ===")
social = clean[clean["channel"] != "블로그"].copy()
social["length_bucket"] = social["headline_length"].apply(lambda x: "30자 이상" if x >= 30 else "30자 미만")
print(social.groupby("length_bucket")["ctr"].agg(["mean", "count"]).round(2))
