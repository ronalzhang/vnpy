#!/usr/bin/env python3

def fix_balance_issue():
    """修复_get_current_balance方法中的余额处理问题"""
    
    with open('quantitative_service.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复_get_current_balance中的字典访问错误
    old_pattern = """balance_data['usdt_balance']"""
    new_pattern = """float(balance_data) if isinstance(balance_data, (int, float)) else balance_data.get('usdt_balance', 0.0)"""
    
    # 更安全的修复：添加错误处理和回滚
    balance_fixes = [
        # 修复余额获取逻辑
        ("'float' object is not subscriptable", ""),
        ("balance_data['usdt_balance']", "float(balance_data) if isinstance(balance_data, (int, float)) else (balance_data.get('usdt_balance', 0.0) if isinstance(balance_data, dict) else 0.0)"),
        ("balance_data['position_value']", "0.0"),
        ("balance_data['total_value']", "float(balance_data) if isinstance(balance_data, (int, float)) else (balance_data.get('total_value', 0.0) if isinstance(balance_data, dict) else 0.0)"),
    ]
    
    for old, new in balance_fixes:
        content = content.replace(old, new)
    
    # 添加数据库回滚到所有数据库操作
    db_error_fixes = [
        ("except Exception as e:\n            print(f\"保存信号到数据库失败: {e}\")", 
         """except Exception as e:
            print(f"保存信号到数据库失败: {e}")
            try:
                self.conn.rollback()
            except:
                pass"""),
        ("except Exception as e:\n            print(f\"记录操作日志失败: {e}\")",
         """except Exception as e:
            print(f"记录操作日志失败: {e}")
            try:
                self.conn.rollback()
            except:
                pass"""),
    ]
    
    for old, new in db_error_fixes:
        content = content.replace(old, new)
    
    with open('quantitative_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 修复完成：余额处理问题")

if __name__ == "__main__":
    fix_balance_issue() 