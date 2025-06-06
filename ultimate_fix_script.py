#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
终极修复脚本 - 彻底解决所有重启和运行问题
"""

import subprocess
import time
import sys
import os

def run_command(command, description=""):
    """安全执行命令"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"✅ {description} - 成功")
            if result.stdout.strip():
                print(f"输出: {result.stdout.strip()}")
        else:
            print(f"❌ {description} - 失败")
            if result.stderr.strip():
                print(f"错误: {result.stderr.strip()}")
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - 超时")
        return False, "", "超时"
    except Exception as e:
        print(f"❌ {description} - 异常: {e}")
        return False, "", str(e)

def main():
    print("🚀 开始终极修复...")
    
    # 1. 检查本地文件语法
    print("\n=== 阶段1: 检查本地文件 ===")
    success, _, _ = run_command("python -m py_compile quantitative_service.py", "检查本地quantitative_service.py语法")
    if not success:
        print("❌ 本地文件有语法错误，请先修复")
        return False
    
    # 2. 强制清理并推送
    print("\n=== 阶段2: 推送最新代码 ===")
    run_command("git add -A", "添加所有更改")
    run_command("git commit -m '终极修复: 解决所有重启问题'", "提交更改")
    run_command("git push origin master", "推送到远程仓库")
    
    # 3. 服务器端完全重置
    print("\n=== 阶段3: 服务器端重置 ===")
    
    # 停止所有相关服务
    run_command("ssh -i baba.pem root@47.236.39.134 'pm2 stop quant-b'", "停止quant-b服务")
    run_command("ssh -i baba.pem root@47.236.39.134 'pm2 delete quant-b'", "删除quant-b进程")
    
    # 强制更新代码
    run_command("ssh -i baba.pem root@47.236.39.134 'cd /root/VNPY && git reset --hard HEAD'", "重置服务器代码")
    run_command("ssh -i baba.pem root@47.236.39.134 'cd /root/VNPY && git clean -fd'", "清理未跟踪文件")
    run_command("ssh -i baba.pem root@47.236.39.134 'cd /root/VNPY && git pull origin master'", "拉取最新代码")
    
    # 验证服务器文件
    success, stdout, _ = run_command("ssh -i baba.pem root@47.236.39.134 'cd /root/VNPY && python -m py_compile quantitative_service.py'", "验证服务器文件语法")
    if not success:
        print("❌ 服务器文件语法错误")
        return False
    
    # 4. 创建改进的启动配置
    print("\n=== 阶段4: 创建改进的启动配置 ===")
    
    # 创建新的PM2配置
    pm2_config = """
module.exports = {
  apps: [{
    name: 'quant-b',
    script: 'quantitative_service.py',
    interpreter: 'python',
    cwd: '/root/VNPY',
    max_memory_restart: '500M',
    restart_delay: 5000,
    max_restarts: 10,
    min_uptime: '10s',
    kill_timeout: 5000,
    wait_ready: true,
    listen_timeout: 8000,
    env: {
      PYTHONPATH: '/root/VNPY',
      NODE_ENV: 'production'
    },
    error_file: '/root/.pm2/logs/quant-b-error.log',
    out_file: '/root/.pm2/logs/quant-b-out.log',
    log_file: '/root/.pm2/logs/quant-b-combined.log'
  }]
};
"""
    
    # 上传PM2配置
    with open('temp_ecosystem.config.js', 'w') as f:
        f.write(pm2_config)
    
    run_command("scp -i baba.pem temp_ecosystem.config.js root@47.236.39.134:/root/VNPY/ecosystem.config.js", "上传PM2配置")
    os.remove('temp_ecosystem.config.js')
    
    # 5. 清理并重启服务
    print("\n=== 阶段5: 清理并重启服务 ===")
    
    # 清理PM2日志
    run_command("ssh -i baba.pem root@47.236.39.134 'pm2 flush'", "清理PM2日志")
    run_command("ssh -i baba.pem root@47.236.39.134 'rm -f /root/.pm2/logs/quant-b-*'", "删除旧日志文件")
    
    # 使用新配置启动
    run_command("ssh -i baba.pem root@47.236.39.134 'cd /root/VNPY && pm2 start ecosystem.config.js'", "使用新配置启动服务")
    
    # 6. 监控启动结果
    print("\n=== 阶段6: 监控启动结果 ===")
    
    for i in range(6):  # 监控30秒
        time.sleep(5)
        success, stdout, _ = run_command("ssh -i baba.pem root@47.236.39.134 'pm2 status'", f"检查状态 (第{i+1}次)")
        if success and "online" in stdout and "errored" not in stdout:
            print("✅ 服务启动成功！")
            
            # 检查重启次数
            if "↺" in stdout:
                restart_count = stdout.split("↺")[1].split()[0] if "↺" in stdout else "0"
                print(f"重启次数: {restart_count}")
                if int(restart_count) < 5:
                    print("🎉 服务稳定运行！")
                    return True
            break
        else:
            print(f"⚠️ 第{i+1}次检查 - 服务还未稳定")
    
    # 7. 如果还有问题，检查具体错误
    print("\n=== 阶段7: 问题诊断 ===")
    run_command("ssh -i baba.pem root@47.236.39.134 'pm2 logs quant-b --lines 20'", "查看最新日志")
    
    return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 终极修复成功！系统已稳定运行。")
    else:
        print("\n❌ 修复过程中遇到问题，需要进一步诊断。")
    
    sys.exit(0 if success else 1) 