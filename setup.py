#!/usr/bin/env python3
"""
ResearchMind - 智能科研助手
基于Google Agent Developer Kit的科研智能体系统
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="researchmind",
    version="0.1.0",
    author="ResearchMind Team",
    author_email="contact@researchmind.ai",
    description="智能科研助手 - 基于Google ADK的全流程科研支持系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/researchmind/researchmind",
    packages=find_packages(include=["agents", "agents.*", "mcp_servers", "mcp_servers.*"]),
    package_dir={"": "."},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
        "jupyter": [
            "jupyter>=1.0.0",
            "ipykernel>=6.25.0",
            "jupyterlab>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "researchmind=main_mcp:main",
            "researchmind-test=test_agents:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": [
            "config/*.yaml",
            "docs/**/*.md",
            "examples/*.py",
        ],
    },
    zip_safe=False,
    keywords=[
        "artificial intelligence",
        "research assistant",
        "literature review",
        "materials science",
        "simulation",
        "experiment design",
        "google adk",
        "agent",
        "llm",
    ],
    project_urls={
        "Bug Reports": "https://github.com/researchmind/researchmind/issues",
        "Source": "https://github.com/researchmind/researchmind",
        "Documentation": "https://researchmind.readthedocs.io/",
    },
)
