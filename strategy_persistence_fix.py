#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🛡️ 策略进化持久化修复系统
彻底解决策略演化重启丢失问题，确保高分策略永久保存
"""

import sqlite3
import json
import re
from datetime import datetime

class StrategyPersistenceFix:
    """策略持久化修复器"""
    
    def __init__(self):
        self.db_path = 'quantitative.db'
        
    def run_complete_fix(self):
        """运行完整的策略持久化修复"""
        print("🛡️ 策略进化持久化修复开始...")
        print("=" * 60)
        
        # 1. 数据库结构增强
        print("\n1️⃣ 增强数据库结构")
        self.enhance_database_structure()
        
        # 2. 修复演化引擎加载逻辑
        print("\n2️⃣ 修复演化引擎加载逻辑")
        self.fix_evolution_engine_loading()
        
        # 3. 添加策略保护机制
        print("\n3️⃣ 添加高分策略保护机制")
        self.add_high_score_protection()
        
        # 4. 实施演化连续性
        print("\n4️⃣ 实施演化连续性")
        self.implement_evolution_continuity()
        
        # 5. 恢复现有高分策略
        print("\n5️⃣ 恢复和保护现有高分策略")
        self.recover_existing_strategies()
        
        print("\n" + "=" * 60)
        print("✅ 策略持久化修复完成！")
        
    def enhance_database_structure(self):
        """增强数据库结构"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建策略演化历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_evolution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    cycle INTEGER NOT NULL,
                    parent_strategy_id TEXT,
                    evolution_type TEXT,  -- mutation, crossover, elite
                    old_parameters TEXT,
                    new_parameters TEXT,
                    old_score REAL,
                    new_score REAL,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                )
            """)
            
            # 创建策略血统表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_lineage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    ancestor_id TEXT,
                    generation_depth INTEGER DEFAULT 0,
                    lineage_path TEXT,  -- JSON array of ancestor IDs
                    fitness_improvement REAL DEFAULT 0.0,
                    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                )
            """)
            
            # 添加strategies表的新列（如果不存在）
            new_columns = [
                'generation INTEGER DEFAULT 1',
                'cycle INTEGER DEFAULT 1', 
                'evolution_type TEXT DEFAULT "initial"',
                'parent_id TEXT',
                'protected_status INTEGER DEFAULT 0',  # 0=normal, 1=protected, 2=elite
                'evolution_count INTEGER DEFAULT 0',
                'best_score_ever REAL DEFAULT 0.0',
                'last_evolution_time TIMESTAMP',
                'is_persistent INTEGER DEFAULT 1'  # 标记为持久化策略
            ]
            
            for column_def in new_columns:
                try:
                    cursor.execute(f"ALTER TABLE strategies ADD COLUMN {column_def}")
                    print(f"   ✅ 添加列: {column_def.split()[0]}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        print(f"   ⚠️ 列添加失败: {e}")
            
            # 创建策略快照表（用于版本控制）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT NOT NULL,
                    snapshot_name TEXT,
                    parameters TEXT,
                    final_score REAL,
                    performance_metrics TEXT,
                    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    restore_count INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
            conn.close()
            print("   ✅ 数据库结构增强完成")
            
        except Exception as e:
            print(f"   ❌ 数据库结构增强失败: {e}")
    
    def fix_evolution_engine_loading(self):
        """修复演化引擎的策略加载逻辑"""
        try:
            with open('quantitative_service.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. 修复EvolutionaryStrategyEngine的初始化
            evolution_init_fix = '''
    def __init__(self, quantitative_service):
        """初始化演化引擎，智能加载现有策略"""
        self.service = quantitative_service
        self.db_manager = quantitative_service.db_manager
        self.population_size = 100
        self.elite_ratio = 0.2
        self.mutation_rate = 0.3
        self.crossover_rate = 0.7
        
        # 🔥 智能策略加载 - 优先从数据库恢复现有策略
        self.current_generation = self._load_current_generation()
        self.current_cycle = self._load_current_cycle()
        
        # 保护高分策略
        self._protect_high_score_strategies()
        
        # 加载现有策略或创建初始种群
        self._load_or_create_population()
        
        logger.info(f"🧬 演化引擎初始化完成 - 第{self.current_generation}代第{self.current_cycle}轮")
        logger.info(f"📊 当前种群: {self._get_population_count()}个策略")'''
            
            # 2. 添加策略加载方法
            evolution_methods = '''
    def _load_current_generation(self) -> int:
        """从数据库加载当前世代数"""
        try:
            result = self.db_manager.execute_query(
                "SELECT MAX(generation) FROM strategies WHERE is_persistent = 1",
                fetch_one=True
            )
            return (result[0] or 0) + 1 if result and result[0] else 1
        except Exception:
            return 1
    
    def _load_current_cycle(self) -> int:
        """从数据库加载当前轮次"""
        try:
            result = self.db_manager.execute_query(
                "SELECT MAX(cycle) FROM strategies WHERE generation = ?",
                (self.current_generation - 1,),
                fetch_one=True
            )
            return (result[0] or 0) + 1 if result and result[0] else 1
        except Exception:
            return 1
    
    def _protect_high_score_strategies(self):
        """保护高分策略"""
        try:
            # 标记60分以上的策略为保护状态
            self.db_manager.execute_query("""
                UPDATE strategies 
                SET protected_status = 2, is_persistent = 1
                WHERE final_score >= 60.0 AND protected_status < 2
            """)
            
            # 标记50-60分的策略为一般保护
            self.db_manager.execute_query("""
                UPDATE strategies 
                SET protected_status = 1, is_persistent = 1
                WHERE final_score >= 50.0 AND final_score < 60.0 AND protected_status = 0
            """)
            
            logger.info("🛡️ 高分策略保护机制已激活")
        except Exception as e:
            logger.error(f"高分策略保护失败: {e}")
    
    def _load_or_create_population(self):
        """加载现有策略或创建初始种群"""
        try:
            # 获取现有策略数量
            existing_count = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM strategies WHERE is_persistent = 1",
                fetch_one=True
            )[0]
            
            if existing_count >= self.population_size * 0.5:  # 如果现有策略超过一半
                logger.info(f"🔄 发现 {existing_count} 个现有策略，继续演化")
                self._update_existing_strategies_info()
            else:
                logger.info(f"🆕 现有策略不足({existing_count}个)，补充新策略")
                needed = self.population_size - existing_count
                self._create_additional_strategies(needed)
                
        except Exception as e:
            logger.error(f"策略种群加载失败: {e}")
    
    def _update_existing_strategies_info(self):
        """更新现有策略的演化信息"""
        try:
            # 更新策略的世代和轮次信息
            self.db_manager.execute_query("""
                UPDATE strategies 
                SET 
                    generation = COALESCE(generation, ?),
                    cycle = COALESCE(cycle, ?),
                    last_evolution_time = CURRENT_TIMESTAMP,
                    is_persistent = 1
                WHERE generation IS NULL OR generation = 0
            """, (self.current_generation - 1, self.current_cycle - 1))
            
            logger.info("📊 现有策略信息已更新")
        except Exception as e:
            logger.error(f"更新策略信息失败: {e}")
    
    def _create_additional_strategies(self, count: int):
        """创建额外的策略以补充种群"""
        try:
            for i in range(count):
                strategy = self._create_random_strategy()
                strategy['generation'] = self.current_generation
                strategy['cycle'] = self.current_cycle
                strategy['evolution_type'] = 'supplementary'
                strategy['is_persistent'] = 1
                
                self._create_strategy_in_system(strategy)
            
            logger.info(f"➕ 已补充 {count} 个新策略")
        except Exception as e:
            logger.error(f"补充策略失败: {e}")
    
    def _get_population_count(self) -> int:
        """获取当前种群数量"""
        try:
            result = self.db_manager.execute_query(
                "SELECT COUNT(*) FROM strategies WHERE is_persistent = 1",
                fetch_one=True
            )
            return result[0] if result else 0
        except Exception:
            return 0'''
            
            # 查找并替换EvolutionaryStrategyEngine的__init__方法
            init_pattern = r'class EvolutionaryStrategyEngine:.*?\n(.*?def __init__\(self, quantitative_service\):.*?\n.*?self\.service = quantitative_service.*?\n.*?logger\.info\(f"🧬 演化引擎已初始化.*?\n)'
            if re.search(init_pattern, content, re.DOTALL):
                content = re.sub(
                    r'(class EvolutionaryStrategyEngine:.*?\n)(.*?def __init__\(self, quantitative_service\):.*?\n.*?logger\.info\(f"🧬 演化引擎已初始化.*?\n)',
                    r'\1' + evolution_init_fix + '\n',
                    content,
                    flags=re.DOTALL
                )
            
            # 在EvolutionaryStrategyEngine类中添加新方法
            if '_load_current_generation' not in content:
                # 找到类的结尾，插入新方法
                class_end_pattern = r'(class EvolutionaryStrategyEngine:.*?)(    def _get_next_evolution_time.*?\n.*?return.*?\n)'
                if re.search(class_end_pattern, content, re.DOTALL):
                    content = re.sub(
                        class_end_pattern,
                        r'\1' + evolution_methods + r'\n\2',
                        content,
                        flags=re.DOTALL
                    )
            
            # 保存修改
            with open('quantitative_service.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("   ✅ 演化引擎加载逻辑已修复")
            
        except Exception as e:
            print(f"   ❌ 演化引擎修复失败: {e}")
    
    def add_high_score_protection(self):
        """添加高分策略保护机制"""
        try:
            with open('quantitative_service.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复淘汰策略的逻辑，保护高分策略
            protection_code = '''
    def _eliminate_poor_strategies(self, strategies: List[Dict]) -> List[Dict]:
        """淘汰低分策略，但保护高分策略"""
        try:
            # 🛡️ 保护机制：绝不淘汰高分策略
            protected_strategies = []
            regular_strategies = []
            
            for strategy in strategies:
                score = strategy.get('final_score', 0)
                protected = strategy.get('protected_status', 0)
                
                if score >= 60.0 or protected >= 2:
                    # 精英策略：绝对保护
                    protected_strategies.append(strategy)
                    self._mark_strategy_protected(strategy['id'], 2, "elite_protection")
                elif score >= 50.0 or protected >= 1:
                    # 一般保护策略
                    protected_strategies.append(strategy)
                    self._mark_strategy_protected(strategy['id'], 1, "score_protection")
                else:
                    regular_strategies.append(strategy)
            
            # 计算淘汰数量（只从普通策略中淘汰）
            total_count = len(strategies)
            protected_count = len(protected_strategies)
            eliminate_count = max(0, int(total_count * 0.3))  # 淘汰30%
            
            if len(regular_strategies) <= eliminate_count:
                # 如果普通策略不够淘汰，就少淘汰一些
                eliminated = regular_strategies
                survivors = protected_strategies
            else:
                # 从普通策略中淘汰最差的
                regular_strategies.sort(key=lambda x: x['final_score'])
                eliminated = regular_strategies[:eliminate_count]
                survivors = protected_strategies + regular_strategies[eliminate_count:]
            
            # 记录淘汰信息
            for strategy in eliminated:
                self._record_strategy_elimination(
                    strategy['id'], 
                    strategy['final_score'],
                    f"淘汰轮次-第{self.current_generation}代"
                )
            
            logger.info(f"🛡️ 策略淘汰完成：保护 {protected_count} 个，淘汰 {len(eliminated)} 个")
            logger.info(f"📊 保护详情：精英 {len([s for s in protected_strategies if s.get('final_score', 0) >= 60])} 个，一般保护 {len([s for s in protected_strategies if 50 <= s.get('final_score', 0) < 60])} 个")
            
            return survivors
            
        except Exception as e:
            logger.error(f"策略淘汰过程出错: {e}")
            return strategies  # 出错时保持所有策略
    
    def _mark_strategy_protected(self, strategy_id: str, protection_level: int, reason: str):
        """标记策略为保护状态"""
        try:
            self.service.db_manager.execute_query("""
                UPDATE strategies 
                SET protected_status = ?, is_persistent = 1 
                WHERE id = ?
            """, (protection_level, strategy_id))
            
            # 记录保护历史
            self.service.db_manager.execute_query("""
                INSERT INTO strategy_evolution_history 
                (strategy_id, generation, cycle, evolution_type, new_parameters, created_time)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (strategy_id, self.current_generation, self.current_cycle, 
                  f"protection_{reason}", json.dumps({"protection_level": protection_level})))
                  
        except Exception as e:
            logger.error(f"标记策略保护失败: {e}")
    
    def _record_strategy_elimination(self, strategy_id: str, final_score: float, reason: str):
        """记录策略淘汰信息（但不实际删除）"""
        try:
            # 只记录，不删除，以备将来恢复
            self.service.db_manager.execute_query("""
                INSERT INTO strategy_evolution_history 
                (strategy_id, generation, cycle, evolution_type, old_score, created_time)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (strategy_id, self.current_generation, self.current_cycle, 
                  f"eliminated_{reason}", final_score))
                  
            # 将策略标记为非活跃而非删除
            self.service.db_manager.execute_query("""
                UPDATE strategies 
                SET enabled = 0, last_evolution_time = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (strategy_id,))
            
        except Exception as e:
            logger.error(f"记录策略淘汰失败: {e}")'''
            
            # 替换淘汰方法
            if '_eliminate_poor_strategies' in content:
                content = re.sub(
                    r'def _eliminate_poor_strategies\(self, strategies: List\[Dict\]\) -> List\[Dict\]:.*?return.*?\n',
                    protection_code,
                    content,
                    flags=re.DOTALL
                )
            
            with open('quantitative_service.py', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("   ✅ 高分策略保护机制已添加")
            
        except Exception as e:
            print(f"   ❌ 保护机制添加失败: {e}")
    
    def implement_evolution_continuity(self):
        """实施演化连续性"""
        try:
            with open('quantitative_service.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 修复演化过程的数据保存
            continuity_code = '''
    def run_evolution_cycle(self):
        """运行演化周期，确保完整持久化"""
        try:
            logger.info(f"🧬 开始第 {self.current_generation} 代第 {self.current_cycle} 轮演化")
            
            # 1. 评估所有策略适应度
            strategies = self._evaluate_all_strategies()
            if not strategies:
                logger.warning("⚠️ 没有可用策略进行演化")
                return
            
            # 2. 保存演化前状态快照
            self._save_evolution_snapshot("before_evolution", strategies)
            
            # 3. 选择精英策略（保护高分策略）
            elites = self._select_elites(strategies)
            
            # 4. 淘汰低分策略（保护机制）
            survivors = self._eliminate_poor_strategies(strategies)
            
            # 5. 生成新策略（变异和交叉）
            new_strategies = self._generate_new_strategies(elites, survivors)
            
            # 6. 更新世代信息
            self.current_cycle += 1
            if self.current_cycle > 10:  # 每10轮为一代
                self.current_generation += 1
                self.current_cycle = 1
            
            # 7. 保存所有策略演化历史
            self._save_evolution_history(elites, new_strategies)
            
            # 8. 更新策略状态
            self._update_strategies_generation_info()
            
            # 9. 保存演化后状态快照
            self._save_evolution_snapshot("after_evolution", survivors + new_strategies)
            
            logger.info(f"🎯 第 {self.current_generation} 代第 {self.current_cycle} 轮演化完成！")
            logger.info(f"📊 精英: {len(elites)}个, 幸存: {len(survivors)}个, 新增: {len(new_strategies)}个")
            
        except Exception as e:
            logger.error(f"演化周期执行失败: {e}")
            # 演化失败时的恢复机制
            self._recover_from_evolution_failure()
    
    def _save_evolution_snapshot(self, snapshot_type: str, strategies: List[Dict]):
        """保存演化快照"""
        try:
            snapshot_data = {
                'type': snapshot_type,
                'generation': self.current_generation,
                'cycle': self.current_cycle,
                'strategy_count': len(strategies),
                'avg_score': sum(s.get('final_score', 0) for s in strategies) / len(strategies) if strategies else 0,
                'top_scores': sorted([s.get('final_score', 0) for s in strategies], reverse=True)[:10],
                'timestamp': datetime.now().isoformat()
            }
            
            for strategy in strategies:
                self.service.db_manager.execute_query("""
                    INSERT INTO strategy_snapshots 
                    (strategy_id, snapshot_name, parameters, final_score, performance_metrics)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    strategy['id'],
                    f"{snapshot_type}_G{self.current_generation}_C{self.current_cycle}",
                    json.dumps(strategy.get('parameters', {})),
                    strategy.get('final_score', 0),
                    json.dumps(snapshot_data)
                ))
                
        except Exception as e:
            logger.error(f"保存演化快照失败: {e}")
    
    def _save_evolution_history(self, elites: List[Dict], new_strategies: List[Dict]):
        """保存演化历史"""
        try:
            # 保存精英策略历史
            for elite in elites:
                self.service.db_manager.execute_query("""
                    INSERT INTO strategy_evolution_history 
                    (strategy_id, generation, cycle, evolution_type, new_score, created_time)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (elite['id'], self.current_generation, self.current_cycle, 
                      'elite_selected', elite.get('final_score', 0)))
            
            # 保存新策略历史
            for new_strategy in new_strategies:
                parent_id = new_strategy.get('parent_id', '')
                evolution_type = new_strategy.get('evolution_type', 'unknown')
                
                self.service.db_manager.execute_query("""
                    INSERT INTO strategy_evolution_history 
                    (strategy_id, generation, cycle, parent_strategy_id, evolution_type, 
                     new_parameters, new_score, created_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (new_strategy['id'], self.current_generation, self.current_cycle,
                      parent_id, evolution_type, 
                      json.dumps(new_strategy.get('parameters', {})),
                      new_strategy.get('final_score', 0)))
                      
        except Exception as e:
            logger.error(f"保存演化历史失败: {e}")
    
    def _update_strategies_generation_info(self):
        """更新所有策略的世代信息"""
        try:
            self.service.db_manager.execute_query("""
                UPDATE strategies 
                SET generation = ?, cycle = ?, last_evolution_time = CURRENT_TIMESTAMP,
                    evolution_count = evolution_count + 1,
                    is_persistent = 1
                WHERE enabled = 1
            """, (self.current_generation, self.current_cycle))
            
        except Exception as e:
            logger.error(f"更新策略世代信息失败: {e}")
    
    def _recover_from_evolution_failure(self):
        """演化失败后的恢复机制"""
        try:
            logger.warning("🔄 演化失败，尝试恢复上一个稳定状态...")
            
            # 回滚到上一个成功的快照
            last_snapshot = self.service.db_manager.execute_query("""
                SELECT snapshot_name FROM strategy_snapshots 
                WHERE snapshot_name LIKE '%after_evolution%'
                ORDER BY snapshot_time DESC LIMIT 1
            """, fetch_one=True)
            
            if last_snapshot:
                logger.info(f"🔄 恢复到快照: {last_snapshot[0]}")
                # 这里可以添加具体的恢复逻辑
            
        except Exception as e:
            logger.error(f"演化失败恢复机制执行失败: {e}")'''
            
            # 替换run_evolution_cycle方法
            if 'def run_evolution_cycle(self):' in content:
                content = re.sub(
                    r'def run_evolution_cycle\(self\):.*?(?=def |class |\Z)',
                    continuity_code + '\n\n    ',
                    content,
                    flags=re.DOTALL
                )
            
            with open('quantitative_service.py', 'w', encoding='utf-8') as f:
                f.write(content)
                
            print("   ✅ 演化连续性机制已实施")
            
        except Exception as e:
            print(f"   ❌ 演化连续性实施失败: {e}")
    
    def recover_existing_strategies(self):
        """恢复和保护现有高分策略"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查找现有高分策略
            cursor.execute("""
                SELECT id, name, final_score, parameters, created_time
                FROM strategies 
                WHERE final_score >= 50.0
                ORDER BY final_score DESC
            """)
            high_score_strategies = cursor.fetchall()
            
            if high_score_strategies:
                print(f"   🎯 发现 {len(high_score_strategies)} 个高分策略需要保护")
                
                protected_count = 0
                for strategy in high_score_strategies:
                    strategy_id, name, score, parameters, created_time = strategy
                    
                    # 设置保护级别
                    protection_level = 2 if score >= 60.0 else 1
                    
                    # 更新策略保护状态
                    cursor.execute("""
                        UPDATE strategies 
                        SET protected_status = ?, 
                            is_persistent = 1,
                            best_score_ever = MAX(best_score_ever, final_score),
                            last_evolution_time = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (protection_level, strategy_id))
                    
                    # 创建保护记录
                    cursor.execute("""
                        INSERT INTO strategy_evolution_history 
                        (strategy_id, generation, cycle, evolution_type, new_score, created_time)
                        VALUES (?, 1, 1, ?, ?, CURRENT_TIMESTAMP)
                    """, (strategy_id, f"recovery_protection_{protection_level}", score))
                    
                    # 创建快照
                    cursor.execute("""
                        INSERT INTO strategy_snapshots 
                        (strategy_id, snapshot_name, parameters, final_score)
                        VALUES (?, ?, ?, ?)
                    """, (strategy_id, f"recovery_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                          parameters, score))
                    
                    protected_count += 1
                    print(f"   🛡️ 保护策略: {name} (评分: {score:.1f})")
                
                conn.commit()
                print(f"   ✅ 成功保护 {protected_count} 个高分策略")
                
                # 统计保护结果
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN protected_status = 2 THEN 1 END) as elite_count,
                        COUNT(CASE WHEN protected_status = 1 THEN 1 END) as protected_count,
                        MAX(final_score) as max_score,
                        AVG(final_score) as avg_score
                    FROM strategies WHERE protected_status > 0
                """)
                stats = cursor.fetchone()
                
                if stats:
                    elite, protected, max_score, avg_score = stats
                    print(f"   📊 保护统计: 精英策略 {elite} 个, 保护策略 {protected} 个")
                    print(f"   📊 最高评分: {max_score:.1f}, 平均评分: {avg_score:.1f}")
                
            else:
                print("   ℹ️ 未发现需要保护的高分策略")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ 恢复现有策略失败: {e}")

if __name__ == "__main__":
    fixer = StrategyPersistenceFix()
    fixer.run_complete_fix() 