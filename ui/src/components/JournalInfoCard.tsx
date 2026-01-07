import React from 'react'

type BadgeProps = {
  children: React.ReactNode
  color?: 'blue' | 'indigo' | 'purple' | 'rose' | 'gray' | 'emerald'
  title?: string
}

const colorMap: Record<NonNullable<BadgeProps['color']>, string> = {
  blue: 'bg-blue-50 text-blue-700 ring-blue-200',
  indigo: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  purple: 'bg-purple-50 text-purple-700 ring-purple-200',
  rose: 'bg-rose-50 text-rose-700 ring-rose-200',
  gray: 'bg-gray-50 text-gray-700 ring-gray-200',
  emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
}

const Badge: React.FC<BadgeProps> = ({ children, color = 'gray', title }) => (
  <span
    title={title}
    className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ring-1 ring-inset ${colorMap[color]} mr-2 mb-1`}
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
  <div className={`h-3 ${width} bg-gray-200/70 rounded animate-pulse`} />
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
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-3 h-5 w-56 bg-gray-200/70 rounded animate-pulse" />
        <div className="flex flex-wrap gap-x-2 gap-y-2 mb-3">
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
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-gray-500 mb-1">期刊</div>
          <div className="text-lg font-semibold text-gray-900">
            {journalName || 'Unknown Journal'}
          </div>
          {sources.length > 0 && (
            <div className="mt-1 text-xs text-gray-500">数据来源：{sources.join(' · ')}</div>
          )}
        </div>
        <div className="text-right">
          {typeof citedBy === 'number' && (
            <div className="text-sm text-gray-700">
              <span className="text-gray-500 mr-1">被引</span>
              <span className="font-semibold">{citedBy}</span>
            </div>
          )}
          {doi && (
            <a
              href={`https://doi.org/${doi.replace(/^https?:\/\/doi\.org\//i, '')}`}
              target="_blank"
              rel="noreferrer"
              className="block text-xs text-blue-600 hover:text-blue-700 mt-1"
              title="打开 DOI"
            >
              {doi.replace(/^https?:\/\/doi\.org\//i, '')}
            </a>
          )}
        </div>
      </div>

      {/* Metrics */}
      {(hasIF || hasQuartile) && (
        <div className="mt-3 flex flex-wrap items-center">
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
        <div className="mt-3">
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
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-700">
          {issn && (
            <div>
              <span className="text-gray-500 mr-2">ISSN</span>
              <span className="font-medium">{issn}</span>
              {eissn && <span className="ml-2 text-gray-500">E-ISSN <span className="font-medium text-gray-700">{eissn}</span></span>}
            </div>
          )}
          {publisher && (
            <div>
              <span className="text-gray-500 mr-2">出版社</span>
              <span className="font-medium">{publisher}</span>
            </div>
          )}
          {country && (
            <div>
              <span className="text-gray-500 mr-2">国家/地区</span>
              <span className="font-medium">{country}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default JournalInfoCard

