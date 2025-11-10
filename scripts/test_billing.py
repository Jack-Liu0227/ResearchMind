#!/usr/bin/env python3
"""
计费功能诊断脚本

用于测试 Bohrium API 扣费功能是否正常工作
"""

import os
import sys
import time
import secrets
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def test_bohrium_api(access_key: str, sku_id: str = "10048", photons: int = 1):
    """
    测试 Bohrium API 扣费功能
    
    Args:
        access_key: Bohrium AccessKey
        sku_id: SKU ID（默认 10048）
        photons: 扣费光子数（默认 1）
    
    Returns:
        测试结果字典
    """
    print("=" * 60)
    print("🧪 Bohrium API 扣费测试")
    print("=" * 60)
    
    # 1. 验证参数
    print(f"\n📋 测试参数:")
    print(f"  AccessKey: {access_key[:8]}...{access_key[-4:]}")
    print(f"  SKU ID: {sku_id}")
    print(f"  扣费光子数: {photons}")
    
    # 2. 生成 bizNo
    timestamp_ms = int(time.time() * 1000)
    rand_part = secrets.randbelow(10000)
    biz_no = (timestamp_ms % 10000000000) * 10000 + rand_part
    print(f"  BizNo: {biz_no}")
    
    # 3. 构造请求
    url = "https://openapi.dp.tech/openapi/v1/api/integral/consume"
    headers = {
        "accessKey": access_key,
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "ResearchMind/Test"
    }
    payload = {
        "bizNo": biz_no,
        "changeType": 1,
        "eventValue": int(photons),
        "skuId": int(sku_id),
        "scene": "appCustomizeCharge"
    }
    
    print(f"\n📤 请求信息:")
    print(f"  URL: {url}")
    print(f"  Headers: {headers}")
    print(f"  Payload: {payload}")
    
    # 4. 发送请求
    print(f"\n🚀 发送请求...")
    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=(10, 30),
            verify=True
        )
        
        print(f"\n📥 响应信息:")
        print(f"  状态码: {resp.status_code}")
        print(f"  响应头: {dict(resp.headers)}")
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"  响应体: {result}")
            
            # 检查是否成功
            is_success = result.get('success') or (result.get('code') == 0)
            
            if is_success:
                print(f"\n✅ 扣费成功！")
                return {
                    'success': True,
                    'message': '扣费成功',
                    'response': result
                }
            else:
                # 提取错误信息
                error_msg = '未知错误'
                if 'error' in result and isinstance(result['error'], dict):
                    error_msg = result['error'].get('msg') or result['error'].get('message') or error_msg
                elif 'message' in result:
                    error_msg = result['message']
                elif 'msg' in result:
                    error_msg = result['msg']
                
                print(f"\n❌ 扣费失败: {error_msg}")
                print(f"   错误代码: {result.get('code')}")
                return {
                    'success': False,
                    'message': error_msg,
                    'response': result
                }
        else:
            print(f"  响应体: {resp.text}")
            print(f"\n❌ API 请求失败: HTTP {resp.status_code}")
            return {
                'success': False,
                'message': f'API 请求失败: {resp.status_code}',
                'response': resp.text
            }
    
    except requests.exceptions.SSLError as e:
        print(f"\n❌ SSL 验证失败: {e}")
        return {
            'success': False,
            'message': f'SSL 验证失败: {e}'
        }
    except requests.exceptions.Timeout as e:
        print(f"\n❌ 请求超时: {e}")
        return {
            'success': False,
            'message': f'请求超时: {e}'
        }
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return {
            'success': False,
            'message': f'请求异常: {e}'
        }


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🔍 ResearchMind 计费功能诊断工具")
    print("=" * 60)
    
    # 1. 从环境变量读取配置
    access_key = os.getenv("BOHRIUM_ACCESS_KEY")
    sku_id = os.getenv("BOHRIUM_SKU_ID", "10048")
    
    # 2. 如果环境变量没有，提示用户输入
    if not access_key:
        print("\n⚠️ 未检测到环境变量 BOHRIUM_ACCESS_KEY")
        access_key = input("请输入您的 Bohrium AccessKey: ").strip()
    
    if not access_key:
        print("\n❌ AccessKey 不能为空！")
        sys.exit(1)
    
    # 3. 运行测试
    result = test_bohrium_api(access_key, sku_id, photons=1)
    
    # 4. 输出总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    if result['success']:
        print("✅ 计费功能正常工作！")
    else:
        print("❌ 计费功能异常！")
        print(f"   错误信息: {result['message']}")
        print("\n💡 可能的原因:")
        print("   1. AccessKey 无效或已过期")
        print("   2. 账户余额不足")
        print("   3. 网络连接问题")
        print("   4. Bohrium API 服务异常")
    print("=" * 60)


if __name__ == "__main__":
    main()

