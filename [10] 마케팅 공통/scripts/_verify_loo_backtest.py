"""
Leave-one-out 백테스트 (검증 전용 — 리포트 생성에는 관여하지 않음)

topic_category를 유사도 가중치에서 제외한 결정(decisions.md 참고)이 "단순히 다른 결과"를
낸 것인지, 실제로 예측 정확도를 개선한 것인지 확인하기 위한 스크립트.

과거 69건 각각을 하나씩 숨기고(hold-out), 나머지 68건으로 pipeline.py의 similarity_top3()와
동일한 앵커+가중치 로직으로 CTR 범위를 예측한 뒤 실제 CTR과 비교한다. OLD(topic_category=1,
검증 전 가중치)와 NEW(topic_category=0, ANOVA 검증 후 가중치) 두 스킴을 동일 조건에서 비교.

사용법:
    py scripts/_verify_loo_backtest.py
"""
import argparse
import pandas as pd
from scipy import stats

WEIGHT_SCHEMES = {
    "OLD (topic=1)": {"topic_category": 1, "posting_hour": 2, "has_emoji": 1},
    "NEW (topic=0)": {"topic_category": 0, "posting_hour": 2, "has_emoji": 1},
}


def top3_for(pool, row, weights):
    anchor = pool[(pool["type"] == row["type"]) & (pool["channel"] == row["channel"])].copy()
    if len(anchor) < 3:
        type_only = pool[pool["type"] == row["type"]].copy()
        anchor = type_only if len(type_only) > 0 else pool.copy()
    if len(anchor) == 0:
        return None
    anchor["score"] = (
        (anchor["topic_category"] == row["topic_category"]).astype(int) * weights["topic_category"]
        + (anchor["posting_hour"] == row["posting_hour"]).astype(int) * weights["posting_hour"]
        + (anchor["has_emoji"] == row["has_emoji"]).astype(int) * weights["has_emoji"]
    )
    top_n = min(3, len(anchor))
    return anchor.sort_values(["score", "content_id"], ascending=[False, True]).head(top_n)


def run(past_path):
    past = pd.read_csv(past_path)
    clean = past.drop_duplicates(subset="content_id", keep="first").reset_index(drop=True)

    results = {name: {"hit": 0, "n": 0, "width_sum": 0.0, "abs_err_sum": 0.0} for name in WEIGHT_SCHEMES}
    paired_abs_err = {name: [] for name in WEIGHT_SCHEMES}
    paired_width = {name: [] for name in WEIGHT_SCHEMES}

    for i, row in clean.iterrows():
        pool = clean.drop(index=i)
        actual = row["ctr"]
        for name, weights in WEIGHT_SCHEMES.items():
            top3 = top3_for(pool, row, weights)
            if top3 is None or len(top3) == 0:
                continue
            cmin, cmax = top3["ctr"].min(), top3["ctr"].max()
            mid = (cmin + cmax) / 2
            hit = cmin <= actual <= cmax
            results[name]["hit"] += int(hit)
            results[name]["n"] += 1
            results[name]["width_sum"] += (cmax - cmin)
            results[name]["abs_err_sum"] += abs(mid - actual)
            paired_abs_err[name].append(abs(mid - actual))
            paired_width[name].append(cmax - cmin)

    print(f"{'scheme':<16}{'n':>4}{'hit_rate':>10}{'avg_width':>12}{'avg_abs_err(mid)':>18}")
    for name, r in results.items():
        n = r["n"]
        print(f"{name:<16}{n:>4}{r['hit']/n*100:>9.1f}%{r['width_sum']/n:>12.3f}{r['abs_err_sum']/n:>18.3f}")

    old_err, new_err = paired_abs_err["OLD (topic=1)"], paired_abs_err["NEW (topic=0)"]
    old_w, new_w = paired_width["OLD (topic=1)"], paired_width["NEW (topic=0)"]
    t_err, p_err = stats.ttest_rel(old_err, new_err)
    t_w, p_w = stats.ttest_rel(old_w, new_w)
    print(f"\npaired t-test (abs error, OLD vs NEW): t={t_err:.3f}, p={p_err:.4f}")
    print(f"paired t-test (interval width, OLD vs NEW): t={t_w:.3f}, p={p_w:.4f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--past", default="data/past_content_performance.csv")
    args = ap.parse_args()
    run(args.past)
