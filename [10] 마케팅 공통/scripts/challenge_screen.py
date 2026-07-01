import pandas as pd

past = pd.read_csv("data/past_content_performance.csv")
clean = past.drop_duplicates(subset="content_id", keep="first").copy()
N = len(clean)
print(f"기준: 중복 제거 {N}건\n")

print("=== 1. 발행 시간대 분포 vs 성과 ===")
hour_stats = clean.groupby("posting_hour")["ctr"].agg(["mean", "count"])
hour_stats["비중"] = (hour_stats["count"] / N * 100).round(1)
print(hour_stats.round(2))
suboptimal = clean[clean["posting_hour"].isin([8, 12])]
print(f"\n저녁(18/20시) 외 시간대(8/12시) 발행 비중: {len(suboptimal)}/{N} = {len(suboptimal)/N*100:.1f}%")

print("\n=== 2. 이모지 포함 여부 분포 vs 성과 ===")
emoji_stats = clean.groupby("has_emoji")["ctr"].agg(["mean", "count"])
emoji_stats["비중"] = (emoji_stats["count"] / N * 100).round(1)
print(emoji_stats.round(2))

print("\n=== 3. 유형×채널 조합별 발행량 vs 성과 (볼륨-성과 불일치 탐색) ===")
combo = clean.groupby(["type", "channel"]).agg(ctr_mean=("ctr", "mean"), n=("ctr", "count")).reset_index()
combo["비중"] = (combo["n"] / N * 100).round(1)
combo = combo.sort_values("n", ascending=False)
print(combo.round(2).to_string(index=False))

overall_avg_ctr = clean["ctr"].mean()
print(f"\n전체 평균 CTR: {overall_avg_ctr:.2f}%")
print("\n[저성과인데 발행량 많은 조합] (평균 미달 + 상위 40% 볼륨)")
vol_threshold = combo["n"].quantile(0.6)
low_perf_high_vol = combo[(combo["ctr_mean"] < overall_avg_ctr) & (combo["n"] >= vol_threshold)]
print(low_perf_high_vol.round(2).to_string(index=False))

print("\n[고성과인데 발행량 적은 조합] (평균 이상 + 하위 40% 볼륨)")
high_perf_low_vol = combo[(combo["ctr_mean"] > overall_avg_ctr) & (combo["n"] <= combo["n"].quantile(0.4))]
print(high_perf_low_vol.round(2).to_string(index=False))

print("\n=== 4. 주제 카테고리별 발행량 vs 인게이지먼트 ===")
topic_stats = clean.groupby("topic_category").agg(
    eng_mean=("engagement_rate", "mean"), n=("engagement_rate", "count")
)
topic_stats["비중"] = (topic_stats["n"] / N * 100).round(1)
print(topic_stats.round(2))
