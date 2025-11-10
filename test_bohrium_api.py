#!/usr/bin/env python3
"""
测试 Bohrium API 调用

用法：
    python test_bohrium_api.py <your_access_key>

示例：
    python test_bohrium_api.py sk-xxxxxxxxxxxxx
"""

import sys
import requests
import time
import secrets

def test_bohrium_api(access_key: str):
    """测试 Bohrium API 扣费接口"""
    
    # 生成唯一的 bizNo
    timestamp_ms = int(time.time() * 1000)
    rand_part = secrets.randbelow(10000)
    biz_no = (timestamp_ms % 10000000000) * 10000 + rand_part
    
    # API 配置
    url = "https://openapi.dp.tech/openapi/v1/api/integral/consume"
    
    # 请求头（完全按照官方 curl 示例）
    headers = {
        "accessKey": access_key,
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Host": "openapi.dp.tech",
        "Connection": "keep-alive"
    }
    
    # 请求体
    payload = {
        "bizNo": biz_no,
        "changeType": 1,
        "eventValue": 0,  # 测试用，扣 0 光子
        "skuId": 10048,   # 默认 SKU ID
        "scene": "appCustomizeCharge"
    }
    
    print("=" * 60)
    print("🧪 测试 Bohrium API 扣费接口")
    print("=" * 60)
    print(f"\n📤 请求 URL: {url}")
    print(f"\n📤 请求头:")
    for key, value in headers.items():
        if key == "accessKey":
            print(f"  {key}: {value[:8]}...{value[-4:]}")
        else:
            print(f"  {key}: {value}")
    
    print(f"\n📤 请求体:")
    for key, value in payload.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)
    print("🚀 发送请求...")
    print("=" * 60)
    
    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"\n📥 响应状态码: {resp.status_code}")
        print(f"\n📥 响应头:")
        for key, value in resp.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\n📥 响应内容:")
        print(resp.text)
        
        if resp.status_code == 200:
            result = resp.json()
            print("\n✅ 请求成功！")
            print(f"响应数据: {result}")
        elif resp.status_code == 401:
            print("\n❌ 认证失败 (401)")
            print("可能的原因：")
            print("  1. AccessKey 无效或已过期")
            print("  2. AccessKey 格式不正确")
            print("  3. 请求头格式不正确")
            print("\n💡 建议：")
            print("  - 访问 https://bohrium.dp.tech 重新获取 AccessKey")
            print("  - 确保 AccessKey 以 'sk-' 开头")
        else:
            print(f"\n❌ 请求失败: HTTP {resp.status_code}")
            
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_bohrium_api.py <your_access_key>")
        print("示例: python test_bohrium_api.py sk-xxxxxxxxxxxxx")
        sys.exit(1)
    
    access_key = sys.argv[1]
    
    if not access_key.startswith("sk-"):
        print("⚠️ 警告: AccessKey 通常以 'sk-' 开头，请确认您输入的是正确的 AccessKey")
        response = input("是否继续？(y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    test_bohrium_api(access_key)

