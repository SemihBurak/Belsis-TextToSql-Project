import { useState } from 'react';

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
    <div className="bg-gradient-to-br from-gray-900 to-slate-900 rounded-xl overflow-hidden shadow-2xl border-2 border-gray-700">
      <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-gray-800 to-slate-800 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <span className="text-xl">💾</span>
          <span className="text-gray-300 text-sm font-bold uppercase tracking-wide">SQL Query</span>
        </div>
        <button
          onClick={handleCopy}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-300 flex items-center space-x-2 ${
            copied
              ? 'bg-green-500 text-white shadow-lg shadow-green-500/50'
              : 'bg-gray-700 text-gray-300 hover:bg-indigo-600 hover:text-white hover:shadow-lg hover:shadow-indigo-500/50'
          }`}
        >
          <span>{copied ? '✅' : '📋'}</span>
          <span>{copied ? 'Kopyalandı!' : 'Kopyala'}</span>
        </button>
      </div>
      <pre className="p-5 overflow-x-auto">
        <code className="text-green-400 font-mono text-sm leading-relaxed">{sql}</code>
      </pre>
    </div>
  );
}
