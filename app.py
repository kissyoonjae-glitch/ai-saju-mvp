
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

# PG 심사/전자상거래 표시용 사업자 정보
BUSINESS_NAME = get_secret("BUSINESS_NAME", "원엔랩(1NLAB)")
REPRESENTATIVE_NAME = get_secret("REPRESENTATIVE_NAME", "미설정")
BUSINESS_NUMBER = get_secret("BUSINESS_NUMBER", "미설정")
BUSINESS_ADDRESS = get_secret("BUSINESS_ADDRESS", "미설정")
CUSTOMER_SERVICE_PHONE = get_secret("CUSTOMER_SERVICE_PHONE", "미설정")
CUSTOMER_SERVICE_EMAIL = get_secret("CUSTOMER_SERVICE_EMAIL", "미설정")
ECOMMERCE_NUMBER = get_secret("ECOMMERCE_NUMBER", "통신판매업 신고 면제 또는 신고 전")

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
    # 출생시각을 모르면 birthHour / birthMinute 필드를 아예 보내지 않습니다.
    # 일부 API는 null 값을 허용하지 않아 오류가 날 수 있습니다.

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
너는 전통 명리 데이터를 현대적인 '개인 설계도'로 번역하는 프리미엄 명리 에디터다.

이름: {name}
성별: {gender}
출생시각 미상 여부: {time_unknown}

사주 원자료:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

[서비스 콘셉트]
운세를 맞히는 서비스가 아니라 '나를 사용하는 방법을 알려주는 사주'다.
무료 결과는 아래 흐름으로 구성한다.
1) 나의 사주 지문
2) 반복되기 쉬운 인생/행동 패턴
3) 숨겨진 재능 1개
4) 성공 스타일 맛보기
5) 유료 리포트에서 무엇을 더 알 수 있는지

[절대 원칙]
- 제공된 사주 데이터에 없는 내용은 만들지 않는다.
- 출생시각 미상이면 시주 기반 해석을 하지 않는다.
- API/JSON 내부 필드명은 노출하지 않는다.
- '사주의 모순', '내적 모순', '충돌하는 두 성향' 같은 코너는 만들지 않는다.
- 누구에게나 맞을 일반론, 빈 칭찬, 공포 마케팅을 피한다.
- 성공·부·결혼·사건을 확정적으로 예언하지 않는다.
- 전문용어는 최소화하고 쉬운 현대어로 번역한다.
- 유명인의 실제 사주와 같다고 주장하지 않는다.
- 수치 점수는 실제 통계처럼 위장하지 않는다. 아래 fingerprint_scores는 '해석용 지표'이며 사주 원자료의 상대적 특징을 근거로 0~100 사이 정수로 산정한다.
- 근거가 약한 항목은 중간값에 가깝게 두고 과장하지 않는다.
- 희귀도, 상위 몇 %, 유사도 %는 실제 비교 DB가 없으므로 절대 만들지 않는다.

[사주 지문 점수]
아래 5개 축을 원자료에 근거해 산정한다.
- 추진력: 행동 시작·밀어붙임과 관련된 명리 신호
- 독립성: 자기주도·자기결정 성향
- 현실감각: 실리·관리·구체화 성향
- 변화성: 변화·확장·새 환경에 반응하는 성향
- 관계지향: 사람·협업·관계에 에너지를 쓰는 정도
각 점수마다 독자에게는 긴 근거를 쓰지 말고 짧은 설명만 준다.

[출력]
반드시 아래 JSON 형식만 출력한다.

