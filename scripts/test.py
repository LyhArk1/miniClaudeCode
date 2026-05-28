"""
日志系统测试脚本。

运行方式：
    python scripts/test_logger.py

这个脚本用于测试：
1. 是否能读取 logging.yaml；
2. 是否能初始化 logger；
3. 是否能输出 debug / info / warning / error 日志；
4. 是否能创建子模块 logger。
"""

from pathlib import Path
import sys


# ============================================================
# 临时加入 src 路径
# ============================================================
# 因为当前项目采用 src/ 结构：
#
# miniClaudeCode/
# ├── scripts/
# │   └── test_logger.py
# └── src/
#     └── miniclaudecode/
#
# 直接运行 scripts/test_logger.py 时，Python 默认找不到 src/miniclaudecode。
# 所以这里手动把 src/ 加入 Python 模块搜索路径。
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))


from miniclaudecode.services.config import get_config_summary, load_config
from miniclaudecode.services.logger import get_logger, log_config_summary, setup_logger


def main() -> None:
    """测试 logger 是否可以正常工作。"""

    # 1. 加载配置
    config = load_config()

    # 2. 初始化日志系统
    logger = setup_logger(config)

    # 3. 测试不同等级的日志输出
    logger.debug("这是一条 DEBUG 日志，用于调试细节")
    logger.info("这是一条 INFO 日志，表示普通运行信息")
    logger.warning("这是一条 WARNING 日志，表示警告信息")
    logger.error("这是一条 ERROR 日志，表示错误信息")

    # 4. 测试子模块 logger
    tool_logger = get_logger("tools")
    tool_logger.info("这是 tools 模块输出的日志")

    permission_logger = get_logger("permissions.gate")
    permission_logger.warning("这是 permissions.gate 模块输出的日志")

    # 5. 打印配置摘要
    summary = get_config_summary(config)
    log_config_summary(logger, summary)

    logger.info("日志系统测试完成")


if __name__ == "__main__":
    main()