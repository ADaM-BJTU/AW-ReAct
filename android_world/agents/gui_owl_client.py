# client.py 
import requests
import base64
import json
import os

# --- 配置 ---

# 服务器 IP 和 vLLM 端口
# vLLM 的 OpenAI 兼容接口在 /v1/chat/completions
SERVER_URL = "http://10.126.56.106:8000/v1/chat/completions"

#  服务器上模型的名称
MODEL_ID = "/mnt/sdc1/ModelWarehouse/GUI-Owl-32B"

#  本地 测试图片
IMAGE_PATH = "./start.png"


PROMPT = "我要打电话请问怎么操作,具体点击屏幕中的什么地方"

# --- 辅助函数 ---
def image_to_base64_url(image_path):
    """将图片文件转为 Base64 data URL"""
    if not os.path.exists(image_path):
        print(f"错误: 找不到图片文件 '{image_path}'")
        return None

    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        #  data URL 
        return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        print(f"读取或编码图片时出错: {e}")
        return None

# --- 主函数 ---
def run_client():
    print(f"正在准备图片: {IMAGE_PATH}")
    b64_image_url = image_to_base64_url(IMAGE_PATH)
    
    if b64_image_url is None:
        return

    # 1. 构建 OpenAI 兼容的多模态 Payload
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": b64_image_url
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1024, # vLLM 需要这个
        "temperature": 0 # GUI-Owl 任务需要确定性输出
    }

    print(f"正在向服务器 {SERVER_URL} 发送请求...")
    print(f"指令: {PROMPT}")

    try:
        # 2. 发送 POST 请求
        response = requests.post(
            SERVER_URL, 
            json=payload, 
            timeout=300 # 兜底
        )

        # 3. 解析响应
        if response.status_code == 200:
            print("\n--- ✅ 请求成功 ---")
            result_data = response.json()
            
            # 提取 vLLM 的 OpenAI 格式响应
            message_content = result_data["choices"][0]["message"]["content"]
            
            print("模型返回结果:")
            print(message_content)
            
        else:
            print(f"\n--- ❌ 请求失败 ---")
            print(f"状态码: {response.status_code}")
            print(f"服务器错误详情: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"\n--- ❌ 连接错误 ---")
        print(f"无法连接到 {SERVER_URL}")
        print(f"错误详情: {e}")

if __name__ == "__main__":
    run_client()