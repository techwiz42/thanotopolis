// src/app/conversations/[id]/components/DownloadButton.tsx
import React from 'react';
import { Download } from 'lucide-react';

interface DownloadButtonProps {
  content: string;
  defaultFileName?: string;
}

export const DownloadButton: React.FC<DownloadButtonProps> = ({ 
  content, 
  defaultFileName = 'message.txt' 
}) => {
  const handleDownload = () => {
    // Extract plain text from HTML content if needed
    const extractText = (html: string): string => {
      const temp = document.createElement('div');
      temp.innerHTML = html;
      return temp.textContent || temp.innerText || html;
    };

    const textContent = content.includes('<') && content.includes('>') 
      ? extractText(content) 
      : content;

    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = defaultFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <button
      onClick={handleDownload}
      className="text-gray-600 hover:text-gray-900"
      aria-label="Download content"
    >
      <Download className="w-4 h-4" />
    </button>
  );
};
