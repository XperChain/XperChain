import pandas as pd
import math

import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import time

import hashlib, json, base64
from ecdsa import VerifyingKey, VerifyingKey, BadSignatureError, SigningKey, SECP256k1

block_time_in_min = 1   # 블록 생성 주기(분)
transaction_fee = 1     # 거래 수수료

# 블록 해시 함수
def generate_hash(contents):
    contents_string = json.dumps(contents, sort_keys=True).encode()
    return hashlib.sha256(contents_string).hexdigest()

# 서명 검증 함수
def verify_signature(tx):
    try:
        tx_copy = dict(tx)
        signature_b64 = tx_copy.pop("signature", None)
        if not signature_b64:
            return False

        tx_string = json.dumps(tx_copy, sort_keys=True).encode()
        tx_hash = hashlib.sha256(tx_string).digest()

        public_key_hex = tx["sender"]
        public_key_bytes = bytes.fromhex(public_key_hex)

        if len(public_key_bytes) != 64:
            return False  # SECP256k1 expects uncompressed 64-byte public key

        vk = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1)
        signature = base64.b64decode(signature_b64)

        return vk.verify(signature, tx_hash)

    except (BadSignatureError, ValueError, KeyError):
        return False

# 서명 생성 함수
def sign_transaction(private_key, tx_data):
    tx_copy = dict(tx_data)
    tx_string = json.dumps(tx_copy, sort_keys=True).encode()
    tx_hash = hashlib.sha256(tx_string).digest()

    sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
    signature = sk.sign(tx_hash)

    return base64.b64encode(signature).decode()

# 지갑 생성 함수
def generate_wallet():
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.get_verifying_key()

    private_key = sk.to_string().hex()      # 32바이트 개인키 → hex 문자열
    public_key = vk.to_string().hex()       # 64바이트 공개키 → hex 문자열 (압축X)

    return public_key, private_key

# 잔고 확인 함수
def get_balance(address, blocks):
    balance = 0
    for blk in blocks.find().sort("index"):
        for tx in blk["transactions"]:
            if tx["sender"] == address:
                balance = balance - tx["amount"] - tx["fee"]
            if tx["recipient"] == address:
                balance += tx["amount"]
    return balance

def get_block_reward(block_height):
    R0 = 100
    blocks_per_year = int(365 * 24 * 60 * 4 / block_time_in_min) # 반감기 4년
    halvings = block_height // blocks_per_year
    reward = R0 // (2 ** halvings)
    return max(0, reward)

# 블록 생성 시간 검증 함수
def verify_blocktime(timestamp_after, timestamp_before, block_time_in_min):   
    #st.write(f"timestamp_after {timestamp_after}, timestamp_before {timestamp_before}")
    if timestamp_after - timestamp_before >= block_time_in_min*60:
        return True
    else:
        return False
    
