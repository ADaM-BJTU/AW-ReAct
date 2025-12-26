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
    自动生成自: ContactsAddContact.json
    总操作步骤: 14
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

        # 步骤 1/14：click
        # 无有效元素索引，直接使用坐标点击
        self._click_by_coords(
            env=env,
            x=513,
            y=2228,
            step_desc="点击坐标(原始:(15594,30432) → 屏幕:(513,2228))"
        )

        # 步骤 2/14：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=1,
                step_desc="点击坐标(原始:(8859,3003) → 屏幕:(291,219))"
            )
        except IndexError:
            logging.warning(f"元素索引1无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=291,
                y=219,
                step_desc="点击坐标(原始:(8859,3003) → 屏幕:(291,219))（索引无效，坐标兜底）"
            )

        # 步骤 3/14：WAIT
        logging.info("⌛ 等待4.49秒")
        time.sleep(4.49)

        # 步骤 4/14：input_text
        self._input_text(
            env=env,
            text="contact",
            step_desc="输入文本contact\n"
        )

        # 步骤 5/14：WAIT
        logging.info("⌛ 等待3.56秒")
        time.sleep(3.56)

        # 步骤 6/14：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=3,
                step_desc="点击坐标(原始:(5552,5911) → 屏幕:(182,432))"
            )
        except IndexError:
            logging.warning(f"元素索引3无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=182,
                y=432,
                step_desc="点击坐标(原始:(5552,5911) → 屏幕:(182,432))（索引无效，坐标兜底）"
            )

        # 步骤 7/14：WAIT
        logging.info("⌛ 等待6.93秒")
        time.sleep(6.93)

        # 步骤 8/14：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=0,
                step_desc="点击坐标(原始:(28610,27578) → 屏幕:(942,2019))"
            )
        except IndexError:
            logging.warning(f"元素索引0无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=942,
                y=2019,
                step_desc="点击坐标(原始:(28610,27578) → 屏幕:(942,2019))（索引无效，坐标兜底）"
            )

        # 步骤 9/14：WAIT
        logging.info("⌛ 等待3.55秒")
        time.sleep(3.55)

        # 步骤 10/14：click
        # 优先尝试元素索引点击
        try:
            self._click_by_index(
                env=env,
                index=4,
                step_desc="点击坐标(原始:(12469,11796) → 屏幕:(410,863))"
            )
        except IndexError:
            logging.warning(f"元素索引4无效，切换为坐标点击")
            self._click_by_coords(
                env=env,
                x=410,
                y=863,
                step_desc="点击坐标(原始:(12469,11796) → 屏幕:(410,863))（索引无效，坐标兜底）"
            )

        # 步骤 11/14：WAIT
        logging.info("⌛ 等待2.29秒")
        time.sleep(2.29)

        # 步骤 12/14：input_text
        self._input_text(
            env=env,
            text="123",
            step_desc="输入文本123\n"
        )

        # 步骤 13/14：WAIT
        logging.info("⌛ 等待2.98秒")
        time.sleep(2.98)

        # 步骤 14/14：input_text
        self._input_text(
            env=env,
            text="456",
            step_desc="输入文本456\n"
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
