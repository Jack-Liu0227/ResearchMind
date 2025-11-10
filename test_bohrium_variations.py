#!/usr/bin/env python3
"""
测试 Bohrium API 的多种配置组合
用于诊断 401 错误的根本原因
"""

import sys
import requests
import time
import secrets
import json

def test_api_variation(access_key: str, variation_name: str, headers: dict, payload: dict):
    """测试单个 API 配置变体"""
    
    url = "https://openapi.dp.tech/openapi/v1/api/integral/consume"
    
    print("\n" + "=" * 70)
    print(f"🧪 测试变体: {variation_name}")
    print("=" * 70)
    
    print(f"\n📤 请求头:")
    for key, value in headers.items():
        if key == "accessKey":
            print(f"  {key}: {value[:8]}...{value[-4:]}")
        else:
            print(f"  {key}: {value}")
    
    print(f"\n📤 请求体:")
    print(f"  {json.dumps(payload, indent=2)}")
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"\n📥 响应状态码: {resp.status_code}")
        print(f"📥 响应内容: {resp.text}")
        
        if resp.status_code == 200:
            print(f"\n✅ 成功！变体 '{variation_name}' 有效！")
            return True
        else:
            print(f"\n❌ 失败: HTTP {resp.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return False


def run_all_tests(access_key: str):
    """运行所有测试变体"""
    
    # 生成唯一的 bizNo
    timestamp_ms = int(time.time() * 1000)
    rand_part = secrets.randbelow(10000)
    biz_no = (timestamp_ms % 10000000000) * 10000 + rand_part
    
    print("=" * 70)
    print("🔍 Bohrium API 多变体测试")
    print("=" * 70)
    print(f"\nAccessKey: {access_key[:8]}...{access_key[-4:]}")
    print(f"BizNo: {biz_no}")
    
    # 基础 payload
    base_payload = {
        "bizNo": biz_no,
        "changeType": 1,
        "eventValue": 0,  # 测试用，扣 0 光子
        "skuId": 10048,
        "scene": "appCustomizeCharge"
    }
    
    # 测试变体列表
    variations = [
        # 变体 1: 只有 accessKey（原始方式）
        {
            "name": "仅 accessKey",
            "headers": {
                "accessKey": access_key,
                "Content-Type": "application/json",
                "Accept": "*/*"
            },
            "payload": base_payload.copy()
        },
        
        # 变体 2: accessKey + x-app-key (ResearchMind)
        {
            "name": "accessKey + x-app-key (ResearchMind)",
            "headers": {
                "accessKey": access_key,
                "x-app-key": "ResearchMind",
                "Content-Type": "application/json",
                "Accept": "*/*"
            },
            "payload": base_payload.copy()
        },
        
        # 变体 3: accessKey + x-app-key (空字符串)
        {
            "name": "accessKey + x-app-key (空)",
            "headers": {
                "accessKey": access_key,
                "x-app-key": "",
                "Content-Type": "application/json",
                "Accept": "*/*"
            },
            "payload": base_payload.copy()
        },
        
        # 变体 4: 不同的 SKU ID
        {
            "name": "SKU ID = 10049",
            "headers": {
                "accessKey": access_key,
                "x-app-key": "ResearchMind",
                "Content-Type": "application/json",
                "Accept": "*/*"
            },
            "payload": {**base_payload, "skuId": 10049}
        },
        
        # 变体 5: 不同的 scene
        {
            "name": "scene = customCharge",
            "headers": {
                "accessKey": access_key,
                "x-app-key": "ResearchMind",
                "Content-Type": "application/json",
                "Accept": "*/*"
            },
            "payload": {**base_payload, "scene": "customCharge"}
        },
    ]
    
    # 运行所有测试
    results = []
    for variation in variations:
        success = test_api_variation(
            access_key,
            variation["name"],
            variation["headers"],
            variation["payload"]
        )
        results.append((variation["name"], success))
        time.sleep(0.5)  # 避免请求过快
    
    # 总结
    print("\n" + "=" * 70)
    print("📊 测试总结")
    print("=" * 70)
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{status} - {name}")
    
    successful_count = sum(1 for _, success in results if success)
    print(f"\n总计: {successful_count}/{len(results)} 个变体成功")
    
    if successful_count == 0:
        print("\n⚠️ 所有变体均失败，可能的原因：")
        print("  1. AccessKey 本身无效或已过期")
        print("  2. AccessKey 没有调用此 API 的权限")
        print("  3. 需要在 Bohrium 平台注册应用")
        print("  4. API 端点或认证方式已变更")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_bohrium_variations.py <your_access_key>")
        print("示例: python test_bohrium_variations.py sk-xxxxxxxxxxxxx")
        sys.exit(1)
    
    access_key = sys.argv[1]
    run_all_tests(access_key)

