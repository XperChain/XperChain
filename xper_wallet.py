import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import time
import pandas as pd
from io import BytesIO
from PIL import Image
import cv2
import numpy as np
import qrcode
from ecdsa import SigningKey, SECP256k1

from blockchain import *
import utils

KST = timezone(timedelta(hours=9))  # KST timezone

MONGO_URL = st.secrets["mongodb"]["uri"]  # DB 설정

client = MongoClient(MONGO_URL)
db = client["blockchain_db"]
transactions = db["transactions"]
transaction_pool = db["transaction_pool"]
accounts = db["accounts"]
users = db["users"]
peers = db['peers']  # p2p network will be implemented

BLOCK_INTERVAL = 6

if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None   # 처음 접속 시 로그인 모드 진입을 위한 변수

if "balance" not in st.session_state:
    st.session_state["balance"] = 0.0

# 로그인 및 회원가입
if not st.session_state["logged_in_user"]:
    with st.expander("로그인", expanded=True):
        if "auth_mode_last" not in st.session_state:
            st.session_state["auth_mode_last"] = "로그인"   # 모드 기억용 변수

        auth_mode = st.radio("", ["로그인", "회원가입"], horizontal=True, key="auth_mode")        
        if auth_mode != st.session_state["auth_mode_last"]:  # 모드가 변했으면 입력 필드 초기화
            st.session_state["auth_mode_last"] = auth_mode
            st.session_state["username"] = ""
            st.session_state["password"] = ""
        
        username = st.text_input("👤 사용자", key="username")
        password = st.text_input("🔑 비밀번호", type="password", key="password")

        if auth_mode == "회원가입":
            private_key_input = st.text_input("🔐 지갑 개인키(미입력 시 자동 생성)", key="private_key_input")

            if st.button("✅ 회원가입"):
                if username == "" or password == "":
                    st.warning("모든 필드를 입력하세요.")
                elif len(username) < 5:
                    st.warning("사용자 명칭은 최소 5자리 이상이어야 합니다.")
                elif len(password) < 8:
                    st.warning("비밀번호는 최소 8자리 이상이어야 합니다.")
                elif users.find_one({"username": username}):
                    st.error("이미 존재하는 사용자입니다.")
                else:                    
                    if private_key_input.strip(): # 개인키 입력 여부 확인
                        try:
                            sk = SigningKey.from_string(bytes.fromhex(private_key_input), curve=SECP256k1)
                            pub = sk.get_verifying_key().to_string().hex()
                            priv = private_key_input
                        except Exception as e:
                            st.error(f"❌ 개인키 형식 오류: {e}")
                            st.stop()
                    else:
                        # 개인키 및 공개키 자동 생성
                        pub, priv = generate_wallet()

                    users.insert_one({
                        "username": username,
                        "password_hash": utils.hash_password(password),
                        "public_key": pub,
                        "private_key": priv
                    })                      
                    st.success("🎉 회원가입 성공! 이제 로그인 해보세요.")                  

        elif auth_mode == "로그인":
            if st.button("🔓 로그인"):
                user = users.find_one({"username": username})
                if not user or user["password_hash"] != utils.hash_password(password):
                    st.error("❌ 사용자 또는 비밀번호가 틀렸습니다.")
                else:                                                          
                    
                    st.session_state["logged_in_user"] = user
                    st.session_state["balance"] = get_balance(user["public_key"], accounts)
                    st.success(f"환영합니다, {username}님!")                    
                    st.rerun()

if not st.session_state["logged_in_user"]:
    st.stop()
    
# 사용자 세션 정보
user = st.session_state["logged_in_user"]
public_key = user["public_key"]  # 공개키가 지갑 주소 역할을 함
private_key = user["private_key"]
    
with st.expander("📂 내 지갑 정보", expanded=True):  
    st.markdown(f"👤 사용자: `{user['username']}`")        
    st.success(f"🪪 지갑 주소 `{public_key}`")
    st.success(f"💰 잔고 `{st.session_state['balance']:,.2f} XPER`")       
    
    col1, col2, col3 = st.columns([1, 1, 1], gap="small")
    with col1:
        if st.button("🔒 로그아웃", key="logout_btn"):
            st.session_state["logged_in_user"] = None
            st.rerun()
    with col2:
        if "qr_generated" not in st.session_state:  # QR 생성 상태 관리
            st.session_state["qr_generated"] = False            
        if not st.session_state["qr_generated"]:
            if st.button("QR 보기", key="generate_qr_btn"):
                st.session_state["qr_generated"] = True
                st.rerun()
        if st.session_state["qr_generated"]:
            qr_img = qrcode.make(public_key)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            st.image(buf.getvalue(), width=300)              
    with col3:
        if st.button("🔄 새로고침", key="refresh_balance"):
            st.session_state["balance"] = get_balance(public_key, accounts)   
            st.session_state["qr_generated"] = False
            st.rerun()            

