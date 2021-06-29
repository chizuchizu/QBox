# streamlit run app.py
import streamlit as st

import numpy as np
from amplify import *
from amplify.client import FixstarsClient
import matplotlib.pyplot as plt
import json
from mpl_toolkits.mplot3d import Axes3D

client = FixstarsClient()

with open("/home/yuma/.amplify/token.json") as f:
    client.token = json.load(f)["AMPLIFY_TOKEN"]
client.parameters.timeout = 1000  # タイムアウト1i秒


def main():
    placeholderl = st.empty()
    placeholderl.write("積み付け最適化")

    h = st.slider(label='縦の長さ',
                  min_value=3,
                  max_value=20,
                  value=3,
                  )
    w = st.slider(label='横の長さ',
                  min_value=3,
                  max_value=20,
                  value=3,
                  )
    d = st.slider(label='高さ',
                  min_value=3,
                  max_value=20,
                  value=3,
                  )

    box_1 = st.slider(label='Box 1の数',
                      min_value=0,
                      max_value=10,
                      value=1,
                      )

    box_2 = st.slider(label='Box 2の数',
                      min_value=0,
                      max_value=10,
                      value=1,
                      )

    box_3 = st.slider(label='Box 3の数',
                      min_value=0,
                      max_value=10,
                      value=1,
                      )

    box_1_size = [
        2, 3, 3
    ]
    box_2_size = [
        2, 5, 2
    ]
    box_3_size = [
        4, 4, 4
    ]

    pack = [
        box_1_size,
        box_2_size,
        box_3_size
    ]
    num = [
        box_1,
        box_2,
        box_3
    ]
    packs = []
    for i in range(3):
        for _ in range(num[i]):
            packs.append(pack[i])

    print(packs)
    print(h, w, d)
    print(type(h))
    placeholder = st.empty()
    with placeholder:
        st.write('実行中')

        r = solve_model(h, w, d, packs)
        if type(r) == int:
            st.write('解けませんでした！！')
        else:

            status = st.empty()
            progress_bar = st.progress(0)
            # plt_area = st.empty()
            # plt_area.pyplot(r)
            u_used = r
            angle = 0

            k = 0
            figs = []
            num_loop = 12

            st.subheader("描画してみる")

            for k in range(num_loop):
                status.text(f"グラフ描画Progress: {k * 100 / num_loop} %")
                progress_bar.progress(k / num_loop)
                fig = plt.figure(figsize=(5, 5))
                figs.append(fig)
                ax = Axes3D(fig)

                colors = [
                    "blue",
                    "green",
                    "red",
                ]

                colors_idx = []
                for i in range(3):
                    for _ in range(num[i]):
                        colors_idx.append(i)

                for _n in range(1, len(packs) + 1):

                    memo = np.where(u_used == _n)

                    for i in range(len(memo[0])):
                        ax.scatter3D(memo[0][i], memo[1][i], memo[2][i], "s", color=colors[colors_idx[_n - 1]],
                                     alpha=0.6, s=300)

                ax.view_init(30, angle)
                angle += 30

            status.text("Done!")
            plt_area = st.empty()
            k = 0
            while True:
                plt_area.pyplot(figs[k])
                # time.sleep(0.03)

                k += 1
                k %= num_loop


def solve_model(h, w, d, packs):
    # パターンの全列挙
    patterns = []
    for i in range(len(packs)):
        pack = packs[i]
        pattern = np.array([])

        # 縦方向、横方向、奥方向にどれだけすすめるか
        pattern_h = h - pack[0] + 1
        pattern_w = w - pack[1] + 1
        pattern_d = d - pack[2] + 1

        flag = True
        for x in range(pattern_h):
            for y in range(pattern_w):
                for z in range(pattern_d):
                    memo = np.zeros(
                        (
                            h, w, d
                        )
                    )
                    # 荷物を座標にマスク
                    memo[x:x + pack[0], y:y + pack[1], z:z + pack[2]] = 1
                    memo = memo.reshape((1, h, w, d))

                    # 4次元配列（パターン + 座標）
                    if flag:
                        pattern = memo
                        flag = False
                    else:
                        pattern = np.append(pattern, memo, axis=0)

        print(pattern.shape)
        patterns.append(pattern)

    # 荷物の数とパターン数(パターン数最大はh * w * d）
    q = gen_symbols(BinaryPoly, len(packs), h * w * d)

    f1 = 0
    for x in range(h):
        # 進捗度合いを確認するだけ
        print(x)
        for y in range(w):
            for z in range(d):
                f = 0
                for i in range(len(packs)):
                    for j in range(len(patterns[i])):
                        # 座標(x, y, z)に荷物が含まれるか
                        f += q[i][j] * patterns[i][j][x, y, z]
                # 座標(x, y, z)において荷物が重複がしないように　1以下という制約を追加
                f1 += constraint.less_equal(f, 1)

    # 一つの荷物につき一つの配置パターンしかできない制約
    f2 = sum(
        # 配置パターンのqubitの合計が1になればいい
        constraint.equal_to(sum(q[i][:len(patterns[i])]), 1)
        for i in range(len(packs))
    )

    f3 = sum(
        # 使わない配置パターンもあるので、それらはqubitの総和が0になるような制約を付け加える
        constraint.equal_to(sum(q[i][len(patterns[i]):]), 0)
        for i in range(len(packs))
        if len(patterns[i]) != h * w * d
    )
    # すべての制約を足す
    f = f1 + f2 + f3

    # トークン外部流出が怖いのでローカルフォルダが読み込むようにさせた

    solver = Solver(client)

    result = solver.solve(f)
    try:
        result[0]
    except:
        return 0

    # 1になったパターンが最適そうな解
    res = [k for k, v in sorted(result[0].values.items()) if v == 1]

    used = np.zeros((len(packs), h, w, d))

    for i in range(len(packs)):
        used[i] = patterns[i][res[i] % (h * w * d)]

    n_used = np.zeros_like(used)
    for i in range(len(packs)):
        n_used[i] = used[i] * (i + 1)

    for i in range(d):
        plt.imshow(n_used.sum(axis=0)[:, :, i])
        plt.show()

    u_used = n_used.sum(axis=0)

    return u_used


if __name__ == "__main__":
    main()
