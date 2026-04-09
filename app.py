import streamlit as st
import pandas as pd
import random

st.title("シフト自動作成アプリ（最終版・色分けチェック）")

# ---------------------------
# スタッフ人数
# ---------------------------
num_staff = st.number_input("スタッフ人数", 1, 10, 6)
staff_names = [f"スタッフ{i+1}" for i in range(num_staff)]
hours = list(range(24))

# ---------------------------
# 勤務時間上限
# ---------------------------
max_hours = st.number_input("1人あたりの最大勤務時間", 1, 24, 8)

# ---------------------------
# 必要人数
# ---------------------------
st.subheader("必要人数")
required = {}
for h in hours:
    required[h] = st.number_input(f"{h}時 必要人数", 0, num_staff, 3, key=f"req_{h}")

# ---------------------------
# 勤務希望・休憩希望（タブ・色分け）
# ---------------------------
work_df = pd.DataFrame(0, index=staff_names, columns=hours)
break_df = pd.DataFrame(0, index=staff_names, columns=hours)

st.subheader("勤務希望／休憩希望")

tabs = st.tabs(staff_names)
for idx, staff in enumerate(staff_names):
    with tabs[idx]:
        st.markdown("### 勤務希望（オレンジ） / 休憩希望（水色）")
        cols = st.columns(24)
        for h in hours:
            col = cols[h]
            with col:
                # 勤務希望
                if st.checkbox(f"{h}勤務", key=f"w_{staff}_{h}"):
                    work_df.loc[staff, h] = 1
                # 休憩希望
                if st.checkbox(f"{h}休憩", key=f"b_{staff}_{h}"):
                    break_df.loc[staff, h] = 1

# ---------------------------
# 実行
# ---------------------------
if st.button("実行"):

    schedule = work_df.copy()

    # ---------------------------
    # ① 休憩反映
    # ---------------------------
    for s in staff_names:
        for h in hours:
            if break_df.loc[s, h] == 1:
                schedule.loc[s, h] = 0

    # ---------------------------
    # ② 必要人数を満たす人員調整 + 単発除去 + ご飯休憩
    # ---------------------------
    target_ranges = [
        [11, 12, 13],  # 昼休憩
        [17, 18, 19, 20]  # 夕休憩
    ]

    # 初期人数調整
    for h in hours:
        current = schedule[h].sum()
        need = required[h]

        # 人が足りない場合
        if current < need:
            candidates = [
                s for s in staff_names
                if schedule.loc[s, h] == 0 and break_df.loc[s, h] == 0
                and schedule.loc[s].sum() < max_hours
            ]
            random.shuffle(candidates)
            for s in candidates:
                if current >= need:
                    break
                schedule.loc[s, h] = 1
                current += 1

        # 人が多い場合
        elif current > need:
            candidates = [s for s in staff_names if schedule.loc[s, h] == 1]
            random.shuffle(candidates)
            for s in candidates:
                if current <= need:
                    break
                schedule.loc[s, h] = 0
                current -= 1

    # ご飯休憩必ず確保
    for s in staff_names:
        for tr in target_ranges:
            # 全部勤務になっていたらランダムに1つ休憩
            if all(schedule.loc[s, h] == 1 for h in tr):
                h = random.choice(tr)
                schedule.loc[s, h] = 0

    # 単発勤務削除と連続勤務調整
    for s in staff_names:
        h = 0
        while h < 24:
            if schedule.loc[s, h] == 1:
                start = h
                while h < 24 and schedule.loc[s, h] == 1:
                    h += 1
                if h - start == 1:  # 単発
                    # 前後でつなぐか、勤務時間が少ない人に移動
                    moved = False
                    for target in staff_names:
                        if target != s and schedule.loc[target, start] == 0 and schedule.loc[target].sum() < max_hours:
                            schedule.loc[target, start] = 1
                            schedule.loc[s, start] = 0
                            moved = True
                            break
                    if not moved:
                        schedule.loc[s, start] = 1  # どうしても移動できなければ残す
            else:
                h += 1

    # ---------------------------
    # ③ 最終調整：必要人数確保＆勤務時間均等化
    # ---------------------------
    for h in hours:
        while schedule[h].sum() < required[h]:
            # 勤務可能な人を選ぶ
            candidates = [s for s in staff_names if schedule.loc[s, h] == 0 and break_df.loc[s, h] == 0 and schedule.loc[s].sum() < max_hours]
            if not candidates:
                break
            # 勤務時間が少ない人優先
            s = min(candidates, key=lambda x: schedule.loc[x].sum())
            schedule.loc[s, h] = 1

    # ---------------------------
    # ④ シフト表出力（ビジュアル）
    # ---------------------------
    st.subheader("シフト表（ビジュアル）")
    display_df = schedule.copy()
    display_df.columns = [f"{h:02d}" for h in hours]
    display_df.index.name = "スタッフ"

    # 色付け
    def color_map(val):
        if val == 1:
            return "background-color: #F6A068"  # 勤務
        else:
            return "background-color: #FFEEDB"  # 休憩

    styled = display_df.style.map(color_map).format(lambda x: "")
    styled = styled.set_properties(**{"border": "2px solid #999", "text-align": "center"})

    st.dataframe(styled, use_container_width=True)

    # ---------------------------
    # ⑤ 勤務時間チェック
    # ---------------------------
    st.subheader("勤務時間")
    st.dataframe(schedule.sum(axis=1).rename("勤務時間"))

    # ---------------------------
    # ⑥ 必要人数チェック
    # ---------------------------
    st.subheader("必要人数チェック")
    error_flag = False
    for h in hours:
        assigned = schedule[h].sum()
        need = required[h]
        if assigned < need:
            st.error(f"{h}時：人数不足（{assigned}/{need}）")
            error_flag = True
        elif assigned > need:
            st.warning(f"{h}時：人数超過（{assigned}/{need}）")
    if not error_flag:
        st.success("すべての時間で必要人数を満たしています")
