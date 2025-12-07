# 修复 Hydration 错误

## 问题原因

你看到的 "Hydration failed" 错误通常是由以下原因引起的：

1. **localStorage 数据损坏**
2. **浏览器扩展干扰**（如 React DevTools、Redux DevTools）
3. **Zustand persist 中间件的初始化问题**

## 快速修复步骤

### 方法 1：清除 localStorage（推荐）

1. 打开浏览器开发者工具（F12）
2. 进入 **Console** 标签
3. 运行以下命令：

```javascript
// 清除所有 ResearchMind 相关的存储
localStorage.clear()
sessionStorage.clear()

// 或者只清除特定的键
localStorage.removeItem('researchmind-app-store')
localStorage.removeItem('researchmind-version')

// 刷新页面
location.reload()
```

### 方法 2：禁用浏览器扩展

1. 打开浏览器的**无痕模式/隐私模式**
2. 访问应用：http://localhost:50010
3. 如果问题消失，说明是浏览器扩展导致的

常见干扰扩展：
- React Developer Tools
- Redux DevTools
- Grammarly
- 广告拦截器

### 方法 3：强制刷新

1. Windows/Linux: `Ctrl + Shift + R`
2. Mac: `Cmd + Shift + R`

### 方法 4：清除 Vite 缓存

```bash
cd ui
npm run clean:cache
npm run dev
```

## 代码修复（如果上述方法无效）

如果问题持续存在，可能需要修改代码：

### 修复 1：添加 SSR 检查

在 `ui/src/store/useAppStore.ts` 中，确保 persist 配置正确：

```typescript
export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // ... 你的状态
    }),
    {
      name: 'researchmind-app-store',
      // 🔧 添加这个配置
      skipHydration: false,
      // 🔧 添加错误处理
      onRehydrateStorage: () => (state, error) => {
        if (error) {
          console.error('Hydration error:', error)
          // 清除损坏的数据
          localStorage.removeItem('researchmind-app-store')
        }
      },
    }
  )
)
```

### 修复 2：延迟 localStorage 访问

在 `ui/src/main.tsx` 中：

```typescript
// 修改前
try {
  initStorage()
} catch (error) {
  console.error('存储初始化失败:', error)
}

// 修改后
if (typeof window !== 'undefined') {
  try {
    initStorage()
  } catch (error) {
    console.error('存储初始化失败:', error)
    // 清除损坏的数据
    localStorage.clear()
  }
}
```

## 验证修复

1. 清除所有缓存和存储
2. 重启开发服务器
3. 在无痕模式下访问应用
4. 检查控制台是否还有错误

## 预防措施

1. **定期清理 localStorage**：在应用更新时自动清理旧数据
2. **添加版本控制**：使用版本号管理存储数据格式
3. **错误边界**：添加 Error Boundary 捕获 Hydration 错误

## 如果问题仍然存在

请提供以下信息：

1. 浏览器类型和版本
2. 控制台的完整错误信息
3. localStorage 中的数据（运行 `console.log(localStorage)` 查看）
4. 是否在无痕模式下也出现问题

