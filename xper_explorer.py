import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import pandas as pd
import time

KST = timezone(timedelta(hours=9))  # KST timezone

MONGO_URL = st.secrets["mongodb_read"]["uri"] # DB 설정

client = MongoClient(MONGO_URL)
db = client["blockchain_db"]
blocks = db["blocks"]
transactions = db["transactions"]
transaction_pool = db["transaction_pool"]
accounts = db["accounts"]
account_snapshots = db["account_snapshots"]

# 총 발행량 계산
supply_pipeline = [
    {"$group": {"_id": None, "total_supply": {"$sum": "$balance"}}}
]
supply_result = list(accounts.aggregate(supply_pipeline))
total_supply = supply_result[0]["total_supply"] if supply_result else 0.0

# 마지막 블록 인덱스
latest_block = blocks.find_one(sort=[("index", -1)])
last_block_index = latest_block["index"] if latest_block else 0

col1, col2 = st.columns(2)
col1.metric("📦 총 블록 수", f"{last_block_index:,}")
col2.metric("🔢 총 발행량", f"{total_supply:,.2f} XPER")

 
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

    table_html = """
        <table style="width:100%; border-collapse: collapse;" border="1">
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="text-align: center;">지갑 주소</th>
                    <th style="text-align: center;">잔고</th>
                    <th style="text-align: center;">비율</th>
                </tr>
            </thead>
            <tbody>"""

    for row in table_data:
        table_html += f"""
                <tr>
                    <td style="text-align: center;">{row['지갑 주소']}</td>
                    <td style="text-align: center;">{row['잔고']}</td>
                    <td style="text-align: center;">{row['비율']}</td>
                </tr>"""

    table_html += "</tbody></table>"        

    st.markdown(table_html, unsafe_allow_html=True)

with st.expander("⛓️ 블록체인 탐색기", expanded=True):
    latest_block = blocks.find_one(sort=[("index", -1)])    
    if latest_block is None:
        st.warning("📭 아직 블록체인이 생성되지 않았습니다.")
    else:    
        latest_index = latest_block["index"]
        
        if "search_index" not in st.session_state:
            st.session_state["search_index"] = latest_index

        search_index = st.number_input(
            "🔍 블록 번호 검색",
            min_value=1,
            max_value=latest_index,
            step=1,
            value=st.session_state["search_index"],
            key="search_index",
            format="%d"
        )

        block = blocks.find_one({"index": search_index})
        if block:
            txs = list(transactions.find({"block_index": search_index}).sort("timestamp", -1))

            # 📋 블록 정보 (HTML)
            block_html = f"""
            <h4>📋 블록 정보</h4>
            <table style="width:100%; border-collapse: collapse;" border="1">
                <thead>
                    <tr style="background-color:#f2f2f2;">
                        <th style="text-align: center;">속성</th><th style="text-align: center;">값</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>블록 번호</td><td>{block.get("index")}</td></tr>
                    <tr><td>해시</td><td>{block.get("hash", "")[:10]}...</td></tr>
                    <tr><td>이전 해시</td><td>{block.get("previous_hash", "")[:10]}...</td></tr>
                    <tr><td>생성 시간</td><td>{datetime.fromtimestamp(block.get("timestamp", time.time()), tz=KST).strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                    <tr><td>트랜잭션 수</td><td>{len(txs)}</td></tr>
                </tbody>
            </table>
            """
            st.markdown(block_html, unsafe_allow_html=True)

            # 📦 트랜잭션 목록 (HTML)
            if not txs:
                st.info("📭 이 블록에는 트랜잭션이 없습니다.")
            else:
                tx_html = """
                <h4>📦 트랜잭션 목록</h4>
                <table style="width:100%; border-collapse: collapse;" border="1">
                    <thead>
                        <tr style="background-color:#f2f2f2;">
                            <th style="text-align: center;">보낸 사람</th><th style="text-align: center;">받는 사람</th><th style="text-align: center;">금액</th><th style="text-align: center;">수수료</th><th style="text-align: center;">합계계</th>
                        </tr>
                    </thead>
                    <tbody>"""

                for tx in txs:
                    ts = tx.get("timestamp")
                    time_str = datetime.fromtimestamp(ts, tz=KST).strftime('%Y-%m-%d %H:%M:%S') if ts else "없음"
                    amount = tx.get("amount", 0.0)
                    fee = tx.get("fee", 0.0)
                    total = amount + fee
                    tx_html += f"""
                        <tr>
                            <td>{tx.get("sender", "")[:5]}...</td>
                            <td>{tx.get("recipient", "")[:5]}...</td>
                            <td style="text-align:right;">{amount:,.2f}</td>
                            <td style="text-align:right;">{fee:,.2f}</td>
                            <td style="text-align:right;">{total:,.2f}</td>
                        </tr>"""

                tx_html += "</tbody></table>"
                st.markdown(tx_html, unsafe_allow_html=True)
        else:            
            st.info("❗해당 블록은 저장 공간 절약을 위해 삭제(pruning)되었습니다.")
    
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