{{
  "fingerprint_type": "개척형 × 전략형 × 확장형처럼 2~3개의 현대적 유형 조합",
  "fingerprint_line": "이 사람의 작동방식을 압축한 기억에 남는 한 문장",
  "fingerprint_scores": {{
    "추진력": 0,
    "독립성": 0,
    "현실감각": 0,
    "변화성": 0,
    "관계지향": 0
  }},
  "fingerprint_note": "점수 전체를 연결해 2~3문장으로 설명",
  "repeat_patterns": [
    {{
      "title": "반복 패턴 1의 짧은 제목",
      "body": "현실에서 어떻게 나타날 수 있는지 구체적으로"
    }},
    {{
      "title": "반복 패턴 2의 짧은 제목",
      "body": "현실에서 어떻게 나타날 수 있는지 구체적으로"
    }}
  ],
  "hidden_talent": {{
    "title": "과소평가하기 쉬운 재능 하나",
    "body": "왜 이것이 재능으로 읽히고 현실에서 어떻게 나타나는지 2~3문장"
  }},
  "success_style": {{
    "name": "개척자형/축적가형/조율가형/장인형/전략가형 등",
    "body": "이 사람이 성과를 만들기 쉬운 방식에 대한 2~3문장"
  }},
  "locked_hooks": [
    "숨겨진 재능 4가지",
    "돈이 움직이는 방식",
    "직업·사업 적성",
    "관계에서 힘이 살아나는 방식",
    "인생 흐름과 주목할 시기",
    "나 사용설명서",
    "내 성공 공식",
    "내 사주에게 질문하기"
  ],
  "closing_hook": "무료 분석에서 확인한 작동방식을 유료 리포트에서 어떻게 현실 전략으로 연결하는지 한 문장"
}}
"""
    response = client.responses.create(model="gpt-5-mini", input=prompt)
    return json.loads(clean_json_text(response.output_text))

def stream_premium_report(name, gender, saju_data, time_unknown=False):
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
너는 사주를 운세 문장으로 나열하는 AI가 아니라, 전통 명리 데이터를 현대적인 '개인 사용설명서'로 번역하는 프리미엄 명리 에디터다.

이름: {name}
성별: {gender}
출생시각 미상 여부: {time_unknown}

사주 원자료:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

[핵심 콘셉트]
"운세를 알려주는 사주가 아니라, 나를 사용하는 방법을 알려주는 사주."

[절대 원칙]
- 제공된 데이터에 없는 명리 정보나 시기를 만들지 않는다.
- 출생시각 미상이면 시주 기반 해석은 제외한다.
- API/JSON 내부 필드명은 노출하지 않는다.
- '사주의 모순', '숨은 긴장', '충돌하는 두 힘'을 별도 코너로 만들지 않는다.
- 좋은 말만 늘어놓지 말되, 약점은 현실적인 주의점/습관으로 설명한다.
- 성공·부·결혼·사건을 확정적으로 예언하지 않는다.
- 의료·법률·투자 판단을 사주로 지시하지 않는다.
- 희귀도, 상위 %, 유명인 유사도 %는 실제 비교 DB가 없으므로 만들지 않는다.
- 유명인은 실제 사주가 같다는 뜻으로 쓰지 않는다. 꼭 도움이 될 때만 '행동 스타일을 설명하기 위한 비유'로 최대 1명 사용한다.
- 같은 내용을 표현만 바꿔 반복하지 않는다.
- 독자가 '나에 관한 짧은 책 + 현실 사용설명서'를 읽는 느낌이 들게 쓴다.

[문체]
한국어 에세이와 프리미엄 리포트의 중간. 전문용어는 필요한 만큼만 쓰고 바로 풀어쓴다.
구체적인 행동·환경·선택의 언어를 사용한다.

다음 구조를 반드시 따른다.

# {name}님의 AI 정밀 사주

## 1. 나의 사주 지문
2~3개의 현대적 유형 조합으로 이름을 붙이고 핵심 작동방식을 설명한다.
추진력·독립성·현실감각·변화성·관계지향을 원자료에 근거한 '해석용 지표'로 설명하되, 통계나 과학적 성격검사처럼 과장하지 않는다.

## 2. 내가 반복하기 쉬운 인생 패턴
데이터에서 근거가 강한 패턴 3~5개를 뽑는다.
각 패턴은 '언제 나타나는지 → 현실에서 어떤 모습인지 → 어떻게 활용하거나 조절할지'까지 연결한다.

## 3. 내가 과소평가하기 쉬운 재능
숨겨진 재능을 3~5개 선정한다.
재능 이름만 나열하지 말고 왜 본인은 평범하게 여길 수 있는지, 어떤 환경에서 가치가 생기는지 설명한다.

## 4. 일 — 어디에서 힘이 살아나는가
조직/독립, 기획/실행, 안정/변화, 혼자/협업 등을 연결한다.
### 잘 맞는 일의 조건
### 오래 버티기 어려울 수 있는 환경
### 직업 선택에서 기억할 한 문장

## 5. 사업 — 사업가인가보다 '어떻게 판을 다루는가'
사업 성향이 실제 데이터에서 읽히는 범위만 해석한다.
### 사업에서 강한 무기
### 사업에서 경계할 습관
### 혼자/동업/조직 중 어떤 구조가 편한가

## 6. 돈 — 나에게 돈이 움직이는 방식
돈을 버는 방식, 지키는 방식, 기회에 반응하는 방식, 리스크 습관을 데이터 범위 안에서 설명한다.
투자상품은 추천하지 않는다.
### 돈에서 반복하지 말아야 할 패턴

## 7. 관계 — 어떤 거리에서 가장 편안한가
신뢰 형성, 표현, 갈등, 친밀감, 협업을 설명한다.
### 연애
### 친구와 동료
### 관계에서 기억할 한 가지

## 8. 나의 성공 공식
이 사주의 강점을 현실에서 성과로 연결하는 3~5개의 요소를 하나의 공식처럼 표현한다.
예: 호기심 × 자율성 × 빠른 실행 × 반복 개선.
이어 '성과를 막기 쉬운 조건'도 구체적으로 설명한다.

## 9. 나 사용설명서
이 리포트의 핵심 장이다.
### 최상의 환경
### 피해야 할 환경
### 일하는 방식
### 돈을 다루는 방식
### 사람을 대하는 방식
### 슬럼프 복구 순서
### 중요한 결정을 내릴 때
각 항목을 매우 실용적으로 작성한다.

## 10. 인생 흐름
대운/세운 등 실제 시기 데이터가 있을 때만 작성한다.
가능하면 확장기/정비기/전환기/수확기 같은 쉬운 언어로 번역한다.
구체적 사건은 예언하지 않는다.
데이터가 없으면 '구체적 시기 데이터가 없어 생략한다'고 짧게 밝힌다.

## 11. 당신과 가까운 성공 스타일
개척자형·축적가형·조율가형·장인형·전략가형 등으로 정리한다.
유명인 비유가 정말 적절할 때만 최대 1명을 행동 스타일의 예시로 사용하고, 같은 사주라는 뜻이 아님을 명시한다.

## 12. 결국, 나를 어떻게 써야 하는가
앞 내용을 단순 요약하지 말고 가장 중요한 현실 전략을 3~5개로 압축한다.
마지막 문장은 독자가 기억할 만한 문장으로 끝낸다.

## 13. 내 사주에게 물어볼 질문
이 리포트를 읽은 사람이 다음으로 궁금해할 개인화 질문 4개를 제안한다.
예: 직장과 사업 중 어떤 환경에서 강점이 더 살아나는가?
실제 채팅 기능이 연결되기 전까지는 '추천 질문'만 제시한다.

마지막에:
"이 리포트는 전통 명리학 데이터를 AI가 현대적인 언어로 해석한 자기성찰·엔터테인먼트 콘텐츠입니다. 중요한 삶의 결정은 현실의 정보와 판단을 함께 고려하세요."
"""

    stream = client.responses.create(model="gpt-5-mini", input=prompt, stream=True)
    for event in stream:
        if getattr(event, "type", None) == "response.output_text.delta":
            yield event.delta


