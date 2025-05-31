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
      
      {/* Left wing - Egyptian style with elegant feathers */}
      <path d="M19 12 C17 9 14 7 10 7 C7 8 4 9 2 12 C4 15 7 16 10 17 C14 17 17 15 19 12 Z" />
      
      {/* Left wing feather details */}
      <path d="M18 10 C15 8 12 7 9 8" strokeWidth="0.5" />
      <path d="M17 9 C14 7 11 6 8 7" strokeWidth="0.5" />
      <path d="M16 8 C13 6 10 5 7 6" strokeWidth="0.5" />
      <path d="M18 14 C15 16 12 17 9 16" strokeWidth="0.5" />
      <path d="M17 15 C14 17 11 18 8 17" strokeWidth="0.5" />
      <path d="M16 16 C13 18 10 19 7 18" strokeWidth="0.5" />
      
      {/* Right wing - Egyptian style with elegant feathers */}
      <path d="M29 12 C31 9 34 7 38 7 C41 8 44 9 46 12 C44 15 41 16 38 17 C34 17 31 15 29 12 Z" />
      
      {/* Right wing feather details */}
      <path d="M30 10 C33 8 36 7 39 8" strokeWidth="0.5" />
      <path d="M31 9 C34 7 37 6 40 7" strokeWidth="0.5" />
      <path d="M32 8 C35 6 38 5 41 6" strokeWidth="0.5" />
      <path d="M30 14 C33 16 36 17 39 16" strokeWidth="0.5" />
      <path d="M31 15 C34 17 37 18 40 17" strokeWidth="0.5" />
      <path d="M32 16 C35 18 38 19 41 18" strokeWidth="0.5" />
    </svg>
  )
}

export default WingedSolarIcon
