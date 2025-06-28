import streamlit as st
import pandas as pd

# 初始化狀態
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.team_names = []
    st.session_state.players = []
    st.session_state.teams = {}
    st.session_state.pick_index = 0
    st.session_state.draft_finished = False

st.title("🏟️ 中職選秀模擬系統")

# Step 1: 輸入隊伍數量與隊名
if st.session_state.step == 1:
    num_teams = st.number_input("請輸入要參與選秀的隊伍數量", min_value=2, max_value=10, value=2, step=1)
    team_inputs = []
    for i in range(num_teams):
        team_name = st.text_input(f"請輸入第 {i+1} 隊名稱", key=f"team_{i}")
        team_inputs.append(team_name)

    if all(name.strip() != "" for name in team_inputs):
        if st.button("確認隊伍"):
            st.session_state.team_names = team_inputs
            st.session_state.teams = {name: [] for name in team_inputs}
            st.session_state.step = 2
            st.experimental_rerun()

# Step 2: 輸入選手名單
elif st.session_state.step == 2:
    st.subheader("請輸入選手名單")
    player_name = st.text_input("選手姓名")
    player_pos = st.text_input("選手位置")
    if st.button("新增選手"):
        if player_name and player_pos:
            st.session_state.players.append({"姓名": player_name, "位置": player_pos})
            st.experimental_rerun()

    if st.session_state.players:
        st.markdown("### 已輸入選手")
        df = pd.DataFrame(st.session_state.players)
        st.table(df)

    if len(st.session_state.players) >= len(st.session_state.team_names):
        if st.button("開始選秀"):
            st.session_state.step = 3
            st.experimental_rerun()

# Step 3: 開始選秀
elif st.session_state.step == 3 and not st.session_state.draft_finished:
    available_players = [p for p in st.session_state.players if p not in sum(st.session_state.teams.values(), [])]
    team_order = st.session_state.team_names
    current_team = team_order[st.session_state.pick_index % len(team_order)]

    st.header(f"🎯 輪到：{current_team}")
    if available_players:
        player_names = [p["姓名"] for p in available_players]
        selected_name = st.selectbox("請選擇選手", ["請選擇"] + player_names, key=f"select_{st.session_state.pick_index}")

        col1, col2 = st.columns(2)
        with col1:
            if selected_name != "請選擇":
                if st.button("✅ 確認選秀"):
                    selected_player = next(p for p in available_players if p["姓名"] == selected_name)
                    st.session_state.teams[current_team].append(selected_player)
                    st.session_state.pick_index += 1
                    st.experimental_rerun()
        with col2:
            if st.button("❌ 放棄本輪選秀"):
                st.session_state.pick_index += 1
                st.experimental_rerun()
    else:
        st.success("所有選手皆已被選走！")
        st.session_state.draft_finished = True

# Step 4: 結果
if st.session_state.step == 3 and st.session_state.draft_finished:
    st.subheader("✅ 選秀結果")
    for team, players in st.session_state.teams.items():
        st.markdown(f"**{team}**：")
        if players:
            for p in players:
                st.markdown(f"- {p['姓名']}（{p['位置']}）")
        else:
            st.markdown("_本隊無選手_")
