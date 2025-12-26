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
    自动生成自: real_time_operations.json
    总操作步骤: 11
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

        # 步骤 1/11：click
        # 无有效元素索引，直接使用坐标点击
        self._click_by_coords(
            env=env,
            x=318,
            y=2249,
            step_desc="点击坐标(原始:(9678,30719) → 屏幕:(318,2249))"
        )

        # 步骤 2/11：WAIT
        logging.info("⌛ 等待6.01秒")
        time.sleep(6.01)

        # 步骤 3/11：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=1,
                step_desc="点击坐标(原始:(11286,2962) → 屏幕:(371,216))"
            )
        except IndexError:
            logging.warning(f"元素索引1无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=371,
                y=216,
                step_desc="点击坐标(原始:(11286,2962) → 屏幕:(371,216))（索引无效，坐标兜底）"
            )

        # 步骤 4/11：WAIT
        logging.info("⌛ 等待2.11秒")
        time.sleep(2.11)

        # 步骤 5/11：input_text
        self._input_text(
            env=env,
            text="audio recorder",
            step_desc="输入文本「audio recorder」"
        )

        # 步骤 6/11：WAIT
        logging.info("⌛ 等待14.23秒")
        time.sleep(14.23)

        # 步骤 7/11：click
        # 无有效元素索引，直接使用坐标点击
        self._click_by_coords(
            env=env,
            x=170,
            y=432,
            step_desc="点击坐标(原始:(5188,5911) → 屏幕:(170,432))"
        )

        # 步骤 8/11：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=12,
                step_desc="点击坐标(原始:(16656,29667) → 屏幕:(548,2172))"
            )
        except IndexError:
            logging.warning(f"元素索引12无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=548,
                y=2172,
                step_desc="点击坐标(原始:(16656,29667) → 屏幕:(548,2172))（索引无效，坐标兜底）"
            )

        # 步骤 9/11：WAIT
        logging.info("⌛ 等待10.95秒")
        time.sleep(10.95)

        # 步骤 10/11：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=40,
                step_desc="点击坐标(原始:(22330,29872) → 屏幕:(735,2187))"
            )
        except IndexError:
            logging.warning(f"元素索引40无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=735,
                y=2187,
                step_desc="点击坐标(原始:(22330,29872) → 屏幕:(735,2187))（索引无效，坐标兜底）"
            )

        # 步骤 11/11：input_text
        self._input_text(
            env=env,
            text="ccc",
            step_desc="输入文本「ccc」"
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
