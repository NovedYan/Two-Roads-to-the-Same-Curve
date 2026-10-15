"""
Interactive Bezier Curve Laboratory

A Python-based experimental environment for exploring
cubic Bezier curves, midpoint subdivision, convergence
analysis, and curve continuity.

Experiments:
    1. Curve Construction
       - Cubic Bezier Formula
       - Midpoint Subdivision

    2. Convergence Analysis
       - Approximation Error
       - Subdivision Depth
       - Error Reduction

    3. Curve Joins
       - Smooth and Corner Joins
       - C1 and G1 Continuity

Development Approach:
    Phase A: Static mathematical experiments
    Phase B: Interactive visualization and analysis

All Bezier coordinates and subdivision polylines are
computed by the implemented algorithms.
Matplotlib is used for visualization and interaction.

Environment: Python 3.10+ / Matplotlib
Run: python main.py
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider


# ==============================================================
# 基本設定
# ==============================================================
WIDTH = 800
HEIGHT = 600
OUTPUT_DIR = Path(__file__).resolve().parent

# 先固定四個固定控制點，產生清楚Bezier(測試用的四個點)。
B0 = [80, 450]
B1 = [180, 100]
B2 = [620, 100]
B3 = [720, 450]
STATIC_CONTROL_POINTS = [B0, B1, B2, B3]

# 三段 Bezier，第一處為 Smooth Join，第二處為 Corner。
SEGMENT_1 = [[70, 460], [120, 200], [220, 310], [280, 310]]
SEGMENT_2 = [[280, 310], [340, 310], [490, 150], [540, 280]]
SEGMENT_3 = [[540, 280], [670, 320], [660, 500], [730, 350]]
JOIN_T_VALUES = [i / 200 for i in range(201)]

# 用於避免重複開啟 Joins Editor 時重設狀態。
_joins_editor_figure = None


# ==============================================================
# 核心演算法 — Bezier Formula
# ==============================================================
def cubic_bezier(t, b0, b1, b2, b3):
    """自行實作的三次Bezier公式，回傳 (x, y)。"""
    x = (
        (1 - t) ** 3 * b0[0]
        + 3 * t * (1 - t) ** 2 * b1[0]
        + 3 * t**2 * (1 - t) * b2[0]
        + t**3 * b3[0]
    )
    y = (
        (1 - t) ** 3 * b0[1]
        + 3 * t * (1 - t) ** 2 * b1[1]
        + 3 * t**2 * (1 - t) * b2[1]
        + t**3 * b3[1]
    )
    return x, y


def midpoint(p1, p2):
    """兩點的中點。"""
    return [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2]


# ==============================================================
# 核心演算法 — Mid-point Construction
# ==============================================================
def split_bezier_half(b0, b1, b2, b3):
    """De Casteljau 中點法：在 t=0.5 分割為兩條三次Bezier。"""
    m01 = midpoint(b0, b1)
    m12 = midpoint(b1, b2)
    m23 = midpoint(b2, b3)
    m012 = midpoint(m01, m12)
    m123 = midpoint(m12, m23)
    m = midpoint(m012, m123)
    return [b0, m01, m012, m], [m, m123, m23, b3]


def midpoint_polyline(b0, b1, b2, b3, depth):
    """遞迴至指定深度，將各子曲線端點接成折線。"""
    if depth < 0:
        raise ValueError("Subdivision depth must be non-negative")
    if depth == 0:
        return [b0, b3]

    left, right = split_bezier_half(b0, b1, b2, b3)
    left_points = midpoint_polyline(*left, depth - 1)
    right_points = midpoint_polyline(*right, depth - 1)
    return left_points[:-1] + right_points  # 移除重複的接合點


def point_to_segment_distance(px, py, a, b):
    """取樣點 P 到有限線段 AB 的最短距離，投影會限制在 AB 範圍內。"""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return math.hypot(px - ax, py - ay)
    u = ((px - ax) * dx + (py - ay) * dy) / length_squared
    u = max(0.0, min(1.0, u))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy))


def sample_formula_curve(control_points, initial_intervals=2000, max_spacing_px=0.1):
    """取樣直到公式曲線所有相鄰取樣點間距嚴格小於 0.1 px。"""
    intervals = initial_intervals
    while True:
        curve = [
            cubic_bezier(i / intervals, *control_points)
            for i in range(intervals + 1)
        ]
        spacing = max(
            math.hypot(
                curve[i + 1][0] - curve[i][0],
                curve[i + 1][1] - curve[i][1],
            )
            for i in range(intervals)
        )
        if spacing < max_spacing_px:
            return curve, spacing
        intervals *= 2
        if intervals > 1_048_576:
            raise ValueError("Curve requires too many samples; check control points")


# ==============================================================
# 收斂實驗共用函式
# ==============================================================
def analyze_bezier_convergence(control_points, max_depth=12):
    """誤差方向：公式取樣點 -> 最近的中點折線線段。

    逐層加深到最大誤差首次低於 0.5 px；回傳：
    results、公式取樣點數、最大相鄰取樣間距。
    """
    curve, max_spacing = sample_formula_curve(control_points)
    results = []
    previous_error = None

    for depth in range(max_depth + 1):
        polyline = midpoint_polyline(*control_points, depth)
        max_error = 0.0
        for x, y in curve:
            nearest_distance = min(
                point_to_segment_distance(x, y, polyline[j], polyline[j + 1])
                for j in range(len(polyline) - 1)
            )
            max_error = max(max_error, nearest_distance)

        ratio = (
            previous_error / max_error
            if previous_error is not None and max_error > 0
            else None
        )
        results.append({
            "depth": depth,
            "segments": len(polyline) - 1,
            "error": max_error,
            "ratio": ratio,
        })
        if max_error < 0.5:
            break
        previous_error = max_error

    return results, len(curve), max_spacing


def print_convergence_results(results, sample_count, max_spacing, title):
    """靜態實驗與互動實驗統一使用的輸出格式。"""
    print(f"\n========== {title} ==========")
    print(f"Sample Points = {sample_count}")
    print(f"Max Sample Spacing = {max_spacing:.6f} px")
    print("Sampling Requirement:", "PASS" if max_spacing < 0.1 else "FAIL")
    for row in results:
        ratio_text = "N/A" if row["ratio"] is None else f"{row['ratio']:.4f}"
        print(
            f"Depth = {row['depth']}, Segments = {row['segments']}, "
            f"Error = {row['error']:.6f} px, Reduction Ratio = {ratio_text}"
        )
    last = results[-1]
    passed = last["error"] < 0.5
    print("Minimum Qualified Depth =", last["depth"] if passed else "Not found")
    print(f"Maximum Error = {last['error']:.6f} px")
    print("Requirement:", "PASS" if passed else "FAIL")
    return passed


def make_convergence_figure(results, title="Part 1.2 - Bezier Convergence Analysis"):
    """只繪出本程式算出的數據；沒有使用內建曲線計算。"""
    fig, ax = plt.subplots(figsize=(8, 5))
    depths = [row["depth"] for row in results]
    errors = [row["error"] for row in results]
    ax.plot(depths, errors, marker="o", linewidth=2, label="Maximum Error")
    if all(error > 0 for error in errors):
        ax.set_yscale("log")
    ax.axhline(0.5, color="red", linestyle="--", label="Threshold = 0.5 px")
    ax.set_title(title)
    ax.set_xlabel("Subdivision Depth")
    ax.set_ylabel("Maximum Error (px)")
    ax.set_xticks(depths)
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    return fig


def save_convergence_experiment(control_points, results, sample_count, max_spacing):
    """一次保存同一次分析的 PNG + CSV + JSON，防止來源控制點不一致。"""
    """這個功能主要是要觀察是否符合需求"""
    image_path = OUTPUT_DIR / "part1_2_interactive_convergence.png"
    csv_path = OUTPUT_DIR / "part1_2_interactive_convergence.csv"
    json_path = OUTPUT_DIR / "part1_2_analysis.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["Depth", "Segments", "Maximum Error (px)", "Reduction Ratio"])
        for row in results:
            writer.writerow([
                row["depth"],
                row["segments"],
                f"{row['error']:.9f}",
                "" if row["ratio"] is None else f"{row['ratio']:.6f}",
            ])

    last = results[-1]
    analysis_data = {
        "control_points": [p.copy() for p in control_points],
        "canvas": {"width": WIDTH, "height": HEIGHT},
        "sample_points": sample_count,
        "max_sample_spacing_px": max_spacing,
        "error_threshold_px": 0.5,
        "minimum_depth": last["depth"] if last["error"] < 0.5 else None,
        "results": results,
    }
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(analysis_data, file, indent=2, ensure_ascii=False)

    fig = make_convergence_figure(results)
    fig.savefig(image_path, dpi=150, bbox_inches="tight")
    print(f"Convergence data saved: {csv_path}")
    print(f"Analysis configuration saved: {json_path}")
    print(f"Convergence graph saved: {image_path}")
    return fig


# ==============================================================
# 原始靜態實驗（保留開發歷程與報告對照），靜態版先驗證數學計算。
# ==============================================================
def run_part1_1_static():
    """Part 1.1：同一組控制點的公式曲線與 depth=2 折線疊圖。"""
    points = STATIC_CONTROL_POINTS
    t_values = [i / 200 for i in range(201)]
    curve = [cubic_bezier(t, *points) for t in t_values]
    polyline = midpoint_polyline(*points, 2)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([p[0] for p in points], [p[1] for p in points],
            "o--", label="Control Points")
    ax.plot([p[0] for p in curve], [p[1] for p in curve],
            color="orange", linewidth=2, label="Cubic Bezier Formula")
    ax.plot([p[0] for p in polyline], [p[1] for p in polyline],
            "s-", color="red", markersize=4,
            label="Mid-point Construction (depth=2)")
    setup_canvas(ax, "Part 1.1 - Formula vs Mid-point Construction")
    fig.savefig(OUTPUT_DIR / "part1_1_overlay.png", dpi=150)
    plt.close(fig)
    print("Part 1.1 static comparison saved.")


def run_part1_2_static():
    """固定初始控制點的基準收斂實驗。"""
    results, count, spacing = analyze_bezier_convergence(STATIC_CONTROL_POINTS)
    print_convergence_results(results, count, spacing, "Part 1.2 - Static Baseline")
    fig = make_convergence_figure(results, "Part 1.2 - Static Convergence")
    fig.savefig(OUTPUT_DIR / "part1_2_convergence.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Part 1.2 static convergence graph saved.")


def draw_part1_3_three_segments(seg1, seg2, seg3):
    """三段開放路徑，其中前一接點平滑、後一接點為角點。"""
    segments = [seg1, seg2, seg3]
    fig, ax = plt.subplots(figsize=(8, 6))
    for i, segment in enumerate(segments):
        curve = [cubic_bezier(t, *segment) for t in JOIN_T_VALUES]
        ax.plot([p[0] for p in curve], [p[1] for p in curve],
                linewidth=2, label=f"Segment {i + 1}")
    smooth, corner = seg1[3], seg2[3]
    ax.scatter([smooth[0], corner[0]], [smooth[1], corner[1]],
               color="red", s=70, zorder=5)
    ax.annotate("Smooth Join", smooth, xytext=(-30, -25), textcoords="offset points")
    ax.annotate("Corner Join", corner, xytext=(10, -25), textcoords="offset points")
    setup_canvas(ax, "Part 1.3 - Three Bezier Segments")
    fig.savefig(OUTPUT_DIR / "part1_3_three_segments.png", dpi=150)
    return fig


def draw_part1_3_equal_vs_unequal(seg1, seg2):
    """控制左右方向線共線，比較等長 C1 與不等長 G1。"""
    equal = [p.copy() for p in seg2]
    unequal = [p.copy() for p in seg2]
    join = seg1[3]
    before = seg1[2]
    # 保持方向，只把接合後方向線延長為三倍。
    unequal[1] = [
        join[0] + 3 * (join[0] - before[0]),
        join[1] + 3 * (join[1] - before[1]),
    ]

    left_length = math.dist(before, join)
    right_equal = math.dist(join, equal[1])
    right_unequal = math.dist(join, unequal[1])
    cases = [
        (f"Equal Length ({left_length:.0f} / {right_equal:.0f} px)", equal),
        (f"Unequal Length ({left_length:.0f} / {right_unequal:.0f} px)", unequal),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, (title, second) in zip(axes, cases):
        for i, segment in enumerate([seg1, second]):
            curve = [cubic_bezier(t, *segment) for t in JOIN_T_VALUES]
            ax.plot([p[0] for p in curve], [p[1] for p in curve],
                    linewidth=2, label=f"Segment {i + 1}")
        after = second[1]
        ax.plot([before[0], join[0], after[0]],
                [before[1], join[1], after[1]],
                "o--", color="black", linewidth=1.5, label="Direction Lines")
        ax.scatter(join[0], join[1], color="red", s=80, zorder=5)
        ax.set_title(title)
        ax.set_xlim(40, 570)
        ax.set_ylim(520, 50)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("X (pixels)")
        ax.set_ylabel("Y (pixels)")
        ax.grid(True)
        ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "part1_3_equal_vs_unequal.png",
                dpi=150, bbox_inches="tight")
    return fig


def setup_canvas(ax, title):
    """共用圖框設定；數學座標已由本程式求得。"""
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(HEIGHT, 0)  # 螢幕座標：Y 向下增加
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title)
    ax.set_xlabel("X (pixels)")
    ax.set_ylabel("Y (pixels)")
    ax.grid(True)
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend()


def generate_static_experiments():
    """保留靜態實驗輸出，但只執行一次，不再重複計算。"""
    print("\n===== Stage A: Static Experiments =====")
    run_part1_1_static()
    run_part1_2_static()
    fig1 = draw_part1_3_three_segments(SEGMENT_1, SEGMENT_2, SEGMENT_3)
    fig2 = draw_part1_3_equal_vs_unequal(SEGMENT_1, SEGMENT_2)
    plt.close(fig1)
    plt.close(fig2)
    print("Part 1.3 static figures generated successfully.")


# ==============================================================
# 5. Stage B — Part 1.3 Interactive Joins Editor
# ==============================================================
def open_joins_editor():
    """三段曲線拖曳；Smooth Join 維持 C1 / G1，Corner Join 不強制共線。"""
    global _joins_editor_figure

    # 同一個 Joins Editor 不重複初始化：避免遺失已編輯控制點。
    if _joins_editor_figure is not None and plt.fignum_exists(
        _joins_editor_figure.number
    ):
        _joins_editor_figure.show()
        return _joins_editor_figure

    fig, ax = plt.subplots(num="Part 1.3 - Joins Editor", figsize=(9, 6))
    fig.subplots_adjust(bottom=0.20)
    _joins_editor_figure = fig

    join_segments = [
        [p.copy() for p in SEGMENT_1],
        [p.copy() for p in SEGMENT_2],
        [p.copy() for p in SEGMENT_3],
    ]
    fig.join_segments = join_segments
    colors = ["blue", "orange", "green"]
    join_mode = {"ratio": 1.0}  # Equal=1:1 (C1), Unequal=1:3 (G1)
    active = {"point": None}

    def redraw_joins():
        ax.clear()
        for i, segment in enumerate(join_segments):
            curve = [cubic_bezier(t, *segment) for t in JOIN_T_VALUES]
            ax.plot([p[0] for p in curve], [p[1] for p in curve],
                    color=colors[i], linewidth=2, label=f"Segment {i + 1}")
            ax.plot([p[0] for p in segment], [p[1] for p in segment],
                    "o--", color=colors[i], alpha=0.5, markersize=7)

        smooth = join_segments[0][3]
        corner = join_segments[1][3]
        ax.scatter([smooth[0], corner[0]], [smooth[1], corner[1]],
                   color="red", s=90, zorder=5)
        ax.annotate("Smooth Join", smooth,
                    xytext=(-40, 25), textcoords="offset points")
        ax.annotate("Corner Join", corner,
                    xytext=(10, -30), textcoords="offset points")

        # 每次重畫都保留目前的模式，不再被固定標題覆蓋。
        mode = "Equal Length (C1)" if join_mode["ratio"] == 1 else "Unequal Length (G1)"
        setup_canvas(ax, f"Part 1.3 - Interactive Bezier Joins | {mode}")
        fig.canvas.draw_idle()

    def on_press(event):
        if event.inaxes != ax or event.button != 1:
            return
        nearest = None
        min_distance = 12  # 螢幕像素中的點選容許距離
        for i, segment in enumerate(join_segments):
            for j, point in enumerate(segment):
                if (i, j) in [(1, 0), (2, 0)]:
                    continue  # 接合點的另一個副本不重複選取
                px, py = ax.transData.transform(point)
                distance = math.hypot(event.x - px, event.y - py)
                if distance < min_distance:
                    nearest, min_distance = (i, j), distance
        active["point"] = nearest

    def on_motion(event):
        if active["point"] is None or event.inaxes != ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        i, j = active["point"]
        old = join_segments[i][j]
        new = [float(event.xdata), float(event.ydata)]
        dx, dy = new[0] - old[0], new[1] - old[1]
        join_segments[i][j] = new

        if (i, j) == (0, 3):  # 拖曳 Smooth Join
            join_segments[1][0] = new.copy()
            for si, pi in [(0, 2), (1, 1)]:
                p = join_segments[si][pi]
                join_segments[si][pi] = [p[0] + dx, p[1] + dy]
        elif (i, j) == (1, 3):  # 拖曳 Corner Join
            join_segments[2][0] = new.copy()
            for si, pi in [(1, 2), (2, 1)]:
                p = join_segments[si][pi]
                join_segments[si][pi] = [p[0] + dx, p[1] + dy]
        elif (i, j) == (0, 2):  # Smooth Join 左側方向點
            join = join_segments[0][3]
            ratio = join_mode["ratio"]
            join_segments[1][1] = [
                join[0] + ratio * (join[0] - new[0]),
                join[1] + ratio * (join[1] - new[1]),
            ]
        elif (i, j) == (1, 1):  # Smooth Join 右側方向點
            join = join_segments[0][3]
            ratio = join_mode["ratio"]
            join_segments[0][2] = [
                join[0] - (new[0] - join[0]) / ratio,
                join[1] - (new[1] - join[1]) / ratio,
            ]
        redraw_joins()

    def on_release(event):
        active["point"] = None

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_motion)
    fig.canvas.mpl_connect("button_release_event", on_release)

    # 讓使用者直接隔離「共線」與「長度相等」兩項條件。
    toggle_ax = fig.add_axes([0.30, 0.05, 0.40, 0.06])
    toggle_button = Button(toggle_ax, "Switch to Unequal (G1)")

    def on_toggle_join(event):
        join_mode["ratio"] = 3.0 if join_mode["ratio"] == 1.0 else 1.0
        button_label = (
            "Switch to Equal (C1)" if join_mode["ratio"] == 3.0
            else "Switch to Unequal (G1)"
        )
        toggle_button.label.set_text(button_label)
        join = join_segments[0][3]
        left = join_segments[0][2]
        ratio = join_mode["ratio"]
        join_segments[1][1] = [
            join[0] + ratio * (join[0] - left[0]),
            join[1] + ratio * (join[1] - left[1]),
        ]
        redraw_joins()

    toggle_button.on_clicked(on_toggle_join)
    fig.toggle_button = toggle_button

    # Equal / Unequal 分別儲存，避免互相覆蓋。
    save_ax = fig.add_axes([0.08, 0.05, 0.18, 0.06])
    save_button = Button(save_ax, "Save Joins")

    def on_save_joins(event):
        mode = "equal" if join_mode["ratio"] == 1.0 else "unequal"
        json_path = OUTPUT_DIR / f"part1_3_joins_{mode}.json"
        png_path = OUTPUT_DIR / f"part1_3_joins_{mode}.png"
        data = {
            "part": "1.3",
            "mode": mode,
            "direction_length_ratio": join_mode["ratio"],
            "canvas": {"width": WIDTH, "height": HEIGHT},
            "segments": [[p.copy() for p in s] for s in join_segments],
            "smooth_join": join_segments[0][3],
            "corner_join": join_segments[1][3],
        }
        with json_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        fig.savefig(png_path, dpi=150, bbox_inches="tight", facecolor="white")
        print(f"Part 1.3 JSON saved: {json_path}")
        print(f"Part 1.3 PNG saved: {png_path}")

    save_button.on_clicked(on_save_joins)
    fig.save_join_button = save_button

    redraw_joins()
    fig.show()
    return fig


# ==============================================================
# 滑鼠拖曳設計
# ==============================================================
def open_bezier_editor():
    """滑鼠點四點 -> 曲線；可拖曳、Depth 滑桿、Save/Load、Analyze、Joins。"""
    fig, ax = plt.subplots(num="Interactive Bezier Editor", figsize=(8, 6))
    fig.subplots_adjust(bottom=0.23)
    setup_canvas(ax, "Click 4 Control Points (0/4)")

    points = []
    dragging = {"index": None}
    depth_state = {"value": 2}

    control_line, = ax.plot([], [], "o--", color="blue", markersize=8,
                            label="Control Points")
    bezier_line, = ax.plot([], [], color="orange", linewidth=2,
                           label="Bezier Curve")
    midpoint_line, = ax.plot([], [], "s-", color="red", markersize=4,
                             linewidth=1.5, label="Mid-point (depth=2)")
    ax.legend()

    def redraw():
        control_line.set_data(
            [p[0] for p in points], [p[1] for p in points]
        )
        if len(points) == 4:
            curve = [cubic_bezier(i / 300, *points) for i in range(301)]
            bezier_line.set_data(
                [p[0] for p in curve], [p[1] for p in curve]
            )
            polyline = midpoint_polyline(*points, depth_state["value"])
            midpoint_line.set_data(
                [p[0] for p in polyline], [p[1] for p in polyline]
            )
            ax.set_title("Drag Control Points | Press R to Reset")
        else:
            bezier_line.set_data([], [])
            midpoint_line.set_data([], [])
            ax.set_title(f"Click 4 Control Points ({len(points)}/4)")
        fig.canvas.draw_idle()

    def on_press(event):
        if event.inaxes != ax or event.button != 1:
            return
        if event.xdata is None or event.ydata is None:
            return
        if len(points) < 4:
            points.append([float(event.xdata), float(event.ydata)])
            redraw()
            return
        # 四點已就緒後，按住控制點才能拖曳。
        dragging["index"] = None
        best_distance = 12
        for i, p in enumerate(points):
            px, py = ax.transData.transform(p)
            distance = math.hypot(event.x - px, event.y - py)
            if distance <= best_distance:
                dragging["index"] = i
                best_distance = distance

    def on_motion(event):
        i = dragging["index"]
        if i is None or event.inaxes != ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        points[i][:] = [float(event.xdata), float(event.ydata)]
        redraw()

    def on_release(event):
        dragging["index"] = None

    def on_key(event):
        if event.key and event.key.lower() == "r":
            points.clear()
            dragging["index"] = None
            redraw()

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("motion_notify_event", on_motion)
    fig.canvas.mpl_connect("button_release_event", on_release)
    fig.canvas.mpl_connect("key_press_event", on_key)

    # Depth：改變視覺化的中點折線密度，不等於 1.2 找出的最小合格深度。
    slider_ax = fig.add_axes([0.22, 0.08, 0.60, 0.035])
    depth_slider = Slider(slider_ax, label="Depth", valmin=0, valmax=8,
                          valinit=2, valstep=1)

    def on_depth_change(value):
        depth_state["value"] = int(value)
        midpoint_line.set_label(f"Mid-point (depth={depth_state['value']})")
        ax.legend()
        redraw()

    depth_slider.on_changed(on_depth_change)
    fig.depth_slider = depth_slider

    # Save Points：儲存控制點 JSON 與當下畫面 PNG。
    save_ax = fig.add_axes([0.03, 0.145, 0.15, 0.05])
    save_button = Button(save_ax, "Save Points")

    def on_save_points(event):
        if len(points) != 4:
            print("Please create 4 control points first.")
            return
        json_path = OUTPUT_DIR / "part1_1_control_points.json"
        image_path = OUTPUT_DIR / "part1_1_interactive.png"
        data = {
            "control_points": [p.copy() for p in points],
            "depth": depth_state["value"],
            "canvas": {"width": WIDTH, "height": HEIGHT},
        }
        with json_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        fig.savefig(image_path, dpi=150, facecolor="white")
        print(f"Control points saved: {json_path}")
        print(f"Interactive image saved: {image_path}")

    save_button.on_clicked(on_save_points)
    fig.save_button = save_button

    # Load Points：恢復之前的四點與 Depth。
    load_ax = fig.add_axes([0.22, 0.145, 0.15, 0.05])
    load_button = Button(load_ax, "Load Points")

    def on_load_points(event):
        json_path = OUTPUT_DIR / "part1_1_control_points.json"
        if not json_path.exists():
            print("No saved control points found.")
            return
        try:
            with json_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            saved_points = data["control_points"]
            saved_depth = int(data["depth"])
            if not isinstance(saved_points, list) or len(saved_points) != 4:
                raise ValueError("Expected exactly four control points")
            new_points = []
            for p in saved_points:
                if not isinstance(p, (list, tuple)) or len(p) != 2:
                    raise ValueError("Each control point must contain [x, y]")
                x, y = float(p[0]), float(p[1])
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError("Control point coordinates must be finite")
                new_points.append([x, y])
            if not 0 <= saved_depth <= 8:
                raise ValueError("Invalid subdivision depth")
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError) as error:
            print(f"Load failed: {error}")
            return

        points[:] = new_points
        dragging["index"] = None
        depth_slider.set_val(saved_depth)
        redraw()
        print(f"Control points loaded: {json_path}")

    load_button.on_clicked(on_load_points)
    fig.load_button = load_button

    # Analyze：直接分析目前四點，不使用靜態基準控制點。
    analysis_window = {"figure": None}
    analyze_ax = fig.add_axes([0.41, 0.145, 0.18, 0.05])
    analyze_button = Button(analyze_ax, "Analyze")

    def on_analyze(event):
        if len(points) != 4:
            print("Please create 4 control points first.")
            return
        current_points = [p.copy() for p in points]
        results, sample_count, max_spacing = analyze_bezier_convergence(current_points)
        print_convergence_results(
            results, sample_count, max_spacing, "Part 1.2 - Interactive Convergence"
        )
        # 更新同一份分析結果：先關閉先前的視窗，避免堆疊過時圖表。
        old_fig = analysis_window["figure"]
        if old_fig is not None and plt.fignum_exists(old_fig.number):
            plt.close(old_fig)
        result_fig = save_convergence_experiment(
            current_points, results, sample_count, max_spacing
        )
        result_fig.canvas.manager.set_window_title("Part 1.2 - Convergence Analysis")
        analysis_window["figure"] = result_fig
        result_fig.show()

    analyze_button.on_clicked(on_analyze)
    fig.analyze_button = analyze_button

    # Joins Editor：獨立互動視窗，用同一組基礎演算法。
    joins_ax = fig.add_axes([0.62, 0.145, 0.17, 0.05])
    joins_button = Button(joins_ax, "Joins Editor")
    joins_button.on_clicked(lambda event: open_joins_editor())
    fig.joins_button = joins_button

    redraw()
    return fig


# ==============================================================
# 產生靜態實驗證據，再啟動互動版
# ==============================================================
def main():
    generate_static_experiments()
    print("\n===== Stage B: Interactive Bezier Editor =====")
    print("Click four points, drag to edit, press R to reset.")
    print("Use Save / Load / Analyze / Joins Editor for the experiments.")
    open_bezier_editor()
    plt.show()


if __name__ == "__main__":
    main()