# QR 스캔 상태 초기화
if "qr_scan_requested" not in st.session_state:
    st.session_state["qr_scan_requested"] = False
    
if "recipient_scanned" not in st.session_state:
    st.session_state["recipient_scanned"] = ""
    
if "clear_inputs" not in st.session_state:   # 초기화용
    st.session_state["clear_inputs"] = False  

recipient_value = "" if st.session_state.clear_inputs else st.session_state.get("recipient_input", "")
amount_value = 0.0 if st.session_state.clear_inputs else st.session_state.get("amount_input", 0.0)

with st.expander("📤 이체", expanded=True):
    col1, col2 = st.columns([4, 1], gap="small")    
    with col1:        
        if st.session_state.get("clear_inputs", False):
            st.session_state["recipient_input"] = ""  
            st.session_state["clear_inputs"] = False 
            
        recipient = st.text_input("📨 받는 지갑 주소", value=recipient_value, key="recipient_input") 
        
    with col2:    
        st.markdown("")
        if st.button("📷 QR 스캔", key="qr_scan_btn"):
            st.session_state["qr_scan_requested"] = True

    # QR 스캔
    if st.session_state.get("qr_scan_requested", False):
        if st.button("❌ 스캔 취소", key="cancel_qr_btn"):
            st.session_state["qr_scan_requested"] = False
            st.rerun()
        image_file = st.camera_input("📸 QR 코드를 카메라로 스캔하세요")
        if image_file:
            image = Image.open(image_file).convert("RGB")
            img_np = np.array(image)
            qr_decoder = cv2.QRCodeDetector()
            data, points, _ = qr_decoder.detectAndDecode(img_np)
            if data:
                st.session_state["recipient_scanned"] = data
                st.session_state["qr_scan_requested"] = False
                st.success("✅ QR 코드 인식 성공!")
                st.rerun()
            else:
                st.error("❌ QR 코드 인식에 실패했습니다.")
                
    amount = st.number_input("💸 금액", min_value=0.0, value=amount_value, key="amount_input")      
    st.info(f"💰 수수료: `{transaction_fee:.2f} XPER`")        
    if st.button("➕ 이체하기"):
        recipient_value = st.session_state.get("recipient_input", "")
        amount_value = st.session_state.get("amount_input", 0.0)
        if recipient_value.strip() == "":
            st.warning("받는 지갑의 주소를 입력하세요.")
        elif amount_value <= 0:
            st.warning("이체 금액을 입력하세요.")
        elif amount_value + transaction_fee > st.session_state["balance"]:
            st.error("❌ 잔고 부족(수수료 포함)")
        else:            
            tx_data = {
                "sender": public_key,
                "recipient": recipient_value,
                "amount": amount_value,
                "fee": transaction_fee,
                "timestamp": time.time()
            }
            tx_data["signature"] = sign_transaction(private_key, tx_data)
            transaction_pool.insert_one(tx_data)                            
            st.success("✅ 이체 트랜잭션이 처리중입니다...")     
                        
            # 입력값 초기화용 플래그 활성화         
            time.sleep(BLOCK_INTERVAL)  # 블록 생성 시간 동안 대기
            st.session_state["clear_inputs"] = True
            st.session_state["balance"] = get_balance(public_key, accounts)            
            st.rerun()                        

with st.expander("📥 이체 내역", expanded=True):    
    txs = list(transactions.find({
        "$or": [
            {"sender": public_key},
            {"recipient": public_key}
        ]
    }).sort("timestamp", -1).limit(100))  # 최대 100개만 불러오기

    if txs:
        table_data = []
        for tx in txs:
            sender = tx.get("sender", "")
            recipient = tx.get("recipient", "")
            amount = tx.get("amount", 0.0)
            fee = tx.get("fee", 0.0)
            total = amount + fee
            time_str = datetime.fromtimestamp(tx["timestamp"], tz=KST).strftime('%Y-%m-%d %H:%M:%S')

            # 입출금 및 부호(+, -) 결정
            if sender == public_key:
                sign = "-"
                direction = "출금"
            elif recipient == public_key:
                sign = "+"
                direction = "입금"
            else:
                sign = ""
                direction = "기타"

            row = {
                "보낸 사람": sender[:5] + "...",
                "받는 사람": recipient[:5] + "...",
                "금액": f"{sign}{amount:.2f}" if sign else f"{amount:,.2f}",
                "수수료": f"{sign}{fee:.2f}" if direction == "출금" else f"{fee:.2f}",
                "시간": time_str,
                "구분": direction
            }
            table_data.append(row)  

        df = pd.DataFrame(table_data)

        def highlight_signed(val):
            if isinstance(val, str) and val.startswith('+'):
                return 'color: green; font-weight: bold'
            elif isinstance(val, str) and val.startswith('-'):
                return 'color: red; font-weight: bold'
            return ''

        styled_df = df.style.applymap(highlight_signed, subset=["금액", "수수료"])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("이체 내역이 없습니다.")
