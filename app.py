import streamlit as st
import pandas as pd
import random

st.set_page_config(layout="wide")
st.title("シフト自動最適化アプリ（希望尊重版）")

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
cols_req = st.columns(6)
for h in hours:
    col = cols_req[h % 6]
    required[h] = col.number_input(f"{h}時", 0, num_staff, 3, key=f"req_{h}")

# ---------------------------
# 勤務希望・休憩希望（タブ表示）
# ---------------------------
st.subheader("勤務希望／休憩希望")
work_df = pd.DataFrame(0, index=staff_names, columns=hours)
break_df = pd.DataFrame(0, index=staff_names, columns=hours)

tabs = st.tabs(staff_names)
for idx, staff in enumerate(staff_names):
    with tabs[idx]:
        st.write(f"--- {staff} ---")
        cols_work = st.columns(24)
        cols_break = st.columns(24)
        for h in hours:
            work_df.loc[staff, h] = 1 if cols_work[h].checkbox(f"{h}勤務", key=f"w_{staff}_{h}") else 0
            break_df.loc[staff, h] = 1 if cols_break[h].checkbox(f"{h}休憩", key=f"b_{staff}_{h}") else 0

# ---------------------------
# 実行
# ---------------------------
def fix_singletons(schedule):
    """単発勤務を除去して前後に連結する"""
    for s in staff_names:
        h = 0
        while h < 24:
            if schedule.loc[s, h] == 1:
                start = h
                while h < 24 and schedule.loc[s, h] == 1:
                    h += 1
                length = h - start
                if length == 1:
                    # 前後に勤務がある場合はくっつける
                    if start > 0 and schedule.loc[s, start-1] == 1:
                        schedule.loc[s, start] = 1
                    elif h < 24 and schedule.loc[s, h] == 1:
                        schedule.loc[s, start] = 1
                    else:
                        schedule.loc[s, start] = 0
            else:
                h += 1
    return schedule

def assign_needed(schedule):
    """必要人数を満たすように補充"""
    for h in hours:
        current = schedule[h].sum()
        need = required[h]
        if current < need:
            # 勤務希望があるスタッフ優先
            candidates = [
                s for s in staff_names
                if schedule.loc[s, h] == 0
                and break_df.loc[s, h] == 0
                and schedule.loc[s].sum() < max_hours
            ]
            # 希望勤務を優先
            candidates.sort(key=lambda x: work_df.loc[x, h], reverse=True)
            for s in candidates:
                if current >= need:
                    break
                schedule.loc[s, h] = 1
                current += 1
    return schedule

if st.button("最適化シフト作成"):

    schedule = work_df.copy()

    # ① 希望休憩を反映
    for s in staff_names:
        for h in hours:
            if break_df.loc[s, h] == 1:
                schedule.loc[s, h] = 0

    # ② 必要人数を満たす
    schedule = assign_needed(schedule)

    # ③ 単発勤務除去
    schedule = fix_singletons(schedule)

    # ④ 指定時間帯に必ず休憩
    target_ranges = [[11,12,13],[17,18,19,20]]
    for s in staff_names:
        for tr in target_ranges:
            if all(schedule.loc[s, h] == 1 for h in tr):
                h = random.choice(tr)
                schedule.loc[s, h] = 0

    # ⑤ 再単発補正
    schedule = fix_singletons(schedule)

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

    def color_map(val):
        return "background-color: #F6A068" if val == 1 else "background-color: #FFEEDB"

    styled = display_df.style.map(color_map)
    styled = styled.format(lambda x: "")
    styled = styled.set_properties(**{
        "border": "2px solid #999",
        "text-align": "center"
    })
    st.dataframe(styled, use_container_width=True)
