"""
도메인 시프트 검증용 더미 데이터 생성 + 통계 검증 (검증 전용 — 리포트 생성에는 관여하지 않음)

"입력 데이터가 바뀌면(예: 시간이 지나 플랫폼 알고리즘·소비자 행태가 바뀌면) CTR에 영향을
미치는 축 자체가 달라질 수 있다"는 도메인적 가설(decisions.md 최신 항목 참고)을 확인하기 위한 스크립트.

실제 past_content_performance.csv(69건)와 표본 크기는 비슷하게 맞추되, 의도적으로 다른
데이터 생성 과정(DGP)으로 더미 데이터를 만든다.
- posting_hour 효과 제거: 알고리즘이 실시간 노출 대신 추천 기반 노출로 바뀌었다고 가정
- has_emoji 효과 제거: 이모지 사용이 보편화돼 더 이상 차별화 요인이 아니라고 가정
- topic_category 효과 신규 부여: 트렌드/이슈 소재가 급부상했다고 가정 (원본에서는 CTR과 무관했던 축, decisions.md 58번 항목)
- type/channel 포맷·플랫폼 효과는 유지: 콘텐츠 소비 방식의 근본 차이는 알고리즘 변화와 무관하게 유지된다고 가정

원본과 동일한 방법론(일원배치 ANOVA·Welch t-test·Pearson 상관)으로 재검증해 유의성 판정이
실제로 달라지는지 확인한다.

사용법:
    py scripts/_verify_domain_shift.py
"""
import random
import pandas as pd
from scipy import stats

random.seed(7)

TYPES_N = [("카드뉴스", 18), ("숏폼", 18), ("블로그", 18), ("인포그래픽", 15)]
TOPICS = ["생산성", "커리어", "트렌드", "후기"]
HOURS = [8, 12, 18, 20]

TYPE_CHANNEL_BIAS = {
    "카드뉴스": {"인스타그램": 0.7, "유튜브": 0.1, "블로그": 0.2},
    "숏폼": {"유튜브": 0.6, "인스타그램": 0.35, "블로그": 0.05},
    "블로그": {"블로그": 0.9, "유튜브": 0.05, "인스타그램": 0.05},
    "인포그래픽": {"인스타그램": 0.5, "블로그": 0.3, "유튜브": 0.2},
}

BASE_CTR = {"카드뉴스": 3.5, "숏폼": 4.0, "블로그": 2.8, "인포그래픽": 2.9}   # 포맷 효과: 원본과 동일하게 유지
CHANNEL_BONUS = {"유튜브": 0.3, "인스타그램": 0.1, "블로그": -0.1}            # 플랫폼 효과: 원본과 동일하게 유지
TOPIC_BONUS = {"트렌드": 1.0, "후기": 0.6, "커리어": 0.1, "생산성": -0.3}      # 신규: 이번엔 유의하도록 설계
# posting_hour, has_emoji는 CTR 산식에서 완전히 제외 -> 원본과 반대로 "무관"하게 설계

rows = []
cid = 1
for type_, n in TYPES_N:
    channels = list(TYPE_CHANNEL_BIAS[type_].keys())
    weights = list(TYPE_CHANNEL_BIAS[type_].values())
    for _ in range(n):
        channel = random.choices(channels, weights=weights)[0]
        topic = random.choice(TOPICS)
        hour = random.choice(HOURS)
        emoji = random.random() < 0.5
        length = random.randint(10, 32)

        ctr = (BASE_CTR[type_] + CHANNEL_BONUS[channel] + TOPIC_BONUS[topic]
               + random.gauss(0, 0.4))  # hour/emoji 항 없음 -> 순수 노이즈로만 반영됨
        ctr = max(0.5, round(ctr, 1))
        engagement = round(max(0.5, ctr * 1.6 + random.gauss(0, 0.5)), 1)
        reach = random.randint(4000, 48000)

        rows.append({
            "content_id": f"T{cid:03d}",
            "title": f"[도메인시프트 검증용] {type_}-{topic}-{channel}-{hour}시 샘플 {cid}",
            "type": type_, "topic_category": topic, "channel": channel,
            "ctr": ctr, "engagement_rate": engagement, "reach": reach,
            "headline_length": length, "has_emoji": emoji, "posting_hour": hour,
        })
        cid += 1

df = pd.DataFrame(rows)
df.to_csv("output/_verify/dummy_test.csv", index=False)
print(f"dummy_test.csv 생성: {len(df)}행 -> output/_verify/dummy_test.csv\n")


def anova(data, col):
    groups = [g.values for _, g in data.groupby(col)["ctr"]]
    f, p = stats.f_oneway(*groups)
    grand_mean = data["ctr"].mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_total = ((data["ctr"] - grand_mean) ** 2).sum()
    eta2 = ss_between / ss_total
    return f, p, eta2


print(f"=== ANOVA / t-test / 상관분석 (dummy_test.csv, n={len(df)}) ===\n")
print("원본(decisions.md 58번 항목, 69건) 대비 유의성 변화 확인용\n")

for col, label in [("type", "type"), ("channel", "channel"),
                    ("posting_hour", "posting_hour"), ("topic_category", "topic_category")]:
    f, p, eta2 = anova(df, col)
    sig = "유의함" if p < 0.05 else "유의하지 않음"
    means = df.groupby(col)["ctr"].mean().round(2).to_dict()
    print(f"[{label}] F={f:.2f}, p={p:.4f}, eta2={eta2:.3f} -> {sig}")
    print(f"  그룹 평균: {means}\n")

true_grp = df[df["has_emoji"] == True]["ctr"]
false_grp = df[df["has_emoji"] == False]["ctr"]
t, p = stats.ttest_ind(true_grp, false_grp, equal_var=False)
sig = "유의함" if p < 0.05 else "유의하지 않음"
print(f"[has_emoji] Welch t={t:.2f}, p={p:.4f} -> {sig}")
print(f"  True 평균={true_grp.mean():.2f}(n={len(true_grp)}), False 평균={false_grp.mean():.2f}(n={len(false_grp)})\n")

r, p = stats.pearsonr(df["headline_length"], df["ctr"])
sig = "유의함" if p < 0.05 else "유의하지 않음"
print(f"[headline_length, 전체] Pearson r={r:.3f}, p={p:.4f} -> {sig}")

social = df[df["channel"] != "블로그"]
r_s, p_s = stats.pearsonr(social["headline_length"], social["ctr"])
sig_s = "유의함" if p_s < 0.05 else "유의하지 않음"
print(f"[headline_length, 소셜(블로그 제외)] Pearson r={r_s:.3f}, p={p_s:.4f} -> {sig_s}")
