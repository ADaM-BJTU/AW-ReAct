@echo off
REM 获取当前时间字符串
for /f "tokens=1-6 delims=/:. " %%a in ("%date% %time%") do (
  set datetime=%%a%%b%%c_%%d%%e%%f
)

set MODEL_NAME=mobile_agent_v3
set MODEL=/mnt/sdc1/ModelWarehouse/GUI-Owl-32B
set API_KEY=dummy_key
set BASE_URL=http://10.126.56.106:8000/v1
set TRAJ_OUTPUT_PATH=traj_%datetime%
set GRPC_PORT=8554
set CONSOLE_PORT=5554

python run_ma3.py ^
  --suite_family=android_world ^
  --agent_name=%MODEL_NAME% ^
  --model=%MODEL% ^
  --api_key=%API_KEY% ^
  --base_url=%BASE_URL% ^
  --tasks=MarkorMoveNote ^
  --traj_output_path=%TRAJ_OUTPUT_PATH% ^
  --grpc_port=%GRPC_PORT% ^
  --console_port=%CONSOLE_PORT%

pause
