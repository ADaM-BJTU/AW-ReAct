import os
import time
from typing import Tuple, Optional, List

from absl import logging
from android_world.env.interface import AsyncAndroidEnv, State
from android_world.env import actuation, representation_utils
from android_world.env import json_action
from android_world.env import android_world_controller


def split_filename(filename: str):
    """
    分离文件名与后缀。
    输入: 'adipiscing_fair_jelly_final.png'
    返回: ('adipiscing_fair_jelly_final', '.png')
    """
    name, ext = os.path.splitext(filename)
    return name, ext

class DrawInitSteps:
    """
    初始化步骤类：实现打开Files APP，进入指定目录，创建诱饵文件并删除。
    适配依据：
    1. interface.py中AsyncAndroidEnv及controller相关接口
    2. actuation.py中动作执行相关函数
    3. json_action.py中动作定义常量
    """

    def __init__(self):
        # 兜底屏幕尺寸（默认）
        self._default_screen_size = (1080, 2400)

    def _get_valid_controller(self, env: AsyncAndroidEnv) -> android_world_controller.AndroidWorldController:
        if not hasattr(env, "controller"):
            raise RuntimeError("AsyncAndroidEnv缺少controller属性")
        controller = env.controller
        if not isinstance(controller, android_world_controller.AndroidWorldController):
            raise RuntimeError(
                f"controller类型错误：需为AndroidWorldController，实际为{type(controller).__name__}"
            )
        return controller

    def _get_screen_size(self, env: AsyncAndroidEnv) -> Tuple[int, int]:
        try:
            return env.logical_screen_size
        except AttributeError:
            logging.warning("未找到logical_screen_size属性，尝试device_screen_size")
        try:
            return env.device_screen_size
        except AttributeError:
            logging.warning(f"未找到device_screen_size属性，使用默认尺寸{self._default_screen_size}")
            return self._default_screen_size

    def _get_stable_ui_elements(self, env: AsyncAndroidEnv) -> List[representation_utils.UIElement]:
        try:
            state: State = env.get_state(wait_to_stabilize=True)
        except AttributeError as e:
            raise RuntimeError(f"❌ 调用get_state()失败：{str(e)}") from e

        ui_elements = state.ui_elements
        if not isinstance(ui_elements, list):
            raise RuntimeError(f"❌ ui_elements类型错误：需为list，实际为{type(ui_elements).__name__}")

        print("\n" + "=" * 80)
        print("📋 当前屏幕UI元素列表：")
        for idx, elem in enumerate(ui_elements):
            text = getattr(elem, "text", None)
            cls = getattr(elem, "class_name", None)
            cont = getattr(elem, "content_description", False)
            bounds = getattr(elem, "bbox_pixels", None)
            print(f"  [{idx:2d}] text={text}|class={cls}|cont={cont}|bounds={bounds}")
            # print(elem)
        print("=" * 80 + "\n")

        return ui_elements

    def _click_element_by_text(
            self,
            env: AsyncAndroidEnv,
            target_texts: List[str],
            step_desc: str,
            fallback_index: Optional[int] = None
    ) -> None:
        """
        根据文本点击UI元素，文本匹配失败则用索引兜底点击
        """
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        for text in target_texts:
            try:
                actuation.find_and_click_element(
                    element_text=text,
                    env=controller,
                    case_sensitive=False
                )
                logging.info(f"✅ {step_desc}：成功匹配文本「{text}」")
                time.sleep(2)
                return
            except ValueError:
                continue

        if fallback_index is None:
            raise RuntimeError(f"❌ {step_desc}：文本匹配失败且无兜底索引")

        ui_elements = self._get_stable_ui_elements(env)
        if not (0 <= fallback_index < len(ui_elements)):
            raise IndexError(f"兜底索引{fallback_index}无效，UI元素数：{len(ui_elements)}")

        click_action = json_action.JSONAction(
            action_type=json_action.CLICK,
            index=fallback_index
        )
        actuation.execute_adb_action(
            action=click_action,
            screen_elements=ui_elements,
            screen_size=screen_size,
            env=controller
        )
        logging.warning(f"⚠️ {step_desc}：文本匹配失败，使用索引{fallback_index}点击")
        time.sleep(2)

    #根据content字段进行匹配
    def _click_element_by_content_description(
            self,
            env: AsyncAndroidEnv,
            target_descs: List[str],
            step_desc: str,
            fallback_index: Optional[int] = None
    ) -> None:
        """
        根据 content_description 匹配并点击 UI 元素。
        匹配失败时，可使用 fallback_index 兜底点击。
        """

        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        ui_elements = self._get_stable_ui_elements(env)

        # 遍历所有目标 content_description
        for target in target_descs:
            for idx, elem in enumerate(ui_elements):
                desc = getattr(elem, "content_description", False)
                if desc and target.lower() in desc.lower():
                    # 找到元素，点击
                    click_action = json_action.JSONAction(
                        action_type=json_action.CLICK,
                        index=idx
                    )
                    actuation.execute_adb_action(
                        action=click_action,
                        screen_elements=ui_elements,
                        screen_size=screen_size,
                        env=controller
                    )
                    logging.info(f"✅ {step_desc}：成功点击 content_description 包含「{target}」的元素(idx={idx})")
                    time.sleep(1.5)
                    return

        # 如果这里还没 return → 匹配失败
            raise RuntimeError(f"❌ {step_desc}：未找到匹配 content_description 的元素")
        #
        # # 兜底点击
        # if not (0 <= fallback_index < len(ui_elements)):
        #     raise IndexError(f"兜底索引{fallback_index}无效，总元素数：{len(ui_elements)}")
        #
        # fallback_action = json_action.JSONAction(
        #     action_type=json_action.CLICK,
        #     index=fallback_index
        # )
        # actuation.execute_adb_action(
        #     action=fallback_action,
        #     screen_elements=ui_elements,
        #     screen_size=screen_size,
        #     env=controller
        # )
        # logging.warning(f"⚠️ {step_desc}：content_description 未命中，使用兜底 index={fallback_index}")
        # time.sleep(1.5)

    def _input_text(self, env: AsyncAndroidEnv, text: str, step_desc: str) -> None:
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        input_action = json_action.JSONAction(
            action_type=json_action.INPUT_TEXT,
            text=text,
            clear_text=True,
        )
        actuation.execute_adb_action(
            action=input_action,
            screen_elements=self._get_stable_ui_elements(env),
            screen_size=screen_size,
            env=controller
        )
        logging.info(f"✅ {step_desc}：输入文本「{text}」")
        time.sleep(1)

    def _long_press_element(self, env: AsyncAndroidEnv, index: int, step_desc: str) -> None:
        """
        长按指定索引的UI元素，触发上下文菜单（如文件操作菜单）
        """
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)
        ui_elements = self._get_stable_ui_elements(env)
        if not (0 <= index < len(ui_elements)):
            raise IndexError(f"长按索引{index}无效，UI元素数：{len(ui_elements)}")

        long_press_action = json_action.JSONAction(
            action_type=json_action.LONG_PRESS,
            index=index
        )
        actuation.execute_adb_action(
            action=long_press_action,
            screen_elements=ui_elements,
            screen_size=screen_size,
            env=controller
        )
        logging.info(f"✅ {step_desc}：长按索引{index}")
        time.sleep(2)

    import os



    def run(self, env: AsyncAndroidEnv,file_name:str):

        # 用传入的参数覆盖类属性
        self.file_name = file_name

        # 确保env合法
        if not isinstance(env, AsyncAndroidEnv):
            raise RuntimeError(f"env类型错误：需为AsyncAndroidEnv，实际为{type(env).__name__}")

        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        # 1. 打开simple draw pro APP
        logging.info("📱 步骤1/6：打开simple draw proAPP")
        open_files_action = json_action.JSONAction(
            action_type=json_action.OPEN_APP,
            app_name="simple draw pro"
        )
        actuation.execute_adb_action(
            action=open_files_action,
            screen_elements=self._get_stable_ui_elements(env),
            screen_size=screen_size,
            env=controller
        )
        time.sleep(6)

        #2.打开playlist按钮
        self._click_element_by_content_description(
            env=env,
            target_descs=["Save"],
            step_desc="点击保存按钮",
            fallback_index=0
        )
        name,ext = split_filename(self.file_name)
        time.sleep(3)
        #4.点击 对应的文件类型
        self._click_element_by_text(
            env=env,
            target_texts=[ext],
            step_desc="点击文件类型按钮",
            fallback_index=4
        )
        time.sleep(3)
        #5.输入文件名
        self._input_text(env, name, "输入文件名")
        time.sleep(3)
        #6.点击ok
        self._click_element_by_text(
            env=env,
            target_texts=["OK"],
            step_desc="点击保存按钮",
            fallback_index=3
        )
        time.sleep(3)
        #上一级按钮
        self._click_element_by_text(
            env=env,
            target_texts=["sdk_gphone64_x86_64"],
            step_desc="点击sdk_gphone64_x86_64按钮",
            fallback_index=3
        )
        time.sleep(3)
        #8.点击保存
        self._click_element_by_text(
            env=env,
            target_texts=["SAVE"],
            step_desc="点击保存按钮",
            fallback_index=8
        )
        return {
        }

