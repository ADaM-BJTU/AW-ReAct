import time
from typing import Tuple, Optional, List

from absl import logging
from android_world.env.interface import AsyncAndroidEnv, State
from android_world.env import actuation, representation_utils
from android_world.env import json_action
from android_world.env import android_world_controller

class FilesDeleteFileInitStepsWithNotExsitFile:
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

            raise RuntimeError(f"❌ {step_desc}：未找到匹配 content_description 的元素")

    #根据content字段进行匹配 长按
    def _long_press_element_by_content_description(
            self,
            env: AsyncAndroidEnv,
            target_descs: List[str],
            step_desc: str,
            fallback_index: Optional[int] = None
    ) -> None:

        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        ui_elements = self._get_stable_ui_elements(env)

        # 遍历所有目标 content_description
        for target in target_descs:
            for idx, elem in enumerate(ui_elements):
                desc = getattr(elem, "content_description", False)
                if desc and target.lower() in desc.lower():
                    # 找到元素，点击
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
                    logging.info(f"✅ {step_desc}：成功长按 content_description 包含「{target}」的元素(idx={idx})")
                    time.sleep(1.5)
                    return

        # 如果这里还没 return → 匹配失败
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

    def _long_press_element_by_text(
            self,
            env: AsyncAndroidEnv,
            target_texts: List[str],
            step_desc: str,
            fallback_index: Optional[int] = None
    ) -> None:
        """
        根据 text 长按 UI 元素，文本匹配失败则用索引兜底
        """
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        ui_elements = self._get_stable_ui_elements(env)

        # ===== 优先：按 text 匹配 =====
        for target in target_texts:
            for idx, elem in enumerate(ui_elements):
                text = getattr(elem, "text", None)
                class_name = getattr(elem, "class_name", None)
                if (
                        text is not None
                        and class_name == "android.widget.TextView"
                        and text.strip().lower() == target.strip().lower()
                ):
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
                    logging.info(
                        f"✅ {step_desc}：成功长按 text 包含「{target}」的元素 (idx={idx})"
                    )
                    time.sleep(1.5)
                    return

        # ===== fallback：索引兜底 =====
        if fallback_index is None:
            raise RuntimeError(f"❌ {step_desc}：text 匹配失败且无兜底索引")

        if not (0 <= fallback_index < len(ui_elements)):
            raise IndexError(
                f"兜底索引 {fallback_index} 无效，UI 元素数：{len(ui_elements)}"
            )

        long_press_action = json_action.JSONAction(
            action_type=json_action.LONG_PRESS,
            index=fallback_index
        )
        actuation.execute_adb_action(
            action=long_press_action,
            screen_elements=ui_elements,
            screen_size=screen_size,
            env=controller
        )
        logging.warning(
            f"⚠️ {step_desc}：text 匹配失败，使用索引 {fallback_index} 长按"
        )
        time.sleep(1.5)

    def run(self, env: AsyncAndroidEnv,file_name: str, subfolder: str):
        """
        主流程：
        1. 打开Files APP
        2. 点击左上角目录栏按钮
        3. 点击任务指定目录名（target_directory）
        4. 进入目标文件夹
        5. 创建诱饵文件
        6. 删除诱饵文件
        """
        # 用传入的参数覆盖类属性
        self.target_directory = subfolder
        self.file_name = file_name

        # 确保env合法
        if not isinstance(env, AsyncAndroidEnv):
            raise RuntimeError(f"env类型错误：需为AsyncAndroidEnv，实际为{type(env).__name__}")

        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        # 1. 打开Files APP
        logging.info("📱 步骤1/6：打开Files APP")
        open_files_action = json_action.JSONAction(
            action_type=json_action.OPEN_APP,
            app_name="Files"
        )
        actuation.execute_adb_action(
            action=open_files_action,
            screen_elements=self._get_stable_ui_elements(env),
            screen_size=screen_size,
            env=controller
        )
        time.sleep(3)

        # 2. 点击左上角目录栏按钮（一般文本是“目录”或是按钮图标，此处示例用文本“目录”）
        logging.info("📂 步骤2/6：点击左上角目录栏按钮")
        # 因不同设备目录栏文本不同，这里用多个备选文本尝试点击
        dir_btn_texts = ["目录", "Directory", "Files", "导航栏"]
        self._click_element_by_text(
            env=env,
            target_texts=dir_btn_texts,
            step_desc="点击目录栏按钮",
            fallback_index=1
        )

        # 3. 点击任务给定的目标目录名
        logging.info(f"📁 步骤3/6：点击目录「sdk_gphone_x86_64」")
        self._click_element_by_text(
            env=env,
            target_texts=["sdk_gphone_x86_64"],
            step_desc=f"点击目标目录「sdk_gphone_x86_64」",
            fallback_index=8
        )
        time.sleep(3)
        #7. 点击搜索按钮
        self._click_element_by_content_description(
            env=env,
            target_descs=["Search"],
            step_desc="点击搜索按钮",
        )
        time.sleep(3)
        #输入file名字
        self._input_text(env, self.file_name, "输入文件名")
        time.sleep(3)
        #长按文件按钮
        self._long_press_element_by_text(
            env=env,
            target_texts=[self.file_name],
            step_desc="长按文件",
            fallback_index=19
        )
        time.sleep(3)
        #点击垃圾桶标志
        self._click_element_by_content_description(
            env=env,
            target_descs=["Delete"],
            step_desc="点击垃圾桶标志",
            fallback_index=3
        )
        time.sleep(3)
        #点击ok标志
        self._click_element_by_text(
            env=env,
            target_texts=["OK"],
            step_desc="点击ok",
            fallback_index=2
        )
        time.sleep(3)
        return {
        }

