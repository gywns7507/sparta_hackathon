"""
콘텐츠 성과 예측 파이프라인 (Standard + Challenge)

사용법:
    py scripts\\pipeline.py
    py scripts\\pipeline.py --past data/past_content_performance.csv --new data/new_content_info.csv --out output/content_prediction_report.md
    py scripts\\pipeline.py --strategy   # Challenge: 전략 기획안 자동 생성 섹션까지 포함

새 new_content_info.csv를 넣고 --new 로 경로만 바꿔주면 동일한 절차(정제 -> 유사 TOP3 -> CTR 범위 -> 개선 제안 -> 리포트)로
content_prediction_report.md 를 재생성한다. 유사도 기준·개선 제안 로직은 /analyze, /insight 단계에서 확정한 규칙을 그대로 코드화한 것.
--strategy를 추가하면 과거 데이터 전체 분포에서 팀 차원 전략 후보를 자동 탐지·채점해 리포트 끝에 붙인다.
"""
import argparse
import pandas as pd

# topic_category는 ANOVA 검증 결과(η²=0.006) CTR과 유의한 관계가 없어 0점 처리(decisions.md 참고).
WEIGHTS = {"posting_hour": 2, "topic_category": 0, "has_emoji": 1}
MAX_SCORE = sum(WEIGHTS.values())
WEAK_MATCH_RATIO = 0.75
RELIABILITY_RANK = {"local": 0, "local-weak": 1, "global-fallback": 2, "global": 2, "weak": 3, "n/a": 4}


def load_clean(past_path):
    past = pd.read_csv(past_path)
    return past.drop_duplicates(subset="content_id", keep="first").copy()


def similarity_top3(clean, row):
    """
    type(콘텐츠 형식)은 원칙적으로 완화하지 않는다 — 형식이 다르면 비교 자체가 무의미하다는
    유사도 설계 원칙(decisions.md 참고) 때문. channel만 완화하고, 그래도 3건이 안 되면
    "있는 대로" 쓰고 데이터 부족을 그대로 명시한다. type이 과거 데이터에 전혀 없을 때만
    최후 수단으로 전체 데이터를 참고하되 신뢰도가 매우 낮음을 강하게 표시한다.
    """
    anchor = clean[(clean["type"] == row["type"]) & (clean["channel"] == row["channel"])].copy()
    note = "type+channel 앵커 유지"
    anchor_level = "strict"

    if len(anchor) < 3:
        type_only = clean[clean["type"] == row["type"]].copy()
        if len(type_only) > 0:
            anchor = type_only
            anchor_level = "channel-relaxed" if len(anchor) >= 3 else "channel-relaxed-thin"
            note = (f"후보 부족 -> channel 조건 완화(type={row['type']}만 유지)"
                    if len(anchor) >= 3 else
                    f"후보 부족 -> channel 조건 완화했으나 과거 데이터에 '{row['type']}' 유형이 {len(anchor)}건뿐 (TOP3 미달)")
        else:
            anchor = clean.copy()
            anchor_level = "type-relaxed"
            note = f"과거 데이터에 '{row['type']}' 유형이 전혀 없음 -> 전체 데이터 참고(신뢰도 매우 낮음, 다른 유형과 비교됨)"

    anchor["score"] = (
        (anchor["topic_category"] == row["topic_category"]).astype(int) * WEIGHTS["topic_category"]
        + (anchor["posting_hour"] == row["posting_hour"]).astype(int) * WEIGHTS["posting_hour"]
        + (anchor["has_emoji"] == row["has_emoji"]).astype(int) * WEIGHTS["has_emoji"]
    )
    top_n = min(3, len(anchor))
    top3 = anchor.sort_values(["score", "content_id"], ascending=[False, True]).head(top_n)
    return top3, anchor, len(anchor), note, anchor_level


