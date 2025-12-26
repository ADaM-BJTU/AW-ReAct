from typing import List
from android_world.env.interface import State
from android_world.env import representation_utils
from android_world.env import env_launcher

from PIL import Image, ImageDraw, ImageFont
import io
import subprocess


def adb_screencap(adb_path: str) -> Image.Image:
    """
    使用 adb exec-out 命令截屏，返回PIL.Image对象
    """
    result = subprocess.run([adb_path, "exec-out", "screencap", "-p"], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("adb screencap failed: " + result.stderr.decode(errors='ignore'))

    png_data = result.stdout
    image = Image.open(io.BytesIO(png_data))
    return image


def _draw_ui_debug_image(adb_path: str, ui_elements: List[representation_utils.UIElement], save_path="ui_debug.png"):
    """
    在截图上绘制所有 UI 元素的 bounding box 和编号
    """
    img = adb_screencap(adb_path)
    draw = ImageDraw.Draw(img)

    # 尝试加载字体，没有则用默认
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default()

    for idx, elem in enumerate(ui_elements):
        bbox = elem.bbox_pixels
        if not bbox:
            continue

        x1, x2 = bbox.x_min, bbox.x_max
        y1, y2 = bbox.y_min, bbox.y_max

        # 画矩形框
        draw.rectangle([(x1, y1), (x2, y2)], outline="red", width=3)

        # 画编号
        draw.text((x1 + 5, y1 + 5), str(idx), fill="red", font=font)

    img.save(save_path)
    print(f"📸 已保存 UI 标注截图：{save_path}")


def _get_stable_ui_elements(env) -> List[representation_utils.UIElement]:
    try:
        state: State = env.get_state(wait_to_stabilize=True)
    except AttributeError as e:
        raise RuntimeError(f"❌ 调用get_state()失败：{str(e)}") from e

    ui_elements = state.ui_elements

    print("\n" + "=" * 80)
    print("📋 当前屏幕UI元素列表：")
    for idx, elem in enumerate(ui_elements):
        print(f"  [{idx:2d}] text={elem.text} | class={elem.class_name} | cont={elem.content_description} | bounds={elem.bbox_pixels}")
    print("=" * 80 + "\n")

    return ui_elements


def main():
    console_port = 5554
    adb_path = "C:\\Users\\dell\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe"

    env = env_launcher.load_and_setup_env(
        console_port=console_port,
        emulator_setup=False,
        adb_path=adb_path,
    )

    try:
        ui_elements = _get_stable_ui_elements(env)
        _draw_ui_debug_image(adb_path, ui_elements, "ui_debug.png")
    finally:
        env.close()


if __name__ == "__main__":
    main()
