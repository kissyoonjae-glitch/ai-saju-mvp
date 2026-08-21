
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
    month = st.selectbox("월", list(range(1, 13)), index=0)
with c3:
    day = st.selectbox("일", list(range(1, 32)), index=0)

st.subheader("태어난 시각")
time_options = ["모름"] + [f"{h:02d}:00" for h in range(24)]
birth_time = st.selectbox("시간", time_options, index=13)

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
        payload["birthHour"] = int(birth_time.split(":")[0])
    else:
        payload["birthHour"] = None

    r = requests.post(
        "https://api.sazu.app/v1/sazu/calculate",
        headers={
            "x-api-key": SAZU_API_KEY,
            "Content-Type": "application/json",
        },
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

아래 데이터는 외부 만세력 API가 계산한 결과다.
계산값을 임의로 바꾸거나 새로 만들지 말고 이 데이터만 바탕으로 설명한다.

사주 데이터:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

작성 원칙:
- 쉬운 한국어 사용
- 전문용어가 나오면 바로 뜻을 설명
- 미래를 확정적으로 예언하지 않음
- 공포를 조장하지 않음
- 특정 직업, 투자, 결혼, 의료 판단을 운명처럼 단정하지 않음
- 장점과 주의점을 균형 있게 설명
- 실제 사람이 읽는 사주 풀이처럼 자연스럽게 작성

구성:
# {name or "사용자"}님의 사주 풀이

## 한눈에 보는 성향
핵심 특징 3~5가지

## 기본 기질
전체적인 성향과 기질

## 강점
잘 살릴 수 있는 면

## 조심할 점
반복될 수 있는 패턴이나 스트레스 포인트

## 일과 직업
어떤 환경에서 능력을 발휘하기 쉬운지

## 돈을 대하는 방식
재물에 대한 태도와 주의점

## 인간관계와 연애
관계에서 나타날 수 있는 특징

## 삶의 흐름
대운/운세 데이터가 있으면 경향만 설명하고 없으면 억지로 만들지 않기

## 현실에서 도움이 될 3가지
작고 구체적인 제안 3개

마지막에 짧게:
"이 내용은 전통 명리학을 AI가 해석한 자기성찰·엔터테인먼트 콘텐츠입니다."
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )
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
            saju_data = calculate_saju()

        with st.spinner("AI가 풀이하고 있어요..."):
            report = generate_report(saju_data)

        st.success("풀이가 완료되었습니다.")
        st.markdown(report)

    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("테스트용 MVP · 자기성찰/엔터테인먼트용")
