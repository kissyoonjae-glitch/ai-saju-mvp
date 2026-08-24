
import os
import json
import re
import requests
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="AI 사주", page_icon="🔮", layout="centered")

# ---------- Helpers ----------
def get_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)

SAZU_API_KEY = get_secret("SAZU_API_KEY")
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
PAYMENT_URL = get_secret("PAYMENT_URL")
TEST_MODE = str(get_secret("TEST_MODE", "false")).lower() == "true"

def clean_json_text(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def calculate_saju(year, month, day, birth_time, gender):
    payload = {
        "birthYear": int(year),
        "birthMonth": int(month),
        "birthDay": int(day),
        "isFemale": gender == "여성",
        "isLunar": False,
    }

    if birth_time != "모름":
        hh, mm = birth_time.split(":")
        payload["birthHour"] = int(hh)
        payload["birthMinute"] = int(mm)
    else:
        payload["birthHour"] = None
        payload["birthMinute"] = None

    r = requests.post(
        "https://api.sazu.app/v1/sazu/calculate",
        headers={"x-api-key": SAZU_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    result = r.json()

    if not result.get("success"):
        raise RuntimeError(result.get("error", {}).get("message", "사주 계산 오류"))

    return result["data"]

def generate_preview(name, gender, focus, saju_data):
    """
    무료 맛보기만 짧게 생성.
    상세 리포트는 절대 여기서 만들지 않음.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
너는 전통 명리학 데이터를 바탕으로 '무료 맛보기 사주'를 작성한다.

사용자 이름: {name}
성별: {gender}
가장 궁금한 분야: {focus}

아래 데이터는 외부 만세력 API가 계산한 결과다.
없는 정보를 지어내지 말고 제공된 데이터에 근거해서만 해석하라.

사주 데이터:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

중요 원칙:
- 아주 짧고 핵심적으로 작성한다.
- 미래를 확정적으로 예언하지 않는다.
- 공포를 조장하지 않는다.
- 누구에게나 맞는 모호한 말만 하지 말고, 가능한 한 사주 데이터에 기반한 특징을 말한다.
- 사용자가 선택한 관심 분야를 살짝 건드리되 상세 답은 남겨둔다.
- 출력은 반드시 JSON만 반환한다.

형식:
{{
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "headline": "이 사람의 사주를 한 문장으로 요약",
  "core": "핵심 성향을 2개의 짧은 문단으로 설명",
  "hook": "상세 리포트에서 더 알고 싶게 만드는 구체적인 한 문장"
}}
"""
    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )
    return json.loads(clean_json_text(response.output_text))

def stream_premium_report(name, gender, focus, saju_data):
    """
    상세 사주는 결제 후에만 생성.
    생성되는 내용을 스트리밍으로 바로 보여줌.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
너는 전통 명리학 데이터를 바탕으로 유료 상세 사주 리포트를 작성한다.

사용자 이름: {name}
성별: {gender}
가장 궁금한 분야: {focus}

아래 데이터는 외부 만세력 API가 계산한 결과다.
없는 명리정보를 만들어내지 말고 제공된 데이터에 근거해서만 해석하라.

사주 데이터:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

작성 원칙:
- 무료 사주보다 훨씬 구체적이고 깊이 있게 작성한다.
- 각 항목에서 가능하면 '사주 데이터의 근거 → 해석 → 현실에서 나타날 수 있는 모습' 순서로 쓴다.
- 전문용어는 쉬운 말로 즉시 풀어쓴다.
- 같은 내용을 반복해서 분량만 늘리지 않는다.
- 사용자가 고른 관심 분야는 다른 항목보다 더 자세히 다룬다.
- 미래를 확정적으로 예언하지 않는다.
- 의료·법률·재정 등의 중요한 결정을 사주만으로 권하지 않는다.
- 대운/세운 데이터가 없으면 구체적인 시기 운세를 지어내지 않는다.

마크다운으로 작성:

# {name}님의 상세 사주 리포트

## 1. 사주 핵심 구조
핵심 구조와 전체적인 기질 설명

## 2. 기본 성향과 기질
사고방식, 행동방식, 감정 표현, 에너지 사용 방식

## 3. 강점과 재능
어떤 환경에서 강점이 드러나는지 구체적으로

## 4. 반복될 수 있는 약점과 스트레스 패턴
실제 생활에서 어떻게 나타날 수 있는지 구체적으로

## 5. 일과 직업
조직/독립, 안정/변화, 사람/과업, 기획/실행 관점에서 자세히

## 6. 사업 성향
창업, 독립성, 리더십, 동업, 위험 감수에 대한 전통 명리 관점의 해석

## 7. 돈과 재물
돈을 버는 방식, 쓰는 방식, 관리 경향, 주의점

## 8. 인간관계
대인관계에서 나타나는 특징, 거리감, 갈등 방식

## 9. 연애와 가까운 관계
관계에서 중요하게 느끼는 것과 반복될 수 있는 패턴

## 10. 삶의 흐름
실제 제공된 대운/운세 데이터가 있을 때만 경향을 설명

## 11. 지금 관심 분야에 대한 집중 해석
사용자가 선택한 '{focus}'를 가장 자세히 설명

## 12. 현실에서 활용하는 방법
작고 구체적인 행동 제안 5개

마지막 문구:
"이 내용은 전통 명리학을 AI가 해석한 자기성찰·엔터테인먼트 콘텐츠이며, 중요한 의사결정의 유일한 근거로 사용하지 마세요."
"""

    stream = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
        stream=True,
    )

    for event in stream:
        # Responses API streaming event compatibility
        if getattr(event, "type", None) == "response.output_text.delta":
            yield event.delta

# ---------- UI ----------
st.title("🔮 AI 사주")
st.caption("출생정보를 입력하면 무료 핵심 풀이를 빠르게 확인할 수 있습니다.")

name = st.text_input("이름", placeholder="예: 홍길동")

st.subheader("생년월일")
c1, c2, c3 = st.columns(3)
with c1:
    year = st.selectbox("연도", list(range(2026, 1939, -1)), index=36)
with c2:
    month = st.selectbox("월", list(range(1, 13)))
with c3:
    day = st.selectbox("일", list(range(1, 32)))

st.subheader("태어난 시각")
time_options = ["모름"] + [
    f"{h:02d}:{m:02d}"
    for h in range(24)
    for m in range(0, 60, 10)
]
birth_time = st.selectbox("시간", time_options, index=73)

st.subheader("성별")
gender = st.radio(
    "성별 선택",
    ["남성", "여성"],
    horizontal=True,
    label_visibility="collapsed"
)

st.subheader("가장 궁금한 분야")
focus = st.selectbox(
    "관심 분야",
    ["전체적인 사주", "직업·사업", "돈·재물", "연애·관계", "앞으로의 흐름"],
    label_visibility="collapsed"
)

st.divider()

if st.button("✨ 무료로 내 사주 보기", type="primary", use_container_width=True):
    if not name.strip():
        st.warning("이름을 입력해주세요.")
        st.stop()
    if not SAZU_API_KEY:
        st.error("SAZU API 키가 설정되지 않았습니다.")
        st.stop()
    if not OPENAI_API_KEY:
        st.error("OpenAI API 키가 설정되지 않았습니다.")
        st.stop()

    # 입력값이 바뀌면 기존 상세 리포트 상태 초기화
    st.session_state.pop("show_full_report", None)
    st.session_state.pop("premium_report", None)

    try:
        with st.spinner("사주 데이터를 계산하고 있어요..."):
            data = calculate_saju(year, month, day, birth_time, gender)

        # 사주 데이터는 재사용
        st.session_state["saju_data"] = data
        st.session_state["saju_name"] = name
        st.session_state["saju_gender"] = gender
        st.session_state["saju_focus"] = focus

        with st.spinner("핵심만 빠르게 보고 있어요..."):
            preview = generate_preview(name, gender, focus, data)

        st.session_state["preview"] = preview

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

if "preview" in st.session_state:
    preview = st.session_state["preview"]

    st.success("무료 핵심 풀이가 완성되었습니다.")

    st.markdown("## 한눈에 보는 당신의 사주")

    keywords = preview.get("keywords", [])
    if keywords:
        st.markdown(" · ".join([f"**{k}**" for k in keywords]))

    headline = preview.get("headline", "")
    if headline:
        st.markdown(f"### {headline}")

    st.write(preview.get("core", ""))

    if preview.get("hook"):
        st.info(preview["hook"])

    st.divider()
    st.markdown("## 🔒 전체 사주 리포트에서 확인할 수 있어요")
    for title in [
        "사주 핵심 구조",
        "기본 성향과 기질",
        "강점과 재능",
        "반복되는 약점과 스트레스 패턴",
        "일과 직업",
        "사업 성향",
        "돈과 재물",
        "인간관계",
        "연애와 가까운 관계",
        "삶의 흐름",
        "관심 분야 집중 해석",
        "현실에서 활용하는 방법",
    ]:
        st.markdown(f"🔒 **{title}**")

    st.markdown("---")
    st.markdown("### 전체 사주 풀이 · 4,900원")
    st.caption("상세 리포트는 결제 후 생성되므로 무료 결과가 더 빠르게 표시됩니다.")

    if PAYMENT_URL:
        st.link_button("💳 전체 사주 풀이 구매하기", PAYMENT_URL, use_container_width=True)
        st.caption("※ 현재는 외부 결제 링크 연결용입니다.")
    else:
        st.button("💳 전체 사주 풀이 구매하기", use_container_width=True, disabled=True)
        st.caption("결제 링크 연결 전 테스트 버전입니다.")

    # 운영자 테스트용
    if TEST_MODE:
        st.divider()
        st.markdown("### 🧪 운영자 테스트")
        st.caption("이 버튼은 TEST_MODE=true일 때만 보입니다.")

        if st.button("전체 상세 리포트 생성 테스트", use_container_width=True):
            st.session_state["show_full_report"] = True

        if st.session_state.get("show_full_report"):
            st.markdown("## 전체 상세 리포트")

            if "premium_report" not in st.session_state:
                placeholder = st.empty()
                full_text = ""

                try:
                    for chunk in stream_premium_report(
                        st.session_state["saju_name"],
                        st.session_state["saju_gender"],
                        st.session_state["saju_focus"],
                        st.session_state["saju_data"],
                    ):
                        full_text += chunk
                        placeholder.markdown(full_text + "▌")

                    placeholder.markdown(full_text)
                    st.session_state["premium_report"] = full_text

                except Exception as e:
                    st.error(f"상세 리포트 생성 중 오류: {e}")
            else:
                st.markdown(st.session_state["premium_report"])

st.divider()
st.caption("전통 명리학 기반 자기성찰·엔터테인먼트 콘텐츠")
