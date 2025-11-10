# 登录门户（Login Gateway）

## 📋 概述

**登录门户**是一个全屏阻塞式登录界面，用户必须先输入 Bohrium AccessKey 才能进入主应用界面。

---

## 🎯 设计理念

### 方案选择：阻塞式登录门户

**为什么选择阻塞式？**

1. **功能完整性**：计费功能是核心功能，未登录时应该阻止用户进入主界面
2. **用户体验**：避免用户在未登录状态下操作，发现功能不可用后感到困惑
3. **符合习惯**：大多数应用都采用"先登录，后使用"的流程

---

## 🎨 界面设计

### 视觉效果

```
┌─────────────────────────────────────┐
│                                     │
│         🛡️ ResearchMind             │
│         请登录以继续使用             │
│                                     │
│   ┌─────────────────────────────┐   │
│   │  Bohrium AccessKey *        │   │
│   │  ┌───────────────────────┐  │   │
│   │  │ ••••••••••••••••••••  │  │   │
│   │  └───────────────────────┘  │   │
│   │                             │   │
│   │  客户端名称（可选）         │   │
│   │  ┌───────────────────────┐  │   │
│   │  │ ResearchMind          │  │   │
│   │  └───────────────────────┘  │   │
│   │                             │   │
│   │  [ 登录 ]                   │   │
│   │  [ 访问 Bohrium 平台 ]      │   │
│   │                             │   │
│   └─────────────────────────────┘   │
│                                     │
│  💡 提示：如果您已登录 Bohrium，    │
│  Cookie 会自动填充，无需手动输入   │
│                                     │
└─────────────────────────────────────┘
```

### 动画效果

1. **淡入动画**：门户背景淡入（0.3s）
2. **滑入动画**：登录卡片从下方滑入（0.4s）
3. **加载动画**：检查 Cookie 时显示旋转加载器
4. **成功动画**：登录成功后淡出门户

---

## 🔄 工作流程

### 1. 页面加载

```
用户访问应用
  ↓
显示加载动画（检查 Cookie）
  ↓
延迟 500ms（显示加载效果）
  ↓
检查 Cookie 是否存在
```

### 2. Cookie 存在

```
检测到 Cookie
  ↓
console.log('✅ 检测到 Cookie，自动跳过登录门户')
  ↓
调用 onAuthenticated() 回调
  ↓
门户消失，显示主界面
```

### 3. Cookie 不存在

```
未检测到 Cookie
  ↓
console.log('⚠️ 未检测到 Cookie，显示登录门户')
  ↓
显示登录表单
  ↓
用户输入 AccessKey
  ↓
点击"登录"按钮
  ↓
设置 Cookie（30 天有效期）
  ↓
toast.success('登录成功！')
  ↓
延迟 500ms（显示成功动画）
  ↓
调用 onAuthenticated() 回调
  ↓
门户消失，显示主界面
```

---

## 📝 代码实现

### 组件位置

- **文件**: `ui/src/components/LoginGateway.tsx`
- **集成**: `ui/src/App.tsx`

### 核心代码

```typescript
// App.tsx
const [isAuthenticated, setIsAuthenticated] = useState(false)

return (
  <StorageValidator>
    {/* 登录门户（阻塞式） */}
    {!isAuthenticated && (
      <LoginGateway onAuthenticated={() => setIsAuthenticated(true)} />
    )}

    {/* 主应用界面 */}
    <div className="min-h-screen bg-gray-50">
      <Router>
        {/* ... 路由 ... */}
      </Router>
    </div>
  </StorageValidator>
)
```

### 关键特性

1. **自动检测 Cookie**
   ```typescript
   useEffect(() => {
     const checkCookie = async () => {
       await new Promise(resolve => setTimeout(resolve, 500))
       
       if (hasBohriumCookie()) {
         onAuthenticated()
       } else {
         setChecking(false)
       }
     }
     checkCookie()
   }, [onAuthenticated])
   ```

2. **直接设置 Cookie**
   ```typescript
   const handleLogin = async () => {
     const expiryDays = 30
     const expiryDate = new Date()
     expiryDate.setDate(expiryDate.getDate() + expiryDays)
     
     document.cookie = `appAccessKey=${accessKey.trim()}; expires=${expiryDate.toUTCString()}; path=/`
     document.cookie = `clientName=${clientName.trim()}; expires=${expiryDate.toUTCString()}; path=/`
     
     toast.success('登录成功！')
     setTimeout(() => onAuthenticated(), 500)
   }
   ```

3. **支持回车键登录**
   ```typescript
   const handleKeyPress = (e: React.KeyboardEvent) => {
     if (e.key === 'Enter' && !loading) {
       handleLogin()
     }
   }
   ```

---

## 🎨 样式定制

### CSS 动画

```css
/* ui/src/index.css */

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out;
}

.animate-slide-up {
  animation: slide-up 0.4s ease-out;
}
```

### Tailwind 类名

- **背景渐变**: `bg-gradient-to-br from-blue-50 to-indigo-100`
- **卡片样式**: `bg-white rounded-2xl shadow-2xl`
- **按钮样式**: `bg-blue-500 hover:bg-blue-600`

---

## 🔍 调试方法

### 查看 Cookie 检测日志

```javascript
// 浏览器控制台
// 如果 Cookie 存在
✅ 检测到 Cookie，自动跳过登录门户

// 如果 Cookie 不存在
⚠️ 未检测到 Cookie，显示登录门户
```

### 手动触发登录门户

```javascript
// 清除 Cookie
document.cookie = 'appAccessKey=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
document.cookie = 'clientName=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';

// 刷新页面
window.location.reload();
```

---

## ✅ 优势

1. **强制登录**：用户必须先登录才能使用应用
2. **自动跳过**：已登录用户无感知，自动进入主界面
3. **优雅动画**：加载、登录、成功都有流畅的动画效果
4. **用户友好**：提供"访问 Bohrium 平台"链接，引导用户登录

---

## 📞 相关文档

- `docs/ARCHITECTURE_SIMPLIFICATION.md` - 架构简化说明
- `docs/COOKIE_PRIORITY_AUTHENTICATION.md` - Cookie 认证机制
- `docs/CLEAR_COOKIES_COMMANDS.md` - 清除 Cookie 命令

