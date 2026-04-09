import streamlit as st
import pandas as pd
import random

st.title("シフト自動作成アプリ（最終版・単発修正版）")

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
    required[h] = st.number_input(f"{h}時", 0, num_staff, 3, key=f"req_{h}")

# ---------------------------
# タブで勤務希望・休憩希望
# ---------------------------
tabs = st.tabs(staff_names)
work_df = pd.DataFrame(0, index=staff_names, columns=hours)
break_df = pd.DataFrame(0, index=staff_names, columns=hours)

for i, staff in enumerate(staff_names):
    with tabs[i]:
        cols = st.columns([1]*12 + [0.2] + [1]*12)  # 24時間＋休憩スペース
        st.write(f"--- {staff} ---")
        for h in hours:
            col = cols[h] if h < 12 else cols[h+1]  # 12時間目以降は列ずらす
            with col:
                work_df.loc[staff, h] = 1 if st.checkbox(f"{h}時勤務", key=f"w_{staff}_{h}") else 0
                break_df.loc[staff, h] = 1 if st.checkbox(f"{h}時休憩", key=f"b_{staff}_{h}") else 0

# ---------------------------
# 実行
# ---------------------------
if st.button("実行"):

    schedule = work_df.copy()

    # ① 休憩反映
    for s in staff_names:
        for h in hours:
            if break_df.loc[s, h] == 1:
                schedule.loc[s, h] = 0

    # ---------------------------
    # 人数調整関数
    # ---------------------------
    def adjust_staff(schedule, required, max_hours):
        for h in hours:
            current = schedule[h].sum()
            need = required[h]
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
            elif current > need:
                candidates = [s for s in staff_names if schedule.loc[s, h] == 1]
                random.shuffle(candidates)
                for s in candidates:
                    if current <= need:
                        break
                    schedule.loc[s, h] = 0
                    current -= 1
        return schedule

    # ② 人数調整（2回）
    schedule = adjust_staff(schedule, required, max_hours)
    schedule = adjust_staff(schedule, required, max_hours)

    # ③ 単発勤務を連続に変換
    def remove_single(schedule):
        for s in staff_names:
            h = 0
            while h < 24:
                if schedule.loc[s, h] == 1:
                    start = h
                    while h < 24 and schedule.loc[s, h] == 1:
                        h += 1
                    if h - start == 1:
                        # 単発を前後にくっつける
                        if start > 0 and schedule.loc[s, start-1] == 1:
                            schedule.loc[s, start] = 1
                        elif start < 23 and schedule.loc[s, start+1] == 1:
                            schedule.loc[s, start] = 1
                        else:
                            # 空き時間に2時間セットで補填
                            if start < 23 and schedule.loc[s, start+1] == 0:
                                schedule.loc[s, start] = 1
                                schedule.loc[s, start+1] = 1
                            elif start > 0 and schedule.loc[s, start-1] == 0:
                                schedule.loc[s, start-1] = 1
                                schedule.loc[s, start] = 1
                            else:
                                schedule.loc[s, start] = 1
                else:
                    h += 1
        return schedule

    schedule = remove_single(schedule)

    # ④ 指定時間帯に必ず休憩
    target_ranges = [[11,12,13],[17,18,19,20]]
    for s in staff_names:
        for tr in target_ranges:
            if all(schedule.loc[s, h]==1 for h in tr):
                h = random.choice(tr)
                schedule.loc[s, h] = 0

    # ⑤ 最終人数調整
    schedule = adjust_staff(schedule, required, max_hours)

    # ---------------------------
    # チェック
    # ---------------------------
    st.subheader("チェック結果")
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

    # ---------------------------
    # 勤務時間
    # ---------------------------
    st.subheader("勤務時間")
    st.dataframe(schedule.sum(axis=1).rename("勤務時間"))

    # ---------------------------
    # シフト表（ビジュアル）
    # ---------------------------
    st.subheader("シフト表（ビジュアル）")
    display_df = schedule.copy()
    display_df.columns = [f"{h:02d}" for h in hours]
    display_df.index.name = "スタッフ"

    # 色付け
    def color_map(val):
        if val==1:
            return "background-color: #F6A068"  # 勤務
        else:
            return "background-color: #FFEEDB"  # 休憩

    styled = display_df.style.map(color_map)
    styled = styled.format(lambda x: "")
    styled = styled.set_properties(**{"border":"2px solid #999","text-align":"center"})
    st.dataframe(styled, use_container_width=True)
