// src/app/conversations/[id]/components/FileDisplay.tsx
import React, { useState, useEffect } from 'react';
import { FileText, Edit } from 'lucide-react';

interface FileDisplayProps {
  content: string;
  fileName?: string;
  isUserMessage: boolean;
  onEdit?: () => void;
}

const FileDisplay: React.FC<FileDisplayProps> = ({ 
  content, 
  fileName = 'file.txt', 
  isUserMessage,
  onEdit 
}) => {
  const [displayContent, setDisplayContent] = useState<string>('');
  
  useEffect(() => {
    // Extract content from HTML if needed
    const extractContent = (html: string) => {
      // Check for file-content div
      const fileContentMatch = html.match(/<div class="file-content[^>]*>[\s\S]*?<pre[^>]*>[\s\S]*?<code[^>]*>([\s\S]*?)<\/code>[\s\S]*?<\/pre>[\s\S]*?<\/div>/);
      if (fileContentMatch) {
        return fileContentMatch[1]
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&amp;/g, '&')
          .replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'");
      }
      
      // Check for code-monkey-response
      const codeMonkeyMatch = html.match(/<div class="code-monkey-response[^>]*>[\s\S]*?<pre[^>]*>[\s\S]*?<code[^>]*>([\s\S]*?)<\/code>[\s\S]*?<\/pre>[\s\S]*?<\/div>/);
      if (codeMonkeyMatch) {
        return codeMonkeyMatch[1]
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&amp;/g, '&')
          .replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'");
      }
      
      return html;
    };
    
    setDisplayContent(extractContent(content));
  }, [content]);

  const getLanguageFromFileName = (name: string): string => {
    const ext = name.split('.').pop()?.toLowerCase() || '';
    const extToLang: { [key: string]: string } = {
      'py': 'python',
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'rb': 'ruby',
      'go': 'go',
      'rs': 'rust',
      'php': 'php',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'sql': 'sql',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'xml': 'xml',
      'json': 'json',
      'yaml': 'yaml',
      'yml': 'yaml',
      'md': 'markdown',
      'sh': 'bash',
      'bash': 'bash',
      'zsh': 'bash',
      'fish': 'bash',
    };
    return extToLang[ext] || 'plaintext';
  };

  const language = getLanguageFromFileName(fileName);

  return (
    <div className={`file-display rounded-lg overflow-hidden ${
      isUserMessage ? 'bg-blue-600' : 'bg-gray-100'
    }`}>
      <div className={`file-header flex items-center justify-between px-4 py-2 ${
        isUserMessage ? 'bg-blue-700 text-white' : 'bg-gray-200 text-gray-700'
      }`}>
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4" />
          <span className="text-sm font-medium">{fileName}</span>
        </div>
        {onEdit && (
          <button
            onClick={onEdit}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
              isUserMessage 
                ? 'bg-blue-600 hover:bg-blue-500 text-white' 
                : 'bg-white hover:bg-gray-50 text-gray-700'
            }`}
          >
            <Edit className="w-3 h-3" />
            Edit
          </button>
        )}
      </div>
      <div className={`file-content p-4 ${
        isUserMessage ? 'text-white' : 'text-gray-900'
      }`}>
        <pre className="whitespace-pre-wrap font-mono text-sm overflow-x-auto">
          <code className={`language-${language}`}>
            {displayContent}
          </code>
        </pre>
      </div>
    </div>
  );
};

export default FileDisplay;
