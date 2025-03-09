#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="vnpy_cryptoarbitrage",
    version="1.0.0",
    author="VeighNa Team",
    author_email="vn.py@foxmail.com",
    license="MIT",
    description="VeighNa加密货币套利应用模块",
    
    # 指定包索引，以便pip搜索
    url="https://www.vnpy.com",
    
    # 打包要求
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "vnpy>=3.0.0",
        "ccxt>=1.40.0",
        "tabulate>=0.8.9",
    ]
) 