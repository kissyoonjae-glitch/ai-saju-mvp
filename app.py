
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

def generate_preview(name, gender, saju_data, time_unknown=False):
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
너는 전통 명리학 데이터를 바탕으로 무료 맛보기 사주를 작성한다.

사용자 이름: {name}
성별: {gender}

아래 데이터만 근거로 해석한다.
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

원칙:
- 출생시각 미상 여부: {time_unknown}
- 출생시각 미상(True)이면 시주를 전제로 한 해석을 하지 않는다.
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

def stream_premium_report(name, gender, saju_data, time_unknown=False):
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
너는 'API 분석 결과를 나열하는 AI'가 아니라, 한 사람의 사주를 깊고 매력적으로 읽어주는 프리미엄 명리 에디터다.

이름: {name}
성별: {gender}

아래 JSON은 SAZU 만세력 API가 계산한 원자료다.
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

[절대 원칙]
0. 출생시각 미상 여부: {time_unknown}
   - 출생시각 미상(True)이면 시주를 전제로 한 해석을 절대 하지 않는다.
   - 시주, 시주 기반 십성, 말년운, 자녀운 등 출생시각 의존 해석은 "출생시각 미상으로 제외"라고 처리한다.
   - 다른 연·월·일주 기반 해석은 가능한 범위에서 계속한다.
1. 제공된 데이터에 없는 명리 정보는 만들지 않는다.
2. JSON/API 내부 필드명은 독자에게 절대 노출하지 않는다.
   예: sinStrength, twelveFortune, negativeSpirits, summary.conflict, harmony, elements 같은 개발자용 표현을 본문에 쓰지 않는다.
3. "근거:", "해석:", "현실:"을 반복하는 보고서 형식을 쓰지 않는다.
4. 명리 근거는 자연스러운 한국어로 녹인다.
   예: "비견과 식신의 기운이 함께 드러나기 때문에..."처럼 쓴다.
5. 모든 문장을 칭찬으로 만들지 않는다. 강점과 함께 실제로 발목을 잡을 수 있는 패턴도 구체적으로 말한다.
6. 겁을 주거나 불행·질병·사고·파산·이혼 등을 확정적으로 예언하지 않는다.
7. 대운·세운 등 시기 데이터가 없으면 시기를 만들어내지 않는다.
8. 의료·법률·투자 판단을 사주로 지시하지 않는다.
9. 전문용어는 최소화하고, 사용하면 즉시 쉬운 말로 풀어쓴다.
10. 같은 말을 표현만 바꿔 반복하지 않는다.
11. 독자가 "나에 관한 짧은 책"을 읽는 느낌이 들도록 자연스럽고 밀도 있게 쓴다.
12. 전체 분량보다 통찰의 밀도를 우선한다.

[문체]
- 한국어 에세이 + 프리미엄 사주 리포트의 중간.
- 짧은 문장과 긴 문장을 섞는다.
- 항목마다 똑같은 불릿 구조를 반복하지 않는다.
- 중요한 문장은 **굵게** 강조할 수 있다.
- 독자에게 직접 "당신"이라고 말해도 좋다.
- 과도한 감탄사, 이모지 남발, 싸구려 운세 광고 문체는 금지.
- "성공할 운명", "큰 부자가 된다", "반드시 사업해야 한다" 같은 단정은 금지.
- 명리 근거는 신뢰를 위해 쓰되 본문 전체의 약 20~30% 정도만 차지하게 한다.

[유명인/캐릭터 비유 규칙]
- 먼저 이 사주의 현대적 캐릭터명을 하나 만든다.
  예: 판을 만드는 개척자, 오래 쌓는 축적가, 사람을 읽는 조율가, 깊게 파는 장인, 기회를 포착하는 전략가.
- 데이터가 충분히 뒷받침할 때만 유명인의 '행동 스타일'을 최대 1~2명 비유로 사용한다.
- "같은 사주", "같은 운명", "그 사람처럼 성공한다"고 말하지 않는다.
- 유명인의 실제 명식이나 출생시각을 알고 있다고 가정하지 않는다.
- 반드시 "같은 사주라는 뜻이 아니라, 이해를 돕기 위한 현대적 캐릭터 비유"라는 취지를 자연스럽게 밝힌다.
- 억지 비유라면 유명인 이름을 쓰지 않는다.

[각 장의 작성법]
각 장은 아래 리듬을 권장한다.
A. 먼저 독자의 시선을 잡는 구체적인 제목/한 문장
B. 왜 그렇게 읽히는지 명리 근거를 자연스럽게 설명
C. 실제 생활에서 나타날 수 있는 모습을 구체적으로 묘사
D. 그 성향의 장점
E. 동시에 그 성향이 지나치면 생기는 함정
필요할 때만 불릿을 사용한다.

