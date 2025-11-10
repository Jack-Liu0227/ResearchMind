"""
数据库模型定义

使用 SQLAlchemy ORM 管理用户、会话、计费配置等数据
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
from pathlib import Path

# 数据库文件路径
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "researchmind.db"

# 创建数据库引擎
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Bohrium 认证信息
    access_key = Column(String(64), unique=True, index=True, nullable=False, comment="Bohrium AccessKey（唯一标识）")
    access_key_hash = Column(String(64), index=True, comment="AccessKey 哈希值（用于快速查找）")
    client_name = Column(String(100), comment="Bohrium 客户端名称")
    
    # 用户信息
    email = Column(String(255), unique=True, index=True, comment="邮箱（可选，从 Bohrium 获取）")
    username = Column(String(100), comment="用户名（可选）")
    avatar_url = Column(String(500), comment="头像 URL（可选）")
    
    # 计费配置
    sku_id = Column(String(20), default="10048", comment="SKU ID")
    billing_enabled = Column(Boolean, default=True, comment="是否启用计费")
    
    # 配额管理
    total_photons_used = Column(Float, default=0.0, comment="累计使用光子数")
    total_tokens_used = Column(Integer, default=0, comment="累计使用 Token 数")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    last_login_at = Column(DateTime, comment="最后登录时间")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_verified = Column(Boolean, default=False, comment="是否已验证 AccessKey")
    
    # 关联关系
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    billing_records = relationship("BillingRecord", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """会话表"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False, comment="会话 ID")
    
    # 关联用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户 ID")
    user = relationship("User", back_populates="sessions")
    
    # 会话信息
    title = Column(String(200), default="新对话", comment="会话标题")
    agent_id = Column(String(100), comment="智能体 ID")
    
    # 统计信息
    message_count = Column(Integer, default=0, comment="消息数量")
    structure_count = Column(Integer, default=0, comment="结构数量")
    image_count = Column(Integer, default=0, comment="图片数量")
    
    # 计费统计
    total_tokens = Column(Integer, default=0, comment="累计 Token 数")
    total_photons = Column(Float, default=0.0, comment="累计光子数")
    charged = Column(Boolean, default=False, comment="是否已扣费")
    charged_photons = Column(Integer, default=0, comment="已扣费光子数")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否激活")
    
    # 关联关系
    billing_records = relationship("BillingRecord", back_populates="session", cascade="all, delete-orphan")


class BillingRecord(Base):
    """计费记录表"""
    __tablename__ = "billing_records"

    id = Column(Integer, primary_key=True, index=True)

    # 关联用户和会话
    # 🔧 优化：添加索引以加速查询
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户 ID")
    user = relationship("User", back_populates="billing_records")

    session_id = Column(Integer, ForeignKey("sessions.id"), index=True, comment="会话 ID（可选）")
    session = relationship("Session", back_populates="billing_records")

    # 计费信息
    tokens = Column(Integer, nullable=False, comment="Token 数量")
    photons = Column(Float, nullable=False, comment="光子数量")
    model = Column(String(100), comment="模型名称")

    # Bohrium API 调用信息
    biz_no = Column(String(50), unique=True, index=True, comment="业务流水号")
    charge_result = Column(JSON, comment="扣费结果（JSON）")
    charge_success = Column(Boolean, default=False, comment="扣费是否成功")

    # 元数据（注意：不能使用 metadata 作为字段名，因为 SQLAlchemy 保留了这个名字）
    extra_data = Column(JSON, comment="额外元数据（JSON）")

    # 时间戳
    # 🔧 优化：添加索引以加速按时间查询
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")

    # 🔧 优化：添加复合索引以加速常见查询
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),  # 按用户查询历史记录
        Index('idx_session_created', 'session_id', 'created_at'),  # 按会话查询历史记录
    )


class AuthToken(Base):
    """认证 Token 表（用于 JWT Token 黑名单）"""
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    
    # Token 信息
    token_hash = Column(String(64), unique=True, index=True, nullable=False, comment="Token 哈希值")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户 ID")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    revoked_at = Column(DateTime, comment="撤销时间")
    
    # 状态
    is_revoked = Column(Boolean, default=False, comment="是否已撤销")


def init_db():
    """初始化数据库（创建所有表）"""
    Base.metadata.create_all(bind=engine)
    print(f"✅ 数据库初始化完成: {DB_PATH}")


def get_db():
    """获取数据库会话（FastAPI 依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

