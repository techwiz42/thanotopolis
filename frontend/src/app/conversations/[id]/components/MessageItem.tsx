// src/app/conversations/[id]/components/MessageItem.tsx
import React, { useEffect, useRef, useState } from 'react';
import { Message } from '@/app/conversations/[id]/types/message.types';
import { DownloadButton } from '@/app/conversations/[id]/components/DownloadButton';
import { Copy } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import FileDisplay from '@/app/conversations/[id]/components/FileDisplay';
import { PrintButton } from '@/app/conversations/[id]/components/PrintButton';

// Define an enhanced interface for the Message type to include all needed properties
interface EnhancedMessage extends Message {
  message_info?: {
    is_file?: boolean;
    file_name?: string;
    file_type?: string;
    file_size?: number;
    is_private?: boolean;
    is_streaming?: boolean;  // New flag to indicate streaming
    [key: string]: unknown;
  };
  agent_type?: string;
  is_streaming?: boolean;    // Top-level flag for easier access
  streaming_content?: string; // Current streamed content
}

// Create a type guard function
function hasMessageInfo(message: Message): message is EnhancedMessage {
  return 'message_info' in message && message.message_info !== undefined;
}

interface Props {
  message: Message;
  formatDate: (date: string) => string;
  responseTime?: string;
  isStreaming?: boolean;
  streamingContent?: string;
}

