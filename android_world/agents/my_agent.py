"""
my_agent.py
自定义 AndroidWorld Agent（基于 M3A）+ .env 自动加载 API Key / URL / Model

"""

import time
import base64
import requests
import os

from dotenv import load_dotenv
from absl import logging

from android_world.agents import base_agent, agent_utils
from android_world.agents.infer import LlmWrapper, MultimodalLlmWrapper
from android_world.env import json_action
from android_world.agents import m3a_utils
from android_world.agents.m3a import (
    _action_selection_prompt,
    _summarize_prompt,
    _generate_ui_elements_description_list,
)


# ================================================================
# 1. 自动加载 .env 配置
# ================================================================
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

if not API_KEY or not API_URL or not MODEL_NAME:
    raise RuntimeError(
        "❌ 缺少必要环境变量，请在 .env 中设置：\n"
        "API_KEY=你的API密钥\n"
        "API_URL=模型接口URL\n"
        "MODEL_NAME=模型名称\n"
    )


# ================================================================
# 2. CustomAPIWrapper —— 自定义模型 API 包装器
# ================================================================
class CustomAPIWrapper(LlmWrapper, MultimodalLlmWrapper):
    def __init__(self, api_key: str, url: str, model: str, max_retry: int = 3):
        self.api_key = api_key
        self.url = url
        self.model = model
        self.max_retry = max_retry if max_retry > 0 else 3

    def predict(
        self,
        text_prompt: str,
        enable_safety_checks: bool = True,
        generation_config: dict | None = None,
    ) -> tuple[str, bool | None, dict | None]:
        # 纯文本调用时，调用 predict_mm 但传空图片列表
        return self.predict_mm(text_prompt, [])

    def predict_mm(
        self,
        prompt: str,
        images: list,
        enable_safety_checks: bool = True,
        generation_config: dict | None = None,
    ) -> tuple[str, bool | None, dict | None]:

        import cv2
        import base64
        import time
        import requests

        image_contents = []
        for img in images:
            _, buf = cv2.imencode(".png", img)
            b64 = base64.b64encode(buf).decode("utf-8")
            image_contents.append({
                "type": "image_url",
                "image_url": f"data:image/png;base64,{b64}"
            })

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *image_contents
                ]
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1500
        }
        if generation_config:
            payload.update(generation_config)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        counter = self.max_retry
        retry_delay = 1.0
        last_response = None

        while counter > 0:
            try:
                resp = requests.post(self.url, json=payload, headers=headers)
                resp.raise_for_status()
                raw = resp.json()
                output = raw["choices"][0]["message"]["content"]
                return output, True, raw
            except Exception as e:
                print(f"Error calling LLM, retry in {retry_delay} seconds. Error: {e}")
                last_response = raw if 'raw' in locals() else None
                counter -= 1
                if counter == 0:
                    break
                time.sleep(retry_delay)
                retry_delay *= 2

        # 如果都失败了，返回错误提示和原始返回
        return "Error calling LLM.", False, last_response



