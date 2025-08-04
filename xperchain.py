import streamlit as st

st.set_page_config(page_title="XPER Chain", page_icon="⛓️", layout="centered")

# 전체 스타일링
st.markdown("""
<style>
/* 배경 색상 그라데이션 */
body {
    background: linear-gradient(to right, #e0f7fa, #f0f8ff);
}

/* 헤더 */
h1.title {
    text-align: center;
    color: #2c3e50;
    font-size: 3.5em;
    font-weight: bold;
    margin-bottom: 0;
}
h4.subtitle {
    text-align: center;
    color: #16a085;
    font-style: italic;
    margin-top: 0.2em;
    font-size: 1.4em;
}

/* 버튼 커스터마이징 */
.stButton > button {
    background: linear-gradient(135deg, #2980b9, #6dd5fa);
    color: white;
    font-weight: bold;
    font-size: 1em;
    border-radius: 12px;
    padding: 0.6em 1.2em;
    box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
    border: none;
    transition: 0.3s ease-in-out;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1c5980, #4fb7f0);
    transform: scale(1.02);
}

/* 박스 설명 글 */
.block-description {
    font-size: 1.05em;
    color: #34495e;
    margin-bottom: 0.5em;
}

/* 푸터 */
.centered-footer {
    text-align: center;
    margin-top: 2em;
    color: #7f8c8d;
    font-style: italic;
    font-size: 0.9em;
}
</style>
""", unsafe_allow_html=True)

# 타이틀 영역
st.markdown("""
<h1 class='title'>XPER</h1>
<h4 class='subtitle'>eXPert in Education and Research</h4>
""", unsafe_allow_html=True)

st.divider()

# 메인 메뉴
col1, col2 = st.columns(2)
with col1:
    st.subheader("💼 Wallet")
    st.markdown("<p class='block-description'>지갑을 생성하고 송금 기능을 사용할 수 있습니다.</p>", unsafe_allow_html=True)
    st.link_button("🔑 Go to Wallet", "https://xper-wallet.streamlit.app", use_container_width=True)

with col2:
    st.subheader("🔍 Explorer")
    st.markdown("<p class='block-description'>블록과 트랜잭션 내역을 탐색할 수 있습니다.</p>", unsafe_allow_html=True)
    st.link_button("🔗 Go to Explorer", "https://xper-explorer.streamlit.app", use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("⛏️ Mining")
    st.markdown("<p class='block-description'>채굴에 참여하여 XPER를 획득하세요.</p>", unsafe_allow_html=True)
    st.link_button("⚙️ Go to Miner", "https://xper-mining.streamlit.app", use_container_width=True)

with col2:
    pass  # 여백

st.divider()

# 푸터
st.markdown("<p class='centered-footer'>🌐 Powered by the <strong>XPER Chain</strong> ⛓️</p>", unsafe_allow_html=True)
