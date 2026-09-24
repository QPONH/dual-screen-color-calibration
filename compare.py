from pathlib import Path
import sys
import re
import statistics
from PIL import Image

MIDDLE_DROP = 0.20
SIDE_MARGIN = 0.15
VERTICAL_MARGIN = 0.12
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def sample_stats(im, box):
    c = im.crop(box)
    c.thumbnail((500, 500))
    # Pillow 12+ 推荐的新接口；避免 getdata() 的弃用警告。
    px = list(c.get_flattened_data())
    means = {
        k: statistics.fmean(p[i] for p in px)
        for i, k in enumerate("RGB")
    }
    stds = {
        k: statistics.pstdev(p[i] for p in px)
        for i, k in enumerate("RGB")
    }
    return means, stds


def get_stats(path):
    with Image.open(path) as src:
        im = src.convert("RGB")
        w, h = im.size

        x1 = int(w * SIDE_MARGIN)
        x2 = int(w * (1 - SIDE_MARGIN))

        top_end = int(h * (1 - MIDDLE_DROP) / 2)
        bottom_start = int(h * (1 + MIDDLE_DROP) / 2)

        ah = top_end
        bh = h - bottom_start

        a_box = (
            x1,
            int(ah * VERTICAL_MARGIN),
            x2,
            top_end - int(ah * VERTICAL_MARGIN),
        )
        b_box = (
            x1,
            bottom_start + int(bh * VERTICAL_MARGIN),
            x2,
            h - int(bh * VERTICAL_MARGIN),
        )

        a, a_std = sample_stats(im, a_box)
        b, b_std = sample_stats(im, b_box)

    delta = {k: b[k] - a[k] for k in "RGB"}
    return {
        "path": str(path),
        "name": path.name,
        "width": w,
        "height": h,
        "a_box": a_box,
        "b_box": b_box,
        "a": a,
        "a_std": a_std,
        "b": b,
        "b_std": b_std,
        "delta": delta,
    }


def print_one(r, show_note=True):
    print(f"\n照片: {r['path']}  尺寸: {r['width']}x{r['height']}")
    print("A区域:", r["a_box"])
    print("B区域:", r["b_box"])
    print("\nA 平均 RGB: " + ", ".join(f"{r['a'][k]:.2f}" for k in "RGB"))
    print("B 平均 RGB: " + ", ".join(f"{r['b'][k]:.2f}" for k in "RGB"))
    print("\nB - A:")
    for k in "RGB":
        print(f"  {k}: {r['delta'][k]:+.2f}")
    print("\n区域标准差（越大说明区域内部变化越明显）:")
    print("A:", ", ".join(f"{k}={r['a_std'][k]:.2f}" for k in "RGB"))
    print("B:", ", ".join(f"{k}={r['b_std'][k]:.2f}" for k in "RGB"))
    if show_note:
        print("\n注意：这是相对比较值，不是显示器绝对色度。")


def group_key(path):
    # 红1 / 红2 / 红3 -> 红；50灰1 / 50灰2 -> 50灰
    # 文件名末尾没有数字时，就用完整文件名作为组名。
    stem = path.stem
    m = re.match(r"^(.*?)(\d+)$", stem)
    return m.group(1) if m else stem


def find_images(folder):
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS],
        key=lambda p: (group_key(p), p.name),
    )


def print_batch(results):
    groups = {}
    for r in results:
        groups.setdefault(group_key(Path(r["path"])), []).append(r)

    print("\n" + "=" * 72)
    print("批量汇总")
    print("=" * 72)
    print("\n每张照片的 B-A：")
    print(f"{'组名':<16} {'文件':<20} {'ΔR':>9} {'ΔG':>9} {'ΔB':>9}")
    print("-" * 72)

    for gname, rs in groups.items():
        for r in rs:
            print(
                f"{gname:<16} {r['name']:<20} "
                f"{r['delta']['R']:+9.2f} {r['delta']['G']:+9.2f} {r['delta']['B']:+9.2f}"
            )

    print("\n同组多张照片的平均值：")
    print(f"{'组名':<16} {'张数':>5} {'平均ΔR':>12} {'平均ΔG':>12} {'平均ΔB':>12} {'波动范围(最大-最小)':>20}")
    print("-" * 82)

    for gname, rs in groups.items():
        values = {k: [r['delta'][k] for r in rs] for k in "RGB"}
        avgs = {k: statistics.fmean(values[k]) for k in "RGB"}
        ranges = {k: max(values[k]) - min(values[k]) for k in "RGB"}
        max_range = max(ranges.values())
        print(
            f"{gname:<16} {len(rs):>5} "
            f"{avgs['R']:+12.2f} {avgs['G']:+12.2f} {avgs['B']:+12.2f} "
            f"{max_range:>20.2f}"
        )

    print("\n怎么看：")
    print("- 同一颜色通常拍3张时，重点看‘平均ΔR/ΔG/ΔB’。")
    print("- ‘波动范围’越小，说明重复拍摄越稳定。")
    print("- 若某个通道三张照片差异很大，先不要据此调整显示器。")
    print("- 不要把 ΔR/ΔG/ΔB 直接当成 OSD 应该调多少格。")
    print("- 标准差很大时，可能存在摩尔纹、反光、亮度不均或相机处理造成的区域变化。")
    print("\n注意：这是相对比较值，不是显示器绝对色度。")


def main():
    if len(sys.argv) != 2:
        print("用法：")
        print("  单张：python compare.py photos\\红1.png")
        print("  批量：python compare.py photos")
        raise SystemExit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"找不到：{target}")
        raise SystemExit(1)

    try:
        if target.is_file():
            r = get_stats(target)
            print_one(r)
        elif target.is_dir():
            files = find_images(target)
            if not files:
                print(f"文件夹里没有支持的图片：{target}")
                print("支持：JPG / JPEG / PNG / WEBP / BMP / TIF / TIFF")
                raise SystemExit(1)

            print(f"找到 {len(files)} 张图片，开始批量分析……")
            results = []
            for p in files:
                try:
                    results.append(get_stats(p))
                except Exception as e:
                    print(f"[跳过] {p.name}: {e}")

            if not results:
                print("没有成功读取任何图片。")
                raise SystemExit(1)

            print_batch(results)
        else:
            print("目标既不是文件也不是文件夹。")
            raise SystemExit(1)
    except ImportError:
        print("缺少 Pillow，请运行：python -m pip install pillow")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
