"""
结果验证模块

功能：
1. 验证分析结果的格式和完整性
2. 检测缺失字段
3. 验证数据类型
4. 提供验证报告
"""
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class ResultValidator:
    """结果验证器"""
    
    # 必需字段定义
    REQUIRED_FIELDS = {
        'paper_analysis': [
            'paper_id',
            'title',
            'authors',
            'abstract_zh',
            'key_info'
        ],
        'key_info': [
            'objective',
            'method',
            'result',
            'innovation'
        ]
    }
    
    # 字段类型定义
    FIELD_TYPES = {
        'paper_id': str,
        'title': str,
        'authors': list,
        'abstract_zh': str,
        'key_info': dict,
        'objective': str,
        'method': str,
        'result': str,
        'innovation': str
    }
    
    def __init__(self):
        """初始化结果验证器"""
        self.validation_stats = {
            'total': 0,
            'passed': 0,
            'failed': 0
        }
    
    def validate_paper_analysis(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证论文分析结果
        
        Args:
            result: 分析结果字典
        
        Returns:
            验证结果字典：
            {
                'is_valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'missing_fields': List[str],
                'type_errors': List[str]
            }
        """
        errors = []
        warnings = []
        missing_fields = []
        type_errors = []
        
        # 1. 检查必需字段
        for field in self.REQUIRED_FIELDS['paper_analysis']:
            if field not in result:
                missing_fields.append(field)
                errors.append(f"缺失必需字段: {field}")
            else:
                # 2. 检查字段类型
                expected_type = self.FIELD_TYPES.get(field)
                if expected_type and not isinstance(result[field], expected_type):
                    type_errors.append(f"{field}: 期望 {expected_type.__name__}, 实际 {type(result[field]).__name__}")
                    errors.append(f"字段类型错误: {field}")
                
                # 3. 检查字段内容
                if field == 'key_info' and isinstance(result[field], dict):
                    # 验证 key_info 的子字段
                    for sub_field in self.REQUIRED_FIELDS['key_info']:
                        if sub_field not in result[field]:
                            missing_fields.append(f"key_info.{sub_field}")
                            errors.append(f"缺失 key_info 子字段: {sub_field}")
                        else:
                            # 检查子字段类型
                            expected_sub_type = self.FIELD_TYPES.get(sub_field)
                            if expected_sub_type and not isinstance(result[field][sub_field], expected_sub_type):
                                type_errors.append(f"key_info.{sub_field}: 期望 {expected_sub_type.__name__}")
                                errors.append(f"key_info 子字段类型错误: {sub_field}")
                            
                            # 检查子字段是否为空
                            if not result[field][sub_field] or (isinstance(result[field][sub_field], str) and len(result[field][sub_field].strip()) == 0):
                                warnings.append(f"key_info.{sub_field} 为空")
        
        # 4. 检查可选字段的合理性
        if 'authors' in result and isinstance(result['authors'], list):
            if len(result['authors']) == 0:
                warnings.append("作者列表为空")
        
        if 'abstract_zh' in result and isinstance(result['abstract_zh'], str):
            if len(result['abstract_zh']) < 50:
                warnings.append(f"中文摘要过短（{len(result['abstract_zh'])} 字符）")
        
        # 5. 判断是否有效
        is_valid = len(errors) == 0
        
        # 6. 更新统计
        self.validation_stats['total'] += 1
        if is_valid:
            self.validation_stats['passed'] += 1
        else:
            self.validation_stats['failed'] += 1
        
        # 7. 记录日志
        paper_id = result.get('paper_id', 'unknown')
        if not is_valid:
            logger.warning(
                f"Validation failed for {paper_id}",
                errors_count=len(errors),
                warnings_count=len(warnings)
            )
        else:
            logger.info(f"Validation passed for {paper_id}")
        
        return {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'missing_fields': missing_fields,
            'type_errors': type_errors
        }
    
    def validate_batch_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证批量分析结果
        
        Args:
            results: 分析结果列表
        
        Returns:
            批量验证结果字典
        """
        total = len(results)
        valid_count = 0
        invalid_count = 0
        all_errors = []
        all_warnings = []
        
        for i, result in enumerate(results):
            validation = self.validate_paper_analysis(result)
            
            if validation['is_valid']:
                valid_count += 1
            else:
                invalid_count += 1
                all_errors.extend([f"[{i+1}] {err}" for err in validation['errors']])
            
            all_warnings.extend([f"[{i+1}] {warn}" for warn in validation['warnings']])
        
        return {
            'total': total,
            'valid': valid_count,
            'invalid': invalid_count,
            'validity_rate': valid_count / total if total > 0 else 0,
            'errors': all_errors,
            'warnings': all_warnings
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取验证统计"""
        stats = self.validation_stats.copy()
        if stats['total'] > 0:
            stats['pass_rate'] = stats['passed'] / stats['total']
        else:
            stats['pass_rate'] = 0
        return stats


# 全局结果验证器实例
_result_validator: Optional[ResultValidator] = None


def get_result_validator() -> ResultValidator:
    """获取全局结果验证器实例"""
    global _result_validator
    
    if _result_validator is None:
        _result_validator = ResultValidator()
    
    return _result_validator