# 블록 생성 함수
def create_block(blocks, tx_pool, block_time_in_min, miner_address=None, display=False):
    last_block = blocks.find_one(sort=[("index", -1)])
    last_block_timestamp = last_block["timestamp"] if last_block else 0       
     
    if verify_blocktime(timestamp_after = time.time(), timestamp_before = last_block_timestamp, block_time_in_min = block_time_in_min): 
        raw_txs = list(tx_pool.find({}))                
        new_index = last_block["index"] + 1 if last_block else 1

        # 보상 합계 준비
        reward = get_block_reward(new_index)
        total_fees = 0
        valid_txs = []
        invalid_txs = []
        system_tx_count = 0        
        temp_balances = {}

        for tx in raw_txs:
            tx = dict(tx)
            tx.pop("_id", None)

            sender = tx["sender"]
            recipient = tx["recipient"]
            amount = tx["amount"]
            fee = tx.get("fee", 0)

            if sender == "SYSTEM":
                system_tx_count += 1
                invalid_txs.append(tx)                
                continue

            if not verify_signature(tx):
                if display:
                    st.warning(f"❌ 서명 검증 실패: {sender[:10]}...")
                invalid_txs.append(tx)
                continue

            temp_balances[sender] = temp_balances.get(sender, get_balance(sender, blocks))
            if temp_balances[sender] < amount + fee:
                if display:
                    st.warning(f"❌ 잔고 부족: {sender[:10]}...")
                invalid_txs.append(tx)
                continue

            # 유효한 거래
            temp_balances[sender] -= (amount + fee)
            temp_balances[recipient] = temp_balances.get(recipient, get_balance(recipient, blocks)) + amount
            total_fees += fee
            valid_txs.append(tx)

        # SYSTEM 보상이 아직 추가되지 않았는데, 보상 트랜잭션이 있으면 않됨
        if system_tx_count >=1:
            if display:
                st.warning(f"⚠️ SYSTEM 트랜잭션이 {system_tx_count}개 존재합니다. 모두 무시하고 새 보상 트랜잭션만 생성됩니다.")
            
        # 보상 트랜잭션 생성        
        timestamp = time.time()
        if (reward > 0 or total_fees > 0) and miner_address:
            coinbase_tx = {
                "sender": "SYSTEM",
                "recipient": miner_address,
                "amount": reward + total_fees,
                "timestamp": timestamp,
                "signature": "coinbase"
            }
            # 트랜잭션 해시 계산
            tx_hash = generate_hash(coinbase_tx)            
            coinbase_tx["tx_hash"] = tx_hash
            valid_txs.insert(0, coinbase_tx)

        # 블록 생성
        new_block = {
            "index": new_index,
            "timestamp": timestamp,
            "transactions": valid_txs,
            "previous_hash": last_block["hash"] if last_block else "0"
        }
        new_block["hash"] = generate_hash(new_block)
        blocks.insert_one(new_block)

        # 트랜잭션 풀 정리
        for tx in valid_txs + invalid_txs:
            tx_pool.delete_one({
                "sender": tx["sender"],
                "recipient": tx["recipient"],
                "amount": tx["amount"],
                "timestamp": tx["timestamp"],
                "signature": tx["signature"]
            })

        if display:
            st.success(f"✅ 블록 생성됨: #{new_block['index']} | 트랜잭션 수: {len(valid_txs)} | 보상: {reward} + 수수료 {total_fees}")

    else:
        if display:
            st.info("⏳ 블록 생성 조건(시간간)이 충족되지 않았습니다.")

            
