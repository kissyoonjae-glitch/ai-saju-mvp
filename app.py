import os, json, requests, streamlit as st
from openai import OpenAI

st.set_page_config(page_title='AI 사주 리포트', page_icon='🔮', layout='centered')
st.title('🔮 AI 사주 리포트 MVP')
st.caption('생년월일시 → 만세력 계산 → AI 해석')

with st.sidebar:
    st.header('API 설정')
    sazu_key = st.text_input('SAZU API Key', value=os.getenv('SAZU_API_KEY',''), type='password')
    openai_key = st.text_input('OpenAI API Key', value=os.getenv('OPENAI_API_KEY',''), type='password')
    model = st.selectbox('AI 모델', ['gpt-5.6-luna','gpt-5.6-terra','gpt-5.6-sol'], index=0)

st.subheader('1. 출생 정보')
name = st.text_input('이름 또는 닉네임', placeholder='예: 홍길동')
c1,c2,c3 = st.columns(3)
with c1: year = st.number_input('출생연도',1900,2100,1990)
with c2: month = st.number_input('월',1,12,1)
with c3: day = st.number_input('일',1,31,1)
c4,c5 = st.columns(2)
with c4:
    hour_known = st.checkbox('출생시간을 알고 있음', value=True)
    hour = st.number_input('출생시간(0~23시)',0,23,12,disabled=not hour_known)
with c5:
    gender = st.radio('성별',['남성','여성'],horizontal=True)
is_lunar = st.checkbox('음력 생일', value=False)
birth_city = st.text_input('출생 도시(선택)', placeholder='예: 부산')

st.subheader('2. 가장 궁금한 것')
question = st.text_area('질문', placeholder='예: 저는 직장생활과 사업 중 어떤 방식이 더 잘 맞는 편인가요?', height=90)
report_type = st.selectbox('리포트 유형',['종합','직업/사업','재물','연애/관계','자기이해'],index=4)

focus = {
'종합':'성향, 관계, 일, 돈, 삶의 흐름을 균형 있게',
'직업/사업':'일하는 방식, 조직생활, 창업 성향, 강점과 주의점 중심',
'재물':'돈을 다루는 성향, 수입 구조, 소비/축적 성향 중심',
'연애/관계':'관계 패턴, 갈등 방식, 관계에서의 강점과 주의점 중심',
'자기이해':'미래예언보다 성향과 반복 패턴, 자기성찰 중심'}

def call_sazu():
    payload = {
        'birthYear': int(year), 'birthMonth': int(month), 'birthDay': int(day),
        'birthHour': int(hour) if hour_known else None,
        'isFemale': gender=='여성', 'isLunar': bool(is_lunar)}
    if birth_city.strip():
        payload['birthCity']=birth_city.strip(); payload['trueSolarTime']=True
    r=requests.post('https://api.sazu.app/v1/sazu/calculate',headers={'x-api-key':sazu_key,'Content-Type':'application/json'},json=payload,timeout=30)
    r.raise_for_status(); data=r.json()
    if not data.get('success'): raise RuntimeError(data.get('error',{}).get('message','SAZU API 오류'))
    return data['data']

def make_prompt(data):
    return f'''너는 명리학 데이터를 읽어 설명하는 AI 사주 리포트 작성자다.

원칙:
- 제공된 명리 데이터를 계산하거나 임의로 수정하지 않는다.
- 미래를 확정적으로 예언하지 않는다.
- 반드시/무조건/확실히 같은 단정 표현을 피한다.
- 재정, 의료, 법률, 안전에 관한 결정을 사주만으로 권하지 않는다.
- 사주 해석은 전통 명리 관점의 자기성찰·엔터테인먼트 콘텐츠임을 분명히 한다.
- 전문용어는 쉬운 말로 풀어쓴다.
- 상반된 요소가 있으면 양면성을 설명한다.

사용자: {name or '미입력'}
리포트 유형: {report_type}
초점: {focus[report_type]}
질문: {question or '특별한 질문 없음'}

만세력 데이터(JSON):
{json.dumps(data,ensure_ascii=False,indent=2)}

다음 목차로 한국어 리포트를 작성하라.
# {name or '사용자'}님의 AI 사주 리포트
## 1. 한눈에 보는 핵심
## 2. 기본 기질
## 3. 일하는 방식과 적성
## 4. 돈을 대하는 방식
## 5. 관계에서 나타나는 패턴
## 6. 흐름 읽기
## 7. 사용자의 질문에 대한 답
## 8. 현실에서 해볼 3가지

마지막에: 이 리포트는 전통 명리학을 AI가 해석한 자기성찰·엔터테인먼트 콘텐츠이며, 중요한 의사결정의 유일한 근거로 사용하지 마세요.
'''

def call_openai(data):
    client=OpenAI(api_key=openai_key)
    r=client.responses.create(model=model,input=make_prompt(data))
    return r.output_text

st.divider()
if st.button('✨ 사주 리포트 생성', type='primary', use_container_width=True):
    if not sazu_key: st.error('SAZU API Key를 입력해주세요.'); st.stop()
    if not openai_key: st.error('OpenAI API Key를 입력해주세요.'); st.stop()
    try:
        with st.spinner('만세력 데이터를 계산하는 중...'): data=call_sazu()
        with st.expander('만세력 원본 데이터 보기'): st.json(data)
        with st.spinner('AI가 해석 리포트를 작성하는 중...'): report=call_openai(data)
        st.success('리포트가 생성되었습니다.')
        st.markdown(report)
        st.download_button('📄 리포트 TXT로 저장',report.encode('utf-8'),file_name=f"{name or 'saju'}_ai_saju_report.txt",mime='text/plain',use_container_width=True)
    except requests.HTTPError as e:
        st.error(f'SAZU API 호출 실패: {e}')
        if e.response is not None: st.code(e.response.text)
    except Exception as e:
        st.error(f'오류가 발생했습니다: {e}')

st.divider()
st.caption('MVP 버전 · 결제/회원가입/DB/PDF 자동생성 기능은 아직 포함하지 않았습니다.')
