# Bohrium API 401 Error Diagnosis Guide

## Current Situation

You're getting a 401 authentication error when calling the Bohrium billing API:

```
❌ [计费] API 请求失败: HTTP 401
❌ [计费] 认证失败 (401): AccessKey 可能无效或已过期
🔍 [调试] 使用的 AccessKey: sk-43edc...dbe5
```

## Possible Causes

### 1. **Wrong Type of AccessKey**

The Bohrium platform may have different types of keys:
- **User AccessKey**: For personal API access
- **App AccessKey**: For application-level billing
- **OAuth Client Credentials**: For third-party applications

**Action**: Check if the AccessKey you're using is specifically for the **billing/integral API**.

### 2. **AccessKey from Wrong Location**

Based on your screenshot, you found the AccessKey in a specific location. However:
- Make sure it's from the **API Settings** or **Billing Settings** section
- Not from **OAuth Applications** or **Personal Tokens**

**Action**: Navigate to https://bohrium.dp.tech and look for:
- "API 密钥" (API Keys)
- "计费设置" (Billing Settings)  
- "开放平台" (Open Platform)

### 3. **Missing App Registration**

The billing API might require:
- Registering your application first
- Getting an **App ID** and **App Secret**
- Using those credentials instead of personal AccessKey

**Action**: Check if there's an "应用管理" (Application Management) section where you need to register ResearchMind.

### 4. **AccessKey Permissions**

The AccessKey might not have permission to call the billing API.

**Action**: Check the AccessKey's permissions/scopes in the Bohrium platform.

## Diagnostic Steps

### Step 1: Test with the diagnostic script

```bash
python test_bohrium_api.py sk-43edcc41b4794df892cde0e5c45bdbe5
```

This will show you the exact API response.

### Step 2: Check Bohrium Documentation

Visit the Bohrium platform and look for:
1. API documentation
2. Billing API specific requirements
3. Authentication guide

### Step 3: Compare with Working Example

If you have access to a working implementation (like the Flask example you mentioned), compare:
- The exact AccessKey format and source
- Any additional headers or parameters
- The API endpoint URL

### Step 4: Contact Bohrium Support

If the above doesn't work, you may need to:
1. Contact Bohrium support
2. Ask specifically about the `/openapi/v1/api/integral/consume` endpoint
3. Confirm the correct authentication method

## Alternative Solutions

### Option 1: Use Environment Variable for Testing

If you have a known working AccessKey, add it to `.env`:

```bash
BOHRIUM_ACCESS_KEY=your_working_access_key_here
```

Then modify the code to use it as a fallback for testing.

### Option 2: Disable Billing Temporarily

To continue development while investigating:

```bash
# In .env file
PHOTON_BILLING_ENABLED=false
```

This will disable actual billing calls but still track token usage.

## Next Steps

1. ✅ Run the test script to see the exact error response
2. ✅ Check the Bohrium platform for the correct AccessKey location
3. ✅ Verify the AccessKey has billing API permissions
4. ✅ If still failing, contact Bohrium support with the error details

## Questions to Answer

- [ ] Where exactly did you get the AccessKey? (Screenshot the page)
- [ ] Does the Bohrium platform show any API usage limits or quotas?
- [ ] Are there any error messages in the Bohrium platform dashboard?
- [ ] Do you have access to Bohrium's API documentation?