def consensus_algorithm(blocks, peers, tx_pool, block_time_in_min, display=False):
    if display:
        st.subheader("🔍 [블록체인 검증 시작]")

    all_blocks = list(blocks.find().sort("index", 1))
    prev_timestamp = 0
    prev_hash = "0"
    balances = {}
    delete_from_index = None

    for blk in all_blocks:
        index = blk["index"]
        timestamp = blk["timestamp"]
        transactions = blk.get("transactions", [])
        current_hash = blk.get("hash")

        # 1. 블록 생성 주기 검증
        if index > 1 and timestamp - prev_timestamp < block_time_in_min * 60:
            delete_from_index = index
            if display:
                st.error(f"❌ 블록 #{index} 생성 주기 미만: 삭제 예정")
            break

        # 2. 블록 해시 검증
        expected_hash = generate_hash({
            "index": index,
            "timestamp": timestamp,
            "transactions": transactions,
            "previous_hash": blk["previous_hash"]
        })
        if expected_hash != current_hash:
            delete_from_index = index
            if display:
                st.error(f"❌ 블록 #{index} 해시 불일치: 삭제 예정")
            break

        # 3. 트랜잭션 검증
        system_txs = [tx for tx in transactions if tx.get("sender") == "SYSTEM"]
        normal_txs = [tx for tx in transactions if tx.get("sender") != "SYSTEM"]

        # SYSTEM 트랜잭션이 1개 초과되면 오류
        if len(system_txs) > 1:
            delete_from_index = index
            if display:
                st.error(f"❌ 블록 #{index} SYSTEM 트랜잭션이 1개를 초과함")
            break

        # 보상 검증
        if system_txs:
            reward_expected = get_block_reward(index)
            total_fees = sum(tx.get("fee", 0.0) for tx in normal_txs)
            reward_actual = system_txs[0].get("amount", 0.0)

            if reward_actual != reward_expected + total_fees:
                delete_from_index = index
                if display:
                    st.error(f"❌ 블록 #{index} SYSTEM 보상 불일치 (예상: {reward_expected + total_fees}, 실제: {reward_actual})")
                break

        # 일반 트랜잭션 처리
        for tx in normal_txs:
            sender = tx.get("sender")
            recipient = tx.get("recipient")
            amount = tx.get("amount", 0.0)
            fee = tx.get("fee", 0.0)

            if not verify_signature(tx):
                delete_from_index = index
                if display:
                    st.error(f"❌ 블록 #{index} 트랜잭션 서명 오류")
                break

            if balances.get(sender, 0) < amount + fee:
                delete_from_index = index
                if display:
                    st.error(f"❌ 블록 #{index} 잔고 부족 오류")
                break

            balances[sender] -= amount + fee
            balances[recipient] = balances.get(recipient, 0) + amount

        # SYSTEM 수령자에게 보상 추가
        if system_txs:
            recipient = system_txs[0].get("recipient")
            reward = system_txs[0].get("amount", 0.0)
            balances[recipient] = balances.get(recipient, 0) + reward

        if delete_from_index:
            break

        prev_timestamp = timestamp
        prev_hash = current_hash

    # 오류 블록 삭제
    if delete_from_index is not None:
        blocks.delete_many({"index": {"$gte": delete_from_index}})
        if display:
            st.warning(f"⚠️ 블록 #{delete_from_index}부터 이후 블록 모두 삭제됨")


            
# 합의 알고리즘
# [사용자 버튼 클릭]
#     ↓
# [노드들로부터 체인 길이 수집]
#     ↓
# [긴 노드 → 블록 정합성 확인]
#      ↓
# [필요한 블록만 가져오기]
#     ↓
# [각 블록의 트랜잭션 검증 및 추가]
#      ↓
# [분기 블록 기록 → 추후 비교 및 처리]
#      ↓
# [내 체인 시간 ≥ 1분 → 블록 생성 및 추가]

