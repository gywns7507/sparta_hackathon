import pandas as pd

past = pd.read_csv("data/past_content_performance.csv")
new = pd.read_csv("data/new_content_info.csv")

print("=== 1. 구조 확인 ===")
print(f"past_content_performance.csv: {past.shape[0]}행, 컬럼: {list(past.columns)}")
print(f"new_content_info.csv: {new.shape[0]}행, 컬럼: {list(new.columns)}")

for col in ["type", "topic_category", "channel", "posting_hour", "has_emoji"]:
    print(f"  {col}: {sorted(past[col].dropna().unique().tolist())}")

print("\n=== 2. 데이터 품질 점검 ===")

print("[결측치]")
missing = past[past[["ctr", "engagement_rate", "reach"]].isna().any(axis=1)]
print(missing[["content_id", "ctr", "engagement_rate", "reach"]])

print("\n[완전 중복 content_id]")
dup_ids = past[past.duplicated(subset="content_id", keep=False)]
print(dup_ids[["content_id", "title", "ctr", "engagement_rate", "reach"]])

print(f"\n[has_emoji dtype] {past['has_emoji'].dtype}")
print(f"  샘플 값: {past['has_emoji'].unique()}")
if past["has_emoji"].dtype == object:
    print("  -> 문자열 'True'/'False'로 로드됨. 불리언 변환 필요.")
else:
    print("  -> pandas가 자동으로 bool 타입으로 인식함 (변환 불필요, 확인만 하면 됨).")

print("\n=== 3. 성과 패턴 분포 (중복 제거 69건 기준) ===")
clean = past.drop_duplicates(subset="content_id", keep="first").copy()
if clean["has_emoji"].dtype == object:
    clean["has_emoji_bool"] = clean["has_emoji"].map({"True": True, "False": False})
else:
    clean["has_emoji_bool"] = clean["has_emoji"].astype(bool)
print(f"중복 제거 후 행수: {clean.shape[0]}")

print("\n[posting_hour별 평균 CTR]")
print(clean.groupby("posting_hour")["ctr"].agg(["mean", "count"]).round(2))

print("\n[has_emoji별 평균 CTR]")
print(clean.groupby("has_emoji_bool")["ctr"].agg(["mean", "count"]).round(2))

print("\n[type x channel별 평균 CTR]")
print(clean.groupby(["type", "channel"])["ctr"].agg(["mean", "count"]).round(2))

print("\n[topic_category별 평균 engagement_rate] (결측 2건 제외)")
print(clean.groupby("topic_category")["engagement_rate"].agg(["mean", "count"]).round(2))

print("\n=== 신규 콘텐츠 5건 ===")
print(new.to_string(index=False))
