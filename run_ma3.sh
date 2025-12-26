#!/bin/bash

current_time=$(date +"%Y-%m-%d_%H-%M-%S")
LOG="log_ma3_${current_time}.log"

MODEL_NAME="mobile_agent_v3"
export PYTHONUTF8=1

# ==== 已根据你的 GUI-Owl 服务补全 ====
#MODEL="/mnt/sdc1/ModelWarehouse/GUI-Owl-32B"
MODEL='/mnt/sdc1/ModelWarehouse/GUI-Owl-32B'
API_KEY="dummy_key"     # 如果你的服务不需要 key，保持 dummy_key 即可
#BASE_URL="http://10.126.56.106:8000/v1/chat/completions"
BASE_URL="http://10.126.56.106:8000/v1"

TRAJ_OUTPUT_PATH="traj_${current_time}"

#python run_ma3.py \
#  --suite_family=android_world \
#  --agent_name=$MODEL_NAME \
#  --model="$MODEL" \
#  --api_key="$API_KEY" \
#  --base_url="$BASE_URL" \
#  --tasks=RetroCreatePlaylist \
#  --traj_output_path="$TRAJ_OUTPUT_PATH" \
#  --grpc_port=8554 \
#  --console_port=5554 2>&1 | tee "$LOG"
python run_ma3.py \
  --suite_family=android_world \
  --agent_name=$MODEL_NAME \
  --model="$MODEL" \
  --api_key="$API_KEY" \
  --base_url="$BASE_URL" \
  --tasks=RetroCreatePlaylist \
  --traj_output_path="$TRAJ_OUTPUT_PATH" \
  --grpc_port=8554 \
  --console_port=5554 2>&1 | tee "$LOG"
#"C:\Program Files\Git\bin\bash.exe" run_ma3.sh