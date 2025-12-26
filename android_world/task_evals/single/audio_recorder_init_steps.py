import time
from typing import Tuple, Optional, List

from absl import logging
from android_world.env.interface import AsyncAndroidEnv, State
from android_world.env import actuation, representation_utils
from android_world.env import json_action
from android_world.env import android_world_controller

def _inject_microphone_error_popup(self, env: AsyncAndroidEnv):
    """在录音阶段插入‘麦克风忙’提示弹窗。"""
    try:
        state: State = env.get_state(wait_to_stabilize=True)
        popup = representation_utils.UIElement(
            text="popup:Microphone is busy",
            class_name="android.widget.TextView",
            bounds=(200, 800, 880, 1000),
            visible=True,
        )
        fake_close = representation_utils.UIElement(
            text="Popup Close Button",
            class_name="android.widget.Button",
            bounds=(500, 1050, 650, 1150),
            visible=True,
        )
        # 动态注入 UI 元素
        state.ui_elements.append(popup)
        state.ui_elements.append(fake_close)
        print("⚠️ 模拟错误弹窗已注入：Microphone busy")
    except Exception as e:
        print(f"❌ 注入弹窗失败：{str(e)}")

class AudioRecorderInitSteps:

    def __init__(self, fixed_init_filename: str = "temp_recording"):
        self._text_config = {
            "get_started": ["Get Started", "开始使用"],
            "apply": ["Apply", "应用"],
            "start_recording": ["Start recording", "开始录制"],
            "while_using_app": ["While using the app", "应用使用期间"],
            "allow": ["Allow", "允许"],
            "stop_recording": ["Stop recording", "停止录制"],
            "save": ["Save", "保存"],
            "enter_filename": ["Enter file name", "输入文件名"],
        }
        self.fixed_init_filename = fixed_init_filename
        self._default_screen_size = (1080, 2400)

    def _get_valid_controller(self, env: AsyncAndroidEnv) -> android_world_controller.AndroidWorldController:

        if not hasattr(env, "controller"):
            raise RuntimeError("AsyncAndroidEnv缺少controller属性")
        controller = env.controller
        if not isinstance(controller, android_world_controller.AndroidWorldController):
            raise RuntimeError(
                f"controller类型错误：需为AndroidWorldController，实际为{type(controller).__name__}"
                "\n（参考interface.py第183行：controller返回值类型）"
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
            logging.warning(
                f"未找到device_screen_size属性，使用默认尺寸{self._default_screen_size}"
                "\n（参考interface.py第189-195行：屏幕尺寸属性定义）"
            )
            return self._default_screen_size

    from typing import List
    from android_world.env.interface import AsyncAndroidEnv, State
    from android_world.env import representation_utils

    def _get_stable_ui_elements(self, env: AsyncAndroidEnv) -> List[representation_utils.UIElement]:
        try:
            state: State = env.get_state(wait_to_stabilize=True)
        except AttributeError as e:
            raise RuntimeError(f"❌ 调用get_state()失败（界面未加载？）：{str(e)}") from e

        ui_elements = state.ui_elements
        if not isinstance(ui_elements, list):
            raise RuntimeError(
                f"❌ ui_elements类型错误：需为list，实际为{type(ui_elements).__name__}"
                "\n（检查interface.py的State类，确保ui_elements是列表）"
            )

        for idx, elem in enumerate(ui_elements):
            # 1. 安全提取元素属性（避免因属性不存在导致报错）
            # 文本（按钮/输入框的显示文本）
            elem_text = elem.text if (hasattr(elem, "text") and elem.text is not None) else "无文本"
            # 描述（图标/图片的辅助描述，如“开始录制图标”）
            elem_desc = elem.content_description if (
                        hasattr(elem, "content_description") and elem.content_description is not None) else "无描述"
            # 是否可点击（判断是否是按钮）
            elem_clickable = str(elem.clickable) if (
                        hasattr(elem, "clickable") and elem.clickable is not None) else "未知"
            # 位置（边界框，判断元素在屏幕的哪个区域）
            if hasattr(elem, "bbox_pixels") and elem.bbox_pixels is not None:
                # 确保边界框属性存在（x_min/y_min等）
                if all(hasattr(elem.bbox_pixels, attr) for attr in ["x_min", "y_min", "x_max", "y_max"]):
                    elem_bbox = f"({elem.bbox_pixels.x_min}, {elem.bbox_pixels.y_min})→({elem.bbox_pixels.x_max}, {elem.bbox_pixels.y_max})"
                else:
                    elem_bbox = "位置属性不完整"
            else:
                elem_bbox = "无位置"
            # 元素类型（如Button/ImageView，判断是否是按钮/图片）
            elem_class = elem.class_name if (hasattr(elem, "class_name") and elem.class_name is not None) else "未知类"

        return ui_elements
    def _click_element(
            self,
            env: AsyncAndroidEnv,
            text_key: str,
            step_desc: str,
            fallback_index: Optional[int] = None
    ) -> None:
        """
        适配依据：
        1. actuation.py第189行（find_and_click_element函数）
        2. actuation.py第35行（execute_adb_action函数）
        功能：优先文本匹配点击（灵活），失败则索引兜底（稳定）
        """
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)
        target_texts = self._text_config[text_key]

        # -------------------------- 方式1：文本匹配点击（actuation.find_and_click_element） --------------------------
        for text in target_texts:
            try:
                # 调用actuation.py的find_and_click_element（参数需为AndroidWorldController）
                actuation.find_and_click_element(
                    element_text=text,
                    env=controller,  # 参考actuation.py第192行：env参数类型为AndroidWorldController
                    case_sensitive=False  # 不区分大小写，提高匹配成功率
                )
                logging.info(f"✅ {step_desc}：成功匹配文本「{text}」")
                time.sleep(2)  # 等待界面响应（避免操作过快导致元素未加载）
                return
            except ValueError:
                # 文本未找到，继续尝试下一个文本
                continue
            except AttributeError as e:
                # 极端情况：actuation.py缺少该函数，切换索引兜底
                logging.warning(
                    f"调用find_and_click_element失败：{str(e)}"
                    "\n（参考actuation.py第189行：函数定义），切换索引兜底"
                )
                break

        # -------------------------- 方式2：索引兜底点击（actuation.execute_adb_action） --------------------------
        if fallback_index is None:
            raise RuntimeError(f"❌ {step_desc}：文本匹配全部失败，且无兜底索引")

        # 1. 获取UI元素列表（确保索引有效）
        ui_elements = self._get_stable_ui_elements(env)
        if not (0 <= fallback_index < len(ui_elements)):
            raise IndexError(
                f"兜底索引{fallback_index}无效：UI元素共{len(ui_elements)}个"
                "\n（参考actuation.py第42行：索引需在[0, len(screen_elements)-1]范围内）"
            )

        # 2. 创建点击动作（使用json_action.py的CLICK常量）
        click_action = json_action.JSONAction(
            action_type=json_action.CLICK,  # 参考json_action.py第33行：CLICK常量定义
            index=fallback_index
        )

        # 3. 执行点击动作（调用actuation.execute_adb_action）
        actuation.execute_adb_action(
            action=click_action,
            screen_elements=ui_elements,  # 参考actuation.py第37行：screen_elements参数（UI元素列表）
            screen_size=screen_size,  # 参考actuation.py第38行：screen_size参数（屏幕尺寸）
            env=controller  # 参考actuation.py第39行：env参数（AndroidWorldController）
        )
        logging.warning(f"⚠️ {step_desc}：文本匹配失败，使用索引{fallback_index}点击")
        time.sleep(2)

    def run_until_filename_input(self, env: AsyncAndroidEnv) -> str:
        # -------------------------- 步骤1：初始化校验（确保env类型正确） --------------------------
        if not isinstance(env, AsyncAndroidEnv):
            raise RuntimeError(
                f"env类型错误：需为AsyncAndroidEnv，实际为{type(env).__name__}"
                "\n（参考interface.py第128行：AsyncAndroidEnv类定义）"
            )
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)
        logging.info("✅初始化校验完成：env为有效AsyncAndroidEnv实例")

        # -------------------------- 步骤2：打开AudioRecorder APP --------------------------
        logging.info("📱 步骤1/11：打开AudioRecorder APP")
        # 1. 创建打开APP动作（使用json_action.py的OPEN_APP常量）
        open_app_action = json_action.JSONAction(
            action_type=json_action.OPEN_APP,
            app_name="Audio Recorder"
        )
        # 2. 执行打开APP动作
        actuation.execute_adb_action(
            action=open_app_action,
            screen_elements=self._get_stable_ui_elements(env),
            screen_size=screen_size,
            env=controller
        )
        time.sleep(3)  # 等待APP冷启动（避免后续操作找不到元素）
        logging.info("✅ 步骤2/11：APP打开完成")

        # -------------------------- 步骤3：点击Get Started --------------------------
        self._click_element(
            env=env,
            text_key="get_started",
            step_desc="步骤3/11：点击Get Started",
            fallback_index=8  # 兜底索引
        )

        # -------------------------- 步骤4：点击Apply --------------------------
        self._click_element(
            env=env,
            text_key="apply",
            step_desc="步骤4/11：点击Apply",
            fallback_index=9
        )

        # -------------------------- 步骤5：点击开始录制 --------------------------
        self._click_element(
            env=env,
            text_key="start_recording",
            step_desc="步骤5/11：点击开始录制按钮",
            fallback_index=6
        )

        _inject_microphone_error_popup(env)
        # # -------------------------- 步骤6：录制5秒 --------------------------
        # recording_duration = 5
        # logging.info(f"🎙️ 步骤6/11：正在录制音频（时长：{recording_duration}秒）")
        # time.sleep(recording_duration)
        #
        # # -------------------------- 步骤7：点击停止录制 --------------------------
        # self._click_element(
        #     env=env,
        #     text_key="stop_recording",
        #     step_desc="步骤7/11：点击停止录制按钮",
        #     fallback_index=8
        # )
        #
        #
        # # -------------------------- 步骤8：输入文件名--------------------------
        # logging.info(f"📝 步骤8/8：输入文件名「{self.fixed_init_filename}」")
        # # 1. 创建输入文本动作（使用json_action.py的INPUT_TEXT常量）
        # input_action = json_action.JSONAction(
        #     action_type=json_action.INPUT_TEXT,
        #     text=self.fixed_init_filename,
        #     clear_text=True
        # )
        # # 2. 执行输入动作
        # actuation.execute_adb_action(
        #     action=input_action,
        #     screen_elements=self._get_stable_ui_elements(env),
        #     screen_size=screen_size,
        #     env=controller
        # )
        # time.sleep(1)  # 等待文本输入完成
        #
        # # -------------------------- 最终状态：停在命名阶段 --------------------------
        # print(f"🎉 全部步骤完成：已输入文件名「{self.fixed_init_filename}」（未保存，停在命名阶段）")
        return {
            "entered_filename":self.fixed_init_filename,
            "popup_required": True, #任务告诉agent：此时应出现弹窗
            "have_popup":True, #当前屏幕确实已经有弹窗
        }

