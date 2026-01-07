/**
 * EasyScholar API 服务
 * 用于获取期刊信息（影响因子、分区等）
 * API 文档: https://www.easyscholar.cc/console/user/open
 */

import { API_CONFIG } from '../constants'

// EasyScholar API 配置（从环境变量读取）
const EASYSCHOLAR_API_BASE = import.meta.env.VITE_EASYSCHOLAR_API_BASE || 'https://easyscholar.cc/open/getPublicationRank'
const EASYSCHOLAR_API_KEY = import.meta.env.VITE_EASYSCHOLAR_API_KEY || '20bdbb8588cd469d9af25d1cd6ae7640'

// Semantic Scholar API 配置（从环境变量读取）
const SEMANTIC_SCHOLAR_API_KEY = import.meta.env.VITE_SEMANTIC_SCHOLAR_API_KEY || ''

// 后端 API 基础 URL
const API_BASE_URL = API_CONFIG.API_BASE_URL

/**
 * 期刊信息接口
 */
export interface JournalInfo {
  // 基本信息
  journal_name?: string
  issn?: string
  eissn?: string
  
  // 影响因子
  impact_factor?: number
  five_year_impact_factor?: number
  
  // JCR 分区
  jcr_quartile?: string  // Q1, Q2, Q3, Q4
  jcr_category?: string
  
  // 中科院分区
  cas_quartile?: string  // 1区, 2区, 3区, 4区
  cas_top?: boolean      // 是否为 Top 期刊
  cas_small_category?: string
  
  // 其他索引
  ei?: boolean
  sci?: boolean
  ssci?: boolean
  cscd?: boolean
  
  // 核心期刊
  pku_core?: boolean     // 北大核心
  nju_core?: boolean     // 南大核心
  sci_tech_core?: boolean // 科技核心
  
  // 其他信息
  publisher?: string
  country?: string
  
  // 原始数据（用于调试）
  raw_data?: any
}

/**
 * 根据期刊名称查询期刊信息
 * @param journalName 期刊名称或缩写
 * @returns 期刊信息
 */
export async function getJournalInfo(journalName: string): Promise<JournalInfo | null> {
  if (!journalName || journalName.trim() === '') {
    console.warn('⚠️ [EasyScholar] 期刊名称为空')
    return null
  }

  try {
    console.log('📚 [EasyScholar] 查询期刊信息:', journalName)

    // 🔧 使用后端代理接口（避免 CORS 问题）
    const url = `/api/journal/info?journal_name=${encodeURIComponent(journalName)}`
    console.log('📡 [EasyScholar] 请求 URL:', url)

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    console.log('📥 [EasyScholar] 响应状态:', response.status, response.statusText)

    if (!response.ok) {
      console.error('❌ [EasyScholar] API 请求失败:', response.status, response.statusText)
      const errorText = await response.text()
      console.error('❌ [EasyScholar] 错误详情:', errorText)
      return null
    }

    const result = await response.json()
    console.log('✅ [EasyScholar] API 响应:', JSON.stringify(result, null, 2))

    // 检查响应状态
    if (result.status !== 'success' || !result.data) {
      console.error('❌ [EasyScholar] API 返回错误:', result.error)
      console.error('❌ [EasyScholar] result.status:', result.status)
      console.error('❌ [EasyScholar] result.data:', result.data)
      return null
    }

    console.log('📦 [EasyScholar] result.data:', JSON.stringify(result.data, null, 2))

    // 🔧 修复：后端返回的格式是 { status, data: { code, msg, data: {...} } }
    // 我们需要访问 result.data.data 才能获取真正的期刊信息
    const easyScholarData = result.data.data

    console.log('📦 [EasyScholar] easyScholarData:', JSON.stringify(easyScholarData, null, 2))

    if (!easyScholarData) {
      console.error('❌ [EasyScholar] API 返回的数据为空')
      console.error('❌ [EasyScholar] result.data.data 为空，完整 result.data:', result.data)
      return null
    }

    // 解析并返回期刊信息
    const parsed = parseJournalInfo(easyScholarData)
    console.log('✅ [EasyScholar] 解析后的期刊信息:', JSON.stringify(parsed, null, 2))
    return parsed
  } catch (error) {
    console.error('❌ [EasyScholar] 查询期刊信息失败:', error)
    if (error instanceof Error) {
      console.error('❌ [EasyScholar] 错误堆栈:', error.stack)
    }
    return null
  }
}

