
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
        timeout=30,
    )
    r.raise_for_status()
    result = r.json()

    if not result.get("success"):
        raise RuntimeError(result.get("error", {}).get("message", "사주 계산 오류"))

    return result["data"]

def generate_saju_package(name, gender, focus, saju_data):
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
너는 전통 명리학 데이터를 바탕으로 '무료 맛보기 + 유료 상세 리포트'를 만드는 전문 사주 리포트 작성자다.

사용자 이름: {name}
성별: {gender}
가장 궁금한 분야: {focus}

아래 데이터는 외부 만세력 API가 계산한 결과다.
절대로 없는 명리 정보를 지어내지 말고, 제공된 데이터에 근거해서만 해석하라.

사주 데이터:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

중요 원칙:
- 미래를 확정적으로 예언하지 않는다.
- 공포를 조장하지 않는다.
- 의료·법률·재정 등 중요한 판단을 사주만으로 권하지 않는다.
- 전문용어를 쓰면 바로 쉬운 말로 풀어쓴다.
- 누구에게나 통할 법한 모호한 문장만 쓰지 말고, 가능한 한 '사주 데이터의 근거 → 해석 → 현실에서 나타날 수 있는 모습' 순서로 설명한다.
- 같은 내용을 반복해서 분량만 늘리지 않는다.
- 무료 맛보기는 궁금증을 만들 만큼 구체적이어야 하지만, 유료 상세 내용을 그대로 다 공개하지 않는다.
- 유료 리포트는 읽고 나서 '무료 사주보다 훨씬 구체적이다'라는 느낌이 들 정도로 충분히 자세히 쓴다.
- 각 유료 섹션은 최소 2~4문단 분량의 밀도를 갖는다.
- 사용자가 고른 '가장 궁금한 분야'는 다른 항목보다 조금 더 자세히 다룬다.

반드시 아래 JSON 형식만 출력하라. 마크다운 코드블록은 쓰지 마라.

{{
  "preview": {{
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "headline": "이 사용자의 사주를 한 문장으로 요약",
    "core": "무료로 보여줄 핵심 성향 2~3문단",
    "hook": "상세 리포트에서 더 알고 싶게 만드는 구체적인 한 문장"
  }},
  "premium": {{
    "기본 기질": "상세 내용",
    "강점과 재능": "상세 내용",
    "반복되는 약점과 스트레스 패턴": "상세 내용",
    "일과 직업": "상세 내용",
    "사업 성향": "상세 내용",
    "재물과 돈을 대하는 방식": "상세 내용",
    "인간관계": "상세 내용",
    "연애와 가까운 관계": "상세 내용",
    "삶의 흐름": "대운/운세 데이터가 실제 제공된 경우에만 상세 해석. 없으면 데이터가 없어 구체적 시기 해석을 생략한다고 명시",
    "현실에서 활용하는 방법": "구체적인 행동 제안 3~5개"
  }},
  "disclaimer": "이 내용은 전통 명리학을 AI가 해석한 자기성찰·엔터테인먼트 콘텐츠이며, 중요한 의사결정의 유일한 근거로 사용하지 마세요."
}}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )
    raw = response.output_text
    return json.loads(clean_json_text(raw))

# ---------- UI ----------
st.title("🔮 AI 사주")
st.caption("출생정보를 입력하면 무료 핵심 풀이를 먼저 확인할 수 있습니다.")

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
gender = st.radio("성별 선택", ["남성", "여성"], horizontal=True, label_visibility="collapsed")

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

    try:
        with st.spinner("사주를 계산하고 있어요..."):
            data = calculate_saju(year, month, day, birth_time, gender)

        with st.spinner("핵심 풀이를 만들고 있어요..."):
            package = generate_saju_package(name, gender, focus, data)

        st.session_state["saju_package"] = package
        st.session_state["saju_name"] = name

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

if "saju_package" in st.session_state:
    package = st.session_state["saju_package"]
    preview = package.get("preview", {})
    premium = package.get("premium", {})

    st.success("무료 핵심 풀이가 완성되었습니다.")

    st.markdown("## 한눈에 보는 당신의 사주")
    keywords = preview.get("keywords", [])
    if keywords:
        st.markdown(" · ".join([f"**{k}**" for k in keywords]))

    st.markdown(f"### {preview.get('headline', '')}")
    st.write(preview.get("core", ""))

    if preview.get("hook"):
        st.info(preview["hook"])

    st.divider()
    st.markdown("## 🔒 전체 사주 리포트에서 확인할 수 있어요")

    locked_titles = list(premium.keys())
    for title in locked_titles:
        st.markdown(f"🔒 **{title}**")

    st.markdown("---")
    st.markdown("### 전체 사주 풀이 · 4,900원")
    st.caption("직업·사업 · 재물 · 인간관계 · 연애 · 삶의 흐름 · 현실 활용법까지 상세하게")

    if PAYMENT_URL:
        st.link_button("💳 전체 사주 풀이 구매하기", PAYMENT_URL, use_container_width=True)
        st.caption("※ 결제 후 자동 잠금 해제 기능은 다음 버전에서 연결합니다.")
    else:
        st.button("💳 전체 사주 풀이 구매하기", use_container_width=True, disabled=True)
        st.caption("결제 링크 연결 전 테스트 버전입니다.")

    # 운영자 테스트용: Streamlit Secrets에 TEST_MODE="true"를 넣은 경우에만 보임
    if TEST_MODE:
        st.divider()
        if st.button("🧪 운영자 테스트: 전체 리포트 보기", use_container_width=True):
            st.session_state["show_full_report"] = True

        if st.session_state.get("show_full_report"):
            st.markdown("## 전체 사주 리포트")
            for title, content in premium.items():
                st.markdown(f"### {title}")
                st.write(content)
            st.caption(package.get("disclaimer", ""))

st.divider()
st.caption("전통 명리학 기반 자기성찰·엔터테인먼트 콘텐츠")