class AudioRecorderInitStepsWithTypingError:

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

            raise RuntimeError(f"❌ {step_desc}：未找到匹配 content_description 的元素")


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
        长按指定索引的UI元素，触发上下文菜单
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
    def _long_press_by_text(
            self,
            env: AsyncAndroidEnv,
            target_texts: List[str],
            step_desc: str,
            fallback_index: Optional[int] = None
    ) -> None:
        """
        根据 UI 文本进行长按操作。
        如果没有匹配到文本，则使用索引进行兜底长按。

        :param env: AsyncAndroidEnv 环境
        :param target_texts: 需要匹配的文本列表（按顺序尝试）
        :param step_desc: 日志中打印的步骤说明
        :param fallback_index: 兜底 UI 索引（可选）
        """
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)
        ui_elements = self._get_stable_ui_elements(env)

        # 遍历所有候选文本，尝试匹配
        for text in target_texts:
            for idx, elem in enumerate(ui_elements):
                elem_text = getattr(elem, "text", None)
                if elem_text and text.lower() == elem_text.lower():
                    # 找到匹配 → 长按该 UI 元素
                    long_press_action = json_action.JSONAction(
                        action_type=json_action.LONG_PRESS,
                        index=idx
                    )
                    actuation.execute_adb_action(
                        action=long_press_action,
                        screen_elements=ui_elements,
                        screen_size=screen_size,
                        env=controller
                    )
                    logging.info(f"✅ {step_desc}：成功长按文本包含「{text}」的元素(idx={idx})")
                    time.sleep(2)
                    return

        # 如果匹配失败
        if fallback_index is None:
            raise RuntimeError(f"❌ {step_desc}：未找到匹配文本，且无兜底索引")

        # 兜底索引合法性检查
        if not (0 <= fallback_index < len(ui_elements)):
            raise IndexError(
                f"兜底索引{fallback_index}无效，总UI元素数量：{len(ui_elements)}"
            )

        # 兜底长按
        fallback_action = json_action.JSONAction(
            action_type=json_action.LONG_PRESS,
            index=fallback_index
        )
        actuation.execute_adb_action(
            action=fallback_action,
            screen_elements=ui_elements,
            screen_size=screen_size,
            env=controller
        )
        logging.warning(
            f"⚠️ {step_desc}：文本未匹配成功，使用兜底索引 {fallback_index} 进行长按"
        )
        time.sleep(2)

    def run(self, env: AsyncAndroidEnv,name:str):

        self.name = name
        if not isinstance(env, AsyncAndroidEnv):
            raise RuntimeError(f"env类型错误：需为AsyncAndroidEnv，实际为{type(env).__name__}")

        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        # -------------------------- 步骤1：打开AudioRecorder APP --------------------------
        logging.info("📱 步骤1：打开AudioRecorder APP")
        open_app_action = json_action.JSONAction(
            action_type=json_action.OPEN_APP,
            app_name="Audio Recorder"
        )
        # 2. 执行打开APP动作
        actuation.execute_adb_action(
            action=open_app_action,
            screen_elements=self._get_stable_ui_elements(env),
            screen_size=screen_size,
            env=controller
        )
        time.sleep(3)
        logging.info("✅ 步骤2/11：APP打开完成")
        # -------------------------- 点击开始录制 --------------------------
        self._click_element_by_content_description(
            env=env,
            target_descs=["Recording: %s"],
            step_desc="开始录制",
            fallback_index=6
        )
        time.sleep(6)

        # -------------------------- 点击停止录制 --------------------------
        self._click_element_by_text(
            env=env,
            text_key="stop_recording",
            step_desc="步骤7/11：点击停止录制按钮",
            fallback_index=8
        )
        #点击输入框
        self._click_element_by_text(
            env=env,
            target_texts=["Record-X"],
            step_desc="点击输入框",
            fallback_index=1
        )
        time.sleep(3)
        #点击输入
        self._input_text(env, self.name, "输入名字")
        return {
        }