export const formatAgentName = (agentType?: string, email?: string) => {
  if (!agentType) {
    return email?.split('@')[0].toUpperCase() || 'Unknown';
  }

  return agentType
    .split('_')
    .map(word => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ')
    .replace(/\s?Agent$/, '');
};

const MessageItem: React.FC<Props> = ({ 
  message, 
  formatDate, 
  responseTime,
  isStreaming = false,
  streamingContent = ''
}) => {
  const { toast } = useToast();
  const { user } = useAuth();
  const contentRef = useRef<HTMLDivElement>(null);
  
  // Cast message to EnhancedMessage for easier access to optional properties
  const enhancedMessage = message as EnhancedMessage;
  
  // Use passed streaming content or from message if available
  const currentStreamingContent = streamingContent || enhancedMessage.streaming_content || '';
  const messageIsStreaming = isStreaming || enhancedMessage.is_streaming || 
    (hasMessageInfo(message) && message.message_info?.is_streaming);

  const getMessageClasses = () => {
    const baseClasses = "rounded-lg px-4 py-3 max-w-[70%] relative text-sm break-all";
    return message.sender.type === 'user'
      ? `${baseClasses} bg-blue-500 text-white ml-auto` 
      : `${baseClasses} bg-green-300 text-gray-900 border border-blue-300`;
  };

  // Check if the string is HTML
  const isHTML = (str: string) => {
    return /<[a-z][\s\S]*>/i.test(str);
  };
  
  // Process LaTeX-like math expressions
  const processMathExpressions = (content: string) => {
    // Replace \[ ... \] with proper math display
    const displayMathRegex = /\\[\[](.+?)\\[\]]/g;
    const processedContent = content.replace(displayMathRegex, (match, formula) => {
      return `<div class="math-display">${formula}</div>`;
    });
    
    return processedContent;
  };
  
  // Check if content might be Markdown (with some basic markers)
  const isMarkdown = (text: string): boolean => {
    // Check for common markdown patterns
    const markdownPatterns = [
      /^#{1,6}\s/, // Headers
      /\*\*.*\*\*/, // Bold
      /\*.*\*/, // Italic 
      /`.*`/, // Inline code
      /```[\s\S]*```/, // Code blocks
      /\[.*\]\(.*\)/, // Links
      /^[-*+]\s/, // Unordered lists
      /^\d+\.\s/, // Ordered lists
      /^>\s/, // Blockquotes
      /^---$/ // Horizontal rules
    ];
    
    return markdownPatterns.some(pattern => pattern.test(text));
  };
  
  // Convert markdown to HTML
  const renderMarkdown = (text: string): string => {
    let html = text;

    // Convert headers
    html = html.replace(/^#{6}\s+(.+)$/gm, '<h6>$1</h6>');
    html = html.replace(/^#{5}\s+(.+)$/gm, '<h5>$1</h5>');
    html = html.replace(/^#{4}\s+(.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^#{3}\s+(.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^#{2}\s+(.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^#{1}\s+(.+)$/gm, '<h1>$1</h1>');

    // Convert bold text
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic text
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

    // Convert code blocks
    html = html.replace(/```([a-zA-Z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code class="language-${lang}">${code}</code></pre>`;
    });
    
    // Convert inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Convert links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, 
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Convert unordered lists
    const ulRegex = /^[\s]*[-*+][\s]+(.*)/gm;
    const ulMatches = html.match(ulRegex);
    if (ulMatches) {
      let inList = false;
      html = html.replace(ulRegex, (match, item) => {
        if (!inList) {
          inList = true;
          return `<ul><li>${item}</li>`;
        }
        return `<li>${item}</li>`;
      });
      // Close any open lists
      if (inList) {
        html = html + '</ul>';
      }
    }
    
    // Convert ordered lists
    const olRegex = /^[\s]*(\d+)\.[\s]+(.*)/gm;
    const olMatches = html.match(olRegex);
    if (olMatches) {
      let inList = false;
      html = html.replace(olRegex, (match, num, item) => {
        if (!inList) {
          inList = true;
          return `<ol><li>${item}</li>`;
        }
        return `<li>${item}</li>`;
      });
      // Close any open lists
      if (inList) {
        html = html + '</ol>';
      }
    }
    
    // Convert blockquotes
    html = html.replace(/^>[\s]+(.*)/gm, '<blockquote>$1</blockquote>');
    
    // Convert horizontal rules
    html = html.replace(/^---$/gm, '<hr/>');
    
    // Convert line breaks
    html = html.replace(/\n/g, '<br/>');
    
    return html;
  };

  const renderContent = () => {
    // Handle streaming content
    if (messageIsStreaming) {
      const cleanedStreamingContent = currentStreamingContent
        .replace(/\[\w+ is thinking\.\.\.\]/g, '')
        .replace(/\[\w+ has completed\]/g, '')
        .replace(/\[Synthesizing collaborative response\.\.\.\]/g, '')
        .replace(/\[TIMEOUT\]/g, '')
        .replace(/\[ERROR\]/g, '')
        .replace(/\[DONE\]/g, '')
        .replace(/\[END\]/g, '')
        .replace(/\[AGENT_COMPLETE\]/g, '')
        .replace(/\n{3,}/g, '\n\n')
        .trim();

      return (
        <div className="whitespace-pre-wrap break-words text-sm">
          {cleanedStreamingContent}
          <span className="typing-indicator inline-block ml-1">
            <span className="dot bg-black"></span>
            <span className="dot bg-black"></span>
            <span className="dot bg-black"></span>
          </span>
        </div>
      );
    }

    // Handle file content display
    if (hasMessageInfo(message) && message.message_info?.is_file) {
      return (
        <FileDisplay
          content={message.content}
          fileName={message.message_info.file_name}
          isUserMessage={message.sender.type === 'user'}
        />
      );
    }

    // Special handling for document search agent responses
    if (!message.sender.is_owner &&
        (enhancedMessage.agent_type === 'DOCUMENTSEARCH' ||
         message.content.includes('@documentsearch') ||
         message.content.includes('document-link'))) {

      // For document search results, properly render markdown with clickable links
      const content = message.content;

      // Convert markdown to HTML with emphasis on preserving format
      const convertMarkdown = (text: string) => {
        let html = text;

        // Skip HTML conversion if content already contains HTML links
        // This handles the case where backend returns HTML directly
        const containsHtmlLinks = /<a\s+href=/i.test(html);

        if (!containsHtmlLinks) {
          // Convert headers
          html = html.replace(/### ([^\n]+)/g, '<h3>$1</h3>');
          html = html.replace(/## ([^\n]+)/g, '<h2>$1</h2>');
          html = html.replace(/# ([^\n]+)/g, '<h1>$1</h1>');

          // Convert bold text
          html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

          // Convert links - most important for clickability
          html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener noreferrer" class="document-link">$1</a>');

          // Convert horizontal rules
          html = html.replace(/^---$/gm, '<hr/>');
          
          // Convert code blocks
          html = html.replace(/```([a-zA-Z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang}">${code}</code></pre>`;
          });
          
          // Convert inline code
          html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
          
          // Convert unordered lists
          const listRegex = /^[\s]*[-*+][\s]+(.*)/gm;
          const listMatches = html.match(listRegex);
          if (listMatches) {
            let inList = false;
            html = html.replace(listRegex, (match, item) => {
              if (!inList) {
                inList = true;
                return `<ul><li>${item}</li>`;
              }
              return `<li>${item}</li>`;
            });
            // Close any open lists
            if (inList) {
              html = html + '</ul>';
            }
          }
        }

        // Always convert line breaks properly
        html = html.replace(/\n/g, '<br/>');

        // Add the italicized note at the bottom if not already present
        if (!html.includes('document-note')) {
          html += '<p class="document-note"><em>Some users may require permission from document owners to view text</em></p>';
        }

        return html;
      };

      // Apply conversion
      const processedContent = convertMarkdown(content);

      return (
        <div
          ref={contentRef}
          className="document-search-results break-all w-full"
          dangerouslySetInnerHTML={{ __html: processedContent }}
        />
      );
    }

    // Process and handle HTML content with math expressions
    if (isHTML(message.content)) {
      return <div ref={contentRef} className="overflow-x-auto break-all w-full" dangerouslySetInnerHTML={{ __html: message.content }} />;
    }

    // Process math expressions in non-HTML content
    const processedContent = processMathExpressions(message.content);

    // If processing added HTML, use dangerouslySetInnerHTML
    if (processedContent !== message.content && isHTML(processedContent)) {
      return <div ref={contentRef} className="overflow-x-auto break-all w-full" dangerouslySetInnerHTML={{ __html: processedContent }} />;
    }

    // Handle regular text content
    if (isMarkdown(message.content)) {
      // If content is detected as Markdown, render it as HTML
      return (
        <div 
          ref={contentRef} 
          className="markdown-content whitespace-pre-wrap break-all text-sm w-full"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
        />
      );
    } else {
      // Regular text that's not Markdown
      return (
        <div ref={contentRef} className="whitespace-pre-wrap break-all text-sm w-full">
          {message.content}
        </div>
      );
    }
  };

  const getInitial = (email: string) => {
    return email ? email[0].toUpperCase() : '?';
  };

  const getAvatarColor = (email: string) => {
    const colors = ['bg-red-500', 'bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500'];
    const index = email.charCodeAt(0) % colors.length;
    return colors[index]; 
  };

  const handleCopy = async () => {
    // For streaming content, copy what's available so far
    const contentToCopy = messageIsStreaming ? currentStreamingContent : message.content;
    
    // Check if clipboard API is available
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(contentToCopy);
        toast({
          title: "Copied to clipboard",
          duration: 2000
        });
      } catch (err) {
        console.error('Failed to copy:', err);
        toast({
          title: "Failed to copy", 
          variant: "destructive",
          duration: 2000
        });
      }
    } else {
      // Fallback for environments without clipboard API
      try {
        const textArea = document.createElement('textarea');
        textArea.value = contentToCopy;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);

        toast({
          title: "Copied to clipboard",
          duration: 2000
        });
      } catch (err) {
        console.error('Fallback copy failed:', err);
        toast({
          title: "Failed to copy", 
          variant: "destructive",
          duration: 2000
        });
      }
    }
  };

  return (
    <div className={`flex ${message.sender.is_owner ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`${getMessageClasses()} flex flex-col break-words`}>
        <div className="flex items-center gap-2 mb-1">
          {message.sender.type === 'user' && (
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${getAvatarColor(message.sender.email || user?.email || '')}`}>
              {getInitial(message.sender.email || user?.email || '')}
            </div>
          )}
          <span className="font-medium text-xs">
            {message.sender.type === 'user'
              ? (message.sender.email || user?.email || 'Unknown') 
              : formatAgentName(enhancedMessage.agent_type, message.sender.email)}
          </span>
          <span className="text-xs text-gray-500 ml-auto">
            {formatDate(message.timestamp)}
          </span>
          
          {/* Show streaming indicator in header */}
          {messageIsStreaming && (
            <span className="text-xs text-blue-600 ml-1 animate-pulse">
              streaming...
            </span>
          )}
        </div>
        
        <div className={messageIsStreaming ? "streaming-content" : ""}>
          {renderContent()}
        </div>
        
        <div className="mt-2 flex items-center gap-2">
          <button 
            onClick={handleCopy}
            className="text-gray-600 hover:text-gray-900"
            aria-label="Copy content"
          >
            <Copy className="w-4 h-4" />  
          </button>
          
          {/* Only show download and print buttons for completed messages */}
          {!messageIsStreaming && (
            <>
              <DownloadButton
                content={message.content}
                defaultFileName={`${hasMessageInfo(message) && message.message_info?.file_name || `message_${formatDate(message.timestamp)}`}`}
              />
              <PrintButton 
                content={contentRef.current?.innerHTML || message.content}
                message={message} 
              />
            </>
          )}
        </div>

        {responseTime && !messageIsStreaming && (
          <div className="mt-2 text-xs text-gray-500">
            Response time: {responseTime}
          </div>  
        )}
      </div>
    </div>
  );
};

