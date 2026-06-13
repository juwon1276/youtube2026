import streamlit as st
import googleapiclient.discovery
import re
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import urllib.request
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="슈퍼 유튜브 축구 분석기", layout="wide")
st.title("⚽ 유튜브 댓글 축구 명장면 분석기")
st.markdown("댓글을 통해 **골 주인공, 하이라이트 시간대, 팬들의 여론, 베스트 댓글**까지 한눈에 파악합니다.")

# 2. 사이드바 - API 키 입력 및 설정
st.sidebar.header("🔑 설정")
api_key = st.sidebar.text_input("YouTube API Key를 입력하세요", type="password")
max_results = st.sidebar.slider("수집할 댓글 수", min_value=50, max_value=300, value=150, step=50)

# 3. 유튜브 영상 ID 추출 함수
def get_video_id(url):
    regex = r'(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    if match:
        return match.group(4)
    return None

# 4. 유튜브 댓글 및 좋아요 수 수집 함수
def get_youtube_comments_data(video_id, api_key, max_count):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    comments_data = []
    
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=min(max_count, 100),
            textFormat="plainText"
        )
        
        while request and len(comments_data) < max_count:
            response = request.execute()
            for item in response['items']:
                snippet = item['snippet']['topLevelComment']['snippet']
                text = snippet['textDisplay']
                likes = snippet['likeCount']
                comments_data.append({"text": text, "likes": likes})
            
            if 'nextPageToken' in response and len(comments_data) < max_count:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(max_count - len(comments_data), 100),
                    pageToken=response['nextPageToken'],
                    textFormat="plainText"
                )
            else:
                break
    except Exception as e:
        st.error(f"오류가 발생했습니다 (API 키 및 영상 링크를 확인하세요): {e}")
        return []
        
    return comments_data

# 5. 종합 심층 분석 함수
def analyze_soccer_comments(comments_list):
    full_text = ""
    timestamps = []
    pos_count, neg_count = 0, 0
    
    # 감정 분석용 심플 사전 (축구 커뮤니티 맞춤형)
    pos_words = ['지렸다', '나이스', '대박', '잘한다', '최고', '지존', '클래스', '골', '월클', '와', '캬', '🔥', '🐐', '👑']
    neg_words = ['아쉽다', '실수', '에바', '노답', '왜저러냐', '답답', '부상', '망했다', '패배', '정신차려', '🤬', '🤮']

    for c in comments_list:
        text = c['text']
        full_text += " " + text
        
        # ① 타임스탬프 추출 (예: 1:23, 12:34, 02:45)
        time_matches = re.findall(r'\b\d{1,2}:\d{2}\b', text)
        timestamps.extend(time_matches)
        
        # ② 감정 분석 카운팅
        for pw in pos_words:
            if pw in text: pos_count += 1
        for nw in neg_words:
            if nw in text: neg_count += 1

    # ③ 이모지 및 단어 정제
    soccer_ball_count = full_text.count("⚽")
    cleaned = re.sub(r'[^가-힣\s]', '', full_text)
    words = cleaned.split()
    
    stopwords = {'진짜', '너무', '보고', '영상', '이거', '완전', '조금', '인듯', '그냥', '대한', '정말', '많이', '유튜브', '경기', '하이라이트', '오늘', '축구', '선수'}
    final_words = [word for word in words if len(word) >= 2 and word not in stopwords]
    word_counts = Counter(final_words)
    
    # ④ 선수 언급량 분석
    player_keywords = ['손흥민', '흥민', '이강인', '강인', '황희찬', '희찬', '김민재', '민재', '호날두', '메시', '음바페', '홀란드']
    player_mentions = {}
    for word, count in word_counts.items():
        for player in player_keywords:
            if player in word:
                rep_name = "손흥민" if "흥민" in player else ("이강인" if "강인" in player else ("황희찬" if "희찬" in player else ("김민재" if "민재" in player else player)))
                player_mentions[rep_name] = player_mentions.get(rep_name, 0) + count
                
    sorted_players = sorted(player_mentions.items(), key=lambda x: x[1], reverse=True)
    
    return final_words, word_counts, soccer_ball_count, sorted_players, timestamps, pos_count, neg_count