class FilesMoveFileInitStepsWithNotExsitFile:
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

            raise RuntimeError(f"❌ {step_desc}：未找到匹配 content_description 的元素")

    #根据content字段进行匹配 长按
    def _long_press_element_by_content_description(
            self,
            env: AsyncAndroidEnv,
            target_descs: List[str],
            step_desc: str,
            fallback_index: Optional[int] = None
    ) -> None:

        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        ui_elements = self._get_stable_ui_elements(env)

        # 遍历所有目标 content_description
        for target in target_descs:
            for idx, elem in enumerate(ui_elements):
                desc = getattr(elem, "content_description", False)
                if desc and target.lower() in desc.lower():
                    # 找到元素，点击
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
                    logging.info(f"✅ {step_desc}：成功长按 content_description 包含「{target}」的元素(idx={idx})")
                    time.sleep(1.5)
                    return

        # 如果这里还没 return → 匹配失败
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

    def _long_press_element_by_text(
            self,
            env: AsyncAndroidEnv,
            target_texts: List[str],
            step_desc: str,
            fallback_index: Optional[int] = None
    ) -> None:
        """
        根据 text 长按 UI 元素，文本匹配失败则用索引兜底
        """
        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        ui_elements = self._get_stable_ui_elements(env)

        # ===== 优先：按 text 匹配 =====
        for target in target_texts:
            for idx, elem in enumerate(ui_elements):
                text = getattr(elem, "text", None)
                class_name = getattr(elem, "class_name", None)
                if (
                        text is not None
                        and class_name == "android.widget.TextView"
                        and text.strip().lower() == target.strip().lower()
                ):
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
                    logging.info(
                        f"✅ {step_desc}：成功长按 text 包含「{target}」的元素 (idx={idx})"
                    )
                    time.sleep(1.5)
                    return

        # ===== fallback：索引兜底 =====
        if fallback_index is None:
            raise RuntimeError(f"❌ {step_desc}：text 匹配失败且无兜底索引")

        if not (0 <= fallback_index < len(ui_elements)):
            raise IndexError(
                f"兜底索引 {fallback_index} 无效，UI 元素数：{len(ui_elements)}"
            )

        long_press_action = json_action.JSONAction(
            action_type=json_action.LONG_PRESS,
            index=fallback_index
        )
        actuation.execute_adb_action(
            action=long_press_action,
            screen_elements=ui_elements,
            screen_size=screen_size,
            env=controller
        )
        logging.warning(
            f"⚠️ {step_desc}：text 匹配失败，使用索引 {fallback_index} 长按"
        )
        time.sleep(1.5)

    def run(self, env: AsyncAndroidEnv,file_name: str):
        """
        主流程：
        1. 打开Files APP
        2. 点击左上角目录栏按钮
        3. 点击任务指定目录名（target_directory）
        4. 进入目标文件夹
        5. 创建诱饵文件
        6. 删除诱饵文件
        """
        # 用传入的参数覆盖类属性
        self.file_name = file_name


        # 确保env合法
        if not isinstance(env, AsyncAndroidEnv):
            raise RuntimeError(f"env类型错误：需为AsyncAndroidEnv，实际为{type(env).__name__}")

        controller = self._get_valid_controller(env)
        screen_size = self._get_screen_size(env)

        # 1. 打开Files APP
        logging.info("📱 步骤1/6：打开Files APP")
        open_files_action = json_action.JSONAction(
            action_type=json_action.OPEN_APP,
            app_name="Files"
        )
        actuation.execute_adb_action(
            action=open_files_action,
            screen_elements=self._get_stable_ui_elements(env),
            screen_size=screen_size,
            env=controller
        )
        time.sleep(3)

        # 2. 点击左上角目录栏按钮（一般文本是“目录”或是按钮图标，此处示例用文本“目录”）
        logging.info("📂 步骤2/6：点击左上角目录栏按钮")
        # 因不同设备目录栏文本不同，这里用多个备选文本尝试点击
        dir_btn_texts = ["目录", "Directory", "Files", "导航栏"]
        self._click_element_by_text(
            env=env,
            target_texts=dir_btn_texts,
            step_desc="点击目录栏按钮",
            fallback_index=1
        )

        # 3. 点击任务给定的目标目录名
        logging.info(f"📁 步骤3/6：点击目录「sdk_gphone_x86_64」")
        self._click_element_by_text(
            env=env,
            target_texts=["sdk_gphone_x86_64"],
            step_desc=f"点击目标目录「sdk_gphone_x86_64」",
            fallback_index=8
        )
        time.sleep(3)
        #7. 点击搜索按钮
        self._click_element_by_content_description(
            env=env,
            target_descs=["Search"],
            step_desc="点击搜索按钮",
        )
        time.sleep(3)
        #输入file名字
        self._input_text(env, self.file_name, "输入文件名")
        time.sleep(3)
        #长按文件按钮
        self._long_press_element_by_text(
            env=env,
            target_texts=[self.file_name],
            step_desc="长按文件",
            fallback_index=19
        )
        time.sleep(3)
        #点击垃圾桶标志
        self._click_element_by_content_description(
            env=env,
            target_descs=["Delete"],
            step_desc="点击垃圾桶标志",
            fallback_index=3
        )
        time.sleep(3)
        #点击ok标志
        self._click_element_by_text(
            env=env,
            target_texts=["OK"],
            step_desc="点击ok",
            fallback_index=2
        )
        time.sleep(3)
        return {
        }