/**
 * OpenAlex 解析：根据 DOI 或标题解析被引数、期刊名、ISSN
 */
export async function resolvePaperViaOpenAlex(params: { doi?: string; title?: string }): Promise<{ cited_by_count?: number; journal_name?: string; issn?: string } | null> {
  const { doi, title } = params
  if (!doi && !title) return null
  try {
    const search = new URLSearchParams()
    if (doi) search.set('doi', doi)
    if (title) search.set('title', title)
    const res = await fetch(`/api/journal/resolve?${search.toString()}`, { headers: { 'Accept': 'application/json' } })
    if (!res.ok) return null
    const json = await res.json()
    if (json && json.status === 'success' && json.data) {
      const d = json.data
      return {
        cited_by_count: d.cited_by_count,
        journal_name: d.journal_name,
        issn: Array.isArray(d.issn) ? (d.issn[0] || undefined) : d.issn,
      }
    }
    return null
  } catch (e) {
    console.warn('OpenAlex resolve failed', e)
    return null
  }
}

/**
 * 从 DOI 获取期刊名称
 * @param doi DOI 标识符
 * @returns 期刊名称
 */
export async function getJournalNameFromDOI(doi: string): Promise<string | null> {
  try {
    console.log('🔍 [DOI] 从 DOI 获取期刊名称:', doi)

    // 🔧 使用后端代理接口（避免 CORS 问题）
    const cleanDoi = doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, '')
    const url = `/api/journal/name-from-doi?doi=${encodeURIComponent(cleanDoi)}`

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      console.warn('⚠️ [DOI] API 请求失败:', response.status)
      return null
    }

    const result = await response.json()

    if (result.status === 'success' && result.journal_name) {
      console.log('✅ [DOI] 从 DOI 获取期刊名称成功:', result.journal_name)
      return result.journal_name
    }

    console.warn('⚠️ [DOI] 无法获取期刊名称:', result.error)
    return null
  } catch (error) {
    console.error('❌ [DOI] 从 DOI 获取期刊名称失败:', error)
    return null
  }
}

/**
 * 学术出版商 URL 模式配置
 */
