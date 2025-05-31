// frontend/src/components/WingedSolarIcon.tsx
import React from 'react'

interface WingedSolarIconProps {
  className?: string
  width?: number
  height?: number
}

const WingedSolarIcon: React.FC<WingedSolarIconProps> = ({ 
  className = "w-8 h-4 text-yellow-400", 
  width = 48, 
  height = 24 
}) => {
  return (
    <svg 
      className={className} 
      viewBox="0 0 48 24" 
      fill="currentColor"
      width={width}
      height={height}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Central sun disk */}
      <circle cx="24" cy="12" r="5" />
      
      {/* Left wing */}
      <path d="M19 12 Q16 8 12 8 Q8 8 4 10 Q2 11 2 12 Q2 13 4 14 Q8 16 12 16 Q16 16 19 12" />
      
      {/* Right wing */}
      <path d="M29 12 Q32 8 36 8 Q40 8 44 10 Q46 11 46 12 Q46 13 44 14 Q40 16 36 16 Q32 16 29 12" />
    </svg>
  )
}

export default WingedSolarIcon
