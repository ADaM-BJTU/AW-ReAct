import json
import os
from typing import List, Dict, Any


class JsonToScriptGenerator:
    """
    根据任务JSON文件生成对应的操作脚本代码
    优先使用element.index点击，索引无效或无element时自动切换为坐标点击
    """

    def __init__(self, json_file_path: str, output_script_path: str = None):
        self.json_file_path = json_file_path
        self.operations = self._load_and_validate_json()

        # 设置输出路径
        if output_script_path is None:
            json_dir = os.path.dirname(json_file_path)
            json_name = os.path.splitext(os.path.basename(json_file_path))[0]
            self.output_script_path = os.path.join(json_dir, f"{json_name}_script.py")
        else:
            self.output_script_path = output_script_path

    def _load_and_validate_json(self) -> List[Dict[str, Any]]:
        """加载并验证JSON文件格式"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                operations = json.load(f)
        except Exception as e:
            raise RuntimeError(f"加载JSON文件失败: {str(e)}")

        if not isinstance(operations, list):
            raise ValueError("JSON文件根节点必须是一个列表")

        for i, op in enumerate(operations):
            if not isinstance(op, dict) or "action_type" not in op:
                raise ValueError(f"JSON中第{i}个元素必须是包含action_type的字典")

        return operations

    def _generate_step_code(self) -> str:
        """根据JSON操作生成步骤代码，实现索引优先+坐标兜底逻辑"""
        step_code = []
        step_code.append("        # 主流程：根据JSON操作序列执行")
        step_code.append("        if not isinstance(env, AsyncAndroidEnv):")
        step_code.append("            raise RuntimeError(f\"env需为AsyncAndroidEnv，实际为{type(env).__name__}\")")
        step_code.append("        logging.info(\"✅ 初始化完成，开始执行操作序列\")")
        step_code.append("")

        for i, op in enumerate(self.operations):
            action_type = op["action_type"]
            step_num = i + 1
            total_steps = len(self.operations)

            # 添加步骤分隔注释
            step_code.append(f"        # 步骤 {step_num}/{total_steps}：{action_type}")

            if action_type.lower() == "click":
                # 处理点击操作：优先索引，失败则坐标兜底
                element = op.get("element")  # 获取element（可能为None）
                x = op.get("x")
                y = op.get("y")
                step_desc = op.get("step_desc", f"点击坐标({x},{y})")

                # 提取索引（如果存在）
                index = element.get("index") if (isinstance(element, dict) and element) else None

                if index is not None:
                    # 生成索引点击代码，并添加try-except捕获索引无效错误
                    step_code.append(f"        # 优先尝试元素索引点击")
                    step_code.append(f"        try:")
                    step_code.append(f"            self._click_by_index(")
                    step_code.append(f"                env=env,")
                    step_code.append(f"                index={index},")
                    step_code.append(f"                step_desc=\"{step_desc}\"")
                    step_code.append(f"            )")
                    step_code.append(f"        except IndexError:")
                    step_code.append(f"            logging.warning(f\"元素索引{index}无效，切换为坐标点击\")")
                    # 索引无效时自动调用坐标点击
                    step_code.append(f"            self._click_by_coords(")
                    step_code.append(f"                env=env,")
                    step_code.append(f"                x={x},")
                    step_code.append(f"                y={y},")
                    step_code.append(f"                step_desc=\"{step_desc}（索引无效，坐标兜底）\"")
                    step_code.append(f"            )")
                else:
                    # 无索引时直接使用坐标点击
                    step_code.append(f"        # 无有效元素索引，直接使用坐标点击")
                    step_code.append(f"        self._click_by_coords(")
                    step_code.append(f"            env=env,")
                    step_code.append(f"            x={x},")
                    step_code.append(f"            y={y},")
                    step_code.append(f"            step_desc=\"{step_desc}\"")
                    step_code.append(f"        )")

            elif action_type.lower() == "input_text":
                # 处理输入文本操作：转义特殊字符
                text = op.get("text", "")
                escaped_text = text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
                step_desc = op.get("step_desc", f"输入文本{text}")
                # 转义步骤描述中的特殊字符
                escaped_step_desc = step_desc.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
                step_code.append(f"        self._input_text(")
                step_code.append(f"            env=env,")
                step_code.append(f"            text=\"{escaped_text}\",")
                step_code.append(f"            step_desc=\"{escaped_step_desc}\"")
                step_code.append(f"        )")

            elif action_type.upper() == "WAIT":
                # 处理等待操作
                duration = op.get("duration", 0)
                step_desc = op.get("step_desc", f"等待{duration}秒")

                step_code.append(f"        logging.info(\"⌛ {step_desc}\")")
                step_code.append(f"        time.sleep({duration})")

            else:
                # 处理未知操作类型
                step_code.append(f"        # 警告：不支持的操作类型 {action_type}")
                step_code.append(f"        logging.warning(\"⚠️ 不支持的操作类型：{action_type}\")")

            step_code.append("")  # 步骤间空行

        step_code.append("        logging.info(\"🎉 所有操作执行完成\")")
        return "\n".join(step_code)

    def generate_script(self) -> None:
        """生成完整的脚本代码并写入文件"""
        # 基础框架代码
        base_template = f"""import time
from typing import Tuple, Optional, List

from absl import logging
from android_world.env.interface import AsyncAndroidEnv, State  # 仅导入真实存在的类
from android_world.env import actuation, representation_utils  # 复用动作执行逻辑
from android_world.env import json_action  # 复用动作定义
from android_world.env import android_world_controller  # 控制器类型定义


