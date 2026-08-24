
import os
import json
import requests
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="AI 사주", page_icon="🔮", layout="centered")
st.title("🔮 AI 사주")
st.caption("이름과 출생정보를 선택하면 바로 풀이합니다.")

def get_secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, "")

SAZU_API_KEY = get_secret("SAZU_API_KEY")
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")

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

def calculate_saju():
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

def generate_report(saju_data):
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
너는 전통 명리학 데이터를 일반인이 이해하기 쉬운 한국어로 해석하는 AI 사주 리포트 작성자다.
이름: {name or "사용자"}
성별: {gender}

아래 데이터는 외부 만세력 API가 계산한 결과다. 계산값을 임의로 바꾸지 말고 이 데이터만 바탕으로 설명한다.

사주 데이터:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

쉬운 한국어로 기본 기질, 강점, 조심할 점, 일과 직업, 돈을 대하는 방식,
인간관계와 연애, 삶의 흐름, 현실에서 도움이 될 3가지를 균형 있게 설명하라.
미래를 확정적으로 예언하거나 공포를 조장하지 말고, 중요한 의료·법률·재정 결정을 사주만으로 권하지 말라.
마지막에 "이 내용은 전통 명리학을 AI가 해석한 자기성찰·엔터테인먼트 콘텐츠입니다."라고 표시하라.
"""
    response = client.responses.create(model="gpt-5-mini", input=prompt)
    return response.output_text

st.divider()

if st.button("✨ 내 사주 보기", type="primary", use_container_width=True):
    if not SAZU_API_KEY:
        st.error("SAZU API 키가 설정되지 않았습니다.")
        st.stop()
    if not OPENAI_API_KEY:
        st.error("OpenAI API 키가 설정되지 않았습니다.")
        st.stop()
    if not name.strip():
        st.warning("이름을 입력해주세요.")
        st.stop()
    try:
        with st.spinner("사주를 계산하고 있어요..."):
            data = calculate_saju()
        with st.spinner("AI가 풀이하고 있어요..."):
            report = generate_report(data)
        st.success("풀이가 완료되었습니다.")
        st.markdown(report)
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("테스트용 MVP · 자기성찰/엔터테인먼트용")