def time_candidate(anchor, row, clean):
    cur_hour = row["posting_hour"]
    global_best_hour = clean.groupby("posting_hour")["ctr"].mean().idxmax()
    grp = anchor.groupby("posting_hour")["ctr"].agg(["mean", "count"])
    if cur_hour in grp.index:
        cur_mean, cur_n = grp.loc[cur_hour, "mean"], grp.loc[cur_hour, "count"]
        alt = grp.drop(index=cur_hour, errors="ignore")
        if not alt.empty:
            best_hour = alt["mean"].idxmax()
            best_mean, best_n = alt.loc[best_hour, "mean"], alt.loc[best_hour, "count"]
            delta = best_mean - cur_mean
            # 이미 전체 데이터 기준 최적 시간대(global_best_hour)에 있다면, 소표본(n<5) 지역적 역전 신호는
            # 노이즈로 간주하고 억제한다 (예: n=3짜리 우연한 역전으로 "이미 최선인 조건을 바꾸라"고 하지 않도록)
            if delta > 0.05 and not (cur_hour == global_best_hour and best_n < 5):
                reliability = "local" if cur_n >= 2 and best_n >= 2 else "local-weak"
                text = (f"발행 시간을 {best_hour}시로 변경: 앵커 내 현재({cur_hour}시) 평균 {cur_mean:.2f}%(n={cur_n}) "
                        f"vs {best_hour}시 평균 {best_mean:.2f}%(n={best_n}), {delta:+.2f}%p")
                if reliability == "local-weak":
                    text += " (표본 작음, 참고용)"
                return {"axis": "posting_hour", "delta": delta, "text": text, "reliability": reliability}
    if cur_hour == global_best_hour:
        return None
    g = clean.groupby("posting_hour")["ctr"].mean()
    if cur_hour in g.index:
        alt_g = g.drop(index=cur_hour, errors="ignore")
        if not alt_g.empty:
            best_hour = alt_g.idxmax()
            delta = alt_g.loc[best_hour] - g.loc[cur_hour]
            if delta > 0.05:
                text = (f"발행 시간을 {best_hour}시로 변경(전체 평균 기준, 해당 앵커엔 비교 데이터 부족): "
                        f"전체 평균 현재 {cur_hour}시 {g.loc[cur_hour]:.2f}% vs {best_hour}시 {alt_g.loc[best_hour]:.2f}%, {delta:+.2f}%p")
                return {"axis": "posting_hour", "delta": delta, "text": text, "reliability": "global-fallback"}
    return None


def emoji_candidate(anchor, row, clean):
    cur_emoji = row["has_emoji"]
    global_best_emoji = clean.groupby("has_emoji")["ctr"].mean().idxmax()
    grp = anchor.groupby("has_emoji")["ctr"].agg(["mean", "count"])
    other = not cur_emoji
    if cur_emoji in grp.index and other in grp.index:
        cur_mean, cur_n = grp.loc[cur_emoji, "mean"], grp.loc[cur_emoji, "count"]
        other_mean, other_n = grp.loc[other, "mean"], grp.loc[other, "count"]
        delta = other_mean - cur_mean
        if delta > 0.05 and not (cur_emoji == global_best_emoji and other_n < 5):
            reliability = "local" if cur_n >= 2 and other_n >= 2 else "local-weak"
            verb = "추가" if not cur_emoji else "제거"
            text = (f"제목에 이모지를 {verb}: 앵커 내 현재({'포함' if cur_emoji else '미포함'}) 평균 {cur_mean:.2f}%(n={cur_n}) "
                    f"vs {'포함' if other else '미포함'} 평균 {other_mean:.2f}%(n={other_n}), {delta:+.2f}%p")
            if reliability == "local-weak":
                text += " (표본 작음, 참고용)"
            return {"axis": "has_emoji", "delta": delta, "text": text, "reliability": reliability}
    if cur_emoji == global_best_emoji:
        return None
    g = clean.groupby("has_emoji")["ctr"].mean()
    if cur_emoji in g.index and other in g.index:
        delta = g.loc[other] - g.loc[cur_emoji]
        if delta > 0.05:
            verb = "추가" if not cur_emoji else "제거"
            text = (f"제목에 이모지를 {verb}(전체 평균 기준, 해당 앵커엔 비교 데이터 부족): "
                    f"전체 평균 {'포함' if cur_emoji else '미포함'} {g.loc[cur_emoji]:.2f}% vs {'포함' if other else '미포함'} {g.loc[other]:.2f}%, {delta:+.2f}%p")
            return {"axis": "has_emoji", "delta": delta, "text": text, "reliability": "global-fallback"}
    return None


