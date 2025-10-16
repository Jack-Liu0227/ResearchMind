import React from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '../utils'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  text?: string
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  className,
  text 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  }

  return (
    <div className={cn('flex items-center justify-center', className)}>
      <div className="flex flex-col items-center space-y-2">
        <Loader2 className={cn('animate-spin text-primary-600', sizeClasses[size])} />
        {text && (
          <span className="text-sm text-gray-600">{text}</span>
        )}
      </div>
    </div>
  )
}

export default LoadingSpinner