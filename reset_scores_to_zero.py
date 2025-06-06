
from db_config import get_db_adapter

def reset_scores_for_real_evaluation():
    """重置策略分数为0，准备启动真实评分系统"""
    try:
        print("🔄 重置策略分数为0，准备真实评分...")
        
        db_adapter = get_db_adapter()
        
        # 重置所有策略分数为0
        update_query = """
        UPDATE strategies 
        SET final_score = 0, 
            simulation_score = 0,
            fitness_score = 0,
            qualified_for_trading = 0,
            updated_at = CURRENT_TIMESTAMP
        """
        
        db_adapter.execute_query(update_query)
        
        print("✅ 策略分数重置完成，等待真实评分系统启动")
        return True
        
    except Exception as e:
        print(f"❌ 重置分数失败: {e}")
        return False

if __name__ == "__main__":
    reset_scores_for_real_evaluation()