def format_candidate(clean, row):
    same_channel = clean[clean["channel"] == row["channel"]]
    matrix = same_channel.groupby("type")["ctr"].mean()
    if row["type"] in matrix.index:
        cur = matrix.loc[row["type"]]
        alt = matrix.drop(index=row["type"])
        if not alt.empty:
            best_type = alt.idxmax()
            delta = alt.loc[best_type] - cur
            if delta > 0.15:
                text = (f"{row['channel']}에서 포맷을 '{best_type}'로 전환 검토: 전체 평균 현재 유형({row['type']}) "
                        f"{cur:.2f}% vs {best_type} {alt.loc[best_type]:.2f}%, {delta:+.2f}%p")
                return {"axis": "type", "delta": delta, "text": text, "reliability": "global"}
    return None


def topic_candidate(anchor, row):
    grp = anchor.groupby("topic_category")["ctr"].agg(["mean", "count"])
    if row["topic_category"] in grp.index:
        cur, cur_n = grp.loc[row["topic_category"], "mean"], grp.loc[row["topic_category"], "count"]
        alt = grp.drop(index=row["topic_category"])
        if not alt.empty:
            best = alt["mean"].idxmax()
            best_mean, best_n = alt.loc[best, "mean"], alt.loc[best, "count"]
            delta = best_mean - cur
            if delta > 0.05:
                text = (f"주제 앵글을 '{best}' 쪽으로 조정 실험(근거 약함 — topic_category는 전체 통계 검증상 CTR과 "
                        f"유의한 관계 없음): 앵커 내 현재({row['topic_category']}) {cur:.2f}%(n={cur_n}) vs {best} "
                        f"{best_mean:.2f}%(n={best_n}), {delta:+.2f}%p")
                return {"axis": "topic_category", "delta": delta, "text": text, "reliability": "weak"}
    return None


def length_candidate(anchor, row):
    if anchor.empty:
        return None
    median_len = anchor["headline_length"].median()
    a2 = anchor.copy()
    a2["bucket"] = a2["headline_length"].apply(lambda x: "long" if x >= median_len else "short")
    grp = a2.groupby("bucket")["ctr"].agg(["mean", "count"])
    cur_bucket = "long" if row["headline_length"] >= median_len else "short"
    other = "short" if cur_bucket == "long" else "long"
    if cur_bucket in grp.index and other in grp.index:
        cur, cur_n = grp.loc[cur_bucket, "mean"], grp.loc[cur_bucket, "count"]
        other_mean, other_n = grp.loc[other, "mean"], grp.loc[other, "count"]
        delta = other_mean - cur
        if delta > 0.1:
            direction = "줄이는" if cur_bucket == "long" else "늘리는"
            text = (f"제목 길이를 {direction} 실험(근거 약함, 표본 작음): 앵커 내 현재 그룹 평균 {cur:.2f}%(n={cur_n}) "
                    f"vs 반대 그룹 {other_mean:.2f}%(n={other_n}), {delta:+.2f}%p")
            return {"axis": "headline_length", "delta": delta, "text": text, "reliability": "weak"}
    return None


