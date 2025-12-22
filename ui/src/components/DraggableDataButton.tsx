import React, { useState, useRef, useEffect } from 'react'
import { Database } from 'lucide-react'

interface DraggableDataButtonProps {
    onClick: () => void
    visible: boolean
}

const DraggableDataButton: React.FC<DraggableDataButtonProps> = ({ onClick, visible }) => {
    const buttonRef = useRef<HTMLButtonElement>(null)

    // 初始位置：右侧居中
    // 使用 fixed 定位，left/top 控制
    // 初始 x 设为极大值以吸附右侧，y 设为 window.innerHeight / 2
    const [position, setPosition] = useState({ x: 0, y: 0 })
    const [isDragging, setIsDragging] = useState(false)

    // 用于判断是点击还是拖拽
    const dragStartPos = useRef({ x: 0, y: 0 })
    const hasMoved = useRef(false)

    // 初始化位置到右侧正中间
    useEffect(() => {
        setPosition({
            x: window.innerWidth - 60, // 减去按钮宽度
            y: window.innerHeight / 2 - 25 // 减去按钮高度一半
        })
    }, [])

    const handleTouchStart = (e: React.TouchEvent) => {
        setIsDragging(true)
        hasMoved.current = false
        const touch = e.touches[0]
        dragStartPos.current = { x: touch.clientX, y: touch.clientY }
    }

    const handleTouchMove = (e: React.TouchEvent) => {
        if (!isDragging) return
        const touch = e.touches[0]

        // 计算移动距离
        const moveX = touch.clientX - dragStartPos.current.x
        const moveY = touch.clientY - dragStartPos.current.y

        if (Math.abs(moveX) > 5 || Math.abs(moveY) > 5) {
            hasMoved.current = true
        }

        // 限制在屏幕范围内
        const newX = Math.max(0, Math.min(window.innerWidth - 50, touch.clientX - 25))
        const newY = Math.max(0, Math.min(window.innerHeight - 50, touch.clientY - 25))

        setPosition({ x: newX, y: newY })
    }

    const handleTouchEnd = () => {
        setIsDragging(false)

        // 吸附逻辑：松手后自动吸附到左侧或右侧
        const screenWidth = window.innerWidth
        const threshold = screenWidth / 2

        let targetX = position.x
        if (position.x + 25 < threshold) {
            targetX = 10 // 左侧
        } else {
            targetX = screenWidth - 60 // 右侧
        }

        setPosition(prev => ({ ...prev, x: targetX }))
    }

    const handleClick = (e: React.MouseEvent) => {
        // 如果发生了明显的移动，则不触发点击
        if (hasMoved.current) {
            e.preventDefault()
            e.stopPropagation()
            return
        }
        onClick()
    }

    if (!visible) return null

    return (
        <button
            ref={buttonRef}
            onContextMenu={(e) => e.preventDefault()} // 防止长按弹出菜单
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            onClick={handleClick}
            className={`fixed z-[999] w-12 h-12 rounded-full glass border border-white/40 shadow-xl flex items-center justify-center text-primary-600 bg-white/80 backdrop-blur-lg transition-transform active:scale-95 ${isDragging ? 'cursor-grabbing scale-105' : 'cursor-default transition-all duration-300 ease-out'}`}
            style={{
                left: position.x,
                top: position.y,
                touchAction: 'none' // 防止页面滚动
            }}
        >
            <Database className="w-6 h-6" />
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse shadow-sm ring-1 ring-white" />
        </button>
    )
}

export default DraggableDataButton