// Add CSS for typing indicator and streaming content
const TypingIndicatorStyles = () => (
  <style jsx global>{`
    .typing-indicator {
      display: inline-flex;
      align-items: center;
    }

    .typing-indicator .dot {
      display: inline-block;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      margin: 0 1px;
      background-color: currentColor;
      animation: typingAnimation 1.4s infinite ease-in-out;
    }

    .typing-indicator .dot:nth-child(1) {
      animation-delay: 0s;
    }

    .typing-indicator .dot:nth-child(2) {
      animation-delay: 0.2s;
    }

    .typing-indicator .dot:nth-child(3) {
      animation-delay: 0.4s;
    }

    @keyframes typingAnimation {
      0%, 60%, 100% {
        transform: translateY(0);
        opacity: 0.6;
      }
      30% {
        transform: translateY(-4px);
        opacity: 1;
      }
    }

    /* Streaming content styles */
    .streaming-content {
      white-space: pre-wrap;
      line-height: 1.5;
      overflow-wrap: break-word;
      word-wrap: break-word;
      word-break: break-all;
      max-width: 100%;
    }

    /* Math display styles */
    .math-display {
      margin: 1rem 0;
      padding: 0.5rem;
      background-color: #f9f9f9;
      border-radius: 4px;
      border-left: 3px solid #0066cc;
      font-family: serif;
      font-style: italic;
    }

    /* Document link styles */
    .document-link {
      color: #0066cc !important;
      text-decoration: underline !important;
      cursor: pointer !important;
      font-weight: 500 !important;
      transition: color 0.2s ease !important;
      position: relative !important;
      z-index: 10 !important;
      display: inline-block !important;
      pointer-events: auto !important;
      overflow-wrap: break-word !important;
      word-break: break-word !important;
    }

    .document-link:hover {
      color: #004499 !important;
      text-decoration: underline !important;
    }

    .document-link:focus {
      outline: 2px solid #0066cc !important;
      outline-offset: 2px !important;
    }
    
    /* Markdown content styles */
    .markdown-content h1 {
      font-size: 1.5rem;
      font-weight: 700;
      margin-top: 1.5rem;
      margin-bottom: 0.75rem;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    
    .markdown-content h2 {
      font-size: 1.3rem;
      font-weight: 600;
      margin-top: 1.25rem;
      margin-bottom: 0.5rem;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    
    .markdown-content h3 {
      font-size: 1.1rem;
      font-weight: 600;
      margin-top: 1rem;
      margin-bottom: 0.5rem;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    
    .markdown-content h4, 
    .markdown-content h5, 
    .markdown-content h6 {
      font-size: 1rem;
      font-weight: 600;
      margin-top: 0.75rem;
      margin-bottom: 0.5rem;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    
    .markdown-content code {
      font-family: monospace;
      background-color: #f0f0f0;
      padding: 0.15rem 0.3rem;
      border-radius: 3px;
      font-size: 0.9em;
      overflow-wrap: break-word;
      word-break: break-word;
      max-width: 100%;
    }
    
    .markdown-content pre {
      white-space: pre-wrap;
      max-width: 100%;
    }
    
    .markdown-content pre code {
      display: block;
      padding: 0.75rem;
      margin: 0.75rem 0;
      line-height: 1.5;
      background-color: #f5f5f5;
      border-radius: 5px;
      overflow-x: auto;
      word-wrap: break-word;
      word-break: break-all;
      white-space: pre-wrap;
    }
    
    .markdown-content blockquote {
      border-left: 3px solid #ccc;
      padding-left: 0.75rem;
      margin-left: 0;
      color: #555;
      margin: 0.75rem 0;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    
    .markdown-content a {
      color: #0066cc;
      text-decoration: underline;
      transition: color 0.2s ease;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    
    .markdown-content a:hover {
      color: #004499;
    }
    
    .markdown-content ol,
    .markdown-content ul {
      padding-left: 1.5rem;
      margin: 0.5rem 0;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    
    .markdown-content li {
      margin-bottom: 0.25rem;
      overflow-wrap: break-word;
      word-break: break-word;
    }
    
    .markdown-content hr {
      margin: 1rem 0;
      border: 0;
      border-top: 1px solid #ddd;
    }
    
    .markdown-content p {
      overflow-wrap: break-word;
      word-break: break-word;
      margin-bottom: 0.75rem;
    }

    /* Document search results styling */
    .document-search-results {
      white-space: pre-wrap;
      line-height: 1.5;
      overflow-wrap: break-word;
      word-break: break-word;
      position: relative;
      pointer-events: auto;
      max-width: 100%;
    }

    .document-search-results a {
      color: #0066cc !important;
      text-decoration: underline !important;
      cursor: pointer !important;
      position: relative !important;
      z-index: 10 !important;
      display: inline-block !important;
      pointer-events: auto !important;
      overflow-wrap: break-word !important;
      word-break: break-word !important;
    }

    .document-search-results a:hover {
      color: #004499 !important;
      text-decoration: underline !important;
    }

    .document-search-results h3 {
      font-size: 1.1rem;
      font-weight: 600;
      margin-top: 1rem;
      margin-bottom: 0.5rem;
      overflow-wrap: break-word;
      word-break: break-word;
    }

    .document-search-results strong {
      font-weight: bold;
    }

    .document-search-results hr {
      margin: 1rem 0;
      border: 0;
      border-top: 1px solid #ddd;
    }
    
    .document-search-results p {
      overflow-wrap: break-word;
      word-break: break-word;
      margin-bottom: 0.75rem;
    }

    .document-search-results pre,
    .document-search-results code {
      white-space: pre-wrap;
      overflow-wrap: break-word;
      word-break: break-all;
      max-width: 100%;
    }

    .document-note {
      margin-top: 1.5rem;
      color: #666;
      font-size: 0.9rem;
    }
  `}</style>
);

// Export both the component and the styles
export { TypingIndicatorStyles };
export default React.memo(MessageItem);
