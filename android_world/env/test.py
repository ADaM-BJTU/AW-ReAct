from json_action import JSONAction,CLICK,INPUT_TEXT
# 创建一个点击动作（通过坐标）
click_action = JSONAction(
    action_type=CLICK,
    x=100,
    y=200
)

# 创建一个输入文本动作
input_action = JSONAction(
    action_type=INPUT_TEXT,
    text="Hello Android",
    clear_text=True
)

# 序列化为JSON
print(click_action.json_str())  # 输出: {"action_type":"click","x":100,"y":200}

# 比较两个动作
another_click = JSONAction(action_type=CLICK, x=100, y=200)
print(click_action == another_click)  # 输出: True