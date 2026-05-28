"""
配置加载模块。

这个文件只负责一件事：

读取 configs/ 目录下的配置文件，并合并成一个统一的配置对象。
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """配置加载失败时抛出的异常。"""


CONFIG_FILES = {
    "default": "default.yaml",
    "model": "model.yaml",
    "permission": "permission.yaml",
    "tools": "tools.yaml",
    "logging": "logging.yaml",
}


@dataclass
class AppConfig:
    """
    应用配置对象。

    data:
        合并后的配置字典。

    project_root:
        项目根目录。

    config_dir:
        configs/ 目录路径。
    """

    data: dict[str, Any]
    project_root: Path
    config_dir: Path

    def get(self, key: str, default: Any = None) -> Any:
        """
        按点号路径读取配置。

        示例：
            config.get("model.model")
            config.get("permission.mode")
            config.get("tools.file.read_file")

        如果路径不存在，则返回 default。
        """

        current: Any = self.data

        for part in key.split("."):
            if not isinstance(current, dict):
                return default

            if part not in current:
                return default

            current = current[part]

        return current

    def require(self, key: str) -> Any:
        """
        按点号路径读取配置。

        和 get() 的区别是：
        如果配置不存在，会直接抛出异常。

        适合读取必须存在的配置项。
        """

        value = self.get(key, default=None)

        if value is None:
            raise ConfigError(f"缺少必要配置项：{key}")

        return value

    def section(self, name: str) -> dict[str, Any]:
        """
        获取某个配置分区。

        示例：
            config.section("model")
            config.section("tools")
        """

        value = self.data.get(name, {})

        if not isinstance(value, dict):
            raise ConfigError(f"配置分区必须是字典类型：{name}")

        return value

    def env(self, name: str, default: str | None = None) -> str | None:
        """
        读取环境变量。

        例如：
            config.env("OPENAI_API_KEY")
        """

        return os.getenv(name, default)

    def to_dict(self) -> dict[str, Any]:
        """
        返回配置字典的深拷贝。

        使用深拷贝是为了避免外部代码误修改内部配置。
        """

        return copy.deepcopy(self.data)


def find_project_root(start: Path | None = None) -> Path:
    """
    从当前目录开始，向上查找项目根目录。
    """

    current = (start or Path.cwd()).resolve()

    for path in [current, *current.parents]:
        if (path / "configs").is_dir():
            return path

    raise ConfigError("无法找到项目根目录：当前目录及其父目录中都没有 configs/ 目录。")


def load_yaml_file(path: Path) -> dict[str, Any]:
    """
    读取单个 yaml 文件。

    空文件会被当作空字典处理。
    """

    if not path.exists():
        raise ConfigError(f"配置文件不存在：{path}")

    if not path.is_file():
        raise ConfigError(f"配置路径不是文件：{path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ConfigError(f"yaml 格式错误：{path}") from exc

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ConfigError(f"配置文件顶层必须是 yaml 对象：{path}")

    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    深度合并两个字典。

    override 会覆盖 base 中的同名配置。

    示例：
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": 10}}

        结果：
        {"a": {"b": 10, "c": 2}}
    """

    result = copy.deepcopy(base)

    for key, value in override.items():
        old_value = result.get(key)

        if isinstance(old_value, dict) and isinstance(value, dict):
            result[key] = deep_merge(old_value, value)
        else:
            result[key] = copy.deepcopy(value)

    return result


def load_config(config_dir: str | Path | None = None) -> AppConfig:
    """
    加载项目配置。

    读取顺序：
    1. default.yaml
    2. model.yaml
    3. permission.yaml
    4. tools.yaml
    5. logging.yaml

    合并后的结构大致是：

    {
        ...default.yaml 的内容,
        "model": model.yaml 的内容,
        "permission": permission.yaml 的内容,
        "tools": tools.yaml 的内容,
        "logging": logging.yaml 的内容
    }
    """

    if config_dir is None:
        project_root = find_project_root()
        config_path = project_root / "configs"
    else:
        config_path = Path(config_dir).expanduser().resolve()
        project_root = config_path.parent

    # 加载 .env 文件。
    # override=False 表示：系统环境变量优先级高于 .env。
    load_dotenv(project_root / ".env", override=False)

    # 先读取 default.yaml。
    # default.yaml 是全局基础配置。
    data = load_yaml_file(config_path / CONFIG_FILES["default"])

    # 其他配置文件作为独立分区挂到 data 中。
    for section_name in ["model", "permission", "tools", "logging"]:
        file_name = CONFIG_FILES[section_name]
        section_data = load_yaml_file(config_path / file_name)

        old_section = data.get(section_name, {})

        if isinstance(old_section, dict):
            data[section_name] = deep_merge(old_section, section_data)
        else:
            data[section_name] = section_data

    return AppConfig(
        data=data,
        project_root=project_root,
        config_dir=config_path,
    )


def get_config_summary(config: AppConfig) -> dict[str, Any]:
    """
    返回配置摘要。

    注意：
    这里不会打印真实 API Key。
    """

    api_key_env = config.get("model.api_key_env")
    api_key_loaded = bool(os.getenv(api_key_env)) if api_key_env else False

    return {
        "project": config.get("project", {}),
        "agent": config.get("agent", {}),
        "context": config.get("context", {}),
        "model": {
            "provider": config.get("model.provider"),
            "model": config.get("model.model"),
            "base_url": config.get("model.base_url"),
            "api_key_env": api_key_env,
            "api_key_loaded": api_key_loaded,
        },
        "permission": {
            "mode": config.get("permission.mode"),
            "allow_read_only": config.get("permission.allow_read_only"),
            "allow_file_write": config.get("permission.allow_file_write"),
            "allow_bash": config.get("permission.allow_bash"),
        },
        "tools": config.get("tools", {}),
        "logging": config.get("logging", {}),
    }