#!/usr/bin/env python3
"""
Setup script for DataKwip MCP Connector
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="datakwip-mcp",
    version="1.0.0",
    author="DataKwip Team",
    description="A secure Model Context Protocol server with AWS Cognito OAuth2 authentication",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/datakwip/datakwip-mcp-connector",
    project_urls={
        "Bug Tracker": "https://github.com/datakwip/datakwip-mcp-connector/issues",
        "Documentation": "https://github.com/datakwip/datakwip-mcp-connector/blob/main/README.md",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "httpx>=0.25.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "datakwip-mcp=datakwip_mcp.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "datakwip_mcp": [
            "*.md",
            "config/*.json",
            "templates/*.html",
        ],
    },
    keywords=[
        "mcp",
        "model-context-protocol", 
        "oauth2",
        "aws-cognito",
        "fastapi",
        "security",
        "authentication",
        "datakwip"
    ],
    zip_safe=False,
)