import streamlit as st
import html
import random
import numpy as np

# 등급별 이미지 URL 매핑
grade_image_map = {
    "Common": "https://robohash.org/common.png?set=set4",
    "Rare": "https://robohash.org/rare.png?set=set4",
    "Epic": "https://robohash.org/epic.png?set=set4",
    "Legendary": "https://robohash.org/legendary.png?set=set4"
}

# 등급 결정 함수
def get_grade_by_winrate(wins, losses):
    total = wins + losses
    if total == 0:
        return "Common"
    winrate = wins / total
    if winrate >= 0.8:
        return "Legendary"
    elif winrate >= 0.6:
        return "Epic"
    elif winrate >= 0.4:
        return "Rare"
    else:
        return "Common"

# 카드 렌더 함수
def render_custom_card(name, grade, wins, losses, rank_number, image_url):
    total = wins + losses
    winrate_text = f"{round((wins / total) * 100, 2)}% (승: {wins}, 패: {losses})" if total > 0 else f"- (승: {wins}, 패: {losses})"
    safe_name = html.escape(name)

    st.markdown(f"""
        <style>
        @keyframes glow {{
            0% {{ box-shadow: 0 0 5px gold; }}
            50% {{ box-shadow: 0 0 20px gold, 0 0 40px gold; }}
            100% {{ box-shadow: 0 0 5px gold; }}
        }}
        .card-container {{
            display: flex;
            justify-content: center;
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            border: 3px solid gold;
            border-radius: 15px;
            padding: 20px;
            width: 300px;
            background-color: #f9f9f9;
            text-align: center;
            position: relative;
            animation: glow 2s infinite;
        }}
        </style>
        <div class="card-container">
            <div class="card">
                <div class="card-name">🔎 {safe_name}</div>
                <img src='{image_url}' width='150' style='margin: 10px 0'>
                <p><b>등급:</b> {grade}</p>                
                <p><b>승률:</b> {winrate_text}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 게임 설정
st.title("💣 지뢰찾기 게임")
name = st.text_input("카드 이름", "IronBot")
GRID_SIZE = 5
NUM_MINES = 5

# CSS: 버튼 높이 고정
st.markdown("""
    <style>
    div[data-testid="column"] button {
        height: 40px !important;
        font-size: 18px !important;
        padding: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 지뢰 생성
def generate_board():
    board = np.zeros((GRID_SIZE, GRID_SIZE), dtype=int)
    mine_positions = random.sample(range(GRID_SIZE * GRID_SIZE), NUM_MINES)
    for pos in mine_positions:
        x, y = divmod(pos, GRID_SIZE)
        board[x][y] = -1
    return board

# 주변 지뢰 계산
def calculate_adjacent_mines(board):
    result = np.zeros_like(board)
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            if board[i][j] == -1:
                result[i][j] = -1
            else:
                count = 0
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        ni, nj = i + dx, j + dy
                        if 0 <= ni < GRID_SIZE and 0 <= nj < GRID_SIZE and board[ni][nj] == -1:
                            count += 1
                result[i][j] = count
    return result

# 상태 초기화
if "mines" not in st.session_state:
    st.session_state.mines = generate_board()
    st.session_state.revealed = np.full((GRID_SIZE, GRID_SIZE), False)
    st.session_state.status = "playing"
    st.session_state.numbers = calculate_adjacent_mines(st.session_state.mines)
    st.session_state.success = 0
    st.session_state.failures = 0

# 카드 렌더링
grade = get_grade_by_winrate(st.session_state.success, st.session_state.failures)
render_custom_card(name, grade, st.session_state.success, st.session_state.failures, 1, grade_image_map[grade])

# 게임 버튼 렌더링
for i in range(GRID_SIZE):
    cols = st.columns(GRID_SIZE, gap="small")
    for j in range(GRID_SIZE):
        with cols[j]:
            key = f"{i}-{j}"
            if st.session_state.revealed[i][j]:
                if st.session_state.mines[i][j] == -1:
                    st.button("💣", key=key, disabled=True, use_container_width=True)
                else:
                    st.button(str(st.session_state.numbers[i][j]), key=key, disabled=True, use_container_width=True)
            else:
                if st.button("❓", key=key, use_container_width=True) and st.session_state.status == "playing":
                    st.session_state.revealed[i][j] = True
                    if st.session_state.mines[i][j] == -1:
                        st.session_state.status = "lost"
                        st.session_state.failures += 1
                    else:
                        st.session_state.success += 1
                    st.rerun()

# 게임 상태 메시지
if st.session_state.status == "lost":
    st.error("💥 게임 오버! 다시 시작해보세요.")

# 게임 다시 시작
if st.button("🔁 게임 다시 시작"):
    st.session_state.mines = generate_board()
    st.session_state.revealed = np.full((GRID_SIZE, GRID_SIZE), False)
    st.session_state.status = "playing"
    st.session_state.numbers = calculate_adjacent_mines(st.session_state.mines)
    st.rerun()
