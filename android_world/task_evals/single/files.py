# Copyright 2025 The android_world Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tasks for the file manager app."""

import os
import random
from typing import Any

from android_world.env import device_constants
from android_world.env import interface
from android_world.task_evals import task_eval
from android_world.task_evals.common_validators import file_validators
from android_world.task_evals.similarize_name import generate_similar_contacts
from android_world.task_evals.utils import user_data_generation
from android_world.task_evals.single.files_init_steps import FilesDeleteFileInitStepsWithNotExsitFile,FilesMoveFileInitStepsWithNotExsitFile
from android_world.utils import file_utils

class FilesMoveFile(task_eval.TaskEval):
  """Task for checking that a file has been moved."""

  app_names = ("files",)
  complexity = 2
  schema = file_validators.MoveFile.schema
  template = (
      "Move the file {file_name} from {source_folder} within the"
      " sdk_gphone_x86_64 storage area to the {destination_folder} within the"
      " same sdk_gphone_x86_64 storage area in the Android filesystem."
  )

  def __init__(self, params: dict[str, Any]):
    super().__init__(params)
    self.move_file_task = file_validators.MoveFile(
        params, device_constants.EMULATOR_DATA
    )

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self.move_file_task.initialize_task(env)

  def tear_down(self, env: interface.AsyncEnv) -> None:
    super().tear_down(env)
    self.move_file_task.tear_down(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    super().is_successful(env)
    return self.move_file_task.is_successful(env)

  @classmethod
  def generate_random_params(cls) -> dict[str, Any]:
    source_folder = random.choice(
        list(user_data_generation.EMULATOR_DIRECTORIES.keys())
    )
    destination_folder = random.choice([
        folder
        for folder in user_data_generation.EMULATOR_DIRECTORIES
        if folder != source_folder
    ])
    noise_candidates = user_data_generation.EMULATOR_DIRECTORIES[source_folder]

    destination_candidates = user_data_generation.EMULATOR_DIRECTORIES[
        destination_folder
    ]
    file_name = random.choice(destination_candidates)

    return {
        "file_name": file_name,
        "source_folder": source_folder,
        "destination_folder": destination_folder,
        "noise_candidates": noise_candidates,
    }


class FilesDeleteFile(task_eval.TaskEval):
  """Task for checking that a file has been deleted."""

  app_names = ("files",)
  complexity = 2.2
  schema = file_validators.DeleteFile.schema
  template = (
      "Delete the file {file_name} from the Android filesystem located in the"
      " {subfolder} folder within the sdk_gphone_x86_64 storage area."
  )

  def __init__(self, params: dict[str, Any]):
    super().__init__(params)
    self.delete_file_task = file_validators.DeleteFile(
        params, device_constants.EMULATOR_DATA
    )
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self.delete_file_task.initialize_task(env)

  def tear_down(self, env: interface.AsyncEnv) -> None:
    super().tear_down(env)
    self.delete_file_task.tear_down(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    super().is_successful(env)
    return self.delete_file_task.is_successful(env)

  @classmethod
  def generate_random_params(cls) -> dict[str, Any]:
    subfolder = random.choice(
        list(user_data_generation.EMULATOR_DIRECTORIES.keys())
    )
    noise_candidates = user_data_generation.EMULATOR_DIRECTORIES[subfolder]
    _, ext_part = os.path.splitext(noise_candidates[0])
    file_name = user_data_generation.generate_random_file_name() + ext_part
    return {
        "file_name": file_name,
        "subfolder": subfolder,
        "noise_candidates": noise_candidates,
    }

#由FilesDelteFile 任务变形而来
#1.变体1：多个诱饵文件
class FilesDeleteFileWithSimilarFiles(task_eval.TaskEval):
  """Task for checking that a file has been deleted."""

  app_names = ("files",)
  complexity = 2.2
  schema = file_validators.DeleteFile.schema
  template = (
      "Delete the file {file_name} from the Android filesystem located in the"
      " {subfolder} folder within the sdk_gphone_x86_64 storage area."
  )

  def __init__(self, params: dict[str, Any]):
    super().__init__(params)
    self.delete_file_task = file_validators.DeleteFile(
        params, device_constants.EMULATOR_DATA
    )

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self.delete_file_task.initialize_task(env)
    # 创建多个“极度相似”的假文件
    real_file_name = self.params["file_name"]

    similar_file_names = generate_similar_contacts(
        base_name=real_file_name,
        num_contacts=4,
    )
    source_dir = self.delete_file_task.data_directory
    for fake_name in similar_file_names:
        file_utils.create_file(
            fake_name, source_dir,env.controller
        )

  def tear_down(self, env: interface.AsyncEnv) -> None:
    super().tear_down(env)
    self.delete_file_task.tear_down(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    super().is_successful(env)
    return self.delete_file_task.is_successful(env)

  @classmethod
  def generate_random_params(cls) -> dict[str, Any]:
    subfolder = random.choice(
        list(user_data_generation.EMULATOR_DIRECTORIES.keys())
    )
    noise_candidates = user_data_generation.EMULATOR_DIRECTORIES[subfolder]
    _, ext_part = os.path.splitext(noise_candidates[0])
    file_name = user_data_generation.generate_random_file_name() + ext_part
    return {
        "file_name": file_name,
        "subfolder": subfolder,
        "noise_candidates": noise_candidates,
    }

#2.变体2：初始条件不足
class FilesDeleteFileWithNotExsitFile(task_eval.TaskEval):
  """Task for checking that a file has been deleted."""

  app_names = ("files",)
  complexity = 2.2
  schema = file_validators.DeleteFile.schema
  template = (
      "Delete the file {file_name} from the Android filesystem located in the"
      " {subfolder} folder within the sdk_gphone_x86_64 storage area."
  )

  def __init__(self, params: dict[str, Any]):
    super().__init__(params)
    self.delete_file_task = file_validators.DeleteFile(
        params, device_constants.EMULATOR_DATA
    )
    #初始化独立脚本实例
    self.init_script = FilesDeleteFileInitStepsWithNotExsitFile()
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self.delete_file_task.initialize_task(env)

    file_name, subfolder = self.params['file_name'],self.params['subfolder']
    # 执行初始化脚本
    self.init_script.run(env, file_name, subfolder)

  def tear_down(self, env: interface.AsyncEnv) -> None:
    super().tear_down(env)
    self.delete_file_task.tear_down(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    super().is_successful(env)
    return self.delete_file_task.is_successful(env)

  @classmethod
  def generate_random_params(cls) -> dict[str, Any]:
    subfolder = random.choice(
        list(user_data_generation.EMULATOR_DIRECTORIES.keys())
    )
    noise_candidates = user_data_generation.EMULATOR_DIRECTORIES[subfolder]
    _, ext_part = os.path.splitext(noise_candidates[0])
    file_name = user_data_generation.generate_random_file_name() + ext_part
    return {
        "file_name": file_name,
        "subfolder": subfolder,
        "noise_candidates": noise_candidates,
    }

#由FilesMoveFile 任务变形而来
#1.变体1：多个诱饵文件
class FilesMoveFileWithSimilarFiles(task_eval.TaskEval):
  """Task for checking that a file has been moved."""

  app_names = ("files",)
  complexity = 2
  schema = file_validators.MoveFile.schema
  template = (
      "Move the file {file_name} from {source_folder} within the"
      " sdk_gphone_x86_64 storage area to the {destination_folder} within the"
      " same sdk_gphone_x86_64 storage area in the Android filesystem."
  )

  def __init__(self, params: dict[str, Any]):
    super().__init__(params)
    self.move_file_task = file_validators.MoveFile(
        params, device_constants.EMULATOR_DATA
    )

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self.move_file_task.initialize_task(env)
   # 创建多个“极度相似”的假文件
    real_file_name = self.params["file_name"]

    similar_file_names = generate_similar_contacts(
        base_name=real_file_name,
        num_contacts=4,
    )
    source_dir = self.move_file_task.source_directory
    for fake_name in similar_file_names:
        file_utils.create_file(
            fake_name, source_dir,env.controller
        )

  def tear_down(self, env: interface.AsyncEnv) -> None:
    super().tear_down(env)
    self.move_file_task.tear_down(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    super().is_successful(env)
    return self.move_file_task.is_successful(env)

  @classmethod
  def generate_random_params(cls) -> dict[str, Any]:
    source_folder = random.choice(
        list(user_data_generation.EMULATOR_DIRECTORIES.keys())
    )
    destination_folder = random.choice([
        folder
        for folder in user_data_generation.EMULATOR_DIRECTORIES
        if folder != source_folder
    ])
    noise_candidates = user_data_generation.EMULATOR_DIRECTORIES[source_folder]

    destination_candidates = user_data_generation.EMULATOR_DIRECTORIES[
        destination_folder
    ]
    file_name = random.choice(destination_candidates)

    return {
        "file_name": file_name,
        "source_folder": source_folder,
        "destination_folder": destination_folder,
        "noise_candidates": noise_candidates,
    }

#2.变体2：初始条件不足
class FilesMoveFileWithNotExsitFile(task_eval.TaskEval):
  """Task for checking that a file has been moved."""

  app_names = ("files",)
  complexity = 2
  schema = file_validators.MoveFile.schema
  template = (
      "Move the file {file_name} from {source_folder} within the"
      " sdk_gphone_x86_64 storage area to the {destination_folder} within the"
      " same sdk_gphone_x86_64 storage area in the Android filesystem."
  )

  def __init__(self, params: dict[str, Any]):
    super().__init__(params)
    self.move_file_task = file_validators.MoveFile(
        params, device_constants.EMULATOR_DATA
    )
    #初始化独立脚本实例
    self.init_script = FilesMoveFileInitStepsWithNotExsitFile()
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self.move_file_task.initialize_task(env)
    file_name= self.params['file_name']
    # 执行初始化脚本
    self.init_script.run(env, file_name)

  def tear_down(self, env: interface.AsyncEnv) -> None:
    super().tear_down(env)
    self.move_file_task.tear_down(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    super().is_successful(env)
    return self.move_file_task.is_successful(env)

  @classmethod
  def generate_random_params(cls) -> dict[str, Any]:
    source_folder = random.choice(
        list(user_data_generation.EMULATOR_DIRECTORIES.keys())
    )
    destination_folder = random.choice([
        folder
        for folder in user_data_generation.EMULATOR_DIRECTORIES
        if folder != source_folder
    ])
    noise_candidates = user_data_generation.EMULATOR_DIRECTORIES[source_folder]

    destination_candidates = user_data_generation.EMULATOR_DIRECTORIES[
        destination_folder
    ]
    file_name = random.choice(destination_candidates)

    return {
        "file_name": file_name,
        "source_folder": source_folder,
        "destination_folder": destination_folder,
        "noise_candidates": noise_candidates,
    }