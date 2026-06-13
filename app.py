import streamlit as st
import googleapiclient.discovery
import re
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import urllib.request

# 1. 페이지 설정
st.set_page_config(page_title="유튜브 댓글 심층 분석기", layout="wide")
st.title("📺 유튜브 댓글 심층 분석 & 골 주인공 찾기")
st.markdown("유튜브 영상 링크를 입력하면 댓글을 수집하여 핵심 키워드, 그리고 **⚽ 골을 넣은 것으로 추정되는 선수**를 찾아냅니다!")

# 2. 사이드바 - API 키 입력 및 설정
st.sidebar.header("🔑 설정")
api_key = st.sidebar.text_input("YouTube API Key를 입력하세요", type="password")
max_results = st.sidebar.slider("수집할 댓글 수", min_value=20, max_value=300, value=150, step=20)

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
        st.error(f"댓글을 가져오는 중 오류가 발생했습니다. (API 키 뒤에 따옴표가 없는지 다시 확인해 주세요!): {e}")
        return []
        
    return comments

# 5. 한글 텍스트 및 골 주인공 분석 함수
def analyze_comments_and_goals(text_list):
    full_text = " ".join(text_list)
    
    # ⚽ 축구공 이모지 개수 세기
    soccer_ball_count = full_text.count("⚽")
    
    # 한글과 공백만 남기기
    cleaned = re.sub(r'[^가-힣\s]', '', full_text)
    words = cleaned.split()
    
    # 축구 영상 관련 제외할 기본 불용어
    stopwords = {'진짜', '너무', '보고', '영상', '이거', '완전', '조금', '인듯', '그냥', '대한', '정말', '많이', '유튜브', '경기', '하이라이트', '오늘', '축구'}
    
    # 2글자 이상 단어 필터링
    final_words = [word for word in words if len(word) >= 2 and word not in stopwords]
    word_counts = Counter(final_words)
    
    # 💡 [골 주인공 추정 로직] 
    # 댓글에서 흔히 언급되는 유명 선수 이름 예시 키워드셋 (필요에 따라 확장 가능)
    # 팁: 성을 떼고 이름만 부르는 경우(흥민, 강인)와 풀네임을 모두 고려
    player_keywords = ['손흥민', '흥민', '이강인', '강인', '황희찬', '희찬', '김민재', '민재', '호날두', '메시', '음바페', '홀란드']
    
    player_mentions = {}
    for word, count in word_counts.items():
        for player in player_keywords:
            if player in word:
                # '흥민'과 '손흥민'이 중복 집계되는 것을 방지하기 위해 대표명으로 통일
                rep_name = "손흥민" if "흥민" in player else ("이강인" if "강인" in player else ("황희찬" if "희찬" in player else ("김민재" if "민재" in player else player)))
                player_mentions[rep_name] = player_mentions.get(rep_name, 0) + count

    # 가장 많이 언급된 선수 정렬
    sorted_players = sorted(player_mentions.items(), key=lambda x: x[1], reverse=True)
    
    return final_words, word_counts, soccer_ball_count, sorted_players

# --- 메인 화면 구현 ---
video_url = st.text_input("분석할 유튜브 영상 링크(URL)를 입력하세요:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("댓글 분석 및 골 추적 시작 🚀"):
    if not api_key:
        st.warning("사이드바에 YouTube API Key를 입력해주세요.")
    elif not video_url:
        st.warning("유튜브 영상 링크를 입력해주세요.")
    else:
        video_id = get_video_id(video_url)
        if not video_id:
            st.error("올바른 유튜브 링크 형식이 아닙니다. URL을 다시 확인해주세요.")
        else:
            with st.spinner("댓글을 수집하고 골 주인공을 추적하는 중입니다..."):
                raw_comments = get_youtube_comments(video_id, api_key, max_results)
                
                if not raw_comments:
                    st.info("수집된 댓글이 없습니다.")
                else:
                    st.success(f"총 {len(raw_comments)}개의 댓글을 수집했습니다!")
                    
                    # 데이터 분석 호출
                    processed_words, word_counts, ball_count, top_players = analyze_comments_and_goals(raw_comments)
                    
                    # 🔔 [NEW] 골 추정 결과 대시보드 상단 배치
                    st.markdown("---")
                    st.subheader("⚽ 경기 주요 지표 점검")
                    
                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric(label="댓글 내 축구공(⚽) 이모지 등장 횟수", value=f"{ball_count}회")
                    with metric_col2:
                        if top_players:
                            st.metric(label="🥇 가장 많이 언급된 인물", value=f"{top_players[0][0]} ({top_players[0][1]}회 언급)")
                        else:
                            st.metric(label="🥇 가장 많이 언급된 인물", value="분석 불가 (선수 이름 없음)")
                    
                    # 골 주인공 예측 한줄평
                    if ball_count > 3 and top_players:
                        st.info(f"💡 **분석 결과:** 댓글창에 축구공 이모지가 다수 등장하고 **[{top_players[0][0]}]** 선수가 압도적으로 언급되는 것으로 보아, **{top_players[0][0]} 선수가 골을 넣었을 확률이 매우 높습니다!**")
                    elif top_players:
                        st.info(f"💡 **분석 결과:** 현재 댓글에서 가장 핫한 선수는 **[{top_players[0][0]}]** 선수입니다.")
                    
                    # 화면 분할 (좌측: 워드클라우드, 우측: 빈도수 차트)
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.subheader("☁️ 핵심 키워드 워드클라우드")
                        if word_counts:
                            font_path = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
                            try:
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
                                ax.imshow(wc, interpolation='bilinear')
                                ax.axis("off")
                                st.pyplot(fig)
                            except Exception as e:
                                st.error(f"워드클라우드 생성 중 폰트 로드 실패: {e}")
                        else:
                            st.info("분석할 만한 한글 키워드가 부족합니다.")
                            
                    with col2:
                        st.subheader("📊 언급된 선수 순위")
                        if top_players:
                            chart_df = pd.DataFrame(top_players, columns=["선수명", "언급 횟수"])
                            st.bar_chart(chart_df.set_index("선수명"))
                        else:
                            st.info("댓글에서 주요 축구 선수 이름이 발견되지 않았습니다.")
                            
                    # 원본 댓글 테이블 출력
                    st.markdown("---")
                    st.subheader("💬 수집된 댓글 원본 보기")
                    df = pd.DataFrame(raw_comments, columns=["댓글 내용"])
                    st.dataframe(df, use_container_width=True)
