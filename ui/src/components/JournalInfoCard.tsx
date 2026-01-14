import React from 'react'

type BadgeProps = {
  children: React.ReactNode
  color?: 'blue' | 'indigo' | 'purple' | 'rose' | 'gray' | 'emerald'
  title?: string
}

const colorMap: Record<NonNullable<BadgeProps['color']>, string> = {
  blue: 'bg-blue-50 text-blue-700 ring-blue-200/70 shadow-sm',
  indigo: 'bg-indigo-50 text-indigo-700 ring-indigo-200/70 shadow-sm',
  purple: 'bg-purple-50 text-purple-700 ring-purple-200/70 shadow-sm',
  rose: 'bg-rose-50 text-rose-700 ring-rose-200/70 shadow-sm',
  gray: 'bg-slate-50 text-slate-700 ring-slate-200/70 shadow-sm',
  emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200/70 shadow-sm',
}

const Badge: React.FC<BadgeProps> = ({ children, color = 'gray', title }) => (
  <span
    title={title}
    className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold ring-1 ring-inset ${colorMap[color]} mr-2 mb-1`}
  >
    {children}
  </span>
)

export type JournalInfoCardProps = {
  journalName?: string
  doi?: string
  citedBy?: number
  impactFactor?: number
  fiveYearIF?: number
  jcrQuartile?: string
  jcrCategory?: string
  casQuartile?: string
  casTop?: boolean
  casSmallCategory?: string
  sci?: boolean
  ssci?: boolean
  ei?: boolean
  cscd?: boolean
  pkuCore?: boolean
  njuCore?: boolean
  sciTechCore?: boolean
  issn?: string
  eissn?: string
  publisher?: string
  country?: string
  sources?: string[] // e.g. ['OpenAlex', 'EasyScholar']
  loading?: boolean
}

const SkeletonRow: React.FC<{ width?: string }> = ({ width = 'w-40' }) => (
  <div className={`h-3 ${width} bg-slate-200/70 rounded animate-pulse`} />
)

const JournalInfoCard: React.FC<JournalInfoCardProps> = ({
  journalName,
  doi,
  citedBy,
  impactFactor,
  fiveYearIF,
  jcrQuartile,
  jcrCategory,
  casQuartile,
  casTop,
  casSmallCategory,
  sci,
  ssci,
  ei,
  cscd,
  pkuCore,
  njuCore,
  sciTechCore,
  issn,
  eissn,
  publisher,
  country,
  sources = [],
  loading,
}) => {
  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-3 h-5 w-56 bg-slate-200/70 rounded animate-pulse" />
        <div className="flex flex-wrap gap-x-2 gap-y-2 mb-4">
          <SkeletonRow width="w-20" />
          <SkeletonRow width="w-24" />
          <SkeletonRow width="w-16" />
        </div>
        <div className="space-y-2">
          <SkeletonRow width="w-52" />
          <SkeletonRow width="w-64" />
          <SkeletonRow width="w-40" />
        </div>
      </div>
    )
  }

  const hasIF = typeof impactFactor === 'number' || typeof fiveYearIF === 'number'
  const hasQuartile = !!jcrQuartile || !!casQuartile
  const hasIndexing = sci || ssci || ei || cscd || pkuCore || njuCore || sciTechCore
  const hasMeta = issn || eissn || publisher || country

  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200/70 bg-gradient-to-br from-white via-slate-50 to-blue-50/40 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.08)]">
      <div className="pointer-events-none absolute -right-20 -top-16 h-48 w-48 rounded-full bg-blue-200/20 blur-3xl" />
      <div className="pointer-events-none absolute -left-12 -bottom-16 h-40 w-40 rounded-full bg-emerald-200/20 blur-3xl" />

      {/* Header */}
      <div className="relative z-10 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400 mb-1">期刊</div>
          <div className="text-lg font-semibold text-slate-900 leading-snug">
            {journalName || 'Unknown Journal'}
          </div>
          {sources.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-slate-600">
              <span className="text-slate-400">数据来源</span>
              {sources.map((source) => (
                <span key={source} className="px-2 py-0.5 rounded-full bg-white/80 ring-1 ring-slate-200/70 shadow-sm">
                  {source}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="text-right">
          {typeof citedBy === 'number' && (
            <div className="text-sm text-slate-700">
              <span className="text-slate-400 mr-1">被引</span>
              <span className="font-semibold">{citedBy}</span>
            </div>
          )}
          {doi && (
            <a
              href={`https://doi.org/${doi.replace(/^https?:\/\/doi\.org\//i, '')}`}
              target="_blank"
              rel="noreferrer"
              className="block text-[11px] text-blue-600 hover:text-blue-700 mt-1"
              title="打开 DOI"
            >
              {doi.replace(/^https?:\/\/doi\.org\//i, '')}
            </a>
          )}
        </div>
      </div>

      {/* Metrics */}
      {(hasIF || hasQuartile) && (
        <div className="relative z-10 mt-4 flex flex-wrap items-center">
          {typeof impactFactor === 'number' && (
            <Badge color="blue" title="影响因子">
              IF {impactFactor.toFixed(2)}
            </Badge>
          )}
          {typeof fiveYearIF === 'number' && (
            <Badge color="indigo" title="五年影响因子">
              5-year IF {fiveYearIF.toFixed(2)}
            </Badge>
          )}
          {jcrQuartile && (
            <Badge color="purple" title={jcrCategory || 'JCR 分区'}>
              JCR {jcrQuartile}
            </Badge>
          )}
          {casQuartile && (
            <Badge color="rose" title={casSmallCategory || '中科院分区'}>
              CAS {casQuartile}{casTop ? ' · Top' : ''}
            </Badge>
          )}
        </div>
      )}

      {/* Indexing */}
      {hasIndexing && (
        <div className="relative z-10 mt-3 flex flex-wrap">
          {sci && <Badge>SCI</Badge>}
          {ssci && <Badge>SSCI</Badge>}
          {ei && <Badge>EI</Badge>}
          {cscd && <Badge>CSCD</Badge>}
          {pkuCore && <Badge>北大核心</Badge>}
          {njuCore && <Badge>南大核心</Badge>}
          {sciTechCore && <Badge>科技核心</Badge>}
        </div>
      )}

      {/* Meta */}
      {hasMeta && (
        <div className="relative z-10 mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-slate-700">
          {issn && (
            <div className="rounded-lg bg-white/70 px-3 py-2 ring-1 ring-slate-200/70 shadow-sm">
              <span className="text-slate-400 mr-2">ISSN</span>
              <span className="font-medium">{issn}</span>
              {eissn && (
                <span className="ml-2 text-slate-500">
                  E-ISSN <span className="font-medium text-slate-700">{eissn}</span>
                </span>
              )}
            </div>
          )}
          {publisher && (
            <div className="rounded-lg bg-white/70 px-3 py-2 ring-1 ring-slate-200/70 shadow-sm">
              <span className="text-slate-400 mr-2">出版商</span>
              <span className="font-medium">{publisher}</span>
            </div>
          )}
          {country && (
            <div className="rounded-lg bg-white/70 px-3 py-2 ring-1 ring-slate-200/70 shadow-sm">
              <span className="text-slate-400 mr-2">国家/地区</span>
              <span className="font-medium">{country}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default JournalInfoCard