class TaskOperationExecutor:
    \"\"\"
    根据JSON操作记录生成的执行脚本
    自动生成自: {os.path.basename(self.json_file_path)}
    总操作步骤: {len(self.operations)}
    \"\"\"

    def __init__(self):
        # 兜底屏幕尺寸
        self._default_screen_size = (1080, 2400)

    def _get_valid_controller(self, env: AsyncAndroidEnv) -> android_world_controller.AndroidWorldController:
        \"\"\"获取有效控制器，确保ADB操作载体正确\"\"\"
        if not hasattr(env, "controller"):
            raise RuntimeError("AsyncAndroidEnv缺少controller属性")
        controller = env.controller
        if not isinstance(controller, android_world_controller.AndroidWorldController):
            raise RuntimeError(
                f"controller类型错误：需为AndroidWorldController，实际为{{type(controller).__name__}}"
            )
        return controller

    def _get_screen_size(self, env: AsyncAndroidEnv) -> Tuple[int, int]:
        \"\"\"获取屏幕尺寸，优先逻辑尺寸，次选物理尺寸，最后兜底\"\"\"
        try:
            return env.logical_screen_size
        except AttributeError:
            logging.warning("未找到logical_screen_size，尝试device_screen_size")
        try:
            return env.device_screen_size
        except AttributeError:
            logging.warning(f"使用默认屏幕尺寸{{self._default_screen_size}}")
            return self._default_screen_size

    def _get_stable_ui_elements(self, env: AsyncAndroidEnv) -> List[representation_utils.UIElement]:
        \"\"\"获取稳定的UI元素列表，确保操作目标存在\"\"\"
        try:
            state: State = env.get_state(wait_to_stabilize=True)
        except AttributeError as e:
            raise RuntimeError(f"获取界面状态失败：{{str(e)}}") from e
        ui_elements = state.ui_elements
        if not isinstance(ui_elements, list):
            raise RuntimeError(f"ui_elements需为list，实际为{{type(ui_elements).__name__}}")
        return ui_elements

    def _click_by_index(
            self,
            env: AsyncAndroidEnv,
            index: int,
            step_desc: str
    ) -> None:
        \"\"\"通过元素索引执行点击动作（优先使用）\"\"\"
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)
        ui_elements = self._get_stable_ui_elements(env)

        # 校验索引有效性（无效时会抛出IndexError）
        if not (0 <= index < len(ui_elements)):
            raise IndexError(
                f"元素索引{{index}}无效：当前UI元素共{{len(ui_elements)}}个"
            )

        # 创建点击动作并执行
        click_action = json_action.JSONAction(
            action_type=json_action.CLICK,
            index=index
        )
        actuation.execute_adb_action(
            action=click_action,
            screen_elements=ui_elements,
            screen_size=screen_size,
            env=controller
        )
        logging.info(f"✅ 执行点击：{{step_desc}}（元素索引{{index}}）")
        time.sleep(1.5)  # 等待界面响应

    def _click_by_coords(
            self,
            env: AsyncAndroidEnv,
            x: int,
            y: int,
            step_desc: str
    ) -> None:
        \"\"\"通过坐标执行点击动作（索引无效或无element时使用）\"\"\"
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        # 创建坐标点击动作并执行
        click_action = json_action.JSONAction(
            action_type=json_action.CLICK,
            x=x,
            y=y
        )
        actuation.execute_adb_action(
            action=click_action,
            screen_elements=self._get_stable_ui_elements(env),
            screen_size=screen_size,
            env=controller
        )
        logging.info(f"✅ 执行点击：{{step_desc}}（坐标点击）")
        time.sleep(1.5)  # 等待界面响应

    def _input_text(
            self,
            env: AsyncAndroidEnv,
            text: str,
            step_desc: str
    ) -> None:
        \"\"\"执行文本输入动作\"\"\"
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)
        ui_elements = self._get_stable_ui_elements(env)

        # 创建输入动作并执行
        input_action = json_action.JSONAction(
            action_type=json_action.INPUT_TEXT,
            text=text,
            clear_text=True  # 输入前清空现有内容
        )
        actuation.execute_adb_action(
            action=input_action,
            screen_elements=ui_elements,
            screen_size=screen_size,
            env=controller
        )
        logging.info(f"✅ 执行输入：{{step_desc}}（文本「{{text}}」）")
        time.sleep(1)  # 等待输入完成

    def run_operations(self, env: AsyncAndroidEnv) -> None:
{self._generate_step_code()}


# 使用示例
if __name__ == "__main__":
    # 加载环境
    from android_world.env import env_launcher

    env = env_launcher.load_and_setup_env(
        console_port=5554,
        emulator_setup=False,
        adb_path="C:\\\\Users\\\\dell\\\\AppData\\\\Local\\\\Android\\\\Sdk\\\\platform-tools\\\\adb.exe"
    )

    # 执行操作
    executor = TaskOperationExecutor()
    try:
        executor.run_operations(env)
    finally:
        env.close()
"""

        # 写入生成的代码到文件
        with open(self.output_script_path, 'w', encoding='utf-8') as f:
            f.write(base_template)

        print(f"✅ 脚本已生成：{self.output_script_path}")


# 使用示例
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法：python json_script_generator.py <json文件路径> [输出脚本路径]")
        print("示例：python json_script_generator.py operations.json")
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    generator = JsonToScriptGenerator(json_path, output_path)
    generator.generate_script()