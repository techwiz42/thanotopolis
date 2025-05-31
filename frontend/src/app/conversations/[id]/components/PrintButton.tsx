// src/app/conversations/[id]/components/PrintButton.tsx
import React from 'react';
import { Printer } from 'lucide-react';
import { Message } from '../types/message.types';

interface PrintButtonProps {
  content: string;
  message: Message;
}

export const PrintButton: React.FC<PrintButtonProps> = ({ content, message }) => {
  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    const formattedDate = new Date(message.timestamp).toLocaleString();
    const senderInfo = message.sender.email || message.sender.name || 'Unknown';

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Message from ${senderInfo}</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
          }
          .header {
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            margin-bottom: 20px;
          }
          .sender {
            font-weight: bold;
            color: #333;
          }
          .timestamp {
            color: #666;
            font-size: 0.9em;
          }
          .content {
            margin-top: 20px;
            white-space: pre-wrap;
          }
          pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
          }
          code {
            font-family: 'Courier New', monospace;
          }
          @media print {
            body {
              padding: 0;
            }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="sender">From: ${senderInfo}</div>
          <div class="timestamp">Date: ${formattedDate}</div>
        </div>
        <div class="content">
          ${content}
        </div>
      </body>
      </html>
    `);

    printWindow.document.close();
    printWindow.focus();

    // Wait for content to load before printing
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 250);
  };

  return (
    <button
      onClick={handlePrint}
      className="text-gray-600 hover:text-gray-900"
      aria-label="Print message"
    >
      <Printer className="w-4 h-4" />
    </button>
  );
};