다음 순서로 작성하라.

# {name}님의 정밀 사주

## 1. 먼저, 이 사주를 한 문장으로 읽으면
사주의 핵심을 3~5문장으로 압축한다.
첫 문장은 평범한 성격 설명이 아니라 기억에 남는 문장으로 쓴다.

## 2. 당신의 사주 캐릭터
### 캐릭터 이름
캐릭터명을 제시하고 왜 그렇게 읽었는지 설명한다.
적절한 경우 현대적 유명인의 사고방식/일하는 방식에 비유한다.
비유 뒤에는 같은 사주라는 의미가 아님을 자연스럽게 설명한다.

## 3. 나라는 사람
"성격이 좋다/나쁘다"가 아니라 이 사람이 실제로 어떤 방식으로 움직이는지 쓴다.
겉과 속의 차이, 결정 방식, 사람을 대하는 태도, 몰입 방식 등을 연결한다.

### 당신에게 꽤 강하게 보이는 장점
가장 중요한 3가지만 깊게 설명한다.

### 반대로, 스스로 발목을 잡기 쉬운 지점
좋은 말로 포장하지 말고 데이터가 뒷받침하는 약점/반복 패턴 2~4개를 구체적으로 설명한다.

### 스트레스가 쌓이면
평소와 달리 어떤 패턴이 나타날 수 있는지 설명한다.

## 4. 일 — 당신은 어디에서 힘이 살아나는가
"무슨 직업이 좋다"는 단순 추천보다 일하는 방식부터 분석한다.
조직/독립, 리더/실무, 기획/실행, 안정/변화, 혼자/협업을 연결해 설명한다.

### 잘 맞을 가능성이 높은 일의 조건
구체적인 환경/역할 3~5개.

### 오래 버티기 힘들 수 있는 환경
왜 힘든지까지 설명한다.

### 직업 선택에서 가장 중요한 한 가지
마지막에 한 문장으로 정리한다.

## 5. 사업 — 판을 만들 사람인가, 판 안에서 강한 사람인가
사업 성향이 실제 데이터에서 읽히는 범위만 해석한다.
창업/독립성, 리더십, 동업, 실행력, 위험 감수, 마무리 능력을 종합한다.
사업을 해야 한다고 단정하지 않는다.

### 사업을 한다면 가장 강한 무기
### 사업을 한다면 가장 위험한 습관

## 6. 돈 — 버는 힘과 지키는 힘은 다를 수 있다
재성/십성/원국/대운 등 실제 데이터가 있을 때만 활용한다.
돈을 벌 기회에 반응하는 방식, 축적 방식, 소비/리스크 성향을 자연스럽게 풀어쓴다.
투자상품 추천은 하지 않는다.

### 돈에서 반복하지 말아야 할 패턴
구체적으로 정리한다.

## 7. 관계 — 가까워질수록 드러나는 모습
연애만 따로 떼지 말고 인간관계의 기본 패턴부터 설명한다.
신뢰 형성, 거리감, 갈등, 표현 방식, 가까운 관계에서의 모습을 연결한다.

### 연애에서는
### 친구와 동료 사이에서는
### 관계에서 가장 조심할 패턴

## 8. 당신 사주의 숨은 긴장
합·충·형·파·해, 오행 불균형, 신강/신약, 용신/기신 등 실제 데이터가 있다면
서로 충돌하는 두 성향이나 내적 긴장을 하나의 이야기로 설명한다.
예: "앞으로 나가고 싶은 힘과 안전하게 지키고 싶은 힘이 동시에 있다."
이 장은 특히 개인적인 통찰처럼 느껴지게 작성한다.

## 9. 인생의 흐름
대운/세운 데이터가 실제 제공된 경우에만 작성한다.
연도와 시기를 정확히 데이터에 근거해 설명하고 사건을 확정적으로 예언하지 않는다.
데이터가 충분하지 않다면 솔직하게 구체적 시기 해석을 생략한다.

### 지금의 흐름
### 다음 흐름에서 달라질 수 있는 것
### 주목해서 볼 시기
데이터가 있을 때만 작성.

## 10. 결국 이 사주를 어떻게 써야 하는가
앞의 내용을 다시 요약하지 말고 하나의 결론을 낸다.

### 가장 잘 활용해야 할 세 가지
각각 한두 문장.

### 가장 경계해야 할 세 가지
각각 한두 문장.

