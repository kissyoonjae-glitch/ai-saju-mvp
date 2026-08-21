import os
import json
import requests
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title='AI 사주', page_icon='🔮', layout='centered')
st.title('🔮 AI 사주')
st.caption('이름, 생년월일, 태어난 시각만 입력하면 바로 풀이합니다.')

def get_secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, '')

SAZU_API_KEY = get_secret('SAZU_API_KEY')
OPENAI_API_KEY = get_secret('OPENAI_API_KEY')

name = st.text_input('이름', placeholder='예: 홍길동')

c1, c2, c3 = st.columns(3)
with c1:
    year = st.number_input('출생연도', min_value=1900, max_value=2100, value=1990, step=1)
with c2:
    month = st.number_input('월', min_value=1, max_value=12, value=1, step=1)
with c3:
    day = st.number_input('일', min_value=1, max_value=31, value=1, step=1)

hour = st.number_input('태어난 시각 (0~23시)', min_value=0, max_value=23, value=12, step=1)

st.info('현재 MVP는 양력 기준이며, 기본 성향 중심의 사주 풀이를 제공합니다.')

def calculate_saju():
    payload = {
        'birthYear': int(year),
        'birthMonth': int(month),
        'birthDay': int(day),
        'birthHour': int(hour),
    }
    r = requests.post(
        'https://api.sazu.app/v1/sazu/calculate',
        headers={'x-api-key': SAZU_API_KEY, 'Content-Type': 'application/json'},
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    result = r.json()
    if not result.get('success'):
        raise RuntimeError(result.get('error', {}).get('message', '사주 계산 오류'))
    return result['data']

def generate_report(saju_data):
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
너는 전통 명리학 데이터를 바탕으로 일반인이 이해하기 쉬운 한국어 사주 풀이를 작성한다.

사용자 이름: {name or '사용자'}

아래는 외부 만세력 API가 계산한 사주 데이터다.
계산 결과를 임의로 바꾸지 말고, 이 데이터만 바탕으로 풀이하라.

사주 데이터:
{json.dumps(saju_data, ensure_ascii=False, indent=2)}

작성 방식:
- 어렵고 딱딱한 명리 용어를 남발하지 말 것
- 전문용어가 필요하면 바로 쉬운 말로 설명할 것
- 미래를 확정적으로 예언하지 말 것
- 공포를 조장하지 말 것
- 의료, 법률, 재정 결정을 사주만으로 권하지 말 것
- 자연스럽고 따뜻하지만 과장되지 않은 문체로 쓸 것

아래 순서로 작성:

# {name or '사용자'}님의 사주 풀이

## 한눈에 보는 성향
핵심 성향 3~5가지를 먼저 짧게 정리.

## 기본 기질
사주 구조에서 보이는 성향과 기질을 쉽게 설명.

## 강점
잘 살릴 수 있는 장점과 능력.

## 조심할 점
반복될 수 있는 약점이나 스트레스 패턴.

## 일과 직업
어떤 환경에서 능력을 발휘하기 쉬운지 설명. 특정 직업이 운명이라고 단정하지 말 것.

## 돈을 대하는 방식
돈을 벌고 쓰고 관리하는 성향을 자기성찰 관점에서 설명.

## 인간관계와 연애
관계에서 나타날 수 있는 특징과 주의점.

## 삶의 흐름
제공된 데이터에 대운·운세 정보가 있으면 경향만 설명. 없으면 억지로 만들지 말 것.

## 마지막 한마디
사용자가 자신의 성향을 현실에서 어떻게 활용하면 좋을지 3가지 제안.

마지막에 짧게 표시:
'이 내용은 전통 명리학을 AI가 해석한 자기성찰·엔터테인먼트 콘텐츠입니다.'
"""
    response = client.responses.create(model='gpt-5-mini', input=prompt)
    return response.output_text

if st.button('✨ 내 사주 보기', type='primary', use_container_width=True):
    if not SAZU_API_KEY:
        st.error('SAZU API 키가 설정되지 않았습니다.')
        st.stop()
    if not OPENAI_API_KEY:
        st.error('OpenAI API 키가 설정되지 않았습니다.')
        st.stop()
    if not name.strip():
        st.warning('이름을 입력해주세요.')
        st.stop()
    try:
        with st.spinner('사주를 계산하고 있어요...'):
            saju_data = calculate_saju()
        with st.spinner('AI가 사주를 풀어보고 있어요...'):
            report = generate_report(saju_data)
        st.success('풀이가 완료되었습니다.')
        st.markdown(report)
    except Exception as e:
        st.error(f'오류가 발생했습니다: {e}')

st.divider()
st.caption('테스트용 MVP · 자기성찰/엔터테인먼트용')
