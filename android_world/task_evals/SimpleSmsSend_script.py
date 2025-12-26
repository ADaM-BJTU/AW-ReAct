import time
from typing import Tuple, Optional, List

from absl import logging
from android_world.env.interface import AsyncAndroidEnv, State  # 仅导入真实存在的类
from android_world.env import actuation, representation_utils  # 复用动作执行逻辑
from android_world.env import json_action  # 复用动作定义
from android_world.env import android_world_controller  # 控制器类型定义


class TaskOperationExecutor:
    """
    根据JSON操作记录生成的执行脚本
    自动生成自: SimpleSmsSend.json
    总操作步骤: 9
    """

    def __init__(self):
        # 兜底屏幕尺寸
        self._default_screen_size = (1080, 2400)

    def _get_valid_controller(self, env: AsyncAndroidEnv) -> android_world_controller.AndroidWorldController:
        """获取有效控制器，确保ADB操作载体正确"""
        if not hasattr(env, "controller"):
            raise RuntimeError("AsyncAndroidEnv缺少controller属性")
        controller = env.controller
        if not isinstance(controller, android_world_controller.AndroidWorldController):
            raise RuntimeError(
                f"controller类型错误：需为AndroidWorldController，实际为{type(controller).__name__}"
            )
        return controller

    def _get_screen_size(self, env: AsyncAndroidEnv) -> Tuple[int, int]:
        """获取屏幕尺寸，优先逻辑尺寸，次选物理尺寸，最后兜底"""
        try:
            return env.logical_screen_size
        except AttributeError:
            logging.warning("未找到logical_screen_size，尝试device_screen_size")
        try:
            return env.device_screen_size
        except AttributeError:
            logging.warning(f"使用默认屏幕尺寸{self._default_screen_size}")
            return self._default_screen_size

    def _get_stable_ui_elements(self, env: AsyncAndroidEnv) -> List[representation_utils.UIElement]:
        """获取稳定的UI元素列表，确保操作目标存在"""
        try:
            state: State = env.get_state(wait_to_stabilize=True)
        except AttributeError as e:
            raise RuntimeError(f"获取界面状态失败：{str(e)}") from e
        ui_elements = state.ui_elements
        if not isinstance(ui_elements, list):
            raise RuntimeError(f"ui_elements需为list，实际为{type(ui_elements).__name__}")
        return ui_elements

    def _click_by_index(
            self,
            env: AsyncAndroidEnv,
            index: int,
            step_desc: str
    ) -> None:
        """通过元素索引执行点击动作（优先使用）"""
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)
        ui_elements = self._get_stable_ui_elements(env)

        # 校验索引有效性（无效时会抛出IndexError）
        if not (0 <= index < len(ui_elements)):
            raise IndexError(
                f"元素索引{index}无效：当前UI元素共{len(ui_elements)}个"
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
        logging.info(f"✅ 执行点击：{step_desc}（元素索引{index}）")
        time.sleep(1.5)  # 等待界面响应

    def _click_by_coords(
            self,
            env: AsyncAndroidEnv,
            x: int,
            y: int,
            step_desc: str
    ) -> None:
        """通过坐标执行点击动作（索引无效或无element时使用）"""
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
        logging.info(f"✅ 执行点击：{step_desc}（坐标点击）")
        time.sleep(1.5)  # 等待界面响应

    def _input_text(
            self,
            env: AsyncAndroidEnv,
            text: str,
            step_desc: str
    ) -> None:
        """执行文本输入动作"""
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
        logging.info(f"✅ 执行输入：{step_desc}（文本「{text}」）")
        time.sleep(1)  # 等待输入完成

    def run_operations(self, env: AsyncAndroidEnv) -> None:
        # 主流程：根据JSON操作序列执行
        if not isinstance(env, AsyncAndroidEnv):
            raise RuntimeError(f"env需为AsyncAndroidEnv，实际为{type(env).__name__}")
        logging.info("✅ 初始化完成，开始执行操作序列")

        # 步骤 1/9：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=52,
                step_desc="点击坐标(原始:(11104,29667) → 屏幕:(365,2172))"
            )
        except IndexError:
            logging.warning(f"元素索引52无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=365,
                y=2172,
                step_desc="点击坐标(原始:(11104,29667) → 屏幕:(365,2172))（索引无效，坐标兜底）"
            )

        # 步骤 2/9：input_text
        self._input_text(
            env=env,
            text="sms",
            step_desc="输入文本sms\n"
        )

        # 步骤 3/9：click
        # 无有效元素索引，直接使用坐标点击
        self._click_by_coords(
            env=env,
            x=436,
            y=438,
            step_desc="点击坐标(原始:(13258,5993) → 屏幕:(436,438))"
        )

        # 步骤 4/9：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=3,
                step_desc="点击坐标(原始:(4915,6075) → 屏幕:(161,444))"
            )
        except IndexError:
            logging.warning(f"元素索引3无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=161,
                y=444,
                step_desc="点击坐标(原始:(4915,6075) → 屏幕:(161,444))（索引无效，坐标兜底）"
            )

        # 步骤 5/9：WAIT
        logging.info("⌛ 等待8.23秒")
        time.sleep(8.23)

        # 步骤 6/9：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=50,
                step_desc="点击坐标(原始:(29126,30282) → 屏幕:(959,2217))"
            )
        except IndexError:
            logging.warning(f"元素索引50无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=959,
                y=2217,
                step_desc="点击坐标(原始:(29126,30282) → 屏幕:(959,2217))（索引无效，坐标兜底）"
            )

        # 步骤 7/9：WAIT
        logging.info("⌛ 等待1.67秒")
        time.sleep(1.67)

        # 步骤 8/9：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=2,
                step_desc="点击坐标(原始:(10922,4655) → 屏幕:(359,340))"
            )
        except IndexError:
            logging.warning(f"元素索引2无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=359,
                y=340,
                step_desc="点击坐标(原始:(10922,4655) → 屏幕:(359,340))（索引无效，坐标兜底）"
            )

        # 步骤 9/9：input_text
        self._input_text(
            env=env,
            text="193840583",
            step_desc="输入文本193840583\n"
        )

        logging.info("🎉 所有操作执行完成")


# 使用示例
if __name__ == "__main__":
    # 加载环境
    from android_world.env import env_launcher

    env = env_launcher.load_and_setup_env(
        console_port=5554,
        emulator_setup=False,
        adb_path="C:\\Users\\dell\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe"
    )

    # 执行操作
    executor = TaskOperationExecutor()
    try:
        executor.run_operations(env)
    finally:
        env.close()
