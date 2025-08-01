import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import pandas as pd
import time

KST = timezone(timedelta(hours=9))  # KST timezone

MONGO_URL = st.secrets["mongodb_read"]["uri"] # DB 설정
MONGO_URL = "mongodb+srv://chain:chain@db.leubgkp.mongodb.net/?retryWrites=true&w=majority&appName=db"

client = MongoClient(MONGO_URL)
db = client["blockchain_db"]
blocks = db["blocks"]
transactions = db["transactions"]
transaction_pool = db["transaction_pool"]
accounts = db["accounts"]

with st.expander("⛓️ 블록체인 탐색기", expanded=True):
    latest_block = blocks.find_one(sort=[("index", -1)])    
    if latest_block is None:
        st.warning("📭 아직 블록체인이 생성되지 않았습니다.")
    else:    
        latest_index = latest_block["index"]
        
        if "search_index" not in st.session_state:  # 세션 상태에 기본값을 설정(최초 1회만)
            st.session_state["search_index"] = latest_index
        
        search_index = st.number_input("🔍 블록 번호 검색", min_value=1, max_value=latest_index, step=1, key="search_index", format="%d")
        block = blocks.find_one({"index": search_index})
        if block:
            # 블록 정보 표시
            txs = list(transactions.find({"block_index": search_index}).sort("timestamp", -1))
            block_info = pd.DataFrame({
                "속성": ["블록 번호", "해시", "이전 해시", "생성 시간", "트랜잭션 수"],
                "값": [
                    block.get("index"),
                    block.get("hash", "")[:10] + "...",
                    block.get("previous_hash", "")[:10] + "...",
                    datetime.fromtimestamp(block.get("timestamp", time.time()), tz=KST).strftime('%Y-%m-%d %H:%M:%S'),
                    len(txs)
                ]
            })
            st.markdown("#### 📋 블록 정보")
            st.dataframe(block_info, use_container_width=True)

            # 트랜잭션 목록
            if not txs:
                st.info("📭 이 블록에는 트랜잭션이 없습니다.")
            else:
                tx_table = []
                for tx in txs:
                    ts = tx.get("timestamp")
                    time_str = datetime.fromtimestamp(ts, tz=KST).strftime('%Y-%m-%d %H:%M:%S') if ts else "없음"

                    amount = tx.get("amount", 0.0)
                    fee = tx.get("fee", 0.0)
                    total = amount + fee

                    tx_table.append({
                        "보낸 사람": tx.get("sender", "")[:5] + "...",
                        "받는 사람": tx.get("recipient", "")[:5] + "...",
                        "금액": amount,
                        "수수료": fee,
                        "총합": total,
                        "서명": tx.get("signature", "")[:5] + "...",
                        "시간": time_str
                    })
                st.markdown("#### 📦 트랜잭션 목록")
                st.dataframe(pd.DataFrame(tx_table), use_container_width=True)
        else:
            st.info("❗ 해당 블록은 롤업되었거나 아직 생성되지 않았습니다.")
            
with st.expander("💰 발행량", expanded=True):   
    # 총 발행량 계산 및 출력
    pipeline = [
        {"$group": {"_id": None, "total_supply": {"$sum": "$balance"}}}
    ]
    result = list(accounts.aggregate(pipeline))
    total_supply = result[0]["total_supply"] if result else 0.0
    st.metric(label="🔢 총 발행량 (Total Supply)", value=f"{total_supply:,.2f} XPER")
    
    # 계정 정보 가져오기(잔고 기준 내림차순 정렬)
    account_list = list(accounts.find().sort("balance", -1))

    if not account_list:
        st.info("📭 아직 생성된 지갑이 없습니다.")
    else:
        table_data = []
        for account in account_list:
            address = account.get("address", "")[:10] + "..."
            balance = account.get("balance", 0.0)
            ratio = (balance / total_supply * 100) if total_supply > 0 else 0
            table_data.append({
                "지갑 주소": address,
                "잔고": f"{balance:,.2f}",
                "비율": f"{ratio:.2f} %"
            })

        df_accounts = pd.DataFrame(table_data)
        st.dataframe(df_accounts, use_container_width=True)

    
# with st.expander("📥 트랜잭션 풀", expanded=False):
#     txs = list(transaction_pool.find().sort("timestamp", -1))

#     if txs:
#         table_data = []
#         for tx in txs:
#             sender = tx.get("sender", "")
#             recipient = tx.get("recipient", "")
#             amount = tx.get("amount", 0.0)
#             fee = tx.get("fee", 0.0)
#             total = amount + fee
#             time_str = datetime.fromtimestamp(tx["timestamp"], tz=KST).strftime('%Y-%m-%d %H:%M:%S')
            
#             table_data.append({
#                 "보낸 사람": sender[:5] + "...",
#                 "받는 사람": recipient[:5] + "...",
#                 "금액": f"{amount:.2f}",
#                 "수수료": f"{fee:.2f}",                
#                 "시간": time_str,
#             })

#         df = pd.DataFrame(table_data)

#         def highlight_signed(val):
#             if isinstance(val, str) and val.startswith('+'):
#                 return 'color: green; font-weight: bold'
#             elif isinstance(val, str) and val.startswith('-'):
#                 return 'color: red; font-weight: bold'
#             return ''
        
#         styled_df = df.style.applymap(highlight_signed, subset=["금액", "수수료"])
#         st.dataframe(styled_df, use_container_width=True)
#     else:
#         st.info("트랜잭션 풀이 비어 있습니다.")
