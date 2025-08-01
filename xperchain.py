import streamlit as st

st.set_page_config(page_title="XPER chain", page_icon="⛓️", layout="centered")

st.title("XPER chain - eXPert in Education and Research")

col1, col2 = st.columns(2)
with col1:
    st.subheader("💼 XPER Wallet")
    st.markdown("지갑을 생성하고 XPER을 송금하거나 잔고를 확인할 수 있습니다.")
    st.link_button("🔑 XPER Wallet 열기", "https://xper-wallet.streamlit.app", use_container_width=True)
with col2:
    st.subheader("🔍 XPER Explorer")
    st.markdown("블록체인에 기록된 블록과 트랜잭션을 탐색할 수 있습니다.")
    st.link_button("🔗 XPER Explorer 열기", "https://xper-explorer.streamlit.app", use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("⛏️ XPER Mining")
    st.markdown("트랜잭션을 처리하고 보상을 얻는 채굴 페이지입니다.")
    st.link_button("⚙️ XPER Miner 열기", "https://xper-mining.streamlit.app", use_container_width=True)
with col2:
    pass
    
st.divider()

st.markdown("*Powered by the XPER chain*")