def pick_suggestions(anchor, clean, row):
    strong = [c for c in (time_candidate(anchor, row, clean), emoji_candidate(anchor, row, clean),
                           format_candidate(clean, row)) if c]
    weak = [c for c in (topic_candidate(anchor, row), length_candidate(anchor, row)) if c]
    strong.sort(key=lambda c: (RELIABILITY_RANK[c["reliability"]], -c["delta"]))
    weak.sort(key=lambda c: -c["delta"])
    chosen = strong[:2]
    if len(chosen) < 2:
        chosen += weak[: 2 - len(chosen)]
    if len(chosen) < 2:
        chosen.append({"axis": "none", "delta": 0, "reliability": "n/a",
                        "text": "핵심 변수(시간대·이모지·포맷)에서 이미 최적/준최적 구간에 있어 추가로 바꿀 요소가 제한적입니다. 그대로 발행을 권장합니다."})
    return chosen[:2]


def diagnose_one(clean, row):
    top3, anchor, anchor_n, note, anchor_level = similarity_top3(clean, row)
    ctr_min, ctr_max = top3["ctr"].min(), top3["ctr"].max()
    max_score = top3["score"].max()
    # type이 완화된 경우(anchor_level == "type-relaxed")는 서브점수가 높아도 다른 유형과 비교된 것이므로
    # 무조건 약한 매칭으로 표시한다 — 서브점수만으로는 이 경우를 감지할 수 없기 때문.
    weak_match = max_score < MAX_SCORE * WEAK_MATCH_RATIO or anchor_level in ("type-relaxed", "channel-relaxed-thin")
    suggestions = pick_suggestions(anchor, clean, row)
    return {
        "row": row, "top3": top3, "anchor_n": anchor_n, "note": note, "anchor_level": anchor_level,
        "ctr_min": ctr_min, "ctr_max": ctr_max, "max_score": max_score,
        "weak_match": weak_match, "suggestions": suggestions,
    }


def render_report(clean, new_df, results):
    lines = []
    lines.append("# 콘텐츠 성과 예측 리포트 (파이프라인 생성)\n")
    lines.append("> `scripts/pipeline.py`로 자동 생성됨. ML 예측이 아닌, 유사 콘텐츠의 실제 과거 성과 기반 패턴 진단입니다.\n")
    lines.append("## 1. 데이터 개요\n")
    lines.append(f"- 과거 데이터 정제 후 {len(clean)}건 기준 (원본 중복·결측 포함 여부는 입력 파일에 따라 달라질 수 있음)")
    lines.append(f"- 신규 진단 대상: {len(new_df)}건\n")
    lines.append("## 2. 유사도 기준")
    lines.append("- 앵커: `type` + `channel` 동시 일치. `type`은 원칙적으로 완화하지 않음(형식이 다르면 비교 자체가 무의미)")
    lines.append(f"- 서브 점수({MAX_SCORE}점 만점): `posting_hour` 일치 +2 / `has_emoji` 일치 +1 "
                  "(`topic_category`는 ANOVA 검증 결과 CTR과 유의한 관계 없어 0점 처리, decisions.md 참고)")
    lines.append("- 동점 시 `content_id` 오름차순. 앵커 후보 3건 미달 시 channel만 완화(type 유지), 그래도 부족하면 있는 대로 사용")
    lines.append("- 해당 `type`이 과거 데이터에 전혀 없는 경우에만 최후 수단으로 전체 데이터 참고(신뢰도 매우 낮음으로 표시)\n")
    lines.append("## 3. 신규 콘텐츠 진단\n")

    for i, r in enumerate(results, 1):
        row = r["row"]
        lines.append(f"### 신규 {i}: {row['title']}")
        lines.append(f"- 조건: {row['type']} / {row['topic_category']} / {row['channel']} / {row['posting_hour']}시 / "
                      f"이모지 {'O' if row['has_emoji'] else 'X'} / 제목 {row['headline_length']}자")
        if r["anchor_level"] == "type-relaxed":
            weak_flag = " ⚠️ 과거 데이터에 이 유형이 없어 다른 유형과 비교됨 (신뢰도 매우 낮음, 참고용)"
        elif r["weak_match"]:
            weak_flag = " ⚠️ 매칭 신뢰도 낮음 (참고용)"
        else:
            weak_flag = ""
        lines.append(f"- **예상 CTR 범위: {r['ctr_min']}% ~ {r['ctr_max']}%**{weak_flag} "
                      f"(앵커 후보 {r['anchor_n']}건, {r['note']}, 최고 서브점수 {int(r['max_score'])}/{MAX_SCORE})\n")
        lines.append("| 순위 | content_id | 제목 | CTR | 인게이지먼트율 | 유사 이유 |")
        lines.append("|---|---|---|---|---|---|")
        for rank, (_, t) in enumerate(r["top3"].iterrows(), 1):
            eng = f"{t['engagement_rate']}%" if pd.notna(t["engagement_rate"]) else "N/A(결측)"
            lines.append(f"| {rank} | {t['content_id']} | {t['title']} | {t['ctr']}% | {eng} | 서브점수 {int(t['score'])}/{MAX_SCORE} |")
        lines.append("\n**개선 제안 2가지**")
        for j, s in enumerate(r["suggestions"], 1):
            lines.append(f"{j}. {s['text']}")
        lines.append("")

    return "\n".join(lines)


