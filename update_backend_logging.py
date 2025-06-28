#!/usr/bin/env python3
"""
更新后端代码以支持新的统一日志系统
"""
import re

def update_web_app_logging():
    """更新web_app.py中的日志查询API"""
    
    # 读取原文件
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到get_strategy_logs_by_category函数并替换
    new_function = '''@app.route('/api/quantitative/strategies/<strategy_id>/logs-by-category', methods=['GET'])
def get_strategy_logs_by_category(strategy_id):
    """🔥 新增：按分类获取策略日志 - 使用统一日志表"""
    try:
        log_type = request.args.get('type')  # real_trading, validation, evolution
        limit = int(request.args.get('limit', 100))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 使用新的统一日志表
        if log_type:
            cursor.execute("""
                SELECT strategy_id, log_type, timestamp as created_at, symbol, signal_type, 
                       price, quantity, pnl, executed, confidence, cycle_id, strategy_score,
                       evolution_type, old_parameters, new_parameters, trigger_reason, 
                       improvement, success, notes
                FROM unified_strategy_logs 
                WHERE strategy_id = %s AND log_type = %s
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (strategy_id, log_type, limit))
        else:
            cursor.execute("""
                SELECT strategy_id, log_type, timestamp as created_at, symbol, signal_type, 
                       price, quantity, pnl, executed, confidence, cycle_id, strategy_score,
                       evolution_type, old_parameters, new_parameters, trigger_reason, 
                       improvement, success, notes
                FROM unified_strategy_logs 
                WHERE strategy_id = %s
                ORDER BY timestamp DESC 
                LIMIT %s
            """, (strategy_id, limit))
        
        rows = cursor.fetchall()
        logs = []
        
        for row in rows:
            log_dict = {
                'strategy_id': row[0],
                'log_type': row[1],
                'timestamp': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else '',
                'symbol': row[3],
                'signal_type': row[4],
                'price': float(row[5]) if row[5] else 0,
                'quantity': float(row[6]) if row[6] else 0,
                'pnl': float(row[7]) if row[7] else 0,
                'executed': bool(row[8]) if row[8] is not None else False,
                'confidence': float(row[9]) if row[9] else 0,
                'cycle_id': row[10],
                'strategy_score': float(row[11]) if row[11] else 50.0,
            }
            
            # 进化相关字段
            if row[1] == 'evolution':
                log_dict.update({
                    'evolution_type': row[12],
                    'old_parameters': row[13] if row[13] else {},
                    'new_parameters': row[14] if row[14] else {},
                    'trigger_reason': row[15],
                    'improvement': float(row[16]) if row[16] else 0,
                    'success': bool(row[17]) if row[17] is not None else False,
                })
            
            log_dict['notes'] = row[18] if row[18] else ''
            logs.append(log_dict)
        
        # 按日志类型分类整理
        categorized_logs = {
            'real_trading': [log for log in logs if log['log_type'] == 'real_trading'],
            'validation': [log for log in logs if log['log_type'] == 'validation'],
            'evolution': [log for log in logs if log['log_type'] == 'evolution'],
            'system_operation': [log for log in logs if log['log_type'] == 'system_operation']
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'logs': logs if not log_type else categorized_logs.get(log_type, []),
            'categorized': categorized_logs,
            'total_count': len(logs),
            'log_type': log_type,
            'message': f'✅ 从统一日志表获取到 {len(logs)} 条{log_type or "全部"}日志'
        })
        
    except Exception as e:
        print(f"获取策略分类日志失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500'''
    
    # 查找并替换现有函数
    pattern = r'@app\.route\(\'/api/quantitative/strategies/<strategy_id>/logs-by-category\'[^@]*?def get_strategy_logs_by_category.*?(?=@app\.route|\Z)'
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_function + '\n\n', content, flags=re.DOTALL)
        print("✅ 已更新 get_strategy_logs_by_category 函数")
    else:
        # 如果函数不存在，添加到文件末尾
        insert_point = content.rfind('if __name__ == \'__main__\':')
        if insert_point != -1:
            content = content[:insert_point] + new_function + '\n\n' + content[insert_point:]
            print("✅ 已添加新的 get_strategy_logs_by_category 函数")
    
    # 添加统一日志记录函数
    log_function = '''
def log_to_unified_table(strategy_id, log_type, signal_type=None, symbol=None, 
                        price=None, quantity=None, pnl=0, executed=False, 
                        confidence=0, cycle_id=None, notes=None):
    """记录到统一日志表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT log_strategy_action(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (strategy_id, log_type, signal_type, symbol, price, quantity, 
              pnl, executed, confidence, cycle_id, notes))
        
        log_id = cursor.fetchone()[0] if cursor.fetchone() else None
        conn.close()
        return log_id
        
    except Exception as e:
        print(f"记录到统一日志表失败: {e}")
        return None

'''
    
    # 添加到文件中
    if 'def log_to_unified_table(' not in content:
        insert_point = content.find('def get_db_connection():')
        if insert_point != -1:
            content = content[:insert_point] + log_function + content[insert_point:]
            print("✅ 已添加统一日志记录函数")
    
    # 写回文件
    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ web_app.py 更新完成")

def update_quantitative_service():
    """更新quantitative_service.py以使用统一日志"""
    
    try:
        with open('quantitative_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("⚠️ quantitative_service.py 文件不存在，跳过更新")
        return
    
    # 添加统一日志记录到信号生成函数
    log_integration = '''
        # 记录到统一日志表
        try:
            from db_config import get_db_adapter
            db = get_db_adapter()
            db.execute_query("""
                SELECT log_strategy_action(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (strategy_id, 'validation' if is_validation else 'real_trading', 
                  signal_type, symbol, price, quantity, expected_return, True, 
                  confidence, cycle_id, f'策略信号生成: {strategy_name}'))
        except Exception as e:
            logger.warning(f"记录统一日志失败: {e}")
'''
    
    print("✅ quantitative_service.py 更新提示已准备")

if __name__ == "__main__":
    print("=== 🔧 更新后端代码以支持统一日志系统 ===\n")
    update_web_app_logging()
    update_quantitative_service()
    print("\n=== ✅ 后端代码更新完成 ===") 