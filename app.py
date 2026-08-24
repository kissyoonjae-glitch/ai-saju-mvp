
import os
import json
import re
import requests
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="AI 정밀 사주", page_icon="🔮", layout="centered")

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

def generate_preview(name, gender, saju_data):
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
너는 전통 명리학 데이터를 바탕으로 무료 맛보기 사주를 작성한다.

사용자 이름: {name}
성별: {gender}

아래 데이터만 근거로 해석한다.
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

원칙:
- 무료 맛보기는 짧지만 구체적이어야 한다.
- 누구에게나 맞는 말만 하지 않는다.
- 가능한 경우 '사주 데이터 근거 → 해석 → 현실에서 나타날 수 있는 모습' 순서로 쓴다.
- 미래를 확정적으로 예언하지 않는다.
- 공포를 조장하지 않는다.
- JSON만 출력한다.

추가 규칙:
- 사주 데이터에 근거해 사용자의 현대적 '사주 캐릭터'를 하나 만든다.
- 캐릭터명은 "전략적 개척자형", "꾸준한 축적가형", "섬세한 조율가형", "몰입하는 장인형", "판을 읽는 전략가형"처럼 짧고 매력적으로 만든다.
- 사용자를 유명인과 동일한 사주라고 주장하지 않는다.
- 무료 화면에서는 유명인 이름을 공개하지 않는다. 유료 리포트에서만 근거와 함께 비유한다.