# ── Challenge: 전략 기획안 자동 생성 ─────────────────────────────────────
# 후보 종류(kind)별 실행용이도는 개입 성격(일정·체크리스트 조정=쉬움 / 콘텐츠 믹스·조직 프로세스 변경=어려움)에
# 따라 고정한다. topic_engagement_mix는 engagement_rate에 대해서도 통계적으로 유의하지 않음이 확인돼(ANOVA
# F=0.93, p=0.43 — decisions.md 참고) significant=False로 항상 impact가 1점으로 고정된다.
FEASIBILITY = {
    "posting_hour_mix": 5,
    "emoji_mix": 5,
    "type_channel_underperform": 2,
    "topic_engagement_mix": 2,
}
MIN_AFFECTED_PCT = 20  # 팀 차원 전략으로 의미 있으려면 최소 이 비중 이상 영향을 줘야 후보로 채택


def impact_score(delta_pp, significant):
    if not significant:
        return 1
    if delta_pp >= 1.2:
        return 5
    if delta_pp >= 0.8:
        return 4
    if delta_pp >= 0.5:
        return 3
    if delta_pp >= 0.2:
        return 2
    return 1


def detect_strategic_candidates(clean):
    N = len(clean)
    overall_ctr = clean["ctr"].mean()
    candidates = []

    hour_ctr = clean.groupby("posting_hour")["ctr"].mean()
    low_hours = sorted(hour_ctr[hour_ctr < overall_ctr].index.tolist())
    if low_hours:
        low_n = clean[clean["posting_hour"].isin(low_hours)].shape[0]
        low_pct = low_n / N * 100
        if low_pct >= MIN_AFFECTED_PCT:
            worst_hour, best_hour = hour_ctr.idxmin(), hour_ctr.idxmax()
            delta = hour_ctr.max() - hour_ctr.min()
            hours_str = "·".join(f"{h}시" for h in low_hours)
            candidates.append({
                "kind": "posting_hour_mix", "title": "발행 캘린더 시간대 재배치", "delta": delta, "significant": True,
                "evidence": f"저성과 시간대({hours_str}) 발행 비중 {low_pct:.1f}%({low_n}/{N}건). "
                            f"{worst_hour}시 평균 CTR {hour_ctr.min():.2f}% vs {best_hour}시 {hour_ctr.max():.2f}%",
                "problem": f"콘텐츠의 {low_pct:.1f}%({low_n}건)가 평균 미달 시간대({hours_str})에 발행되고 있습니다.",
                "strategy": f"발행 캘린더에서 {hours_str} 슬롯을 {best_hour}시 등 고성과 시간대로 우선 재배치합니다.",
                "effect": f"해당 {low_n}건에 적용 시 콘텐츠별 최대 {delta:.2f}%p CTR 개선 가능성(관찰치 기준, 인과관계 검증 아님).",
            })

    uniq_emoji = clean["has_emoji"].unique()
    if True in uniq_emoji and False in uniq_emoji:
        emoji_ctr = clean.groupby("has_emoji")["ctr"].mean()
        no_emoji_n = int((clean["has_emoji"] == False).sum())
        no_emoji_pct = no_emoji_n / N * 100
        if no_emoji_pct >= MIN_AFFECTED_PCT:
            delta = emoji_ctr[True] - emoji_ctr[False]
            candidates.append({
                "kind": "emoji_mix", "title": "발행 전 이모지 체크리스트 도입", "delta": delta, "significant": True,
                "evidence": f"이모지 미포함 비중 {no_emoji_pct:.1f}%({no_emoji_n}/{N}건). "
                            f"미포함 평균 CTR {emoji_ctr[False]:.2f}% vs 포함 {emoji_ctr[True]:.2f}%",
                "problem": f"콘텐츠의 {no_emoji_pct:.1f}%({no_emoji_n}건)가 제목에 이모지 없이 발행되고 있습니다.",
                "strategy": "발행 전 체크리스트에 '제목 이모지 포함 여부'를 필수 항목으로 추가합니다.",
                "effect": f"해당 {no_emoji_n}건에 적용 시 콘텐츠별 최대 {delta:.2f}%p CTR 개선 가능성(관찰치 기준, 인과관계 검증 아님).",
            })

    combo = clean.groupby(["type", "channel"]).agg(ctr_mean=("ctr", "mean"), n=("ctr", "count")).reset_index()
    combo["pct"] = combo["n"] / N * 100
    vol_med = combo["n"].median()
    underperf = combo[(combo["ctr_mean"] < overall_ctr) & (combo["n"] >= vol_med) & (combo["pct"] >= MIN_AFFECTED_PCT)]
    for _, r in underperf.iterrows():
        delta = overall_ctr - r["ctr_mean"]
        candidates.append({
            "kind": "type_channel_underperform", "title": f"{r['type']}+{r['channel']} 조합 성과 점검",
            "delta": delta, "significant": True,
            "evidence": f"{r['type']}+{r['channel']} 발행 비중 {r['pct']:.1f}%({int(r['n'])}건)로 상위권이나 "
                        f"평균 CTR {r['ctr_mean']:.2f}%로 전체 평균({overall_ctr:.2f}%) 대비 {delta:.2f}%p 낮음",
            "problem": f"{r['type']}+{r['channel']} 조합이 발행 비중 상위({r['pct']:.1f}%)인데 "
                       f"CTR은 전체 평균 대비 {delta:.2f}%p 낮습니다.",
            "strategy": f"{r['type']}+{r['channel']} 콘텐츠의 제목·발행시간 등 세부 요소를 우선 최적화하고, "
                        f"개선이 없으면 발행 비중 재조정을 검토합니다.",
            "effect": "이 조합은 CTR 외 다른 가치(예: SEO·인게이지먼트)가 있을 수 있어, CTR만으로 발행량 축소를 단정하지 않음.",
        })

    topic_clean = clean.dropna(subset=["engagement_rate"])
    topic_stats = topic_clean.groupby("topic_category").agg(eng=("engagement_rate", "mean"), n=("engagement_rate", "count"))
    topic_stats["pct"] = topic_stats["n"] / topic_stats["n"].sum() * 100
    avg_share = 100 / len(topic_stats)
    best_topic = topic_stats["eng"].idxmax()
    if topic_stats.loc[best_topic, "pct"] < avg_share:
        worst_topic = topic_stats["eng"].idxmin()
        delta = topic_stats.loc[best_topic, "eng"] - topic_stats.loc[worst_topic, "eng"]
        candidates.append({
            "kind": "topic_engagement_mix", "title": f"'{best_topic}' 소재 비중 확대 검토",
            "delta": delta, "significant": False,
            "evidence": f"'{best_topic}' 인게이지먼트 {topic_stats.loc[best_topic, 'eng']:.2f}%"
                        f"(비중 {topic_stats.loc[best_topic, 'pct']:.1f}%)로 최고이나 비중은 평균({avg_share:.1f}%) 미달. "
                        f"다만 topic_category는 engagement_rate와 통계적으로 유의하지 않음(ANOVA p=0.43) — "
                        f"관찰된 차이일 뿐 확정된 패턴 아님",
            "problem": f"'{best_topic}' 카테고리가 인게이지먼트 {topic_stats.loc[best_topic, 'eng']:.2f}%로 가장 높지만 "
                       f"발행 비중은 {topic_stats.loc[best_topic, 'pct']:.1f}%로 평균 미달입니다.",
            "strategy": f"'{best_topic}' 소재를 점진적으로 늘려보는 탐색적 실험을 검토합니다.",
            "effect": "통계적으로 유의하지 않아(ANOVA p=0.43) 확정 효과를 제시하지 않음 — 탐색적 가설 수준.",
        })

    for c in candidates:
        c["impact"] = impact_score(c["delta"], c["significant"])
        c["feasibility"] = FEASIBILITY[c["kind"]]
        c["priority"] = c["impact"] * c["feasibility"]

    return sorted(candidates, key=lambda c: -c["priority"])