# --- 메인 화면 실행 ---
video_url = st.text_input("분석할 유튜브 영상 링크(URL)를 입력하세요:", placeholder="https://www.youtube.com/watch?v=...")

if st.button("심층 데이터 분석 시작 🚀"):
    if not api_key:
        st.warning("사이드바에 YouTube API Key를 입력해주세요.")
    elif not video_url:
        st.warning("유튜브 영상 링크를 입력해주세요.")
    else:
        video_id = get_video_id(video_url)
        if not video_id:
            st.error("올바른 유튜브 링크 형식이 아닙니다.")
        else:
            with st.spinner("댓글 데이터를 입체적으로 분석하는 중입니다..."):
                comments_data = get_youtube_comments_data(video_id, api_key, max_results)
                
                if not comments_data:
                    st.info("수집된 댓글이 없습니다.")
                else:
                    # 데이터 분리
                    raw_texts = [c['text'] for c in comments_data]
                    processed_words, word_counts, ball_count, top_players, timestamps, pos, neg = analyze_soccer_comments(comments_data)
                    
                    # ==========================================
                    # [기능 1] 대시보드 스코어보드 & 골 주인공 예측
                    # ==========================================
                    st.markdown("---")
                    st.subheader("📊 경기 반응 요약 점수판")
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        st.metric(label="⚽ 축구공 이모지 등장", value=f"{ball_count}회")
                    with m2:
                        top_p = top_players[0][0] if top_players else "없음"
                        top_c = top_players[0][1] if top_players else 0
                        st.metric(label="🥇 최다 언급 인물", value=f"{top_p} ({top_c}회)")
                    with m3:
                        st.metric(label="⏱️ 타임스탬프 댓글 수", value=f"{len(timestamps)}개")
                        
                    if ball_count > 3 and top_players:
                        st.success(f"💡 **골 주인공 추정:** 댓글 여론을 분석한 결과, 이 경기의 주인공은 **[{top_players[0][0]}]** 선수일 가능성이 매우 높습니다!")

                    # ==========================================
                    # [기능 2] 시각화 레이아웃 (워드클라우드 & 감정/타임스탬프)
                    # ==========================================
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("☁️ 핵심 키워드 워드클라우드")
                        if word_counts:
                            font_path = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
                            try:
                                font_filename = "NanumGothic.ttf"
                                urllib.request.urlretrieve(font_path, font_filename)
                                wc = WordCloud(font_path=font_filename, background_color="white", width=800, height=500).generate_from_frequencies(word_counts)
                                fig, ax = plt.subplots(figsize=(10, 6))
                                ax.imshow(wc, interpolation='bilinear')
                                ax.axis("off")
                                st.pyplot(fig)
                            except:
                                st.error("한글 폰트를 불러오지 못했습니다.")
                        else:
                            st.info("데이터 부족")
                            
                    with col2:
                        # [기능 업데이트] 감정 여론 (Plotly 도넛 차트)
                        st.subheader("❤️ 팬들의 실시간 여론 분위기")
                        if pos == 0 and neg == 0:
                            st.info("감정을 분석할 만한 키워드가 부족합니다.")
                        else:
                            pie_df = pd.DataFrame({"반응": ["긍정 (환호/칭찬)", "부정 (아쉬움/비판)"], "비율": [pos, neg]})
                            fig_pie = px.pie(pie_df, values='비율', names='반응', hole=0.4, color_discrete_sequence=['#2ECC71', '#E74C3C'])
                            fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
                            st.plotly_chart(fig_pie, use_container_width=True)

                    # ==========================================
                    # [기능 3] 하단 분석 영역 (타임스탬프 명장면 & 베스트 댓글)
                    # ==========================================
                    st.markdown("---")
                    b1, b2 = st.columns(2)
                    
                    with b1:
                        st.subheader("⏱️ 댓글 폭발 하이라이트 시간대")
                        if timestamps:
                            time_counts = Counter(timestamps)
                            top_times = time_counts.most_common(5)
                            time_df = pd.DataFrame(top_times, columns=["영상 시간", "언급 횟수"])
                            st.bar_chart(time_df.set_index("영상 시간"))
                            st.caption("※ 댓글에서 가장 많이 소환된 영상 속 타임스탬프 순위입니다.")
                        else:
                            st.info("댓글에 타임스탬프(시간) 정보가 없습니다.")