형식:
{{
  "keywords": ["핵심키워드1", "핵심키워드2", "핵심키워드3"],
  "headline": "이 사람의 사주를 한 문장으로 표현",
  "core": "핵심 성향 2개 문단",
  "character_name": "사주 캐릭터명",
  "character_teaser": "이 캐릭터를 설명하는 짧고 인상적인 한 문장",
  "hook": "상세 리포트에서 캐릭터 비유와 명리 근거까지 확인하고 싶게 만드는 한 문장"
}}
"""
    response = client.responses.create(model="gpt-5-mini", input=prompt)
    return json.loads(clean_json_text(response.output_text))

def stream_premium_report(name, gender, saju_data):
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
너는 유료 사주 리포트를 작성하는 전문 명리 해석가다.
아래 데이터는 SAZU 만세력 API가 계산한 실제 명리 데이터다.

이름: {name}
성별: {gender}

사주 데이터:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

반드시 지킬 원칙:
- 제공되지 않은 명리 정보는 절대 만들어내지 않는다.
- 사주 데이터의 실제 항목을 근거로 쓴다.
- 가능한 경우 매 섹션에서 '근거 → 해석 → 현실에서의 모습' 순서로 설명한다.
- 같은 말을 반복해 분량만 늘리지 않는다.
- 전문용어는 쉬운 말로 바로 풀어쓴다.
- 미래를 확정적으로 예언하지 않는다.
- 의료·법률·재정 결정을 사주만으로 권하지 않는다.
- 대운/세운 데이터가 실제로 있을 때만 시기 해석을 한다.
- 격국, 용신, 신강/신약, 합형충파해, 신살, 허자, 원국 상호작용, 종합평가가 데이터에 있으면 반드시 활용한다.
- 데이터에 없는 항목은 "제공된 데이터에서는 확인되지 않아 생략합니다"라고 쓴다.
- 문체는 자연스럽고 구체적인 한국어.
- 각 주요 섹션은 충분한 분량으로, 일반 무료 사주보다 확실히 깊게 작성한다.

다음 구성으로 작성하라.

# {name}님의 AI 정밀 사주 리포트

## 1. 사주 핵심 구조
- 연주·월주·일주·시주
- 일간
- 오행 분포
- 십성
- 12운성
이 데이터들이 실제로 제공된 경우 핵심 구조를 쉬운 말로 설명.

## 2. 나의 사주 캐릭터
- 사주 데이터에 근거해 이 사람을 가장 잘 설명하는 현대적 캐릭터명을 하나 정한다.
- 예: 전략적 개척자형, 꾸준한 축적가형, 섬세한 조율가형, 몰입하는 장인형, 판을 읽는 전략가형.
- 먼저 캐릭터를 한 문장으로 설명한다.
- 그 다음, 실제 명리 데이터 중 어떤 요소 때문에 이런 캐릭터로 해석했는지 근거를 설명한다.
- 마지막으로 이해를 돕기 위해 잘 알려진 실제 인물의 '일하는 방식/의사결정 방식/축적 방식/창작 방식'을 비유로 최대 1~2명까지 사용할 수 있다.
- 단, "당신은 일론 머스크와 같은 사주", "워런 버핏과 동일한 운명"처럼 실제 사주가 같다고 주장하지 않는다.
- 유명인의 정확한 출생시각이나 명식을 알고 있다고 가정하지 않는다.
- 비유는 오직 현대적인 캐릭터 이미지를 설명하기 위한 장치이며, 반드시 "같은 사주라는 뜻은 아니다"라는 취지를 자연스럽게 밝힌다.
- 명리 데이터와 맞지 않으면 유명인 비유를 억지로 넣지 않는다.
- 사용자의 기분을 좋게 만들기 위해 과장된 성공 예언이나 부자가 된다는 식의 표현은 쓰지 않는다.

## 3. 나라는 사람
### 타고난 성격과 기질
### 겉으로 보이는 모습과 내면
### 강점과 재능
### 반복되는 약점과 실수
### 스트레스 받을 때 나타나는 패턴
### 사람을 보고 판단하는 방식
### 과하거나 부족한 기운
오행, 십성, 신강/신약, 원국 상호작용이 있다면 적극 활용.

## 4. 직업과 일
### 조직생활과 독립적 일의 적합도
### 리더형 / 실무형 성향
### 혼자 일할 때와 협업할 때
### 잘 맞는 업무환경
### 피로해지기 쉬운 업무환경
### 돈으로 연결하기 쉬운 강점
십성, 격국, 용신, 신강/신약 데이터를 근거로 설명.

## 5. 사업 성향
### 사업가적 성향
### 독립성
### 리더십
### 동업 성향
### 위험 감수 방식
### 사업에서 조심할 패턴
운명처럼 단정하지 말고 성향으로 해석.

## 6. 재물운
### 돈을 버는 방식
### 돈을 모으고 지키는 방식
### 안정 수입과 기회형 수입 중 어느 쪽에 가까운지
### 돈이 새기 쉬운 패턴
### 재물 흐름을 볼 때 주의할 점
십성·재성·대운·세운 관련 데이터가 실제로 있을 때만 연결.

## 7. 연애와 인간관계
### 연애할 때의 모습
### 관계에서 중요하게 느끼는 것
### 끌리기 쉬운 관계
### 갈등 시 패턴
### 결혼생활에서 중요하게 작용할 성향
### 친구관계
### 직장 인간관계
합충형파해와 원국 상호작용이 있으면 관계 해석에 활용.

## 8. 사주의 골격
### 신강 / 신약
### 격국
### 용신 / 희신 / 기신 / 구신
### 합·형·충·파·해
### 신살
### 허자
각 데이터가 실제로 존재할 경우 그 의미와 현실에서 어떻게 작용할 수 있는지 설명.

## 9. 인생의 흐름
### 대운 전체 흐름
### 현재 대운
### 다음 대운
### 세운
### 최근과 앞으로의 주목할 시기
반드시 API가 제공한 실제 대운/세운 데이터에 근거한다.
구체적 사건을 확정적으로 예언하지 않고 '경향'으로 설명.

## 10. 종합평가
API의 evaluation/종합평가 데이터가 있다면 다른 모듈과 교차해서 설명.
없다면 지금까지의 근거를 종합.

## 11. 당신의 사주를 한 문장으로 표현하면
짧고 인상적으로 한 문장.

## 12. 가장 잘 활용해야 할 것
강점과 유리한 방향을 3개.

## 13. 가장 경계해야 할 것
반복 실수와 위험 패턴을 3개.

## 14. 현실에서의 방향
사주를 맹신하지 않는 전제로 지금 삶에서 참고할 수 있는 구체적인 행동 5개.

마지막 문구:
"이 내용은 전통 명리학을 AI가 해석한 자기성찰·엔터테인먼트 콘텐츠이며, 중요한 의사결정의 유일한 근거로 사용하지 마세요."
"""
    stream = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
        stream=True,
    )

    for event in stream:
        if getattr(event, "type", None) == "response.output_text.delta":
            yield event.delta