const ACADEMIC_PUBLISHERS = {
  'ScienceDirect': {
    patterns: ['sciencedirect.com/science/article'],
    doiPattern: /pii\/([A-Z0-9]+)/i,
  },
  'Springer': {
    patterns: ['link.springer.com/article', 'springer.com/article'],
    doiPattern: /article\/(10\.\d{4,9}\/[^\s?#]+)/i,
  },
  'Wiley': {
    patterns: ['onlinelibrary.wiley.com/doi'],
    doiPattern: /doi\/(10\.\d{4,9}\/[^\s?#]+)/i,
  },
  'IEEE': {
    patterns: ['ieeexplore.ieee.org/document', 'ieeexplore.ieee.org/abstract/document'],
    doiPattern: /document\/(\d+)/,
  },
  'Nature': {
    patterns: ['nature.com/articles'],
    doiPattern: /articles\/([a-z0-9\-]+)/i,
  },
  'JSTOR': {
    patterns: ['jstor.org/stable'],
    doiPattern: /stable\/(\d+)/,
  },
  'PubMed Central': {
    patterns: ['ncbi.nlm.nih.gov/pmc/articles'],
    doiPattern: /PMC(\d+)/,
  },
  'ACM Digital Library': {
    patterns: ['dl.acm.org/doi'],
    doiPattern: /doi\/(10\.\d{4,9}\/[^\s?#]+)/i,
  },
  'Taylor & Francis': {
    patterns: ['tandfonline.com/doi'],
    doiPattern: /doi\/(10\.\d{4,9}\/[^\s?#]+)/i,
  },
  'SAGE': {
    patterns: ['journals.sagepub.com/doi'],
    doiPattern: /doi\/(10\.\d{4,9}\/[^\s?#]+)/i,
  },
  'Elsevier': {
    patterns: ['elsevier.com/locate'],
    doiPattern: /10\.\d{4,9}\/[^\s?#]+/i,
  },
  'Oxford Academic': {
    patterns: ['academic.oup.com/'],
    doiPattern: /10\.\d{4,9}\/[^\s?#]+/i,
  },
  'Cambridge': {
    patterns: ['cambridge.org/core/journals'],
    doiPattern: /10\.\d{4,9}\/[^\s?#]+/i,
  },
}

/**
 * 判断 URL 是否为学术出版商
 * @param url 文献 URL
 * @returns 出版商名称或 null
 */
export function getPublisherName(url: string): string | null {
  const urlLower = url.toLowerCase()

  for (const [publisher, config] of Object.entries(ACADEMIC_PUBLISHERS)) {
    if (config.patterns.some(pattern => urlLower.includes(pattern.toLowerCase()))) {
      return publisher
    }
  }

  return null
}

/**
 * 判断是否为学术出版商 URL
 * @param url 文献 URL
 * @returns 是否为学术出版商
 */
export function isAcademicPublisher(url: string): boolean {
  return getPublisherName(url) !== null
}

/**
 * 从 URL 中提取 DOI（增强版）
 * @param url 文献 URL
 * @returns DOI 字符串或 null
 */
export function extractDOIFromURL(url: string): string | null {
  try {
    console.log('🔍 [DOI 提取] 从 URL 提取 DOI:', url)

    // 方法 1：从 doi.org 链接提取
    const doiOrgMatch = url.match(/doi\.org\/(10\.\d{4,9}\/[^\s?#]+)/)
    if (doiOrgMatch) {
      const doi = decodeURIComponent(doiOrgMatch[1])
      console.log('✅ [DOI 提取] 从 doi.org 链接提取成功:', doi)
      return doi
    }

    // 方法 2：从 URL 参数中提取 DOI
    const urlParams = new URLSearchParams(url.split('?')[1] || '')
    const doiParam = urlParams.get('doi')
    if (doiParam) {
      console.log('✅ [DOI 提取] 从 URL 参数提取成功:', doiParam)
      return doiParam
    }

    // 方法 3：使用出版商特定的模式提取
    const publisher = getPublisherName(url)
    if (publisher) {
      const config = ACADEMIC_PUBLISHERS[publisher as keyof typeof ACADEMIC_PUBLISHERS]
      if (config.doiPattern) {
        const match = url.match(config.doiPattern)
        if (match) {
          // 对于标准 DOI 格式，直接返回
          if (match[0].startsWith('10.')) {
            const doi = match[0].replace(/[?#].*$/, '') // 移除查询参数和锚点
            console.log(`✅ [DOI 提取] 从 ${publisher} URL 提取成功:`, doi)
            return doi
          }
          // 对于其他标识符，记录但不返回（需要进一步处理）
          console.log(`ℹ️ [DOI 提取] 从 ${publisher} 提取到标识符:`, match[1])
        }
      }
    }

    // 方法 4：从任意 URL 中提取标准 DOI 模式
    // DOI 格式：10.{prefix}/{suffix}
    // prefix: 4-9 位数字
    // suffix: 任意字符（字母、数字、符号）
    const doiMatch = url.match(/10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i)
    if (doiMatch) {
      const doi = doiMatch[0]
      console.log('✅ [DOI 提取] 从 URL 模式提取成功:', doi)
      return doi
    }

    console.log('ℹ️ [DOI 提取] URL 中未找到 DOI 模式')
    return null
  } catch (error) {
    console.error('❌ [DOI 提取] 提取失败:', error)
    return null
  }
}

/**
 * 从 Semantic Scholar API 获取 DOI
 * @param paperId Semantic Scholar Paper ID
 * @returns DOI 字符串或 null
 */
export async function getDOIFromSemanticScholar(paperId: string): Promise<string | null> {
  try {
    console.log('🔍 [Semantic Scholar] 查询 Paper ID:', paperId)

    // 🔧 使用后端代理接口（避免 CORS 问题）
    const cleanPaperId = paperId.replace(/^s2_/, '')
    const url = `/api/journal/doi?paper_id=${encodeURIComponent(cleanPaperId)}`

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      console.warn('⚠️ [Semantic Scholar] API 请求失败:', response.status)
      return null
    }

    const result = await response.json()

    if (result.status === 'success' && result.doi) {
      console.log('✅ [Semantic Scholar] 获取 DOI 成功:', result.doi)
      return result.doi
    }

    console.log('ℹ️ [Semantic Scholar] 该文献没有 DOI:', result.error)
    return null
  } catch (error) {
    console.error('❌ [Semantic Scholar] 获取 DOI 失败:', error)
    return null
  }
}

/**
 * 从 Semantic Scholar API 获取文献信息（包含 DOI 和期刊名称）
 * @param paperId Semantic Scholar Paper ID
 * @returns 文献信息对象 { doi, journal_name, venue } 或 null
 */
export async function getPaperInfoFromSemanticScholar(paperId: string): Promise<{
  doi?: string
  journal_name?: string
  venue?: string
} | null> {
  try {
    console.log('🔍 [Semantic Scholar] 查询文献完整信息:', paperId)

    // 🔧 使用后端代理接口（避免 CORS 问题）
    const cleanPaperId = paperId.replace(/^s2_/, '')
    const url = `/api/journal/paper-info?paper_id=${encodeURIComponent(cleanPaperId)}`

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      console.warn('⚠️ [Semantic Scholar] API 请求失败:', response.status)
      return null
    }

    const result = await response.json()

    if (result.status === 'success') {
      console.log('✅ [Semantic Scholar] 获取文献信息成功:', {
        doi: result.doi,
        journal_name: result.journal_name,
        venue: result.venue,
      })
      return {
        doi: result.doi,
        journal_name: result.journal_name,
        venue: result.venue,
      }
    }

    console.log('ℹ️ [Semantic Scholar] 该文献没有期刊信息:', result.error)
    return null
  } catch (error) {
    console.error('❌ [Semantic Scholar] 获取文献信息失败:', error)
    return null
  }
}

/**
 * 从 URL 提取期刊名称（增强版 - 支持 Tavily 智能识别）
 * @param url 文献 URL
 * @param paperId Semantic Scholar Paper ID（可选）
 * @param source 数据源（可选）
 * @param doi 已知的 DOI（可选，优先使用）
 * @returns 期刊名称
 */
export async function extractJournalNameFromURL(
  url: string,
  paperId?: string,
  source?: string,
  doi?: string
): Promise<string | null> {
  try {
    console.log('🔍 [URL] 从 URL 提取期刊名称:', url)
    console.log('📋 [URL] 参数:', { paperId, source, doi })

    // 🆕 检查是否为 arXiv（预印本无期刊）
    // 注意：只有纯 arXiv 来源才跳过，Tavily 可能包含 arXiv 链接但需要进一步处理
    if (source === 'arxiv' || (url.includes('arxiv.org') && !source)) {
      console.log('ℹ️ [URL] arXiv 预印本，无期刊信息')
      return null
    }

    // 🆕 优先级 1：如果已提供 DOI，直接使用
    if (doi) {
      console.log('📚 [URL] 使用已提供的 DOI:', doi)
      const journalName = await getJournalNameFromDOI(doi)
      if (journalName) {
        console.log('✅ [URL] 通过已提供的 DOI 获取期刊名称成功:', journalName)
        return journalName
      }
    }

    // 🆕 优先级 2：从 URL 中提取 DOI
    const extractedDOI = extractDOIFromURL(url)
    if (extractedDOI) {
      console.log('📚 [URL] 从 URL 提取到 DOI，调用 CrossRef API')
      const journalName = await getJournalNameFromDOI(extractedDOI)
      if (journalName) {
        console.log('✅ [URL] 通过提取的 DOI 获取期刊名称成功:', journalName)
        return journalName
      }
    }

    // 🆕 优先级 3：检查是否为已知学术出版商
    const publisher = getPublisherName(url)
    if (publisher) {
      console.log(`📚 [URL] 识别为学术出版商: ${publisher}`)
      // 即使无法提取 DOI，也标记为学术来源
      // 返回 null 但不报错，让调用方知道这是学术来源
      console.log(`ℹ️ [URL] ${publisher} 来源但无法提取 DOI，可能需要进一步处理`)
    }

    // 优先级 4：如果是 Semantic Scholar 来源，尝试通过 API 获取完整文献信息（包含 DOI 和期刊名称）
    if (source === 'semantic_scholar' && paperId) {
      console.log('📚 [URL] Semantic Scholar 来源，尝试通过 API 获取完整文献信息')
      console.log('📚 [URL] Paper ID:', paperId)
      const paperInfo = await getPaperInfoFromSemanticScholar(paperId)

      console.log('📚 [URL] Semantic Scholar API 返回结果:', paperInfo)

      if (paperInfo) {
        // 优先使用 journal_name 或 venue
        if (paperInfo.journal_name) {
          console.log('✅ [URL] 从 Semantic Scholar API 直接获取期刊名称成功:', paperInfo.journal_name)
          return paperInfo.journal_name
        }

        // 如果有 DOI，尝试通过 CrossRef 获取更准确的期刊名称
        if (paperInfo.doi) {
          console.log('📚 [URL] 从 Semantic Scholar API 获取到 DOI，调用 CrossRef API')
          const journalName = await getJournalNameFromDOI(paperInfo.doi)
          if (journalName) {
            console.log('✅ [URL] 通过 Semantic Scholar DOI 获取期刊名称成功:', journalName)
            return journalName
          } else {
            console.warn('⚠️ [URL] CrossRef API 未返回期刊名称')
          }
        } else {
          console.warn('⚠️ [URL] Semantic Scholar API 未返回 DOI')
        }
      } else {
        console.warn('⚠️ [URL] Semantic Scholar API 返回空值')
      }
    }

    // 🆕 优先级 5：Tavily 来源，智能解析 URL
    if (source === 'tavily_academic') {
      console.log('🔍 [Tavily] 智能解析 URL:', url)

      // 5.1 检查是否为 arXiv（预印本无期刊）
      if (url.includes('arxiv.org')) {
        console.log('ℹ️ [Tavily] 检测到 arXiv 链接，无期刊信息')
        return null
      }

      // 5.2 尝试从 URL 提取 DOI
      const doiMatch = url.match(/10\.\d{4,}\/[^\s]+/)
      if (doiMatch) {
        const extractedDoi = doiMatch[0]
        console.log('🔍 [Tavily] 从 URL 提取到 DOI:', extractedDoi)
        const journalName = await getJournalNameFromDOI(extractedDoi)
        if (journalName) {
          console.log('✅ [Tavily] 通过 DOI 获取期刊名称成功:', journalName)
          return journalName
        }
      }

      // 5.3 ScienceDirect - 尝试通过后端 API 获取
      if (url.includes('sciencedirect.com')) {
        console.log('🔍 [Tavily] 检测到 ScienceDirect 链接')
        const piiMatch = url.match(/pii\/([A-Z0-9]+)/)
        if (piiMatch) {
          const pii = piiMatch[1]
          console.log('📋 [Tavily] 提取到 PII:', pii)

          try {
            // 调用后端 PII 转 DOI 接口
            const response = await fetch(`${API_BASE_URL}/journal/pii-to-doi?pii=${pii}`)
            const data = await response.json()

            if (data.status === 'success' && data.doi) {
              console.log('✅ [Tavily] PII 转 DOI 成功:', data.doi)

              // 如果后端已经返回了期刊名称，直接使用
              if (data.journal_name) {
                console.log('✅ [Tavily] 从 PII 转 DOI 响应中获取期刊名称:', data.journal_name)
                return data.journal_name
              }

              // 否则，使用 DOI 查询期刊名称
              const journalName = await getJournalNameFromDOI(data.doi)
              if (journalName) {
                console.log('✅ [Tavily] 通过 DOI 获取期刊名称成功:', journalName)
                return journalName
              }
            } else {
              console.warn('⚠️ [Tavily] PII 转 DOI 失败:', data.error)
            }
          } catch (error) {
            console.error('❌ [Tavily] PII 转 DOI 请求失败:', error)
          }
        }
      }

      // 5.4 Springer - 尝试从 URL 提取信息
      if (url.includes('springer.com')) {
        console.log('🔍 [Tavily] 检测到 Springer 链接')

        // 5.4.1 尝试从 URL 提取 DOI（Springer 文章页面）
        // 例如：https://link.springer.com/article/10.1007/s00521-023-08234-y
        const springerArticleMatch = url.match(/\/article\/(10\.\d{4,}\/[^\s?]+)/)
        if (springerArticleMatch) {
          const extractedDoi = springerArticleMatch[1]
          console.log('🔍 [Tavily] 从 Springer 文章 URL 提取到 DOI:', extractedDoi)
          const journalName = await getJournalNameFromDOI(extractedDoi)
          if (journalName) {
            console.log('✅ [Tavily] 通过 Springer DOI 获取期刊名称成功:', journalName)
            return journalName
          }
        }

        // 5.4.2 尝试从 URL 提取 DOI（Springer 章节页面）
        // 例如：https://link.springer.com/chapter/10.1007/978-3-658-08460-8_85-1
        const springerChapterMatch = url.match(/\/chapter\/(10\.\d{4,}\/[^\s?]+)/)
        if (springerChapterMatch) {
          const extractedDoi = springerChapterMatch[1]
          console.log('🔍 [Tavily] 从 Springer 章节 URL 提取到 DOI:', extractedDoi)
          const journalName = await getJournalNameFromDOI(extractedDoi)
          if (journalName) {
            console.log('✅ [Tavily] 通过 Springer DOI 获取期刊名称成功:', journalName)
            return journalName
          }
        }

        // 5.4.3 Springer 期刊主页
        // 例如：https://link.springer.com/journal/10458
        const springerJournalMatch = url.match(/\/journal\/(\d+)/)
        if (springerJournalMatch) {
          const journalId = springerJournalMatch[1]
          console.log('📋 [Tavily] 提取到 Springer 期刊 ID:', journalId)

          try {
            // 调用后端 Springer 期刊信息接口
            const response = await fetch(`${API_BASE_URL}/journal/springer-journal-info?journal_id=${journalId}`)
            const data = await response.json()

            if (data.status === 'success' && data.journal_name) {
              console.log('✅ [Tavily] 从 Springer 期刊主页获取期刊名称成功:', data.journal_name)
              return data.journal_name
            } else {
              console.warn('⚠️ [Tavily] Springer 期刊信息获取失败:', data.error)
            }
          } catch (error) {
            console.error('❌ [Tavily] Springer 期刊信息请求失败:', error)
          }
        }

        // 5.4.4 Springer 参考文献条目或其他类型
        // 例如：https://link.springer.com/rwe/xxx
        if (url.includes('/rwe/')) {
          console.log('⚠️ [Tavily] Springer 参考文献条目，无法直接提取期刊信息')
        }
      }

      console.log('⚠️ [Tavily] 无法从 URL 提取期刊信息')
    }

    // 检查是否为 PubMed
    if (url.includes('pubmed.ncbi.nlm.nih.gov') || url.includes('ncbi.nlm.nih.gov/pubmed')) {
      console.log('ℹ️ [URL] PubMed 链接，需要进一步解析')
      return null
    }

    // 其他情况
    if (publisher) {
      console.log(`ℹ️ [URL] ${publisher} 来源但无法获取期刊信息`)
    } else {
      console.log('ℹ️ [URL] 不支持的 URL 类型或无法提取期刊信息')
    }
    return null
  } catch (error) {
    console.error('❌ [URL] 从 URL 提取期刊名称失败:', error)
    return null
  }
}

/**
 * 批量查询期刊信息
 * @param journalNames 期刊名称列表
 * @returns 期刊信息映射表
 */
export async function batchGetJournalInfo(
  journalNames: string[]
): Promise<Map<string, JournalInfo>> {
  const results = new Map<string, JournalInfo>()

  // 并发查询（限制并发数为 5）
  const batchSize = 5
  for (let i = 0; i < journalNames.length; i += batchSize) {
    const batch = journalNames.slice(i, i + batchSize)
    const promises = batch.map(name => getJournalInfo(name))
    const batchResults = await Promise.all(promises)

    batch.forEach((name, index) => {
      const info = batchResults[index]
      if (info) {
        results.set(name, info)
      }
    })
  }

  return results
}

/**
 * 解析 EasyScholar API 返回的数据
 * 根据 EasyScholar API 的实际响应格式解析
 *
 * API 返回格式：
 * {
 *   "code": 200,
 *   "msg": "SUCCESS",
 *   "data": {
 *     "customRank": {...},
 *     "officialRank": {
 *       "all": { "sci": "Q1", "sciif": "64.8", "sciUpTop": "是", ... },
 *       "select": { ... }
 *     }
 *   }
 * }
 */
function parseJournalInfo(data: any): JournalInfo | null {
  if (!data) return null

  try {
    console.log('🔍 [解析] 开始解析期刊信息:', JSON.stringify(data, null, 2))

    const result: JournalInfo = {
      raw_data: data,
    }

    // 从 officialRank.all 中提取信息
    const officialRank = data.officialRank?.all || {}

    console.log('📊 [解析] officialRank.all:', JSON.stringify(officialRank, null, 2))

    // 🆕 提取期刊名称（从多个可能的字段）
    const journalName = data.publicationName || officialRank.publicationName || data.name || data.title
    if (journalName) {
      result.journal_name = journalName
      console.log('✅ [解析] 期刊名称:', journalName)
    }

    // 影响因子（尝试多个可能的字段名）
    const ifField = officialRank.sciif || officialRank.impactFactor || officialRank.if || officialRank['影响因子']
    if (ifField) {
      const ifValue = parseFloat(ifField)
      if (!isNaN(ifValue)) {
        result.impact_factor = ifValue
        console.log('✅ [解析] 影响因子:', ifValue)
      }
    }

    // 5年影响因子（尝试多个可能的字段名）
    const if5Field = officialRank.sciif5 || officialRank.fiveYearImpactFactor || officialRank.if5 || officialRank['5年影响因子']
    if (if5Field) {
      const if5Value = parseFloat(if5Field)
      if (!isNaN(if5Value)) {
        result.five_year_impact_factor = if5Value
        console.log('✅ [解析] 5年影响因子:', if5Value)
      }
    }

    // JCR 分区（尝试多个可能的字段名）
    const jcrField = officialRank.sci || officialRank.jcr || officialRank.jcrQuartile || officialRank['JCR分区']
    if (jcrField) {
      result.jcr_quartile = jcrField
      console.log('✅ [解析] JCR 分区:', jcrField)
    }

    // JCR 分类（尝试多个可能的字段名）
    const jcrCategoryField = officialRank.sciSmall || officialRank.jcrCategory || officialRank.category || officialRank['学科分类']
    if (jcrCategoryField) {
      result.jcr_category = jcrCategoryField
      console.log('✅ [解析] JCR 分类:', jcrCategoryField)
    }

    // SSCI 分区（尝试多个可能的字段名）
    const ssciField = officialRank.ssci || officialRank.ssciQuartile || officialRank['SSCI分区']
    if (ssciField) {
      result.jcr_quartile = result.jcr_quartile || ssciField
      console.log('✅ [解析] SSCI 分区:', ssciField)
    }

    // 中科院分区（尝试多个可能的字段名）
    const casField = officialRank.sciUp || officialRank.casQuartile || officialRank.cas || officialRank['中科院分区']
    if (casField) {
      result.cas_quartile = casField
      console.log('✅ [解析] 中科院分区:', casField)
    }

    // 中科院小类分区（尝试多个可能的字段名）
    const casSmallField = officialRank.sciUpSmall || officialRank.casSmallCategory || officialRank['中科院小类']
    if (casSmallField) {
      result.cas_small_category = casSmallField
      console.log('✅ [解析] 中科院小类分区:', casSmallField)
    }

    // 是否为 Top 期刊（尝试多个可能的字段名）
    const topField = officialRank.sciUpTop || officialRank.casTop || officialRank.top || officialRank['是否Top']
    if (topField) {
      result.cas_top = topField === '是' || topField === 'true' || topField === true || topField === 'Yes' || topField === 'YES'
      console.log('✅ [解析] Top 期刊:', result.cas_top)
    }

    // 索引标识
    result.ei = officialRank.eii === 'EI' || officialRank.eii === '是' || officialRank.eii === 'true'
    result.sci = !!officialRank.sci
    result.ssci = !!officialRank.ssci
    result.cscd = officialRank.cscd === '是' || officialRank.cscd === 'true'

    // 核心期刊
    result.pku_core = officialRank.pku === '是' || officialRank.pku === 'true'
    result.nju_core = officialRank.cssci === '是' || officialRank.cssci === 'true'

    // 🆕 其他信息
    if (officialRank.publisher || data.publisher) {
      result.publisher = officialRank.publisher || data.publisher
      console.log('✅ [解析] 出版商:', result.publisher)
    }

    if (officialRank.country || data.country) {
      result.country = officialRank.country || data.country
      console.log('✅ [解析] 国家:', result.country)
    }

    if (officialRank.issn || data.issn) {
      result.issn = officialRank.issn || data.issn
      console.log('✅ [解析] ISSN:', result.issn)
    }

    if (officialRank.eissn || data.eissn) {
      result.eissn = officialRank.eissn || data.eissn
      console.log('✅ [解析] E-ISSN:', result.eissn)
    }

    // 添加日志以便调试
    if (result.ei) {
      console.log('✅ [解析] EI 索引: true')
    }

    console.log('✅ [解析] 解析完成:', result)
    console.log('✅ [解析] 解析完成（详细）:', JSON.stringify(result, null, 2))
    return result
  } catch (error) {
    console.error('❌ [EasyScholar] 解析期刊信息失败:', error)
    console.error('原始数据:', data)
    return null
  }
}
