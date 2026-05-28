"""
日志系统模块。

本模块负责根据 configs/logging.yaml 初始化项目日志系统。

解决三个问题：

1. 统一日志格式；
2. 根据配置文件控制日志等级；
3. 后续所有模块都通过 get_logger() 获取日志对象。

"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from miniclaudecode.services.config import AppConfig


# 项目根日志名称
LOGGER_NAME = "miniclaudecode"


def _to_log_level(level: str | None) -> int:
    """
    将字符串日志等级转换成 logging 模块需要的整数等级。

    例如：
        "debug"   -> logging.DEBUG
        "info"    -> logging.INFO
        "warning" -> logging.WARNING
    """

    if level is None:
        return logging.INFO

    level = level.lower().strip()

    mapping = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    return mapping.get(level, logging.INFO)


def _clear_handlers(logger: logging.Logger) -> None:
    """
    清空 logger 上已有的 handler。

    这样做是为了避免重复初始化 logger 时，出现日志重复打印的问题。
    """

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def _build_plain_formatter(show_time: bool, show_path: bool) -> logging.Formatter:
    """
    构建普通 logging 的格式化器。

    当 rich 不可用，或者用户关闭 rich 输出时，会使用这个 formatter。
    """

    parts: list[str] = []

    if show_time:
        parts.append("%(asctime)s")

    parts.append("%(levelname)s")
    parts.append("%(name)s")

    if show_path:
        parts.append("%(pathname)s:%(lineno)d")

    parts.append("%(message)s")

    fmt = " | ".join(parts)

    return logging.Formatter(
        fmt=fmt,
        datefmt="%H:%M:%S",
    )


def setup_logger(config: AppConfig) -> logging.Logger:
    """
    根据配置初始化项目 logger。

    参数
    ----
    config:
        由 load_config() 返回的 AppConfig 对象。

    返回
    ----
    logging.Logger:
        项目根 logger。
    """

    # 从 logging.yaml 中读取配置
    level_text = config.get("logging.level", "info")
    use_rich = bool(config.get("logging.use_rich", True))
    rich_traceback = bool(config.get("logging.rich_traceback", True))
    show_time = bool(config.get("logging.show_time", True))
    show_path = bool(config.get("logging.show_path", False))

    log_file_enabled = bool(config.get("logging.log_file.enabled", False))
    log_file_path = config.get("logging.log_file.path", "logs/miniclaude.log")

    log_level = _to_log_level(level_text)

    # 获取项目根 logger
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(log_level)

    # 禁止日志继续向 root logger 传播，避免重复打印
    logger.propagate = False

    # 每次初始化前清空旧 handler
    _clear_handlers(logger)

    # ----------------------------
    # 1. 终端日志 handler
    # ----------------------------

    if use_rich:
        try:
            from rich.logging import RichHandler
            from rich.traceback import install as install_rich_traceback

            if rich_traceback:
                install_rich_traceback(show_locals=False)

            console_handler = RichHandler(
                level=log_level,
                show_time=show_time,
                show_path=show_path,
                rich_tracebacks=rich_traceback,
                markup=True,
            )

            # RichHandler 自己负责美化等级、时间、路径
            # formatter 只保留消息本体即可
            console_handler.setFormatter(logging.Formatter("%(message)s"))

        except ImportError:
            # 如果没有安装 rich，就退回普通 logging 输出
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(
                _build_plain_formatter(show_time=show_time, show_path=show_path)
            )
    else:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            _build_plain_formatter(show_time=show_time, show_path=show_path)
        )

    logger.addHandler(console_handler)

    # ----------------------------
    # 2. 文件日志 handler
    # ----------------------------

    if log_file_enabled:
        file_path = Path(str(log_file_path))

        # 如果配置的是相对路径，则相对于项目根目录
        if not file_path.is_absolute():
            file_path = config.project_root / file_path

        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(log_level)

        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(pathname)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        logger.addHandler(file_handler)

    logger.debug("日志系统初始化完成")

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    获取项目 logger。

    参数
    ----
    name:
        子模块名称。

    示例
    ----
    get_logger()
        -> miniclaudecode

    get_logger("tools")
        -> miniclaudecode.tools

    get_logger("permissions.gate")
        -> miniclaudecode.permissions.gate
    """

    if not name:
        return logging.getLogger(LOGGER_NAME)

    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def log_config_summary(logger: logging.Logger, summary: dict[str, Any]) -> None:
    """
    打印配置摘要。

    这个函数主要用于开发阶段调试。
    """

    logger.info("当前配置摘要：")

    for section_name, section_value in summary.items():
        logger.info("  %s: %s", section_name, section_value)