# ================================================================
# 3. M3A_CustomLLM —— 自定义Agent
# ================================================================
class M3A_CustomLLM(base_agent.EnvironmentInteractingAgent):
    """
    复刻 M3A Agent：
    ✔ SOM 加标号
    ✔ Action prompt & Summary prompt
    ✔ 历史记录
    ✔ JSON Action 解析
    ✔ 使用你自己的模型完成反思能力
    """

    def __init__(
        self,
        env,
        llm_wrapper: CustomAPIWrapper,
        name="M3A_CustomLLM",
        wait_after_action_seconds=2.0,
    ):
        super().__init__(env, name)
        self.llm = llm_wrapper
        self.history = []
        self.additional_guidelines = None
        self.wait_after_action_seconds = wait_after_action_seconds

    # 设置任务额外规则
    def set_task_guidelines(self, guidelines):
        self.additional_guidelines = guidelines

    def reset(self, go_home_on_reset=False):
        super().reset(go_home_on_reset)
        self.env.hide_automation_ui()
        self.history = []

    # ========================================================
    # step —— agent 的单步推理
    # ========================================================
    def step(self, goal: str):
        step_info = {}
        logging.info("---- Step %d ----", len(self.history) + 1)

        # -------- 1. 获取当前状态 --------
        state = self.get_post_transition_state()

        logical_size = self.env.logical_screen_size
        orientation = self.env.orientation
        frame_boundary = self.env.physical_frame_boundary

        ui_before = state.ui_elements
        step_info["before_ui_elements"] = ui_before

        ui_before_str = _generate_ui_elements_description_list(
            ui_before, logical_size
        )

        before_raw = state.pixels.copy()
        before_som = before_raw.copy()

        # SOM 添加编号
        for idx, elem in enumerate(ui_before):
            if m3a_utils.validate_ui_element(elem, logical_size):
                m3a_utils.add_ui_element_mark(
                    before_som, elem, idx,
                    logical_size, frame_boundary, orientation
                )

        # -------- 2. 构建 Action prompt --------
        history_text = [
            f"Step {i+1}- {h['summary']}" for i, h in enumerate(self.history)
        ]

        action_prompt = _action_selection_prompt(
            goal=goal,
            history=history_text,
            ui_elements_str=ui_before_str,
            additional_guidelines=self.additional_guidelines,
        )
        step_info["action_prompt"] = action_prompt

        # -------- 3. 调模型生成 Action --------
        action_output, _, raw_action = self.llm.predict_mm(
            action_prompt,
            [before_raw, before_som]
        )

        step_info["action_output"] = action_output
        step_info["action_raw_response"] = raw_action

        # 解析 Reason + Action JSON
        reason, action_json_str = m3a_utils.parse_reason_action_output(action_output)
        step_info["action_reason"] = reason

        try:
            obj = agent_utils.extract_json(action_json_str)
            action_obj = json_action.JSONAction(**obj)
        except Exception:
            step_info["summary"] = "Action JSON parsing failed"
            self.history.append(step_info)
            return base_agent.AgentInteractionResult(False, step_info)

        step_info["action_output_json"] = action_obj

        # -------- 4. 执行动作 --------
        try:
            self.env.execute_action(action_obj)
        except Exception as e:
            step_info["summary"] = f"Action execution failed: {e}"
            self.history.append(step_info)
            return base_agent.AgentInteractionResult(False, step_info)

        time.sleep(self.wait_after_action_seconds)

        # -------- 5. 获取执行后的状态 + Summary Prompt --------
        state_after = self.env.get_state(wait_to_stabilize=False)
        ui_after = state_after.ui_elements

        ui_after_str = _generate_ui_elements_description_list(
            ui_after, logical_size
        )

        after_raw = state_after.pixels.copy()
        after_som = after_raw.copy()

        # SOM 标号
        for idx, elem in enumerate(ui_after):
            if m3a_utils.validate_ui_element(elem, logical_size):
                m3a_utils.add_ui_element_mark(
                    after_som, elem, idx,
                    logical_size, frame_boundary, orientation
                )

        m3a_utils.add_screenshot_label(before_som, "before")
        m3a_utils.add_screenshot_label(after_som, "after")

        summary_prompt = _summarize_prompt(
            action_json_str,
            reason,
            goal,
            ui_before_str,
            ui_after_str
        )

        step_info["summary_prompt"] = summary_prompt

        summary_text, _, raw_summary = self.llm.predict_mm(
            summary_prompt,
            [before_som, after_som]
        )

        step_info["summary_raw_response"] = raw_summary
        step_info["summary"] = f"Action selected: {action_json_str}. {summary_text}"

        self.history.append(step_info)

        return base_agent.AgentInteractionResult(False, step_info)



def create_agent(env):

    wrapper = CustomAPIWrapper(
        api_key=API_KEY,
        url=API_URL,
        model=MODEL_NAME
    )
    return M3A_CustomLLM(env, wrapper)
