#!/bin/bash
# 快速测试 Bohrium API 扣费功能

echo "=========================================="
echo "🧪 Bohrium API 扣费快速测试"
echo "=========================================="

# 从 Cookie 读取 AccessKey（你需要替换为实际的值）
ACCESS_KEY="da9176e066244b..."  # 替换为完整的 AccessKey
SKU_ID="10048"
PHOTONS=1

# 生成 bizNo（使用时间戳）
BIZ_NO=$(date +%s%N | cut -b1-14)

echo ""
echo "📋 测试参数:"
echo "  AccessKey: ${ACCESS_KEY:0:8}...${ACCESS_KEY: -4}"
echo "  SKU ID: $SKU_ID"
echo "  扣费光子数: $PHOTONS"
echo "  BizNo: $BIZ_NO"

echo ""
echo "🚀 发送请求..."

# 发送请求
curl -X POST https://openapi.dp.tech/openapi/v1/api/integral/consume \
  -H "accessKey: $ACCESS_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: */*" \
  -H "User-Agent: ResearchMind/Test" \
  -d "{
    \"bizNo\": $BIZ_NO,
    \"changeType\": 1,
    \"eventValue\": $PHOTONS,
    \"skuId\": $SKU_ID,
    \"scene\": \"appCustomizeCharge\"
  }" \
  -w "\n\n📊 HTTP 状态码: %{http_code}\n" \
  -v

echo ""
echo "=========================================="
echo "✅ 测试完成"
echo "=========================================="

