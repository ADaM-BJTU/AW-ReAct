import time
import json
import threading
import subprocess
from typing import List, Dict, Tuple, Optional, Any
import os
import sys
import argparse

from absl import logging
from android_world.env.interface import AsyncAndroidEnv, State
from android_world.env import actuation, representation_utils
from android_world.env import json_action
from android_world.env import android_world_controller


class RealTimeOperationRecorder:

    def __init__(self, env: AsyncAndroidEnv, output_json: str = "real_time_operations.json"):
        self.env = env
        self.controller = self._get_valid_controller()
        self.output_json = output_json
        self.operations: List[Dict[str, Any]] = []
        self.is_recording = False
        self.start_time = 0.0
        self.last_operation_time = 0.0
        self.ui_elements: List[representation_utils.UIElement] = []
        self.event_thread: Optional[threading.Thread] = None
        self._event_debug_log = "event_debug.log"
        self._adb_available = True
        self._coord_cache = {}
        self._lock = threading.Lock()
        self._keyboard_cache = {}
        self._key_mapping = self._init_key_mapping()
        self._input_timeout = 1.0

        # 屏幕与触摸设备参数
        self._screen_width = 1080
        self._screen_height = 2400
        self._raw_min_x = 0
        self._raw_max_x = 32767
        self._raw_min_y = 0
        self._raw_max_y = 32767
        self._init_touch_device_bounds()

    def _init_touch_device_bounds(self):
        """获取触摸设备坐标范围"""
        try:
            result = subprocess.run(
                ["adb", "shell", "getevent", "-p", "/dev/input/event2"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            output = result.stdout

            for line in output.splitlines():
                line = line.strip()
                if "ABS_MT_POSITION_X" in line:
                    parts = line.split()
                    if len(parts) >= 5 and parts[3].isdigit() and parts[5].isdigit():
                        self._raw_min_x = int(parts[3])
                        self._raw_max_x = int(parts[5])
                elif "ABS_MT_POSITION_Y" in line:
                    parts = line.split()
                    if len(parts) >= 5 and parts[3].isdigit() and parts[5].isdigit():
                        self._raw_min_y = int(parts[3])
                        self._raw_max_y = int(parts[5])

            if self._raw_max_x <= self._raw_min_x:
                self._raw_max_x = 32767
            if self._raw_max_y <= self._raw_min_y:
                self._raw_max_y = 32767

            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[触摸范围] X: {self._raw_min_x}-{self._raw_max_x}, Y: {self._raw_min_y}-{self._raw_max_y}\n")
        except Exception as e:
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[触摸范围获取失败] {str(e)}，使用默认范围\n")

    def _convert_raw_to_screen(self, raw_x: int, raw_y: int) -> Tuple[int, int]:
        """转换原始坐标到屏幕坐标"""
        try:
            clamped_x = max(self._raw_min_x, min(raw_x, self._raw_max_x))
            clamped_y = max(self._raw_min_y, min(raw_y, self._raw_max_y))
            screen_x = int((clamped_x - self._raw_min_x) / (self._raw_max_x - self._raw_min_x) * self._screen_width)
            screen_y = int((clamped_y - self._raw_min_y) / (self._raw_max_y - self._raw_min_y) * self._screen_height)
            screen_x = max(0, min(screen_x, self._screen_width))
            screen_y = max(0, min(screen_y, self._screen_height))
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[坐标转换] 原始({raw_x},{raw_y}) → 屏幕({screen_x},{screen_y})\n")
            return (screen_x, screen_y)
        except Exception as e:
            screen_x = raw_x % self._screen_width
            screen_y = raw_y % self._screen_height
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[转换失败] {str(e)}，容错坐标({screen_x},{screen_y})\n")
            return (screen_x, screen_y)

    def _init_key_mapping(self) -> Dict[str, str]:
        return {
            "KEY_A": "a", "KEY_B": "b", "KEY_C": "c", "KEY_D": "d", "KEY_E": "e",
            "KEY_F": "f", "KEY_G": "g", "KEY_H": "h", "KEY_I": "i", "KEY_J": "j",
            "KEY_K": "k", "KEY_L": "l", "KEY_M": "m", "KEY_N": "n", "KEY_O": "o",
            "KEY_P": "p", "KEY_Q": "q", "KEY_R": "r", "KEY_S": "s", "KEY_T": "t",
            "KEY_U": "u", "KEY_V": "v", "KEY_W": "w", "KEY_X": "x", "KEY_Y": "y", "KEY_Z": "z",
            "KEY_1": "1", "KEY_2": "2", "KEY_3": "3", "KEY_4": "4", "KEY_5": "5",
            "KEY_6": "6", "KEY_7": "7", "KEY_8": "8", "KEY_9": "9", "KEY_0": "0",
            "KEY_SPACE": " ", "KEY_ENTER": "\n"
        }

    def _get_valid_controller(self) -> android_world_controller.AndroidWorldController:
        if not hasattr(self.env, "controller"):
            raise RuntimeError("AsyncAndroidEnv缺少controller属性")
        controller = self.env.controller
        if not isinstance(controller, android_world_controller.AndroidWorldController):
            raise RuntimeError(f"controller类型错误：需为AndroidWorldController，实际为{type(controller).__name__}")
        return controller

    def _update_ui_elements(self) -> None:
        """强制更新UI元素，移除不支持的timeout参数"""
        try:
            # 修复：移除timeout参数，因为AsyncAndroidEnv.get_state()不支持
            state: State = self.env.get_state(wait_to_stabilize=True)
            self.ui_elements = state.ui_elements if isinstance(state.ui_elements, list) else []
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[UI元素更新] 共获取到{len(self.ui_elements)}个元素（最新）\n")
        except Exception as e:
            logging.warning(f"更新UI元素失败：{str(e)}，使用缓存列表（可能过时）")
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[UI更新失败] {str(e)}\n")

    def _find_element_by_coords(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """查找元素并记录多维度特征（用于索引容错）"""
        with open(self._event_debug_log, "a", encoding="utf-8") as f:
            f.write(f"[查找元素] 坐标({x},{y})，共{len(self.ui_elements)}个元素\n")

        for idx, elem in enumerate(self.ui_elements):
            if not hasattr(elem, "bbox_pixels") or not elem.bbox_pixels:
                continue
            bbox = elem.bbox_pixels
            if not (hasattr(bbox, "x_min") and hasattr(bbox, "x_max") and
                    hasattr(bbox, "y_min") and hasattr(bbox, "y_max")):
                continue

            # 宽松匹配（±20像素）
            if (bbox.x_min - 20 <= x <= bbox.x_max + 20 and
                    bbox.y_min - 20 <= y <= bbox.y_max + 20):
                # 记录元素多维度特征（索引、文本、描述、类名、坐标范围）
                element_info = {
                    "index": idx,
                    "text": getattr(elem, "text", ""),
                    "content_description": getattr(elem, "content_description", ""),
                    "class_name": getattr(elem, "class_name", ""),
                    "bbox": {
                        "x_min": bbox.x_min,
                        "x_max": bbox.x_max,
                        "y_min": bbox.y_min,
                        "y_max": bbox.y_max
                    }
                }
                with open(self._event_debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[找到元素] 索引{idx}，文本：{element_info['text']}\n")
                return element_info

        with open(self._event_debug_log, "a", encoding="utf-8") as f:
            f.write(f"[未找到元素] 坐标({x},{y})\n")
        return None

    def _parse_touch_event(self, line: str) -> Optional[Tuple[str, str, Any]]:
        """解析触摸事件"""
        with open(self._event_debug_log, "a", encoding="utf-8") as f:
            f.write(f"[原始事件] {line}\n")
        parts = line.strip().split()
        if len(parts) < 4:
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[解析失败] 格式不完整\n")
            return None
        try:
            device_id = parts[0].split(':')[0]
            type_part = parts[1]
            code_part = parts[2]
            value_str = parts[3]
            if type_part in ["0003", "EV_ABS"]:
                x_codes = ["0035", "ABS_MT_POSITION_X", "ABS_X"]
                y_codes = ["0036", "ABS_MT_POSITION_Y", "ABS_Y"]
                try:
                    value = int(value_str, 16) if all(c in '0123456789abcdefABCDEF' for c in value_str) else int(
                        value_str)
                except ValueError:
                    value = 0
                    with open(self._event_debug_log, "a", encoding="utf-8") as f:
                        f.write(f"[解析容错] 无法解析{value_str}\n")
                if code_part in x_codes:
                    return (device_id, "X", value)
                elif code_part in y_codes:
                    return (device_id, "Y", value)
            if type_part == "EV_SYN" and code_part == "SYN_REPORT":
                return (device_id, "SYNC", None)
            if type_part == "EV_KEY":
                key_state = "DOWN" if value_str == "DOWN" else "UP"
                return (device_id, "KEY", (code_part, key_state))
            return None
        except Exception as e:
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[解析异常] {str(e)}\n")
            return None

    def _process_keyboard_event(self, device_id: str, key_info: Tuple[str, str]) -> None:
        """处理键盘事件，增加超时自动记录"""
        key_code, key_state = key_info
        if device_id not in self._keyboard_cache:
            self._keyboard_cache[device_id] = {"text": "", "last_input_time": 0.0}

        # 记录最后输入时间
        now = time.time()
        self._keyboard_cache[device_id]["last_input_time"] = now

        if key_code == "KEY_LEFTSHIFT":
            return

        if key_state != "DOWN":
            return

        # 处理退格键
        if key_code == "KEY_BACKSPACE":
            self._keyboard_cache[device_id]["text"] = self._keyboard_cache[device_id]["text"][:-1]
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[键盘输入] 退格后：{self._keyboard_cache[device_id]['text']}\n")
            return

        # 处理字符输入
        char = self._key_mapping.get(key_code, "")
        if char:
            self._keyboard_cache[device_id]["text"] += char
            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                f.write(f"[键盘输入] 当前文本：{self._keyboard_cache[device_id]['text']}\n")

        # 回车键记录
        if key_code == "KEY_ENTER" and self._keyboard_cache[device_id]["text"].strip():
            # 修复：方法名拼写错误，_record_text_input -> record_text_input
            self.record_text_input(self._keyboard_cache[device_id]["text"])
            self._keyboard_cache[device_id]["text"] = ""
            return

        # 超时自动记录
        self._check_input_timeout(device_id)

    def _check_input_timeout(self, device_id: str) -> None:
        """检查输入超时，自动记录文本"""

        def timeout_callback():
            now = time.time()
            cache = self._keyboard_cache.get(device_id, {})
            if (cache.get("text", "").strip() and
                    now - cache.get("last_input_time", 0) > self._input_timeout):
                # 修复：方法名拼写错误
                self.record_text_input(cache["text"])
                self._keyboard_cache[device_id]["text"] = ""
                with open(self._event_debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[超时记录] 自动记录文本：{cache['text']}\n")

        threading.Thread(target=timeout_callback, daemon=True).start()

    def _listen_touch_events(self) -> None:
        """监听触摸事件"""
        if not self._check_adb_connection():
            logging.error("ADB连接失败")
            self._adb_available = False
            return

        process = subprocess.Popen(
            ["adb", "shell", "getevent", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )

        last_event_time = time.time()
        event_count = 0

        with open(self._event_debug_log, "a", encoding="utf-8") as f:
            f.write("=== 开始监听触摸事件 ===\n")

        while self.is_recording and process.poll() is None and self._adb_available:
            try:
                if time.time() - last_event_time > 10:
                    if not self._check_adb_connection():
                        logging.error("ADB连接断开")
                        self._adb_available = False
                        break
                    last_event_time = time.time()

                line = process.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                event_count += 1
                last_event_time = time.time()
                line_str = line.decode('utf-8', errors='replace').strip()

                event_data = self._parse_touch_event(line_str)
                if not event_data:
                    continue

                device_id, event_type, value = event_data

                if event_type == "KEY":
                    self._process_keyboard_event(device_id, value)
                    continue

                with self._lock:
                    if device_id not in self._coord_cache:
                        self._coord_cache[device_id] = {"X": None, "Y": None}

                    if event_type == "X":
                        self._coord_cache[device_id]["X"] = value
                    elif event_type == "Y":
                        self._coord_cache[device_id]["Y"] = value
                    elif event_type == "SYNC":
                        raw_x = self._coord_cache[device_id]["X"]
                        raw_y = self._coord_cache[device_id]["Y"]

                        if raw_x is not None and raw_y is not None:
                            screen_x, screen_y = self._convert_raw_to_screen(raw_x, raw_y)
                            self._update_ui_elements()
                            element_info = self._find_element_by_coords(screen_x, screen_y)
                            self._record_operation(
                                action_type=json_action.CLICK,
                                step_desc=f"点击坐标(原始:({raw_x},{raw_y}) → 屏幕:({screen_x},{screen_y}))",
                                x=screen_x,
                                y=screen_y,
                                raw_x=raw_x,
                                raw_y=raw_y,
                                element=element_info,
                                text_key=self._get_text_key(element_info)
                            )
                            self._coord_cache[device_id] = {"X": None, "Y": None}
                            with open(self._event_debug_log, "a", encoding="utf-8") as f:
                                f.write(f"[记录点击] 屏幕坐标({screen_x},{screen_y})\n")

            except Exception as e:
                with open(self._event_debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[监听异常] {str(e)}\n")
                logging.warning(f"触摸事件监听异常：{str(e)}")
                time.sleep(0.5)

        if process.poll() is None:
            process.terminate()

        with open(self._event_debug_log, "a", encoding="utf-8") as f:
            f.write(f"=== 停止监听触摸事件（共处理{event_count}个事件） ===\n")

    def _get_text_key(self, element_info: Optional[Dict[str, Any]]) -> str:
        if not element_info or not element_info["text"]:
            return f"element_{element_info['index']}" if element_info else "unknown"
        return element_info["text"].lower().replace(" ", "_").replace("-", "_")

    def _record_operation(self, **kwargs) -> None:
        """记录操作"""
        current_time = time.time() - self.start_time
        wait_duration = current_time - self.last_operation_time

        if wait_duration > 1.0 and self.operations:
            self.operations.append({
                "action_type": "WAIT",
                "step_desc": f"等待{round(wait_duration, 2)}秒",
                "duration": round(wait_duration, 2),
                "timestamp": self.last_operation_time
            })

        operation = {
            "timestamp": current_time, **kwargs
        }
        self.operations.append(operation)
        self.last_operation_time = current_time
        self._save_to_json()
        logging.info(f"记录操作：{operation['step_desc']}")

    def _save_to_json(self) -> None:
        try:
            with open(self.output_json, "w", encoding="utf-8") as f:
                json.dump(self.operations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存JSON失败：{str(e)}")

    def record_text_input(self, text: str) -> None:
        if not self.is_recording or not text.strip():
            return
        self._record_operation(
            action_type=json_action.INPUT_TEXT,
            step_desc=f"输入文本{text}",
            text=text.strip()
        )

    def _check_adb_connection(self) -> bool:
        try:
            result = subprocess.run(
                ["adb", "shell", "echo", "adb_check"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2,
                text=True
            )
            return result.returncode == 0 and "adb_check" in result.stdout
        except Exception:
            return False

    def start_recording(self) -> None:
        if self.is_recording:
            logging.warning("已在录制中")
            return

        if os.path.exists(self._event_debug_log):
            os.remove(self._event_debug_log)

        self.is_recording = True
        self._adb_available = True
        self._coord_cache = {}
        self._keyboard_cache = {}
        self.start_time = time.time()
        self.last_operation_time = 0.0
        self.operations = []
        self._update_ui_elements()  # 初始化UI元素

        self.event_thread = threading.Thread(target=self._listen_touch_events, daemon=True)
        self.event_thread.start()

        time.sleep(1)
        if not self.event_thread.is_alive():
            logging.error("触摸事件监听线程启动失败")
            return

        logging.info("=== 开始实时录制 ===")
        print("=== 开始实时录制 ===")
        logging.info("1. 在设备上进行操作（点击、输入等）")
        logging.info("2. 文本输入会自动记录（回车或超时1秒）")
        logging.info("3. 输入'q'并按回车停止录制")
        logging.info(f"调试日志已开启：{self._event_debug_log}")

        while self.is_recording:
            user_input = input("> ").strip()
            if user_input.lower() == "q":
                self.stop_recording()

    def stop_recording(self) -> None:
        if not self.is_recording:
            return

        # 停止前检查未记录的文本输入
        for device_id, cache in self._keyboard_cache.items():
            if cache.get("text", "").strip():
                # 修复：方法名拼写错误
                self.record_text_input(cache["text"])
                with open(self._event_debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[停止时记录] 剩余文本：{cache['text']}")

        self.is_recording = False
        if self.event_thread and self.event_thread.is_alive():
            self.event_thread.join(timeout=2.0)

        logging.info(f"\n=== 录制结束 ===")
        logging.info(f"共记录{len(self.operations)}个操作，已保存至{self.output_json}")
        logging.info(f"详细事件日志：{self._event_debug_log}")


def main(env: AsyncAndroidEnv,output_json:str):
    recorder = RealTimeOperationRecorder(env,output_json=output_json)
    recorder.start_recording()


if __name__ == "__main__":
    from android_world.env import env_launcher
    parser = argparse.ArgumentParser(description="实时操作记录工具")
    parser.add_argument(
        "--output",
        type=str,
        default="real_time_operations.json",
        help = "指定输入的json文件名"
    )
    args = parser.parse_args() #解析命令行参数
    env = env_launcher.load_and_setup_env(
        console_port=5554,
        emulator_setup=False,
        adb_path="C:\\Users\\dell\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe"
    )
    main(env,output_json=args.output)
    env.close()

