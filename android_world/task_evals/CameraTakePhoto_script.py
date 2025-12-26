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
    自动生成自: CameraTakePhoto.json
    总操作步骤: 12
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
        # -------------------------- 步骤1：初始化校验（确保env类型正确） --------------------------
        if not isinstance(env, AsyncAndroidEnv):
            raise RuntimeError(
                f"env类型错误：需为AsyncAndroidEnv，实际为{type(env).__name__}"
                "\n（参考interface.py第128行：AsyncAndroidEnv类定义）"
            )
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)
        logging.info("✅ 初始化校验完成：env为有效AsyncAndroidEnv实例")

        # -------------------------- 步骤2：打开Camera APP --------------------------
        logging.info("📱 步骤1/11：打开Camera APP")
        open_app_action = json_action.JSONAction(
            action_type=json_action.OPEN_APP,  # 参考json_action.py第38行：OPEN_APP常量定义
            app_name="camera"
        )
        # 2. 执行打开APP动作
        actuation.execute_adb_action(
            action=open_app_action,
            screen_elements=self._get_stable_ui_elements(env),
            screen_size=screen_size,
            env=controller
        )
        time.sleep(3)  # 等待APP冷启动（避免后续操作找不到元素）
        logging.info("✅ 步骤1/11：APP打开完成")

        # 步骤 7/12：WAIT
        logging.info("⌛ 等待4.86秒")
        time.sleep(4.86)

        # 步骤 8/12：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=0,
                step_desc="点击坐标(原始:(3033,2839) → 屏幕:(99,207))"
            )
        except IndexError:
            logging.warning(f"元素索引0无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=99,
                y=207,
                step_desc="点击坐标(原始:(3033,2839) → 屏幕:(99,207))（索引无效，坐标兜底）"
            )

        # 步骤 9/12：WAIT
        logging.info("⌛ 等待2.71秒")
        time.sleep(2.71)

        # 步骤 10/12：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=0,
                step_desc="点击坐标(原始:(3944,18499) → 屏幕:(129,1354))"
            )
        except IndexError:
            logging.warning(f"元素索引0无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=129,
                y=1354,
                step_desc="点击坐标(原始:(3944,18499) → 屏幕:(129,1354))（索引无效，坐标兜底）"
            )

        # 步骤 11/12：WAIT
        logging.info("⌛ 等待1.18秒")
        time.sleep(1.18)

        # 步骤 12/12：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=0,
                step_desc="点击坐标(原始:(15958,30118) → 屏幕:(525,2205))"
            )
        except IndexError:
            logging.warning(f"元素索引0无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=525,
                y=2205,
                step_desc="点击坐标(原始:(15958,30118) → 屏幕:(525,2205))（索引无效，坐标兜底）"
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