def consensus_protocol(blocks, peers, tx_pool, block_time_in_min, miner_address, display=False):
    if display:
        st.subheader("🔍 [합의 시작]")
        st.write("1️⃣ 사용자 요청에 따라 블록 생성 절차를 시작합니다.")

    # 현재 내 체인 정보
    my_last_block = blocks.find_one(sort=[("index", -1)])
    my_last_index = my_last_block["index"] if my_last_block else -1
    my_last_hash = my_last_block["hash"] if my_last_block else "0"
    my_len = blocks.count_documents({})
    
    if display:
        st.write(f"📦 현재 내 체인 길이: {my_len}, 마지막 인덱스: {my_last_index}")

    # 각 피어 체인 확인
    peer_longer = []
    peer_forked = []
    for peer in peers.find():
        try:
            peer_uri = peer["uri"]
            if display:
                st.info(f"🌐 피어 연결 시도: {peer_uri}")

            peer_client = MongoClient(peer_uri)
            peer_db = peer_client["blockchain_db"]
            peer_blocks = peer_db["blocks"]
            peer_len = peer_blocks.count_documents({})

            if peer_len > my_len:
                peer_longer.append({
                    "public_key": peer["public_key"],
                    "uri": peer_uri,
                    "timestamp": peer["timestamp"],
                    "length": peer_len
                })
        except Exception as e:
            if display:
                st.warning(f"❌ 피어 접근 실패: {e}")
                
    peer_longer = sorted(peer_longer, key=lambda x: x["length"], reverse=True)    
    for peer in peer_longer:
        try:
            peer_len = peer["length"]
            peer_uri = peer["uri"]

            # 현재 내 체인 정보
            my_last_block = blocks.find_one(sort=[("index", -1)])
            my_last_index = my_last_block["index"] if my_last_block else -1
            my_last_hash = my_last_block["hash"] if my_last_block else "0"
            my_len = blocks.count_documents({})

            # Peer 정보
            peer_client = MongoClient(peer_uri)
            peer_db = peer_client["blockchain_db"]
            peer_blocks = peer_db["blocks"]            

            if peer_len > my_len:  # 2. 더 긴 체인 존재            
                if display:
                    st.info("📏 피어 체인({peer_len})이 내 체인({my_len})보다 깁니다. 블록 일치 여부 확인 중...")
                    
                valid = True  
                same_block = peer_blocks.find_one({"index": my_last_index})     
                if my_len==0 or (same_block and same_block["hash"] == my_last_hash ):  # 3. 블록 일치 확인
                    if display:
                        st.success("✅ 마지막 블록이 일치하거나 내 블록이 초기화된 경우 입니다. 새로운 블록만 가져옵니다.")

                    new_blocks = list(peer_blocks.find({"index": {"$gt": my_last_index}}).sort("index"))  # 4   

                    for blk in new_blocks:                        
                        prev_block = peer_blocks.find_one({"index": blk["index"] - 1})
                        if prev_block or blk["index"]==1: # Genesis block
                            prev_time = 0 if blk["index"] == 1 else prev_block["timestamp"]                                                    
                            if verify_blocktime(timestamp_after = blk["timestamp"], timestamp_before = prev_time, block_time_in_min = block_time_in_min):
                                system_tx_count = 0  
                                total_fees = sum(tx.get("fee", 0) for tx in blk["transactions"] if tx["sender"] != "SYSTEM")
                                for tx in blk["transactions"]:
                                    if tx["sender"] == "SYSTEM":
                                        system_tx_count += 1                                        
                                        expected_reward = get_block_reward(blk["index"]) + total_fees
                                        if tx["amount"] != expected_reward:
                                            if display:
                                                st.warning(f"❌ SYSTEM 보상 금액 불일치 (예상: {expected_reward}, 실제: {tx['amount']})")
                                            valid = False
                                            break
                                    else:
                                        if not verify_signature(tx):
                                            if display:
                                                st.warning("❌ 서명 검증 실패")
                                            valid = False
                                            break
                                        if get_balance(tx["sender"], blocks) < tx["amount"] + tx.get("fee", 0):
                                            if display:
                                                st.warning("❌ 잔고 부족")
                                            valid = False
                                            break
                                    # 블록 해시 검증 추가 필요

                            if system_tx_count > 1:
                                if display:
                                    st.warning("🚫 SYSTEM 트랜잭션이 1개를 초과합니다.")
                                valid = False
                        else:
                            valid = False
                            if display:
                                st.info(f"⏳ 블록 #{blk['index']}은 생성 시간 기준 조건({block_time_in_min}분 경과)을 만족하지 않음")           
                else:
                    if display:
                        st.warning("⚠️ 마지막 블록이 불일치합니다. 분기 체인으로 처리합니다.")
                    
                    peer_forked.append(peer)
                    valid = False

                if valid:
                    for blk in new_blocks:
                        blocks.insert_one(blk)
                        for tx in blk["transactions"]:
                            tx_pool.delete_one({
                                "sender": tx["sender"],
                                "timestamp": tx["timestamp"]
                            })
                        if display:
                            st.success(f"📥 블록 #{blk['index']} 동기화 완료")
                    break
                            
        except Exception as e:
            if display:
                st.warning(f"❌ 피어 접근 실패: {e}")

    # 분기 체인 처리
    if peer_forked:
        if display:
            st.subheader("🌿 [분기 체인 처리]")
            
        for peer in peer_forked:
            peer_len = peer["length"]
            peer_uri = peer["uri"]

            # 현재 내 체인 정보
            my_last_block = blocks.find_one(sort=[("index", -1)])
            my_last_index = my_last_block["index"] if my_last_block else -1
            my_last_hash = my_last_block["hash"] if my_last_block else "0"
            my_len = blocks.count_documents({})

            # Peer 정보
            peer_client = MongoClient(peer_uri)
            peer_db = peer_client["blockchain_db"]
            peer_blocks = peer_db["blocks"]         
            
            valid = True
            for blk in peer_blocks:                
                prev_block = peer_blocks.find_one({"index": blk["index"] - 1})
                if prev_block or blk["index"]==1: # Genesis block
                    prev_time = 0 if blk["index"] == 1 else prev_block["timestamp"]                                                    
                    if verify_blocktime(timestamp_after = blk["timestamp"], timestamp_before = prev_time, block_time_in_min = block_time_in_min):                            
                        system_tx_count = 0  
                        total_fees = sum(tx.get("fee", 0) for tx in blk["transactions"] if tx["sender"] != "SYSTEM")
                        for tx in blk["transactions"]:
                            if tx["sender"] == "SYSTEM":
                                system_tx_count += 1                                
                                expected_reward = get_block_reward(blk["index"]) + total_fees
                                if tx["amount"] != expected_reward:
                                    if display:
                                        st.warning(f"❌ SYSTEM 보상 금액 불일치 (예상: {expected_reward}, 실제: {tx['amount']})")
                                    valid = False
                                    break
                            else:
                                if not verify_signature(tx):
                                    if display:
                                        st.warning("❌ 서명 검증 실패")
                                    valid = False
                                    break
                                if get_balance(tx["sender"], blocks) < tx["amount"] + tx.get("fee", 0):
                                    if display:
                                        st.warning("❌ 잔고 부족")
                                    valid = False
                                    break

                    if system_tx_count > 1:
                        if display:
                            st.warning("🚫 SYSTEM 트랜잭션이 1개를 초과합니다.")
                        valid = False
                else:
                    valid = False
                    if display:
                        st.info(f"⏳ 블록 #{blk['index']}은 생성 시간 기준 조건({block_time_in_min}분 경과)을 만족하지 않음")  
                        
            if valid:
                # 분기점 탐색
                divergence_index = -1
                for i in range(min(blocks.count_documents({}), peer_blocks.count_documents({}))):
                    my_blk = blocks.find_one({"index": i})
                    peer_blk = peer_blocks.find_one({"index": i})
                    if not my_blk or not peer_blk:
                        break
                    if my_blk["hash"] != peer_blk["hash"]:
                        divergence_index = i
                        break
                        
                # 내 블록 → 삭제 & peer 블록 → 덮어쓰기
                if divergence_index >= 0:
                    # 2-1. 내 체인에서 해당 지점 이후 블록 가져오기 (복원할 트랜잭션 확인용)
                    my_forked_blocks = list(blocks.find({"index": {"$gte": divergence_index}}).sort("index"))

                    # 2-2. 기존 블록 삭제
                    blocks.delete_many({"index": {"$gte": divergence_index}})

                    # 2-3. peer의 블록 삽입
                    peer_new_blocks = list(peer_blocks.find({"index": {"$gte": divergence_index}}).sort("index"))
                    for blk in peer_new_blocks:
                        blocks.insert_one(blk)
                
                # 내 블록에만 있던 트랜잭션 → tx_pool로 복원
                # peer의 모든 트랜잭션 해시 집합                
                peer_tx_hashes = set()
                for blk in peer_new_blocks:
                    for tx in blk["transactions"]:
                        peer_tx_hashes.add(generate_hash(tx))                
                
                for blk in my_forked_blocks:
                    for tx in blk["transactions"]:
                        tx_hash = generate_hash(tx)
                        if tx_hash not in peer_tx_hashes:
                            tx_pool.insert_one(tx)            
            
    # 8. 마지막 블록 1분 경과 시 블록 생성
    if display:
        st.subheader("🏗️ [블록 생성 확인]")
        
    create_block(blocks, tx_pool, block_time_in_min, miner_address = miner_address)

    if display:
        st.success("🎉 합의 프로토콜 완료")