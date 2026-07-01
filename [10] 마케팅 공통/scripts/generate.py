import pandas as pd

past = pd.read_csv("data/past_content_performance.csv")
new = pd.read_csv("data/new_content_info.csv")
clean = past.drop_duplicates(subset="content_id", keep="first").copy()

WEIGHTS = {"posting_hour": 2, "topic_category": 1, "has_emoji": 1}


def get_top3(row):
    anchor = clean[(clean["type"] == row["type"]) & (clean["channel"] == row["channel"])].copy()
    relax_note = "type+channel 앵커 유지"
    if len(anchor) < 3:
        anchor = clean[clean["type"] == row["type"]].copy()
        relax_note = "후보 부족 -> channel 조건 완화(type만 유지)"
    if len(anchor) < 3:
        anchor = clean.copy()
        relax_note = "후보 부족 -> type까지 완화(전체 대상)"

    anchor["score"] = (
        (anchor["topic_category"] == row["topic_category"]).astype(int) * WEIGHTS["topic_category"]
        + (anchor["posting_hour"] == row["posting_hour"]).astype(int) * WEIGHTS["posting_hour"]
        + (anchor["has_emoji"] == row["has_emoji"]).astype(int) * WEIGHTS["has_emoji"]
    )
    top3 = anchor.sort_values(["score", "content_id"], ascending=[False, True]).head(3)
    return top3, len(anchor), relax_note


print("=== 신규 5건 유사 TOP3 + CTR 범위 ===")
for i, row in new.iterrows():
    top3, anchor_n, note = get_top3(row)
    ctr_min, ctr_max = top3["ctr"].min(), top3["ctr"].max()
    max_score = top3["score"].max()
    print(f"\n--- 신규 {i+1}: {row['title']} ---")
    print(f"앵커 후보 수: {anchor_n} ({note})")
    print(f"예상 CTR 범위: {ctr_min}% ~ {ctr_max}%  (최고 서브점수: {max_score}/4)")
    for _, t in top3.iterrows():
        eng = t["engagement_rate"] if pd.notna(t["engagement_rate"]) else "N/A(결측)"
        print(f"  [{t['content_id']}] score={t['score']} ctr={t['ctr']}% engagement={eng} | {t['title']}")

print("\n\n=== 개선 제안용 세부 수치 ===")

print("\n[1] type x channel 매트릭스 (전체 평균 CTR)")
matrix = clean.groupby(["type", "channel"])["ctr"].mean().round(2)
print(matrix)

print("\n[2] 앵커별 posting_hour 효과 (해당 type+channel 내에서)")
for (t, c) in [("숏폼", "유튜브"), ("카드뉴스", "인스타그램"), ("블로그", "블로그"), ("인포그래픽", "인스타그램"), ("숏폼", "인스타그램")]:
    sub = clean[(clean["type"] == t) & (clean["channel"] == c)]
    g = sub.groupby("posting_hour")["ctr"].agg(["mean", "count"]).round(2)
    print(f"  {t}-{c}:\n{g}\n")

print("\n[3] 앵커별 has_emoji 효과 (해당 type+channel 내에서)")
for (t, c) in [("숏폼", "유튜브"), ("카드뉴스", "인스타그램"), ("블로그", "블로그"), ("인포그래픽", "인스타그램"), ("숏폼", "인스타그램")]:
    sub = clean[(clean["type"] == t) & (clean["channel"] == c)]
    g = sub.groupby("has_emoji")["ctr"].agg(["mean", "count"]).round(2)
    print(f"  {t}-{c}:\n{g}\n")

print("\n[4] 숏폼-유튜브 내 topic_category별 평균 CTR (신규1 참고)")
sub = clean[(clean["type"] == "숏폼") & (clean["channel"] == "유튜브")]
print(sub.groupby("topic_category")["ctr"].agg(["mean", "count"]).round(2))
