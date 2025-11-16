"""
添加收费标准相关表和字段

执行方式：
python -m services.database.migrations.add_pricing_tables
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from services.database.models import Base, engine, User, Invitation, FeatureUsage
from sqlalchemy import inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """执行数据库迁移"""
    inspector = inspect(engine)

    # 1. 检查并添加 User 表的新字段
    logger.info("检查 User 表...")
    if inspector.has_table('users'):
        user_columns = [col['name'] for col in inspector.get_columns('users')]

        fields_to_add = []
        if 'free_chat_quota' not in user_columns:
            fields_to_add.append("ADD COLUMN free_chat_quota INTEGER DEFAULT 5")
        if 'free_chat_used' not in user_columns:
            fields_to_add.append("ADD COLUMN free_chat_used INTEGER DEFAULT 0")
        if 'invited_by' not in user_columns:
            fields_to_add.append("ADD COLUMN invited_by INTEGER")
        if 'invitation_code' not in user_columns:
            fields_to_add.append("ADD COLUMN invitation_code VARCHAR(20) UNIQUE")
        if 'invitation_count' not in user_columns:
            fields_to_add.append("ADD COLUMN invitation_count INTEGER DEFAULT 0")
        if 'invitation_rewards_total' not in user_columns:
            fields_to_add.append("ADD COLUMN invitation_rewards_total INTEGER DEFAULT 0")

        if fields_to_add:
            logger.info("添加 User 表新字段...")
            with engine.connect() as conn:
                for field in fields_to_add:
                    try:
                        conn.execute(text(f"ALTER TABLE users {field}"))
                        logger.info(f"  ✅ 添加字段: {field}")
                    except Exception as e:
                        logger.warning(f"  ⚠️ 字段可能已存在: {field} - {e}")
                conn.commit()
            logger.info("✅ User 表字段添加完成")
        else:
            logger.info("✅ User 表字段已存在，无需添加")

    # 2. 创建 Invitation 表
    if not inspector.has_table('invitations'):
        logger.info("创建 Invitation 表...")
        Invitation.__table__.create(engine)
        logger.info("✅ Invitation 表创建完成")
    else:
        logger.info("✅ Invitation 表已存在")

    # 3. 创建 FeatureUsage 表
    if not inspector.has_table('feature_usage'):
        logger.info("创建 FeatureUsage 表...")
        FeatureUsage.__table__.create(engine)
        logger.info("✅ FeatureUsage 表创建完成")
    else:
        logger.info("✅ FeatureUsage 表已存在")

    logger.info("🎉 数据库迁移完成！")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}", exc_info=True)
        sys.exit(1)

