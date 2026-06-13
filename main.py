import streamlit as st
import googleapiclient.discovery
import re
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="유튜브 댓글 심층 분석기", layout="wide")
st.title("📺 유튜브 댓글 심층 분석 & 워드클라우드")
st.markdown("유튜브 영상 링크를 입력하면 댓글을 수집하여 핵심 키워드(한글 지원)와 대략적인 반응을 분석합니다.")

# 2. 사이드바 - API 키 입력 및 설정
st.sidebar.header("🔑 설정")
api_key = st.sidebar.text_input("YouTube API Key를 입력하세요", type="password")
max_results = st.sidebar.slider("수집할 댓글 수", min_value=20, max_value=300, value=100, step=20)

# 3. 유튜브 영상 ID 추출 함수
def get_video_id(url):
    regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    if match:
        return match.group(4)
    return None

# 4. 유튜브 댓글 수집 함수
def get_youtube_comments(video_id, api_key, max_count):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    comments = []
    
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_count, 100),
            textFormat="plainText"
        )
        
        while request and len(comments) < max_count:
            response = request.execute()
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                comments.append(comment)
            
            # 다음 페이지가 있고, 목표 수량을 채우지 못했다면 계속 수집
            if 'nextPageToken' in response and len(comments) < max_count:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(max_count - len(comments), 100),
                    pageToken=response['nextPageToken'],
                    textFormat="plainText"
                )
            else:
                break
    except Exception as e:
        st.error(f"댓글을 가져오는 중 오류가 발생했습니다: {e}")
        return []
        
    return comments

# 5. 한글 텍스트 정제 함수 (간이 명사/키워드 추출)
def clean_korean_text(text_list):
    full_text = " ".join(text_list)
    # 한글과 공백만 남기기
    cleaned = re.sub(r'[^가-힣\s]', '', full_text)
    
    # 단순 띄어쓰기 분할 후 2글자 이상인 단어만 필터링 (조사 필터링 대용)
    words = cleaned.split()
    
    # 한글 분석을 위해 제외할 기본 불용어(Stopwords) 설정
    stopwords = {'진짜', '너무', '보고', '영상', '진짜', '이거', '완전', '조금', '인듯', '진짜', '그냥', '대한', '정말', '많이', '유튜브'}
    
    final_words = [word for word in words if len(word) >= 2 and word not in stopwords]
    return final_words

# --- 메인 화면 구현 ---
video_url = st.text_input("분석할 유튜브 영상 링크(URL)를 입력하세요:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("댓글 분석 시작 🚀"):
    if not api_key:
        st.warning("사이드바에 YouTube API Key를 입력해주세요.")
    elif not video_url:
        st.warning("유튜브 영상 링크를 입력해주세요.")
    else:
        video_id = get_video_id(video_url)
        if not video_id:
            st.error("올바른 유튜브 링크 형식이 아닙니다. URL을 다시 확인해주세요.")
        else:
            with st.spinner("유튜브에서 댓글을 열심히 수집하고 분석하는 중입니다..."):
                # 1. 댓글 수집
                raw_comments = get_youtube_comments(video_id, api_key, max_results)
                
                if not raw_comments:
                    st.info("수집된 댓글이 없거나 API Key 권한을 확인해주세요.")
                else:
                    st.success(f"총 {len(raw_comments)}개의 댓글을 성공적으로 수집했습니다!")
                    
                    # 데이터프레임 변환 및 보여주기
                    df = pd.DataFrame(raw_comments, columns=["댓글 내용"])
                    
                    # 화면 분할 (좌측: 워드클라우드, 우측: 빈도수 탑 10 및 원본 데이터)
                    col1, col2 = st.columns([1, 1])
                    
                    # 2. 텍스트 정제 및 단어 빈도 계산
                    processed_words = clean_korean_text(raw_comments)
                    word_counts = Counter(processed_words)
                    
                    with col1:
                        st.subheader("☁️ 핵심 키워드 워드클라우드")
                        if word_counts:
                            # 🌟 스트림릿 클라우드(리눅스 환경)에서 한글 깨짐을 방지하기 위해 나눔바른고딕 웹 폰트 URL 활용
                            # 시스템 기본 내장 폰트 경로를 사용하지 않고 다운로드 가능한 주소를 넣는 것이 정석입니다.
                            font_path = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
                            
                            try:
                                # 외부 폰트 URL을 사용하기 위해 폰트 직접 다운로드 방식 처리 대신 
                                # 일반적인 패키지 세팅이 어려울 때를 대비해 기본 글꼴을 다운로드 받아 활용하도록 설정
                                import urllib.request
                                font_filename = "NanumGothic.ttf"
                                urllib.request.urlretrieve(font_path, font_filename)
                                
                                wc = WordCloud(
                                    font_path=font_filename,
                                    background_color="white",
                                    width=800,
                                    height=600,
                                    max_words=100
                                ).generate_from_frequencies(word_counts)
                                
                                fig, ax = plt.subplots(figsize=(10, 8))
                                ax.imshow(wc, interpolation='interp0k' if 'interp0k' in dir() else 'bilinear')
                                ax.axis("off")
                                st.pyplot(fig)
                            except Exception as e:
                                st.error(f"워드클라우드 생성 중 폰트 로드 실패: {e}")
                        else:
                            st.info("분석할 만한 한글 키워드가 부족합니다.")
                            
                    with col2:
                        st.subheader("📊 가장 많이 언급된 단어 Top 10")
                        if word_counts:
                            most_common = word_counts.most_common(10)
                            chart_df = pd.DataFrame(most_common, columns=["단어", "빈도수"])
                            st.bar_chart(chart_df.set_index("단어"))
                        else:
                            st.info("데이터가 없습니다.")
                            
                    # 원본 댓글 테이블 출력
                    st.markdown("---")
                    st.subheader("💬 수집된 댓글 원본 보기")
                    st.dataframe(df, use_container_width=True)