# ---------- UI ----------

# ---------- UI ----------
st.markdown("""
<style>
    .stApp {
        background:
            radial-gradient(circle at top, rgba(155,115,65,0.08), transparent 28%),
            linear-gradient(180deg, #fbf8f2 0%, #f4efe6 100%);
        color: #2f2a25;
    }
    .block-container {
        max-width: 760px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }
    .saju-card {
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(103,78,48,0.16);
        border-radius: 24px;
        padding: 28px 28px 22px 28px;
        box-shadow: 0 12px 35px rgba(80,55,30,0.08);
        backdrop-filter: blur(8px);
        margin-bottom: 22px;
    }
    .hero-title {
        text-align:center;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        color:#342b24;
        margin-top: 0.3rem;
        margin-bottom: .4rem;
    }
    .hero-sub {
        text-align:center;
        color:#7a6d60;
        font-size: .98rem;
        margin-bottom: 1.8rem;
    }
    .seal {
        width:74px;height:74px;
        margin:0 auto 10px auto;
        border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        border:1px solid rgba(117,82,44,.28);
        background:linear-gradient(145deg,#efe1cc,#f9f3e9);
        font-size:34px;
        box-shadow: inset 0 0 0 5px rgba(255,255,255,.45);
    }
    .section-kicker {
        color:#9a784d;
        font-size:.78rem;
        letter-spacing:.14em;
        font-weight:700;
        text-transform:uppercase;
        margin-bottom:.35rem;
    }
    .result-title {
        font-size:1.7rem;
        font-weight:800;
        color:#2f2924;
        margin-bottom:.4rem;
    }
    .keyword-wrap { text-align:center; margin: 12px 0 16px 0; }
    .keyword {
        display:inline-block;
        padding:7px 12px;
        margin:4px;
        border-radius:999px;
        background:#efe6d9;
        border:1px solid #ddcbb6;
        color:#5e4b38;
        font-size:.9rem;
        font-weight:700;
    }
    .locked-box {
        background:#f7f1e8;
        border:1px solid #e3d4c2;
        border-radius:16px;
        padding:15px 16px;
        margin:9px 0;
    }
    .price-box {
        background:linear-gradient(135deg,#332a24 0%,#514235 100%);
        color:white;
        border-radius:20px;
        padding:24px;
        margin-top:20px;
        text-align:center;
    }
    .price-box h3 { color:white !important; margin:0 0 6px 0; }
    .price-box p { color:#e9ded1 !important; margin:0; }
    .stButton > button {
        border-radius: 14px !important;
        min-height: 48px;
        font-weight: 700;
    }
    div[data-baseweb="select"] > div, .stTextInput input {
        border-radius: 12px !important;
    }
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    header {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state["page"] = "input"

def go_input():
    st.session_state["page"] = "input"
    st.session_state.pop("preview", None)
    st.session_state.pop("saju_data", None)
    st.session_state.pop("premium_report", None)
    st.session_state.pop("show_full_report", None)

# ---------- PAGE 1 : INPUT ----------
if st.session_state["page"] == "input":
    st.markdown('<div class="seal">☯</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">AI 정밀 사주</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">전통 명리 데이터를 바탕으로, 당신의 사주를 현대적인 언어로 풀어드립니다.</div>', unsafe_allow_html=True)

    st.markdown('<div class="saju-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">BIRTH DATA</div>', unsafe_allow_html=True)

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
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("✨ 내 사주 보기", type="primary", use_container_width=True):
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
            with st.spinner("사주 원국과 명리 데이터를 계산하고 있어요..."):
                data = calculate_saju(year, month, day, birth_time, gender)

            with st.spinner("핵심 풀이를 정리하고 있어요..."):
                preview = generate_preview(name, gender, data)

            st.session_state["saju_data"] = data
            st.session_state["saju_name"] = name
            st.session_state["saju_gender"] = gender
            st.session_state["preview"] = preview
            st.session_state["page"] = "result"
            st.rerun()

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

    st.caption("전통 명리학 기반 자기성찰·엔터테인먼트 콘텐츠")

# ---------- PAGE 2 : RESULT ----------
elif st.session_state["page"] == "result":
    preview = st.session_state.get("preview", {})
    name = st.session_state.get("saju_name", "사용자")

    top1, top2 = st.columns([1, 4])
    with top1:
        if st.button("← 다시 입력"):
            go_input()
            st.rerun()
    with top2:
        st.markdown(f'<div class="section-kicker">SAJU READING</div><div class="result-title">{name}님의 사주 풀이</div>', unsafe_allow_html=True)

    st.markdown('<div class="saju-card">', unsafe_allow_html=True)

    keywords = preview.get("keywords", [])
    if keywords:
        kw_html = "".join([f'<span class="keyword">{k}</span>' for k in keywords])
        st.markdown(f'<div class="keyword-wrap">{kw_html}</div>', unsafe_allow_html=True)

    if preview.get("headline"):
        st.markdown(f"### {preview['headline']}")

    st.write(preview.get("core", ""))

    character_name = preview.get("character_name", "")
    character_teaser = preview.get("character_teaser", "")
    if character_name:
        st.markdown("### 🎭 나의 사주 캐릭터")
        st.markdown(f"**{character_name}**")
        if character_teaser:
            st.write(character_teaser)
        st.caption("정밀 사주에서는 이 캐릭터가 나온 명리 근거와 현대적 인물 비유까지 확인할 수 있습니다.")

    if preview.get("hook"):
        st.info(preview["hook"])

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-kicker">PREMIUM READING</div>', unsafe_allow_html=True)
    st.markdown("## 🔒 전체 정밀 사주에서 확인할 수 있습니다")

    sections = {
        "나의 사주 캐릭터": "캐릭터 유형 · 명리 근거 · 현대적 인물 비유",
        "나라는 사람": "타고난 기질 · 내면과 외면 · 강점 · 약점 · 스트레스 패턴",
        "직업과 일": "조직생활 · 독립형 일 · 리더십 · 적합한 업무환경 · 돈으로 연결되는 강점",
        "사업 성향": "창업 성향 · 독립성 · 동업 · 리더십 · 사업에서 조심할 점",
        "재물운": "돈 버는 방식 · 돈을 모으는 방식 · 재물 패턴 · 주의할 점",
        "연애와 인간관계": "연애 성향 · 갈등 패턴 · 결혼생활 · 친구 · 직장 관계",
        "사주의 골격": "신강/신약 · 격국 · 용신 · 희신 · 기신 · 합형충파해 · 신살 · 허자",
        "인생의 흐름": "대운 · 현재 흐름 · 다음 대운 · 세운 · 주목할 시기",
        "마지막 종합 풀이": "당신을 한 문장으로 · 가장 활용할 강점 · 가장 경계할 점 · 현실 방향",
    }

    for title, desc in sections.items():
        st.markdown(
            f'<div class="locked-box">🔒 <b>{title}</b><br><span style="color:#7c6e61;font-size:.9rem">{desc}</span></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="price-box">
            <h3>AI 정밀 사주 전체 풀이 · 4,900원</h3>
            <p>실제 명리 데이터의 근거부터 직업·사업·재물·관계·대운과 종합 방향까지 상세하게 풀이합니다.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if PAYMENT_URL:
        st.link_button("💳 전체 정밀 사주 구매하기", PAYMENT_URL, use_container_width=True)
    else:
        st.button("💳 전체 정밀 사주 구매하기", use_container_width=True, disabled=True)
        st.caption("결제 링크 연결 전 테스트 버전입니다.")

    if TEST_MODE:
        st.divider()
        st.markdown("### 🧪 운영자 테스트")
        if st.button("전체 정밀 리포트 생성 테스트", use_container_width=True):
            st.session_state["show_full_report"] = True

        if st.session_state.get("show_full_report"):
            st.markdown("## 전체 정밀 사주 리포트")

            if "premium_report" not in st.session_state:
                placeholder = st.empty()
                full_text = ""
                try:
                    for chunk in stream_premium_report(
                        st.session_state["saju_name"],
                        st.session_state["saju_gender"],
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

    st.caption("전통 명리학 기반 자기성찰·엔터테인먼트 콘텐츠")
