import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import secrets
import pandas as pd

# MongoDB 연결 설정
MONGO_URL = st.secrets["mongodb"]["uri"]
client = MongoClient(MONGO_URL)
db = client['blockchain_db']
peers_collection = db['peers']

st.title("Peer 관리 대시보드")

st.header("🧩 새로운 Peer 추가")

public_key = st.text_input("🔑 Public Key")
peer_uri = st.text_input("🌐 Node URI")

if st.button("➕ Add Peer"):
    if public_key and peer_uri:
        # URI 기준 중복 확인
        existing_by_uri = peers_collection.find_one({"uri": peer_uri})
        
        if existing_by_uri:
            st.warning("⚠️ 이 URI는 이미 등록된 peer입니다.")
        else:
            peer_data = {
                "public_key": public_key,
                "uri": peer_uri,
                "timestamp": datetime.utcnow()
            }
            peers_collection.insert_one(peer_data)
            st.success("✅ Peer가 성공적으로 추가되었습니다.")
    else:
        st.error("❗ Public Key와 URI를 모두 입력해주세요.")

# -----------------------------------------
st.header("📜 등록된 Peer 목록 보기")

if st.button("🔍 Show Peer List"):
    peers = list(peers_collection.find({}, {"_id": 0}))  # _id 제외

    if peers:
        df = pd.DataFrame(peers)
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(df)
    else:
        st.info("아직 등록된 peer가 없습니다.")