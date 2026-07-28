"""
대시보드 v3 — 네이티브 Streamlit 컴포넌트 기반 재구성.

이전 버전(dashboard_v2.py)은 HTML/CSS 문자열을 만들어 components.html 로 iframe에 그렸는데,
사용자가 참고한 다른 프로젝트 대시보드(사이드바 필터 + 탭 + st.metric + 인터랙티브 차트, 카드형
커스텀 HTML 없음)의 미니멀한 느낌을 내려면 그 방식 자체를 걷어내야 했음. 이 모듈은 탭·st.metric·
st.dataframe·plotly 차트 등 Streamlit 기본 컴포넌트만으로 같은 내용(신규 콘텐츠 진단, 핵심 성과
패턴, reach/다변량회귀 포트폴리오 확장 분석, Challenge 전략 기획안)을 그린다.

각 render_* 함수는 이미 활성화된 Streamlit 컨테이너(보통 st.tabs()가 반환한 tab) 안에서 호출된다는
전제로 st 모듈에 바로 그린다. 값 계산 로직은 전혀 갖지 않고 pipeline.py / reach_analysis.py /
regression_analysis.py가 계산한 결과를 입력받아 렌더링만 한다.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ACCENT = "#2a78d6"
ACCENT_SOFT = "#86b6ef"
ORANGE = "#eb6834"
CRITICAL = "#d03b3b"
DE_EMPHASIS = "#c3c2b7"
GRID = "#e1e0d9"
INK2 = "#52514e"

FONT = dict(family="system-ui, -apple-system, 'Segoe UI', 'Noto Sans KR', sans-serif", color="#0b0b0b")

AXIS_LABEL = {
    "posting_hour": "발행시간 조정",
    "has_emoji": "이모지 조정",
    "type": "포맷 전환",
    "topic_category": "주제 조정",
    "headline_length": "제목길이 조정",
    "none": "유지",
}


# ────────────────────────────── plotly helpers ──────────────────────────────

def _layout(fig, height=None):
    fig.update_layout(template="plotly_white", font=FONT, height=height,
                       margin=dict(l=10, r=40, t=10, b=10), showlegend=False)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


def _hbar(labels, values, value_fmt="{:.2f}", color=ACCENT, height=None):
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=color,
        text=[value_fmt.format(v) for v in values], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    return _layout(fig, height=height or max(150, 42 * len(labels)))


def verdict_text(r):
    top = r["suggestions"][0]
    if top["axis"] == "none":
        return "이미 최적 · 유지"
    label = AXIS_LABEL.get(top["axis"], "조건 조정")
    if r["anchor_level"] == "type-relaxed" or r["weak_match"]:
        return f"{label} (신뢰도 낮음)"
    return f"{label} 검토"


# ────────────────────────────── 개요 ──────────────────────────────

def render_overview(clean, new_df, regression_result, include_strategy):
    st.markdown("#### 이 대시보드가 하는 일")
    steps = [
        "**신규 콘텐츠 진단** — 유사 콘텐츠 TOP3의 실제 CTR로 예상 범위·개선 제안을 계산합니다.",
        "**핵심 성과 패턴** — 발행시간대·이모지·유형×채널이 CTR에 미치는 실측 차이를 확인합니다.",
        "**reach 활용 검증** — 지금까지 안 쓰던 도달수 변수가 CTR·참여율과 독립적 관계가 있는지 확인합니다.",
        "**다변량 회귀 검증** — type·channel·시간대·이모지를 동시에 통제해 각 축의 순수 기여도를 분리합니다.",
    ]
    if include_strategy:
        steps.append("**발행 전략 기획안** — 팀 차원 구조적 문제를 자동 탐지·채점해 우선순위를 매깁니다.")
    st.markdown("\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)))

    st.markdown("#### 핵심 지표")
    cols = st.columns(5)
    cols[0].metric("학습 콘텐츠", f"{len(clean)}건")
    cols[1].metric("진단 대상", f"{len(new_df)}건")

    hour_ctr = clean.groupby("posting_hour")["ctr"].mean()
    if len(hour_ctr) >= 2:
        best_h, worst_h = hour_ctr.idxmax(), hour_ctr.idxmin()
        delta = hour_ctr.max() - hour_ctr.min()
        cols[2].metric("발행 시간대 효과", f"{delta:+.2f}%p",
                        help=f"{best_h}시 {hour_ctr.max():.2f}% vs {worst_h}시 {hour_ctr.min():.2f}%")
    else:
        cols[2].metric("발행 시간대 효과", "N/A")

    emoji_ctr = clean.groupby("has_emoji")["ctr"].mean()
    if True in emoji_ctr.index and False in emoji_ctr.index:
        delta = emoji_ctr[True] - emoji_ctr[False]
        cols[3].metric("이모지 효과", f"{delta:+.2f}%p",
                        help=f"포함 {emoji_ctr[True]:.2f}% vs 미포함 {emoji_ctr[False]:.2f}%")
    else:
        cols[3].metric("이모지 효과", "N/A")

    if regression_result:
        cols[4].metric("다변량 모델 설명력(R²)", f"{regression_result['r2']:.2f}",
                        help=f"type+channel+시간대+이모지 동시 통제, n={regression_result['n']}")
    else:
        cols[4].metric("다변량 모델 설명력(R²)", "N/A")

    st.divider()
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("#### 발행시간대별 평균 CTR")
        hc = clean.groupby("posting_hour")["ctr"].mean().sort_index()
        st.plotly_chart(_hbar([f"{h}시" for h in hc.index], hc.values, "{:.2f}%", height=210),
                         width="stretch", config={"displayModeBar": False})
    with c2:
        st.markdown("#### 이모지별 평균 CTR")
        ec = clean.groupby("has_emoji")["ctr"].mean()
        labels = ["포함" if k else "미포함" for k in ec.index]
        st.plotly_chart(_hbar(labels, ec.values, "{:.2f}%", height=150),
                         width="stretch", config={"displayModeBar": False})

    st.markdown("#### 유형 × 채널별 평균 CTR")
    combo = clean.groupby(["type", "channel"])["ctr"].mean().sort_values()
    labels = [f"{t}+{c}" for t, c in combo.index]
    st.plotly_chart(_hbar(labels, combo.values, "{:.2f}%", height=max(180, 40 * len(labels))),
                     width="stretch", config={"displayModeBar": False})


# ────────────────────────────── 신규 콘텐츠 진단 ──────────────────────────────

def render_diagnosis(results):
    st.markdown("#### 신규 콘텐츠 일괄 진단")
    table = pd.DataFrame([{
        "#": i,
        "제목": r["row"]["title"],
        "조건": f"{r['row']['type']}·{r['row']['topic_category']}·{r['row']['channel']}·"
               f"{r['row']['posting_hour']}시·이모지{'O' if r['row']['has_emoji'] else 'X'}",
        "예상 CTR": f"{r['ctr_min']}~{r['ctr_max']}%",
        "앵커 후보": f"{r['anchor_n']}건",
        "서브점수": f"{int(r['max_score'])}/3",
        "판정": verdict_text(r),
    } for i, r in enumerate(results, 1)])
    st.dataframe(table, hide_index=True, width="stretch")

    st.markdown("#### 개별 진단")
    titles = [f"{i}. {r['row']['title']}" for i, r in enumerate(results, 1)]
    idx = st.selectbox("콘텐츠 선택", range(len(results)), format_func=lambda i: titles[i])
    r = results[idx]
    row = r["row"]
    weak = r["weak_match"]

    st.caption(f"{row['type']} · {row['topic_category']} · {row['channel']} · {row['posting_hour']}시 · "
               f"이모지 {'포함' if row['has_emoji'] else '미포함'} · 제목 {row['headline_length']}자")
    if weak:
        st.warning("매칭 신뢰도가 낮습니다 — 참고용으로만 활용하세요.")

    st.metric("예상 CTR 범위", f"{r['ctr_min']}~{r['ctr_max']}%")
    st.caption(f"근거: 앵커 후보 {r['anchor_n']}건({r['note']}) 중 서브점수 최고 {int(r['max_score'])}/3인 "
               f"유사 TOP3의 실제 CTR")

    top3 = pd.DataFrame([{
        "순위": rank, "ID": t.get("content_id", ""), "제목": t["title"], "CTR": f"{t['ctr']}%",
        "참여율": f"{t['engagement_rate']}%" if t["engagement_rate"] == t["engagement_rate"] else "N/A(결측)",
        "서브점수": f"{int(t['score'])}/3",
    } for rank, (_, t) in enumerate(r["top3"].iterrows(), 1)])
    st.dataframe(top3, hide_index=True, width="stretch")

    st.markdown("**개선 제안**")
    for j, s in enumerate(r["suggestions"], 1):
        prefix = f"{j}. " + ("(근거 약함) " if s["reliability"] == "weak" else "")
        st.info(prefix + s["text"])


# ────────────────────────────── reach 활용 분석 ──────────────────────────────

def render_reach(reach_result):
    if not reach_result or not reach_result.get("raw_corr"):
        st.info("reach 데이터가 없어 이 분석을 표시할 수 없습니다.")
        return
    r = reach_result
    st.markdown("지금까지 결측치 처리 대상으로만 언급되고 실제 진단에는 쓰이지 않았던 **reach(도달수)**가 "
                "ctr·engagement_rate와 독립적인 관계를 갖는지 검증합니다 (`scripts/reach_analysis.py`).")

    target_label = {"ctr": "CTR", "engagement_rate": "참여율"}
    cats, raw_vals, part_vals = [], [], []
    for target in ("ctr", "engagement_rate"):
        raw = r["raw_corr"].get(target)
        if not raw:
            continue
        cats.append(f"reach → {target_label[target]}")
        raw_vals.append(raw["r"])
        part = r["partial_corr"].get(target)
        part_vals.append(part["r"] if part else None)

    st.markdown("##### reach ↔ 성과지표 상관관계")
    st.caption("type+channel을 통제해도(편상관) 원시 상관에서 거의 줄지 않으면, 포맷·플랫폼 차이만으로는 "
               "설명되지 않는 reach 고유의 신호라는 뜻입니다.")
    fig = go.Figure()
    fig.add_bar(name="원시 상관", x=raw_vals, y=cats, orientation="h", marker_color=ACCENT,
                text=[f"r={v:.3f}" for v in raw_vals], textposition="outside",
                hovertemplate="%{y} 원시 r=%{x:.3f}<extra></extra>")
    if all(v is not None for v in part_vals):
        fig.add_bar(name="type+channel 통제 후(편상관)", x=part_vals, y=cats, orientation="h",
                    marker_color=ACCENT_SOFT, text=[f"r={v:.3f}" for v in part_vals], textposition="outside",
                    hovertemplate="%{y} 편상관 r=%{x:.3f}<extra></extra>")
    fig.update_layout(template="plotly_white", font=FONT, barmode="group", height=180,
                       margin=dict(l=10, r=50, t=10, b=10),
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, range=[0, 1.05])
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.markdown("##### reach는 콘텐츠 속성에 따라 이미 크게 갈립니다")
    group_labels = {"type": "유형별", "channel": "채널별", "posting_hour": "발행시간대별"}
    cols = st.columns(3)
    for col_key, col in zip(("type", "channel", "posting_hour"), cols):
        g = r["group_diff"].get(col_key)
        if not g:
            continue
        with col:
            sig = "유의함" if g["p"] < 0.05 else "유의하지 않음"
            st.caption(f"{group_labels[col_key]} 평균 도달수 · η²={g['eta2']:.2f} · {sig}")
            means = dict(sorted(g["means"].items(), key=lambda kv: -kv[1]))
            st.plotly_chart(_hbar([str(k) for k in means], list(means.values()), "{:,.0f}", height=190),
                             width="stretch", config={"displayModeBar": False})

    st.markdown("##### 그래서, 무엇을 알 수 있나")
    st.markdown(
        "**새로운 발견** — reach는 CTR·참여율과 원시 상관이 매우 강했고(r=0.91 / 0.93), type+channel을 "
        "통제해도 그 관계가 거의 줄지 않았습니다(편상관 r=0.88 / 0.81). 즉 \"형식·플랫폼이 원래 도달도 좋고 "
        "성과도 좋다\"는 착시가 아니라, 같은 형식·플랫폼 안에서도 도달이 큰 콘텐츠가 성과도 좋다는 독립적인 "
        "신호입니다."
    )
    st.warning(
        "**인과관계는 알 수 없음** — 이 데이터만으로는 \"도달이 커서 성과가 좋다\"(원인)와 \"이미 성과가 좋아 "
        "알고리즘이 도달을 더 밀어준다\"(결과·피드백 루프)를 구분할 수 없습니다. 참여율은 정의상 reach를 "
        "분모로 나눈 비율((좋아요+댓글+공유)/reach×100)이라, \"도달이 클수록 비율은 희석된다\"는 통념과 "
        "반대되는 결과라는 점도 함께 감안해야 합니다."
    )
    st.markdown(
        "**실무적 시사점** — posting_hour·이모지처럼 \"이렇게 바꾸면 CTR이 오른다\"는 개선 레버로는 쓸 수 "
        "없습니다 — reach는 마케터가 직접 조작하는 변수가 아니라 알고리즘이 정해주는 결과값에 가깝기 "
        "때문입니다. 대신 **진단 보조 신호**로는 유용합니다: CTR은 평범한데 reach가 유독 낮다면 \"애초에 "
        "노출이 덜 된 콘텐츠\", reach는 높은데 CTR이 낮다면 \"노출은 됐지만 반응이 약한 콘텐츠\"로 구분해 "
        "볼 수 있습니다."
    )


# ────────────────────────────── 다변량 회귀분석 ──────────────────────────────

def _coef_label_map(reg):
    labels = {}
    for c in reg["coefficients"]:
        name = c["name"]
        if name.startswith("type_"):
            labels[name] = f"{name[5:]} (vs 블로그)"
        elif name.startswith("channel_"):
            labels[name] = f"{name[8:]} (vs 블로그)"
        elif name.startswith("posting_hour_cat_"):
            labels[name] = f"{name[17:].replace('h', '시')} (vs 12시)"
        elif name == "has_emoji":
            labels[name] = "이모지 포함"
        else:
            labels[name] = name
    return labels


def render_regression(reg):
    if not reg:
        st.info("표본이 적어 다변량 회귀를 생략했습니다.")
        return
    st.markdown("type·channel을 각각 따로 검정했던 단변량 ANOVA와 달리, 다섯 축을 동시에 통제한 다변량 "
                "회귀로 두 축이 서로 겹쳐 같은 신호를 중복 반영하는 건 아닌지 확인합니다 "
                "(`scripts/regression_analysis.py`, 외부 회귀 라이브러리 없이 numpy로 직접 구현).")
    st.caption(f"n={reg['n']} · R²={reg['r2']:.3f} · adj. R²={reg['adj_r2']:.3f}")

    coef_labels = _coef_label_map(reg)
    names = [coef_labels[c["name"]] for c in reg["coefficients"]]
    coefs = [c["coef"] for c in reg["coefficients"]]
    ses = [c["se"] for c in reg["coefficients"]]
    colors = [ACCENT if c["significant"] else DE_EMPHASIS for c in reg["coefficients"]]

    st.markdown("##### 변수별 CTR 계수 (기준 범주 대비, %p)")
    st.markdown(
        "다섯 변수를 **동시에** 모델에 넣고, 그중 하나만 바꿨을 때 CTR이 얼마나 달라지는지를 보여줍니다. "
        "type 기준은 블로그, channel 기준은 블로그, posting_hour 기준은 12시로 놓고, 나머지 조건은 "
        "고정한 채 그 기준 대비 차이만 계산한 값입니다. 예를 들어 \"20시 (vs 12시)\"가 +0.69%p라면, "
        "유형·채널·이모지가 같다고 가정할 때 12시보다 20시에 올린 콘텐츠의 CTR이 평균 0.69%p 높다는 뜻입니다. "
        "개요 탭의 \"발행시간대별 평균 CTR\"은 다른 변수를 무시한 단순 평균이라 다른 요인이 섞여 있을 수 "
        "있는 반면, 이 차트는 그 요인들을 다 붙잡아 놓고 계산한 순수 효과라는 점이 다릅니다."
    )
    fig = go.Figure(go.Scatter(
        x=coefs, y=names, mode="markers", marker=dict(color=colors, size=11),
        error_x=dict(type="data", array=ses, color="rgba(82,81,78,.5)", thickness=2, width=5),
        hovertemplate="%{y}: %{x:+.2f}%p<extra></extra>",
    ))
    fig.add_vline(x=0, line_dash="dot", line_color=INK2, opacity=0.4)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=GRID, title="CTR 계수 (%p, 회색 선 = ±1 표준오차)")
    fig.update_layout(template="plotly_white", font=FONT, height=max(240, 40 * len(names)),
                       margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("● 파랑 = 통계적으로 유의함(p<0.05) · ● 회색 = 유의하지 않음")

    st.markdown("##### VIF (분산팽창지수) — 10을 넘으면 다른 변수로 대부분 설명되는 중복 신호")
    st.markdown(
        "**뭘 확인하는 차트인가** — 바로 위 계수 차트에서 type·channel 개별 항목이 대부분 유의하지 않게 "
        "나왔는데, 이게 \"진짜 효과가 없어서\"인지 \"다른 변수와 내용이 겹쳐서 추정 자체가 불안정해진 것\"인지 "
        "구분하기 위한 진단 차트입니다. 각 변수를 \"나머지 모든 변수로 예측할 수 있는 정도\"로 점수를 매긴 "
        "것이라, 값이 클수록 그 변수가 다른 변수와 중복된 정보라는 뜻입니다."
    )
    st.markdown(
        "**읽는 법** — VIF=1이면 다른 변수와 완전히 독립적이고, 10을 넘으면 그 변수 변동의 90% 이상이 "
        "다른 변수들로 이미 설명된다는 뜻(경험적으로 통용되는 기준선, 빨간 점선)입니다. 예를 들어 "
        "\"인스타그램 (vs 블로그)\"의 VIF가 14.2라면, channel=인스타그램 여부가 사실상 type(카드뉴스·숏폼 "
        "등)만 알아도 대부분 맞힐 수 있는 중복 정보라는 뜻이고, 그래서 위 계수 차트에서 이 항목의 개별 "
        "효과가 유의하지 않게 나온 건 \"효과가 없어서\"가 아니라 \"type과 겹쳐서 둘 중 어느 쪽 효과인지 "
        "모델이 갈라내지 못해서\"일 가능성이 크다고 해석합니다."
    )
    vif_names = [coef_labels.get(v["name"], v["name"]) for v in reg["vif"]]
    vif_vals = [min(v["vif"], 999) for v in reg["vif"]]
    vif_colors = [CRITICAL if v > 10 else ACCENT for v in vif_vals]
    fig2 = go.Figure(go.Bar(x=vif_vals, y=vif_names, orientation="h", marker_color=vif_colors,
                             text=[f"{v:.1f}" for v in vif_vals], textposition="outside", cliponaxis=False,
                             hovertemplate="%{y}: VIF=%{x:.1f}<extra></extra>"))
    fig2.add_vline(x=10, line_dash="dash", line_color=CRITICAL)
    fig2.update_yaxes(autorange="reversed")
    fig2.update_xaxes(showgrid=True, gridcolor=GRID)
    fig2.update_layout(template="plotly_white", font=FONT, height=max(240, 36 * len(vif_names)),
                        margin=dict(l=10, r=40, t=10, b=10))
    st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})

    st.markdown("##### 블록(축) 단위 부분 F검정")
    st.markdown(
        "**뭘 확인하는 표인가** — 위 VIF에서 확인했듯, 다중공선성이 있으면 개별 더미 계수의 유의성이 "
        "묻힐 수 있습니다. 그래서 개별 더미가 아니라 **축 전체**(예: channel 더미 2개를 한꺼번에)를 "
        "통째로 뺀 모델과 전체 모델을 비교해, 그 축이 빠졌을 때 설명력이 실제로 유의하게 나빠지는지를 "
        "따로 검정한 것이 이 표입니다."
    )
    st.markdown(
        "**읽는 법** — F통계량이 크고 p-value가 0.05보다 작으면(판정: 유의함) 그 축을 빼는 순간 모델이 "
        "뚜렷하게 나빠진다는 뜻 — 그 축이 다른 변수로는 대체되지 않는 독자적인 설명력을 가진다는 뜻입니다. "
        "반대로 p-value가 0.05보다 크면(판정: 유의하지 않음) 그 축을 빼도 모델이 거의 그대로라는 뜻 — "
        "이미 다른 축들이 그 정보를 담고 있어서 굳이 따로 없어도 된다는 뜻입니다."
    )
    bdf = pd.DataFrame([{
        "축": b["label"], "F통계량": f"F({b['q']},{b['dof']})={b['f']:.2f}",
        "p-value": f"{b['p']:.4f}", "판정": "유의함" if b["significant"] else "유의하지 않음",
    } for b in reg["block_tests"]])
    st.dataframe(bdf, hide_index=True, width="stretch")

    st.info("**이 데이터에서 드러난 것** — channel은 F(2,59)=0.92, p=0.40으로 축 전체를 빼도 모델이 거의 "
            "나빠지지 않습니다. type이 만드는 신호와 상당 부분 겹쳐 있었다는 뜻으로, 애초에 type+channel을 "
            "분리하지 않고 함께 앵커로 고정한 이 프로젝트의 유사도 설계가 통계적으로도 타당했음을 "
            "뒷받침합니다.")


# ────────────────────────────── Challenge 전략 기획안 ──────────────────────────────

def render_strategy(candidates, top_n=2):
    if not candidates:
        st.info("전략 기획안을 표시할 후보가 없습니다.")
        return
    st.markdown(
        "앞의 \"신규 콘텐츠 진단\"이 콘텐츠 5건 각각을 개별로 본 것이라면, 이 섹션은 **과거 69건 전체의 "
        "발행 분포**를 지금까지 검증한 성과 패턴과 대조해 팀 차원에서 반복되는 구조적 문제·기회를 자동으로 "
        "찾아낸 것입니다 (`scripts/pipeline.py`의 `detect_strategic_candidates`). 예를 들어 신규 콘텐츠 5건과는 "
        "무관하게, \"과거 콘텐츠의 46%가 저성과 시간대에 몰려 있다\"처럼 발행 운영 자체의 문제를 짚습니다."
    )
    st.markdown(
        "**우선순위는 어떻게 매기나** — 우선순위 점수 = 임팩트(1–5) × 실행용이도(1–5), 25점 만점입니다. "
        "임팩트는 효과크기(%p)를 구간별로 매기되, 통계적으로 유의하지 않으면 효과크기와 무관하게 무조건 "
        "1점으로 고정합니다(근거가 약한 후보가 점수만으로 높게 뽑히지 않도록). 실행용이도는 개입 성격에 "
        "따라 고정 — 발행 일정·체크리스트만 조정하면 되면 5점, 콘텐츠 믹스 재배분처럼 조직적 노력이 "
        "필요하면 2점입니다. 덧셈이 아니라 곱셈을 쓴 이유는, 임팩트가 커도 실행이 극히 어렵다면 당장 "
        "우선순위는 낮아야 하고 반대로 쉬운데 효과가 없어도 의미가 없기 때문입니다 — 덧셈은 한쪽이 0에 "
        "가까워도 다른 쪽 점수로 상쇄되지만, 곱셈은 둘 다 충족해야 높은 점수가 나옵니다."
    )

    for i, c in enumerate(candidates[:top_n], 1):
        st.markdown(f"#### 기획안 {i:02d}. {c['title']}")
        st.caption(f"Priority {c['priority']}점")
        st.markdown(f"**문제 정의** — {c['problem']}")
        st.markdown(f"**근거 데이터 · 예상 효과** — {c['evidence']} {c['effect']}")
        st.markdown(f"**전략 제안** — {c['strategy']}")
        st.markdown("**우선순위 계산**")
        pcol1, pcol2, pcol3 = st.columns(3)
        pcol1.progress(c["impact"] / 5, text=f"임팩트 {c['impact']}/5")
        pcol2.progress(c["feasibility"] / 5, text=f"실행용이도 {c['feasibility']}/5")
        pcol3.progress(c["priority"] / 25, text=f"총점 {c['priority']}/25")
        st.divider()

    rest = candidates[top_n:]
    if rest:
        with st.expander("참고: 탐지됐지만 우선순위 상 채택되지 않은 후보"):
            for c in rest:
                st.markdown(f"**{c['title']}** ({c['priority']}점): {c['evidence']}")
