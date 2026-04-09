import streamlit as st
import pandas as pd
import random

st.set_page_config(layout="wide")
st.title("シフト自動作成アプリ（完全版）")

# ---------------------------
# 人数
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
st.subheader("必要人数（時間順）")
required = {}
cols_req = st.columns(24)
for idx, h in enumerate(hours):
    required[h] = cols_req[idx].number_input(f"{h:02d}時", 0, num_staff, 3, key=f"req_{h}")

# ---------------------------
# 勤務希望・休憩希望（タブ＋横並び）
# ---------------------------
work_df = pd.DataFrame(0, index=staff_names, columns=hours)
break_df = pd.DataFrame(0, index=staff_names, columns=hours)

st.subheader("勤務希望／休憩希望（タブでスタッフごと）")

staff_tabs = st.tabs(staff_names)
for idx, staff in enumerate(staff_names):
    with staff_tabs[idx]:
        st.write(f"--- {staff} ---")
        hour_cols = st.columns(24)
        for h in hours:
            with hour_cols[h]:
                work = st.checkbox(f"{h:02d}勤務", key=f"w_{staff}_{h}")
                brk = st.checkbox(f"{h:02d}休憩", key=f"b_{staff}_{h}")
                work_df.loc[staff, h] = 1 if work else 0
                break_df.loc[staff, h] = 1 if brk else 0

# ---------------------------
# シフト作成実行
# ---------------------------
if st.button("シフト作成"):

    schedule = work_df.copy()

    # ① 休憩反映
    for s in staff_names:
        for h in hours:
            if break_df.loc[s, h] == 1:
                schedule.loc[s, h] = 0

    # ②～⑥ 単発削除＆人数調整
    def adjust_schedule(schedule, required, max_hours):
        # 単発削除
        def remove_single(schedule):
            for s in staff_names:
                h = 0
                while h < 24:
                    if schedule.loc[s, h] == 1:
                        start = h
                        while h < 24 and schedule.loc[s, h] == 1:
                            h += 1
                        if h - start == 1:
                            schedule.loc[s, start] = 0
                    else:
                        h += 1
            return schedule

        schedule = remove_single(schedule)

        # 人数調整
        for h in hours:
            current = schedule[h].sum()
            need = required[h]
            if current < need:
                candidates = [
                    s for s in staff_names
                    if schedule.loc[s, h] == 0
                    and break_df.loc[s, h] == 0
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

        # 再単発除去
        schedule = remove_single(schedule)
        return schedule

    # 繰り返しで調整（偏りも減らす）
    for _ in range(3):
        schedule = adjust_schedule(schedule, required, max_hours)

    # ⑦ チェック
    st.subheader("チェック結果")
    error_flag = False
    for h in hours:
        assigned = schedule[h].sum()
        need = required[h]
        if assigned < need:
            st.error(f"{h:02d}時：人数不足（{assigned}/{need}）")
            error_flag = True
        elif assigned > need:
            st.warning(f"{h:02d}時：人数超過（{assigned}/{need}）")
    if not error_flag:
        st.success("すべての時間で必要人数を満たしています")

    # ⑧ 勤務時間
    st.subheader("勤務時間")
    st.dataframe(schedule.sum(axis=1).rename("勤務時間"))

    # ⑨ シフト表（ビジュアル）
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

    styled = display_df.style.map(color_map)
    styled = styled.format(lambda x: "")
    styled = styled.set_properties(**{
        "border": "2px solid #999",
        "text-align": "center"
    })
    st.dataframe(styled, use_container_width=True)
