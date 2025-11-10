/**
 * Cookie 工具函数
 * 
 * 用于从浏览器 Cookie 中读取 Bohrium 凭证
 */

/**
 * 获取指定名称的 Cookie 值
 * 
 * @param name Cookie 名称
 * @returns Cookie 值，如果不存在则返回 null
 */
export function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift() || null
  }
  return null
}

/**
 * 设置 Cookie
 * 
 * @param name Cookie 名称
 * @param value Cookie 值
 * @param days 过期天数（默认 7 天）
 */
export function setCookie(name: string, value: string, days: number = 7): void {
  const expires = new Date()
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000)
  document.cookie = `${name}=${value}; expires=${expires.toUTCString()}; path=/`
}

/**
 * 删除 Cookie
 * 
 * @param name Cookie 名称
 */
export function deleteCookie(name: string): void {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/`
}

/**
 * 从 Cookie 获取 Bohrium 凭证
 *
 * ✅ 优先级 1：每次都从 Cookie 读取（实时、最新）
 *
 * @returns Bohrium 凭证对象
 */
export function getBohriumCredentials(): {
  appAccessKey: string | null
  clientName: string | null
} {
  const appAccessKey = getCookie('appAccessKey')
  const clientName = getCookie('clientName') || 'ResearchMind'

  // 🔍 调试日志
  console.log('🍪 读取 Cookie 凭证:', {
    appAccessKey: appAccessKey ? `${appAccessKey.substring(0, 8)}...` : 'null',
    clientName: clientName
  })

  return {
    appAccessKey,
    clientName
  }
}

/**
 * 检查是否存在 Bohrium Cookie
 * 
 * @returns 是否存在 appAccessKey Cookie
 */
export function hasBohriumCookie(): boolean {
  return getCookie('appAccessKey') !== null
}

/**
 * 设置 Bohrium 凭证到 Cookie
 * 
 * @param accessKey Bohrium AccessKey
 * @param clientName 客户端名称
 * @param days 过期天数（默认 7 天）
 */
export function setBohriumCredentials(
  accessKey: string,
  clientName: string = 'ResearchMind',
  days: number = 7
): void {
  setCookie('appAccessKey', accessKey, days)
  setCookie('clientName', clientName, days)
}

/**
 * 清除 Bohrium 凭证 Cookie
 */
export function clearBohriumCredentials(): void {
  deleteCookie('appAccessKey')
  deleteCookie('clientName')
}

/**
 * 获取所有 Cookie（用于调试）
 * 
 * @returns Cookie 对象
 */
export function getAllCookies(): Record<string, string> {
  const cookies: Record<string, string> = {}
  
  document.cookie.split(';').forEach(cookie => {
    const [name, value] = cookie.trim().split('=')
    if (name && value) {
      cookies[name] = value
    }
  })
  
  return cookies
}

/**
 * 打印 Cookie 信息（用于调试）
 */
export function debugCookies(): void {
  console.group('🍪 Cookie 信息')
  console.log('所有 Cookie:', getAllCookies())
  console.log('appAccessKey:', getCookie('appAccessKey'))
  console.log('clientName:', getCookie('clientName'))
  console.log('是否存在 Bohrium Cookie:', hasBohriumCookie())
  console.groupEnd()
}

