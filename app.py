import streamlit as st
import pandas as pd
import random

st.title("シフト自動作成アプリ（完全版）")

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
# 勤務希望・休憩希望（タブUI）
# ---------------------------
work_df = pd.DataFrame(0, index=staff_names, columns=hours)
break_df = pd.DataFrame(0, index=staff_names, columns=hours)

st.subheader("勤務希望／休憩希望（スタッフごとにタブ）")

tabs = st.tabs(staff_names)

for i, staff in enumerate(staff_names):
    with tabs[i]:
        st.subheader(f"{staff}")
        col1, col2 = st.columns(2)

        with col1:
            st.write("勤務希望")
            for h in hours:
                work_df.loc[staff, h] = 1 if st.checkbox(
                    f"{h:02d}時", key=f"w_{staff}_{h}"
                ) else 0

        with col2:
            st.write("休憩希望")
            for h in hours:
                break_df.loc[staff, h] = 1 if st.checkbox(
                    f"{h:02d}時", key=f"b_{staff}_{h}"
                ) else 0

# ---------------------------
# シフト自動作成処理
# ---------------------------
def remove_singletons(df):
    for s in df.index:
        h = 0
        while h < 24:
            if df.loc[s, h] == 1:
                start = h
                while h < 24 and df.loc[s, h] == 1:
                    h += 1
                if h - start == 1:
                    df.loc[s, start] = 0
            else:
                h += 1

if st.button("実行"):
    schedule = work_df.copy()

    # ① 休憩反映
    for s in staff_names:
        for h in hours:
            if break_df.loc[s, h] == 1:
                schedule.loc[s, h] = 0

    # ② 人数調整（人数合わせ）
    for h in hours:
        current = schedule[h].sum()
        need = required[h]

        if current < need:
            candidates = [s for s in staff_names
                          if schedule.loc[s, h] == 0
                          and break_df.loc[s, h] == 0
                          and schedule.loc[s].sum() < max_hours]
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

    # ③ 単発除去
    remove_singletons(schedule)

    # ④ 指定時間帯に必ず休憩
    target_ranges = [
        [11, 12, 13],
        [17, 18, 19, 20]
    ]
    for s in staff_names:
        for tr in target_ranges:
            if all(schedule.loc[s, h] == 1 for h in tr):
                h = random.choice(tr)
                schedule.loc[s, h] = 0

    # ⑤ 再度単発除去
    remove_singletons(schedule)

    # ⑥ 最終微調整（連続シフトで人数不足補填）
    for h in hours:
        current = schedule[h].sum()
        need = required[h]
        if current < need:
            candidates = [s for s in staff_names
                          if schedule.loc[s, h] == 0
                          and break_df.loc[s, h] == 0
                          and schedule.loc[s].sum() < max_hours]
            random.shuffle(candidates)
            for s in candidates:
                if current >= need:
                    break
                # 前後とつなげて連続勤務
                if h > 0 and schedule.loc[s, h-1] == 1:
                    schedule.loc[s, h] = 1
                    current += 1
                elif h < 23 and schedule.loc[s, h+1] == 1:
                    schedule.loc[s, h] = 1
                    current += 1
                else:
                    schedule.loc[s, h] = 1
                    current += 1

    # ⑦ 最終単発除去
    remove_singletons(schedule)

    # ⑧ 列順修正
    schedule = schedule[sorted(schedule.columns)]

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
    st.subheader("勤務時間")
    st.dataframe(schedule.sum(axis=1).rename("勤務時間"))

    # ---------------------------
    # シフト表（ビジュアル）
    st.subheader("シフト表（ビジュアル）")
    display_df = schedule.copy()
    display_df.columns = [f"{h:02d}" for h in hours]
    display_df.index.name = "スタッフ"

    def color_map(val):
        return "background-color: #F6A068" if val == 1 else "background-color: #FFEEDB"

    styled = display_df.style.map(color_map)
    styled = styled.format(lambda x: "")
    styled = styled.set_properties(**{"border": "2px solid #999", "text-align": "center"})
    st.dataframe(styled, use_container_width=True)
