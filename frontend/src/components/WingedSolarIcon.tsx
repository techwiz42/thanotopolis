import React from 'react'

interface WingedSolarIconProps {
  className?: string
  width?: number
  height?: number
}

const WingedSolarIcon: React.FC<WingedSolarIconProps> = ({ 
  className = "w-8 h-4", 
  width = 48, 
  height = 24 
}) => {
  return (
    <svg 
      className={className} 
      viewBox="0 0 200 60" 
      fill="none"
      stroke="black"
      strokeWidth="1.5"
      width={width}
      height={height}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Central sun disk */}
      <circle cx="100" cy="30" r="12" fill="white" stroke="black" strokeWidth="1.5" />
      
      {/* Left wing - main body section with scale pattern */}
      <path d="M88 30 C85 25 80 22 75 21 C70 20 65 20 60 22 C55 24 50 27 45 30 C50 33 55 36 60 38 C65 40 70 40 75 39 C80 38 85 35 88 30 Z" fill="white" />
      
      {/* Left wing scale pattern */}
      <g stroke="black" strokeWidth="1" fill="none">
        <path d="M82 26 C80 24 78 23 76 24 C74 25 74 27 76 28 C78 29 80 28 82 26" />
        <path d="M80 28 C78 26 76 25 74 26 C72 27 72 29 74 30 C76 31 78 30 80 28" />
        <path d="M78 30 C76 28 74 27 72 28 C70 29 70 31 72 32 C74 33 76 32 78 30" />
        <path d="M76 32 C74 30 72 29 70 30 C68 31 68 33 70 34 C72 35 74 34 76 32" />
        <path d="M74 34 C72 32 70 31 68 32 C66 33 66 35 68 36 C70 37 72 36 74 34" />
        
        <path d="M84 28 C82 26 80 25 78 26 C76 27 76 29 78 30 C80 31 82 30 84 28" />
        <path d="M82 30 C80 28 78 27 76 28 C74 29 74 31 76 32 C78 33 80 32 82 30" />
        <path d="M80 32 C78 30 76 29 74 30 C72 31 72 33 74 34 C76 35 78 34 80 32" />
        <path d="M78 34 C76 32 74 31 72 32 C70 33 70 35 72 36 C74 37 76 36 78 34" />
      </g>
      
      {/* Left wing individual feathers extending outward */}
      <path d="M45 30 C42 28 38 27 35 28 C32 29 30 31 30 33 C30 35 32 37 35 38 C38 39 42 38 45 36" fill="white" />
      <path d="M50 27 C47 25 43 24 40 25 C37 26 35 28 35 30 C35 32 37 34 40 35 C43 36 47 35 50 33" fill="white" />
      <path d="M55 25 C52 23 48 22 45 23 C42 24 40 26 40 28 C40 30 42 32 45 33 C48 34 52 33 55 31" fill="white" />
      <path d="M60 24 C57 22 53 21 50 22 C47 23 45 25 45 27 C45 29 47 31 50 32 C53 33 57 32 60 30" fill="white" />
      <path d="M65 24 C62 22 58 21 55 22 C52 23 50 25 50 27 C50 29 52 31 55 32 C58 33 62 32 65 30" fill="white" />
      <path d="M70 25 C67 23 63 22 60 23 C57 24 55 26 55 28 C55 30 57 32 60 33 C63 34 67 33 70 31" fill="white" />
      <path d="M75 26 C72 24 68 23 65 24 C62 25 60 27 60 29 C60 31 62 33 65 34 C68 35 72 34 75 32" fill="white" />
      <path d="M80 28 C77 26 73 25 70 26 C67 27 65 29 65 31 C65 33 67 35 70 36 C73 37 77 36 80 34" fill="white" />
      
      {/* Right wing - main body section with scale pattern */}
      <path d="M112 30 C115 25 120 22 125 21 C130 20 135 20 140 22 C145 24 150 27 155 30 C150 33 145 36 140 38 C135 40 130 40 125 39 C120 38 115 35 112 30 Z" fill="white" />
      
      {/* Right wing scale pattern */}
      <g stroke="black" strokeWidth="1" fill="none">
        <path d="M118 26 C120 24 122 23 124 24 C126 25 126 27 124 28 C122 29 120 28 118 26" />
        <path d="M120 28 C122 26 124 25 126 26 C128 27 128 29 126 30 C124 31 122 30 120 28" />
        <path d="M122 30 C124 28 126 27 128 28 C130 29 130 31 128 32 C126 33 124 32 122 30" />
        <path d="M124 32 C126 30 128 29 130 30 C132 31 132 33 130 34 C128 35 126 34 124 32" />
        <path d="M126 34 C128 32 130 31 132 32 C134 33 134 35 132 36 C130 37 128 36 126 34" />
        
        <path d="M116 28 C118 26 120 25 122 26 C124 27 124 29 122 30 C120 31 118 30 116 28" />
        <path d="M118 30 C120 28 122 27 124 28 C126 29 126 31 124 32 C122 33 120 32 118 30" />
        <path d="M120 32 C122 30 124 29 126 30 C128 31 128 33 126 34 C124 35 122 34 120 32" />
        <path d="M122 34 C124 32 126 31 128 32 C130 33 130 35 128 36 C126 37 124 36 122 34" />
      </g>
      
      {/* Right wing individual feathers extending outward */}
      <path d="M155 30 C158 28 162 27 165 28 C168 29 170 31 170 33 C170 35 168 37 165 38 C162 39 158 38 155 36" fill="white" />
      <path d="M150 27 C153 25 157 24 160 25 C163 26 165 28 165 30 C165 32 163 34 160 35 C157 36 153 35 150 33" fill="white" />
      <path d="M145 25 C148 23 152 22 155 23 C158 24 160 26 160 28 C160 30 158 32 155 33 C152 34 148 33 145 31" fill="white" />
      <path d="M140 24 C143 22 147 21 150 22 C153 23 155 25 155 27 C155 29 153 31 150 32 C147 33 143 32 140 30" fill="white" />
      <path d="M135 24 C138 22 142 21 145 22 C148 23 150 25 150 27 C150 29 148 31 145 32 C142 33 138 32 135 30" fill="white" />
      <path d="M130 25 C133 23 137 22 140 23 C143 24 145 26 145 28 C145 30 143 32 140 33 C137 34 133 33 130 31" fill="white" />
      <path d="M125 26 C128 24 132 23 135 24 C138 25 140 27 140 29 C140 31 138 33 135 34 C132 35 128 34 125 32" fill="white" />
      <path d="M120 28 C123 26 127 25 130 26 C133 27 135 29 135 31 C135 33 133 35 130 36 C127 37 123 36 120 34" fill="white" />
    </svg>
  )
}

export default WingedSolarIcon