def render_strategy_section(candidates, top_n=2):
    lines = ["\n---\n", "## [Challenge] 콘텐츠 발행 전략 기획안 (자동 생성)\n"]
    lines.append(f"과거 데이터 전체 분포를 검증된 성과 패턴과 대조해 후보 {len(candidates)}건을 탐지했고, "
                 f"우선순위 점수(임팩트×실행용이도) 상위 {min(top_n, len(candidates))}건을 기획안으로 채택했습니다.\n")
    for i, c in enumerate(candidates[:top_n], 1):
        lines.append(f"### 기획안 {i}: {c['title']}")
        lines.append(f"- **문제 정의**: {c['problem']}")
        lines.append(f"- **근거 데이터**: {c['evidence']}")
        lines.append(f"- **전략 제안**: {c['strategy']}")
        lines.append(f"- **예상 효과**: {c['effect']}")
        lines.append(f"- **우선순위**: 임팩트 {c['impact']} × 실행용이도 {c['feasibility']} = **{c['priority']}점**\n")
    rest = candidates[top_n:]
    if rest:
        lines.append("### 참고: 탐지됐지만 우선순위 상 채택되지 않은 후보")
        for c in rest:
            lines.append(f"- **{c['title']}** (우선순위 {c['priority']}점): {c['evidence']}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--past", default="data/past_content_performance.csv")
    ap.add_argument("--new", default="data/new_content_info.csv")
    ap.add_argument("--out", default="output/content_prediction_report.md")
    ap.add_argument("--strategy", action="store_true", help="Challenge: 전략 기획안 자동 생성 섹션을 리포트에 추가")
    args = ap.parse_args()

    clean = load_clean(args.past)
    new_df = pd.read_csv(args.new)
    results = [diagnose_one(clean, row) for _, row in new_df.iterrows()]
    report = render_report(clean, new_df, results)

    if args.strategy:
        candidates = detect_strategic_candidates(clean)
        report += render_strategy_section(candidates, top_n=2)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"저장 완료: {args.out} ({len(results)}건 진단" + (", 전략 기획안 포함)" if args.strategy else ")"))


if __name__ == "__main__":
    main()
