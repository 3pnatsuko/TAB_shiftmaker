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
# 勤務希望・休憩希望（タブでスタッフごと）
# ---------------------------
work_df = pd.DataFrame(0, index=staff_names, columns=hours)
break_df = pd.DataFrame(0, index=staff_names, columns=hours)

st.subheader("勤務希望／休憩希望")

tabs = st.tabs(staff_names)
for i, staff in enumerate(staff_names):
    with tabs[i]:
        cols_w = st.columns(6)
        cols_b = st.columns(6)
        st.write("勤務希望")
        for h in hours:
            col = cols_w[h % 6]
            work_df.loc[staff, h] = 1 if col.checkbox(f"{h}時", key=f"w_{staff}_{h}") else 0

        st.write("休憩希望")
        for h in hours:
            col = cols_b[h % 6]
            break_df.loc[staff, h] = 1 if col.checkbox(f"{h}時", key=f"b_{staff}_{h}") else 0

# ---------------------------
# 実行
# ---------------------------
if st.button("実行"):

    schedule = work_df.copy()

    # ① 休憩希望反映
    for s in staff_names:
        for h in hours:
            if break_df.loc[s, h] == 1:
                schedule.loc[s, h] = 0

    # ② 必要人数に沿って初期割り当て
    for h in hours:
        assigned = schedule[h].sum()
        need = required[h]

        if assigned < need:
            candidates = [
                s for s in staff_names
                if schedule.loc[s, h] == 0 and break_df.loc[s, h] == 0
                and schedule.loc[s].sum() < max_hours
            ]
            random.shuffle(candidates)
            for s in candidates:
                if schedule[h].sum() >= need:
                    break
                schedule.loc[s, h] = 1

        elif assigned > need:
            candidates = [s for s in staff_names if schedule.loc[s, h] == 1]
            random.shuffle(candidates)
            for s in candidates:
                if schedule[h].sum() <= need:
                    break
                schedule.loc[s, h] = 0

    # ③ 単発を前後にくっつけて調整
    for s in staff_names:
        h = 0
        while h < 24:
            if schedule.loc[s, h] == 1:
                start = h
                while h < 24 and schedule.loc[s, h] == 1:
                    h += 1
                length = h - start
                if length == 1:
                    # 前後に勤務がある場合はつなげる
                    if start > 0 and schedule.loc[s, start-1] == 1:
                        schedule.loc[s, start] = 1
                    elif h < 24 and schedule.loc[s, h] == 1:
                        schedule.loc[s, start] = 1
                    else:
                        # どうしても単発なら削除して補填用リストに追加
                        schedule.loc[s, start] = 0
            else:
                h += 1

    # ④ 休憩時間を必ず確保
    target_ranges = [[11,12,13],[17,18,19,20]]
    for s in staff_names:
        for tr in target_ranges:
            if all(schedule.loc[s, h]==1 for h in tr):
                h = random.choice(tr)
                schedule.loc[s, h] = 0

    # ⑤ 最終微調整で必要人数を満たす
    for h in hours:
        while schedule[h].sum() < required[h]:
            # 勤務時間が少ないスタッフ優先で割り当て
            candidates = sorted(
                [s for s in staff_names if schedule.loc[s, h]==0 and break_df.loc[s, h]==0 and schedule.loc[s].sum()<max_hours],
                key=lambda x: schedule.loc[x].sum()
            )
            if not candidates:
                break
            schedule.loc[candidates[0], h] = 1

    # ⑥ 勤務時間を均等化
    for _ in range(2):  # 繰り返して調整
        max_s = schedule.sum(axis=1).idxmax()
        min_s = schedule.sum(axis=1).idxmin()
        # maxとminの差が2以上なら調整
        if schedule.loc[max_s].sum() - schedule.loc[min_s].sum() > 1:
            # max_sの単発を移動可能なら min_s に移動
            for h in hours:
                if schedule.loc[max_s, h]==1 and schedule.loc[min_s, h]==0 and break_df.loc[min_s,h]==0:
                    # 前後とくっついていない単発を移動
                    left = schedule.loc[max_s, h-1] if h>0 else 0
                    right = schedule.loc[max_s, h+1] if h<23 else 0
                    if left==0 and right==0:
                        schedule.loc[max_s, h]=0
                        schedule.loc[min_s, h]=1
                        break

    # ⑦ チェック表示
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

    # ⑧ 勤務時間
    st.subheader("勤務時間")
    st.dataframe(schedule.sum(axis=1).rename("勤務時間"))

    # ⑨ シフト表（ビジュアル）
    st.subheader("シフト表（ビジュアル）")
    display_df = schedule.copy()
    display_df.columns = [f"{h:02d}時" for h in hours]
    display_df.index.name = "スタッフ"

    def color_map(val):
        if val==1:
            return "background-color: #F6A068"
        else:
            return "background-color: #FFEEDB"

    styled = display_df.style.map(color_map)
    styled = styled.format(lambda x: "")
    styled = styled.set_properties(**{"border":"2px solid #999","text-align":"center"})

    st.dataframe(styled,use_container_width=True)
