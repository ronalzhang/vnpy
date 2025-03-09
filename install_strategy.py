import shutil
import os
import importlib
import site
from pathlib import Path

# 获取vnpy_spreadtrading安装路径
site_packages = site.getsitepackages()
for site_path in site_packages:
    spread_strategy_path = Path(site_path) / "vnpy_spreadtrading" / "strategies"
    if spread_strategy_path.exists():
        print(f"找到策略目录: {spread_strategy_path}")
        
        # 复制策略文件
        source_file = Path("crypto_arbitrage_strategy.py")
        if source_file.exists():
            target_file = spread_strategy_path / "crypto_arbitrage_strategy.py"
            shutil.copy(source_file, target_file)
            print(f"策略文件已复制到: {target_file}")
            
            # 修改__init__.py
            init_file = spread_strategy_path / "__init__.py"
            if init_file.exists():
                with open(init_file, "r") as f:
                    content = f.read()
                
                # 如果策略导入语句不存在，则添加
                import_line = "from .crypto_arbitrage_strategy import CryptoArbitrageStrategy"
                if import_line not in content:
                    with open(init_file, "a") as f:
                        f.write(f"\n{import_line}\n")
                    print("策略已添加到__init__.py")
                else:
                    print("策略已存在于__init__.py中")
                    
                break
        else:
            print(f"错误: 找不到策略文件 {source_file}")
            break
else:
    print("错误: 找不到vnpy_spreadtrading策略目录")

print("安装完成！") 