def render_product_and_policies():
    """PG 심사에서 확인할 판매상품/약관/개인정보/환불정보."""
    st.markdown("---")
    st.markdown('<div class="section-kicker">SERVICE INFORMATION</div>', unsafe_allow_html=True)
    st.markdown("## 판매 상품 안내")

    st.markdown(
        """
        <div class="product-card">
            <div style="font-size:1.15rem;font-weight:800;color:#f2e8d9;">AI 정밀 사주 · 나의 설계도</div>
            <div class="price">4,900원 <span style="font-size:.82rem;color:#a99b8b;font-weight:500;">(부가세 포함)</span></div>
            <div style="color:#c8bbac;line-height:1.75;">
                출생정보를 바탕으로 전통 명리 데이터를 계산하고 AI가 현대적인 언어로 번역하는 개인 설계도형 디지털 리포트입니다.<br>
                주요 구성: 사주 지문·반복 패턴·숨겨진 재능·직업/사업·돈·관계·성공 공식·나 사용설명서·인생 흐름(데이터 제공 시).<br>
                <b style="color:#e4d3b7;">제공 시점:</b> 결제 확인 후 즉시 생성 시작, 통상 수분 이내 화면에서 제공됩니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### 이용 및 결제 전 안내")
    st.markdown(
        """
        <div class="legal-summary">
        본 서비스는 전통 명리학을 AI가 해석하는 자기성찰·엔터테인먼트 목적의 디지털 콘텐츠입니다.
        의료·법률·재정·투자 등 중요한 의사결정의 유일한 근거로 사용해서는 안 됩니다.
        입력정보의 정확도에 따라 결과가 달라질 수 있으며, 출생시각 미상 시 시주 기반 해석은 제외됩니다.
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("이용약관"):
        st.markdown(f"""
**제1조 목적**  
본 약관은 {BUSINESS_NAME}(이하 "회사")가 제공하는 AI 정밀 사주 및 관련 디지털 서비스의 이용조건을 정합니다.

**제2조 서비스의 성격**  
서비스는 이용자가 입력한 출생정보를 바탕으로 명리 계산 결과와 AI 해석을 제공하는 디지털 콘텐츠입니다. 결과는 오락·자기성찰 목적의 참고정보이며 특정 미래나 사건을 보장하지 않습니다.

**제3조 이용자의 의무**  
이용자는 본인의 정보 또는 적법하게 이용 권한이 있는 정보를 입력해야 하며, 타인의 개인정보를 무단으로 입력하거나 서비스 운영을 방해해서는 안 됩니다.

**제4조 결제 및 제공**  
유료 상품의 가격은 구매 화면에 표시하며, 결제 승인 후 디지털 리포트 생성이 시작됩니다. 시스템 장애 등으로 제공이 완료되지 않은 경우 회사는 재제공 또는 환불 등 합리적인 조치를 합니다.

**제5조 서비스 변경·중단**  
점검, 장애, 외부 API 장애 등 불가피한 사유가 있는 경우 서비스가 일시 중단될 수 있습니다. 유료 서비스가 정상 제공되지 않은 경우 회사는 이용자에게 재제공 또는 환불 절차를 안내합니다.

**제6조 책임 제한**  
회사는 AI 해석을 근거로 이용자가 내린 개인적 의사결정의 결과를 보증하지 않습니다. 다만 관계 법령상 회사의 책임이 인정되는 경우에는 해당 법령을 따릅니다.

**제7조 문의**  
고객문의: {CUSTOMER_SERVICE_PHONE} / {CUSTOMER_SERVICE_EMAIL}
""")

    with st.expander("개인정보처리방침"):
        st.markdown(f"""
**1. 수집 항목**  
서비스 이용 과정에서 이름, 생년월일, 출생시각(선택), 성별과 서비스 이용·결제에 필요한 최소 정보가 처리될 수 있습니다.

**2. 이용 목적**  
사주 계산, AI 해석 결과 생성, 결제 확인, 고객문의 처리, 서비스 오류 대응을 위해 사용합니다.

**3. 외부 처리 서비스 이용**  
서비스 제공을 위해 만세력 계산 API와 AI API 등 외부 기술 서비스를 사용할 수 있으며, 결과 생성에 필요한 입력정보 일부가 해당 처리 과정에서 전송될 수 있습니다.

**4. 보유 및 파기**  
법령상 보존 의무가 있는 결제·거래 정보는 해당 기간 동안 보관할 수 있습니다. 그 외 분석용 입력정보는 서비스 제공 목적 달성 후 불필요한 범위에서 보유하지 않는 것을 원칙으로 하며, 운영상 저장 기능을 추가하는 경우 보유기간을 별도로 고지합니다.

**5. 이용자의 권리**  
이용자는 관계 법령이 정한 범위에서 개인정보 열람·정정·삭제 및 처리 관련 문의를 할 수 있습니다.

**6. 개인정보 문의**  
{CUSTOMER_SERVICE_EMAIL} / {CUSTOMER_SERVICE_PHONE}

※ 실제 운영 전 외부 API의 개인정보 처리·국외이전 조건과 결제대행사 처리사항을 확인하여 본 방침을 최종 보완합니다.
""")

    with st.expander("취소·환불 정책"):
        st.markdown(f"""
**AI 정밀 사주 전체 리포트 (디지털 콘텐츠)**

- 결제 후 상세 리포트 **생성 시작 전** 취소 요청: 전액 환불을 원칙으로 합니다.
- 상세 리포트가 생성되기 시작했거나 제공이 완료된 경우: 디지털 콘텐츠의 특성 및 관계 법령에 따라 청약철회가 제한될 수 있습니다.
- 서비스 오류로 리포트가 생성되지 않거나 정상적으로 제공되지 않은 경우: 재제공 또는 환불을 요청할 수 있습니다.
- 중복 결제·오결제 확인 시: 확인 후 해당 금액을 환불합니다.
- 환불 문의: {CUSTOMER_SERVICE_PHONE} / {CUSTOMER_SERVICE_EMAIL}

실제 결제 단계에서는 디지털 콘텐츠의 즉시 제공 및 청약철회 제한 가능성에 관한 동의 절차를 별도로 표시합니다.
""")

def render_business_footer():
    st.markdown(
        f"""
        <div class="commerce-info">
        <b>{BUSINESS_NAME}</b><br>
        대표자: {REPRESENTATIVE_NAME} &nbsp;|&nbsp; 사업자등록번호: {BUSINESS_NUMBER}<br>
        사업장 소재지: {BUSINESS_ADDRESS}<br>
        고객센터: {CUSTOMER_SERVICE_PHONE} &nbsp;|&nbsp; 이메일: {CUSTOMER_SERVICE_EMAIL}<br>
        통신판매업 신고번호: {ECOMMERCE_NUMBER}<br>
        서비스: AI 정밀 사주 · 개인 설계도 디지털 리포트 &nbsp;|&nbsp; 판매가: 4,900원 (부가세 포함)
        </div>
        """,
        unsafe_allow_html=True
    )


# ---------- UI ----------


def render_product_and_policies():
    """PG 심사에서 확인할 판매상품/약관/개인정보/환불정보."""
    st.markdown("---")
    st.markdown('<div class="section-kicker">SERVICE INFORMATION</div>', unsafe_allow_html=True)
    st.markdown("## 판매 상품 안내")

    st.markdown(
        """
        <div class="product-card">
            <div style="font-size:1.15rem;font-weight:800;color:#f2e8d9;">AI 정밀 사주 · 나의 설계도</div>
            <div class="price">4,900원 <span style="font-size:.82rem;color:#a99b8b;font-weight:500;">(부가세 포함)</span></div>
            <div style="color:#c8bbac;line-height:1.75;">
                출생정보를 바탕으로 전통 명리 데이터를 계산하고 AI가 현대적인 언어로 번역하는 개인 설계도형 디지털 리포트입니다.<br>
                주요 구성: 사주 지문·반복 패턴·숨겨진 재능·직업/사업·돈·관계·성공 공식·나 사용설명서·인생 흐름(데이터 제공 시).<br>
                <b style="color:#e4d3b7;">제공 시점:</b> 결제 확인 후 즉시 생성 시작, 통상 수분 이내 화면에서 제공됩니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### 이용 및 결제 전 안내")
    st.markdown(
        """
        <div class="legal-summary">
        본 서비스는 전통 명리학을 AI가 해석하는 자기성찰·엔터테인먼트 목적의 디지털 콘텐츠입니다.
        의료·법률·재정·투자 등 중요한 의사결정의 유일한 근거로 사용해서는 안 됩니다.
        입력정보의 정확도에 따라 결과가 달라질 수 있으며, 출생시각 미상 시 시주 기반 해석은 제외됩니다.
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("이용약관"):
        st.markdown(f"""
**제1조 목적**  
본 약관은 {BUSINESS_NAME}(이하 "회사")가 제공하는 AI 정밀 사주 및 관련 디지털 서비스의 이용조건을 정합니다.

**제2조 서비스의 성격**  
서비스는 이용자가 입력한 출생정보를 바탕으로 명리 계산 결과와 AI 해석을 제공하는 디지털 콘텐츠입니다. 결과는 오락·자기성찰 목적의 참고정보이며 특정 미래나 사건을 보장하지 않습니다.

**제3조 이용자의 의무**  
이용자는 본인의 정보 또는 적법하게 이용 권한이 있는 정보를 입력해야 하며, 타인의 개인정보를 무단으로 입력하거나 서비스 운영을 방해해서는 안 됩니다.

**제4조 결제 및 제공**  
유료 상품의 가격은 구매 화면에 표시하며, 결제 승인 후 디지털 리포트 생성이 시작됩니다. 시스템 장애 등으로 제공이 완료되지 않은 경우 회사는 재제공 또는 환불 등 합리적인 조치를 합니다.

**제5조 서비스 변경·중단**  
점검, 장애, 외부 API 장애 등 불가피한 사유가 있는 경우 서비스가 일시 중단될 수 있습니다. 유료 서비스가 정상 제공되지 않은 경우 회사는 이용자에게 재제공 또는 환불 절차를 안내합니다.

**제6조 책임 제한**  
회사는 AI 해석을 근거로 이용자가 내린 개인적 의사결정의 결과를 보증하지 않습니다. 다만 관계 법령상 회사의 책임이 인정되는 경우에는 해당 법령을 따릅니다.

**제7조 문의**  
고객문의: {CUSTOMER_SERVICE_PHONE} / {CUSTOMER_SERVICE_EMAIL}
""")

    with st.expander("개인정보처리방침"):
        st.markdown(f"""
**1. 수집 항목**  
서비스 이용 과정에서 이름, 생년월일, 출생시각(선택), 성별과 서비스 이용·결제에 필요한 최소 정보가 처리될 수 있습니다.

**2. 이용 목적**  
사주 계산, AI 해석 결과 생성, 결제 확인, 고객문의 처리, 서비스 오류 대응을 위해 사용합니다.

**3. 외부 처리 서비스 이용**  
서비스 제공을 위해 만세력 계산 API와 AI API 등 외부 기술 서비스를 사용할 수 있으며, 결과 생성에 필요한 입력정보 일부가 해당 처리 과정에서 전송될 수 있습니다.

**4. 보유 및 파기**  
법령상 보존 의무가 있는 결제·거래 정보는 해당 기간 동안 보관할 수 있습니다. 그 외 분석용 입력정보는 서비스 제공 목적 달성 후 불필요한 범위에서 보유하지 않는 것을 원칙으로 하며, 운영상 저장 기능을 추가하는 경우 보유기간을 별도로 고지합니다.

**5. 이용자의 권리**  
이용자는 관계 법령이 정한 범위에서 개인정보 열람·정정·삭제 및 처리 관련 문의를 할 수 있습니다.

**6. 개인정보 문의**  
{CUSTOMER_SERVICE_EMAIL} / {CUSTOMER_SERVICE_PHONE}

※ 실제 운영 전 외부 API의 개인정보 처리·국외이전 조건과 결제대행사 처리사항을 확인하여 본 방침을 최종 보완합니다.
""")

    with st.expander("취소·환불 정책"):
        st.markdown(f"""
**AI 정밀 사주 전체 리포트 (디지털 콘텐츠)**

- 결제 후 상세 리포트 **생성 시작 전** 취소 요청: 전액 환불을 원칙으로 합니다.
- 상세 리포트가 생성되기 시작했거나 제공이 완료된 경우: 디지털 콘텐츠의 특성 및 관계 법령에 따라 청약철회가 제한될 수 있습니다.
- 서비스 오류로 리포트가 생성되지 않거나 정상적으로 제공되지 않은 경우: 재제공 또는 환불을 요청할 수 있습니다.
- 중복 결제·오결제 확인 시: 확인 후 해당 금액을 환불합니다.
- 환불 문의: {CUSTOMER_SERVICE_PHONE} / {CUSTOMER_SERVICE_EMAIL}

실제 결제 단계에서는 디지털 콘텐츠의 즉시 제공 및 청약철회 제한 가능성에 관한 동의 절차를 별도로 표시합니다.
""")

def render_business_footer():
    st.markdown(
        f"""
        <div class="commerce-info">
        <b>{BUSINESS_NAME}</b><br>
        대표자: {REPRESENTATIVE_NAME} &nbsp;|&nbsp; 사업자등록번호: {BUSINESS_NUMBER}<br>
        사업장 소재지: {BUSINESS_ADDRESS}<br>
        고객센터: {CUSTOMER_SERVICE_PHONE} &nbsp;|&nbsp; 이메일: {CUSTOMER_SERVICE_EMAIL}<br>
        통신판매업 신고번호: {ECOMMERCE_NUMBER}<br>
        서비스: AI 정밀 사주 · 개인 설계도 디지털 리포트 &nbsp;|&nbsp; 판매가: 4,900원 (부가세 포함)
        </div>
        """,
        unsafe_allow_html=True
    )


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

    .commerce-info {
        margin-top: 34px;
        padding: 18px 20px;
        border-top: 1px solid #3b342c;
        color: #9f9386 !important;
        font-size: .80rem;
        line-height: 1.75;
    }
    .commerce-info b {
        color: #c9b99f !important;
    }
    .product-card {
        background: linear-gradient(145deg,#25211d,#191714);
        border: 1px solid #514434;
        border-radius: 16px;
        padding: 22px 22px 18px 22px;
        margin: 20px 0;
        box-shadow: 0 12px 30px rgba(0,0,0,.18);
    }
    .product-card .price {
        font-size: 1.45rem;
        font-weight: 800;
        color: #e0bd78 !important;
        margin: 4px 0 10px 0;
    }
    .legal-summary {
        background:#1d1a17;
        border:1px solid #3f382f;
        border-radius:12px;
        padding:14px 16px;
        margin:10px 0;
        color:#c8bbac !important;
        line-height:1.7;
        font-size:.9rem;
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

    render_product_and_policies()
    render_business_footer()

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
        st.markdown(
            f'<div class="section-kicker">SAJU READING</div>'
            f'<div class="result-title">{name}님의 사주 풀이</div>',
            unsafe_allow_html=True
        )

    if time_unknown:
        st.info("출생시각 미상으로 시주 기반 해석은 제외하고 풀이했습니다.")

    # 1. 나의 사주 지문
    st.markdown('<div class="saju-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">SAJU FINGERPRINT</div>', unsafe_allow_html=True)
    st.markdown("## 나의 사주 지문")
    st.markdown(f"### {preview.get('fingerprint_type', '나만의 작동 방식')}")
    st.write(preview.get("fingerprint_line", ""))

    scores = preview.get("fingerprint_scores", {})
    if scores:
        for label in ["추진력", "독립성", "현실감각", "변화성", "관계지향"]:
            value = scores.get(label)
            if isinstance(value, (int, float)):
                value = max(0, min(100, int(value)))
                st.markdown(f"**{label} · {value}**")
                st.progress(value)
        st.caption("※ 위 수치는 사주 원자료의 상대적 특징을 현대적으로 번역한 해석용 지표이며, 통계적 성격검사 점수가 아닙니다.")
    st.write(preview.get("fingerprint_note", ""))
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. 반복 패턴
    patterns = preview.get("repeat_patterns", [])
    if patterns:
        st.markdown('<div class="section-kicker">REPEATING PATTERNS</div>', unsafe_allow_html=True)
        st.markdown("## 내게 반복되기 쉬운 패턴")
        for i, item in enumerate(patterns[:2], 1):
            title = item.get("title", "") if isinstance(item, dict) else str(item)
            body = item.get("body", "") if isinstance(item, dict) else ""
            st.markdown(
                f'<div class="locked-box" style="border-left:3px solid #c6a15b;">'
                f'<b style="color:#e0bd78;">{i}. {title}</b><br>'
                f'<span style="color:#d4c8b9;">{body}</span></div>',
                unsafe_allow_html=True
            )

    # 3. 숨겨진 재능 맛보기
    talent = preview.get("hidden_talent", {})
    if isinstance(talent, dict) and talent.get("title"):
        st.markdown('<div class="saju-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-kicker">HIDDEN TALENT</div>', unsafe_allow_html=True)
        st.markdown("## 내가 과소평가하기 쉬운 재능")
        st.markdown(f"### {talent.get('title')}")
        st.write(talent.get("body", ""))
        st.caption("정밀 사주에서는 데이터에서 읽히는 다른 재능들과, 각각 어떤 환경에서 가치가 커지는지까지 이어집니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    # 4. 성공 스타일 맛보기
    style = preview.get("success_style", {})
    if isinstance(style, dict) and style.get("name"):
        st.markdown('<div class="saju-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-kicker">SUCCESS STYLE</div>', unsafe_allow_html=True)
        st.markdown("## 나와 가까운 성공 스타일")
        st.markdown(f"### {style.get('name')}")
        st.write(style.get("body", ""))
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. 잠금 영역
    st.markdown('<div class="section-kicker">YOUR BLUEPRINT</div>', unsafe_allow_html=True)
    st.markdown("## 여기서부터는 '운세'가 아니라 사용설명서입니다")
    locked = preview.get("locked_hooks", [])
    for title in locked[:8]:
        st.markdown(
            f'<div class="locked-box">🔒 <b>{title}</b></div>',
            unsafe_allow_html=True
        )

    if preview.get("closing_hook"):
        st.info(preview["closing_hook"])

    # 6. 구매 가치
    st.markdown('<div class="saju-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker">FULL BLUEPRINT</div>', unsafe_allow_html=True)
    st.markdown("## 나를 사용하는 방법까지 알고 싶다면")
    st.write(
        "정밀 사주는 좋은 운·나쁜 운을 길게 나열하지 않습니다. "
        "**내가 어떤 방식으로 움직이는지 → 어떤 재능을 놓치기 쉬운지 → "
        "어디에서 일의 힘이 살아나는지 → 돈과 관계를 어떤 방식으로 다루는지 → "
        "결국 나를 어떻게 써야 하는지**를 하나의 개인 설계도로 연결합니다."
    )
    st.markdown(
        """
**정밀 사주 전체 구성**
- 전체 사주 지문과 해석
- 반복되는 인생 패턴
- 숨겨진 재능 3~5가지
- 직업·사업에서 힘이 살아나는 조건
- 나에게 돈이 움직이는 방식
- 관계에서 편안한 거리와 주의점
- **나의 성공 공식**
- **나 사용설명서**
- 대운·세운 데이터가 있을 경우 인생 흐름
- 나와 가까운 성공 스타일
- 결국 나를 어떻게 써야 하는가
- 내 사주에게 물어볼 개인화 질문
        """
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="price-box">
            <h3>나의 전체 설계도 열기 · 4,900원</h3>
            <p>운세를 알려주는 사주가 아니라, 나를 사용하는 방법을 알려주는 사주.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if PAYMENT_URL:
        st.link_button("🔓 AI 정밀 사주 전체 리포트 열기", PAYMENT_URL, use_container_width=True)
    else:
        st.button("🔓 AI 정밀 사주 전체 리포트 열기", use_container_width=True, disabled=True)
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

    render_product_and_policies()
    render_business_footer()