### 당신에게 필요한 방향
마지막 2~4문단은 독자가 리포트를 덮고도 기억할 만한 내용으로 쓴다.
운명을 단정하지 말고 "이 사주의 장점을 현실에서 어떻게 사용할 것인가"에 집중한다.

마지막에 작은 글씨 느낌의 문장으로:
"이 리포트는 전통 명리학 데이터를 AI가 현대적인 언어로 해석한 자기성찰·엔터테인먼트 콘텐츠입니다. 중요한 삶의 결정은 현실의 정보와 판단을 함께 고려하세요."
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
    :root {
        --ink:#efe6d8;
        --muted:#b9aa96;
        --gold:#c6a15b;
        --gold2:#8e6d37;
        --panel:#201d1a;
        --panel2:#29241f;
        --line:#4a4035;
        --deep:#12110f;
    }

    html, body, [class*="css"], .stApp {
        color: var(--ink) !important;
    }

    .stApp {
        background:
            radial-gradient(circle at 50% -10%, rgba(170,128,65,.16), transparent 28%),
            radial-gradient(circle at 90% 20%, rgba(111,78,42,.08), transparent 25%),
            linear-gradient(180deg, #171512 0%, #100f0d 100%);
    }

    .block-container {
        max-width: 790px;
        padding-top: 2.6rem;
        padding-bottom: 5rem;
    }

    /* Streamlit text: explicitly dark-theme readable */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
    .stText, label, .stRadio label, .stSelectbox label,
    [data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"] {
        color: var(--ink) !important;
    }

    h1,h2,h3,h4 {
        color:#f3eadc !important;
        letter-spacing:-.025em;
    }

    .saju-card {
        background: linear-gradient(145deg, rgba(38,34,30,.98), rgba(27,25,22,.98));
        border: 1px solid var(--line);
        border-top: 1px solid rgba(198,161,91,.55);
        border-radius: 18px;
        padding: 30px 30px 24px 30px;
        box-shadow: 0 22px 55px rgba(0,0,0,.30);
        margin-bottom: 24px;
    }

    .hero-title {
        text-align:center;
        font-size:2.25rem;
        font-weight:800;
        letter-spacing:-.045em;
        color:#f3eadc;
        margin:.35rem 0 .45rem 0;
    }

    .hero-sub {
        text-align:center;
        color:var(--muted);
        font-size:.96rem;
        line-height:1.7;
        margin-bottom:2rem;
    }

    .seal {
        width:78px;
        height:78px;
        margin:0 auto 12px auto;
        border-radius:50%;
        display:flex;
        align-items:center;
        justify-content:center;
        color:#ead8b6;
        border:1px solid var(--gold2);
        background:
            radial-gradient(circle, #342b21 0%, #201c18 68%);
        font-size:35px;
        box-shadow:
            inset 0 0 0 5px #171411,
            inset 0 0 0 6px rgba(198,161,91,.25),
            0 10px 28px rgba(0,0,0,.30);
    }

    .section-kicker {
        color:var(--gold);
        font-size:.76rem;
        letter-spacing:.18em;
        font-weight:800;
        margin-bottom:.45rem;
    }

    .result-title {
        font-size:1.75rem;
        font-weight:800;
        color:#f3eadc;
        margin-bottom:.55rem;
    }

    .keyword-wrap {
        text-align:center;
        margin:12px 0 20px 0;
    }

    .keyword {
        display:inline-block;
        padding:7px 13px;
        margin:4px;
        border-radius:999px;
        background:#31291f;
        border:1px solid #665236;
        color:#e8d4ad !important;
        font-size:.88rem;
        font-weight:700;
    }

    .locked-box {
        background:linear-gradient(135deg,#24211d,#1c1a17);
        border:1px solid #443b31;
        border-left:3px solid #8e6d37;
        border-radius:12px;
        padding:16px 17px;
        margin:10px 0;
        color:#eee4d5 !important;
        box-shadow:0 8px 22px rgba(0,0,0,.12);
    }

    .locked-box b {
        color:#f1e6d5 !important;
    }

    .price-box {
        background:
            radial-gradient(circle at top right, rgba(198,161,91,.14), transparent 35%),
            linear-gradient(135deg,#28221c 0%,#171512 100%);
        border:1px solid #725936;
        color:#f4eadb !important;
        border-radius:16px;
        padding:26px 24px;
        margin:24px 0 12px 0;
        text-align:center;
        box-shadow:0 18px 45px rgba(0,0,0,.25);
    }

    .price-box h3 {
        color:#f5ead8 !important;
        margin:0 0 8px 0;
    }

    .price-box p {
        color:#c8b8a2 !important;
        margin:0;
        line-height:1.65;
    }

    /* Inputs */
    div[data-baseweb="select"] > div,
    .stTextInput input {
        background:#24211d !important;
        color:#f2e9dc !important;
        border:1px solid #514638 !important;
        border-radius:10px !important;
    }

    .stTextInput input::placeholder {
        color:#8f8375 !important;
    }

    div[data-baseweb="select"] span {
        color:#f2e9dc !important;
    }

    /* Dropdown menu */
    div[role="listbox"], ul[role="listbox"] {
        background:#24211d !important;
    }
    div[role="option"] {
        color:#f2e9dc !important;
        background:#24211d !important;
    }

    /* Primary action */
    .stButton > button[kind="primary"] {
        background:linear-gradient(135deg,#9b763f,#6f512d) !important;
        color:#fff8ec !important;
        border:1px solid #b68e50 !important;
        box-shadow:0 9px 25px rgba(0,0,0,.25);
    }

    .stButton > button {
        border-radius:10px !important;
        min-height:49px;
        font-weight:750;
    }

    .stButton > button:not([kind="primary"]) {
        background:#24211d;
        color:#eadfce;
        border:1px solid #4d4236;
    }

    .stAlert {
        background:#29241f !important;
        color:#eee4d5 !important;
        border-color:#574a3a !important;
    }

    hr {
        border-color:#39332c !important;
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
    st.markdown('<div class="hero-sub">전통 명리의 구조를 바탕으로, 당신의 기질과 흐름을 깊이 있게 풀어드립니다.</div>', unsafe_allow_html=True)

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
    time_unknown = st.checkbox("태어난 시각을 모릅니다", value=False)

    time_options = [
        f"{h:02d}:{m:02d}"
        for h in range(24)
        for m in range(0, 60, 10)
    ]

    birth_time = st.selectbox(
        "시간",
        time_options,
        index=72,
        disabled=time_unknown
    )

    if time_unknown:
        st.caption("출생시각이 없으면 시주를 제외한 정보로 풀이합니다.")

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
                data = calculate_saju(year, month, day, "모름" if time_unknown else birth_time, gender)

            with st.spinner("핵심 풀이를 정리하고 있어요..."):
                preview = generate_preview(name, gender, data, time_unknown)

            st.session_state["saju_data"] = data
            st.session_state["saju_name"] = name
            st.session_state["saju_gender"] = gender
            st.session_state["time_unknown"] = time_unknown
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
    time_unknown = st.session_state.get("time_unknown", False)

    top1, top2 = st.columns([1, 4])
    with top1:
        if st.button("← 다시 입력"):
            go_input()
            st.rerun()
    with top2:
        st.markdown(f'<div class="section-kicker">SAJU READING</div><div class="result-title">{name}님의 사주 풀이</div>', unsafe_allow_html=True)

    st.markdown('<div class="saju-card">', unsafe_allow_html=True)

    if time_unknown:
        st.info("출생시각 미상으로 시주 기반 해석은 제외하고 풀이합니다.")

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
        "나라는 사람": "결정 방식 · 강점 · 스스로 발목 잡는 패턴 · 스트레스가 쌓일 때의 모습",
        "직업과 일": "힘이 살아나는 환경 · 오래 버티기 힘든 일 · 직업 선택의 핵심",
        "사업 성향": "판을 만드는 성향 · 사업에서 강한 무기 · 가장 위험한 습관",
        "재물운": "버는 힘 · 지키는 힘 · 돈에서 반복하지 말아야 할 패턴",
        "연애와 인간관계": "가까워질수록 드러나는 모습 · 연애 · 친구/동료 · 갈등 패턴",
        "사주의 숨은 긴장": "서로 충돌하는 성향 · 오행의 균형 · 내면에서 반복되는 긴장",
        "인생의 흐름": "대운 · 현재 흐름 · 다음 대운 · 세운 · 주목할 시기",
        "마지막 종합 풀이": "가장 활용해야 할 것 · 가장 경계해야 할 것 · 이 사주를 현실에서 쓰는 법",
    }

    for title, desc in sections.items():
        st.markdown(
            f'<div class="locked-box">🔒 <b>{title}</b><br><span style="color:#b9aa96;font-size:.9rem">{desc}</span></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="price-box">
            <h3>AI 정밀 사주 전체 풀이 · 4,900원</h3>
            <p>데이터를 나열하지 않습니다. 당신이 어떻게 움직이고, 어디서 강해지며, 무엇이 발목을 잡는지 하나의 이야기처럼 풀어드립니다.</p>
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
                        st.session_state.get("time_unknown", False),
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
