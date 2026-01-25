import React, { useState } from 'react';

interface SQLPreviewProps {
  sql: string;
}

export default function SQLPreview({ sql }: SQLPreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800">
        <span className="text-gray-400 text-sm font-medium">SQL</span>
        <button
          onClick={handleCopy}
          className="text-gray-400 hover:text-white text-sm transition"
        >
          {copied ? 'Kopyalandi!' : 'Kopyala'}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto">
        <code className="sql-code text-green-400">{sql}</code>
      </pre>
    </div>
  );
}
