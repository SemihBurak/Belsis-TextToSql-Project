import { Message } from '../types';
import QueryResult from './QueryResult';
import SQLPreview from './SQLPreview';

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
        >
          <div
            className={`max-w-4xl rounded-2xl p-5 transition-all duration-300 relative ${
              message.type === 'user'
                ? 'bg-gradient-to-br from-indigo-600 to-purple-600 text-white shadow-lg hover:shadow-xl'
                : 'bg-white/90 backdrop-blur shadow-xl hover:shadow-2xl border border-gray-100'
            }`}
          >
            {/* Confidence Score Badge - Top Right */}
            {message.type === 'assistant' && message.response && message.response.confidence_score > 0 && (
              <div className="absolute -top-2 -right-2">
                <div className={`px-3 py-1.5 rounded-full font-bold text-xs shadow-lg flex items-center space-x-1 ${
                  message.response.confidence_score >= 80
                    ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white'
                    : message.response.confidence_score >= 60
                    ? 'bg-gradient-to-r from-yellow-500 to-amber-500 text-white'
                    : 'bg-gradient-to-r from-red-500 to-orange-500 text-white'
                }`}>
                  <span>{message.response.confidence_score >= 80 ? '✓' : message.response.confidence_score >= 60 ? '!' : '⚠'}</span>
                  <span>{message.response.confidence_score.toFixed(0)}%</span>
                </div>
              </div>
            )}

            {/* User/Assistant Avatar */}
            <div className="flex items-start space-x-3">
              <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-xl ${
                message.type === 'user'
                  ? 'bg-white/20 backdrop-blur'
                  : 'bg-gradient-to-br from-indigo-100 to-purple-100'
              }`}>
                {message.type === 'user' ? '👤' : '🤖'}
              </div>

              <div className="flex-1">
                {/* Message content */}
                <p className={`${message.type === 'user' ? 'text-white' : 'text-gray-800'} text-base leading-relaxed`}>
                  {message.content}
                </p>

                {/* Response details for assistant messages */}
                {message.type === 'assistant' && message.response && (
                  <div className="mt-5 space-y-4">
                    {/* Database info with similarity */}
                    {message.response.success && (
                      <div className="space-y-3">
                        <div className="flex items-center flex-wrap gap-2 text-sm">
                          <span className="px-3 py-1.5 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-full font-medium shadow-md">
                            📊 {message.response.database}
                          </span>
                          {message.response.detection_info?.candidates && (() => {
                            const selected = message.response.detection_info?.candidates?.find(
                              c => c.name === message.response?.database
                            );
                            return selected ? (
                              <span className="px-3 py-1.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-full text-xs font-medium shadow-md">
                                ✨ {(selected.similarity * 100).toFixed(1)}% eşleşme
                              </span>
                            ) : null;
                          })()}
                          <span className="px-3 py-1.5 bg-gradient-to-r from-orange-400 to-amber-400 text-white rounded-full text-xs font-medium shadow-md">
                            📝 {message.response.row_count} sonuç
                          </span>
                          {/* Total timing badge */}
                          {message.response.timing && (
                            <span className="px-3 py-1.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-full text-xs font-medium shadow-md">
                              ⚡ {message.response.timing.total.toFixed(1)}s
                            </span>
                          )}
                        </div>

                        {/* Detection details - collapsible */}
                        {message.response.detection_info?.candidates && (
                          <details className="text-xs group">
                            <summary className="cursor-pointer text-gray-500 hover:text-indigo-600 font-medium transition-colors flex items-center space-x-2">
                              <span className="transform group-open:rotate-90 transition-transform">▶</span>
                              <span>Tespit Detayları ({message.response.detection_info.method})</span>
                              {message.response.timing && <span className="text-gray-400">• Toplam: {message.response.timing.total.toFixed(2)}s</span>}
                            </summary>
                            <div className="mt-3 p-4 bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl border border-gray-200 space-y-3">
                              {/* Step-by-step timing like terminal */}
                              {(message.response.detection_info.timing || message.response.timing) && (
                                <div className="font-mono text-xs space-y-1 bg-gradient-to-br from-gray-900 to-slate-900 text-gray-100 p-4 rounded-lg shadow-inner">
                                  {/* Step 1: Database Detection */}
                                  {message.response.timing && (
                                    <div className="flex justify-between text-blue-400 font-semibold">
                                      <span>⏱️ [Step 1] Database Detection:</span>
                                      <span>{message.response.timing.detection.toFixed(2)}s</span>
                                    </div>
                                  )}
                                  {/* Semantic Search (indented sub-step) */}
                                  {message.response.detection_info.timing?.search !== undefined && (
                                    <div className="flex justify-between pl-4 text-gray-400">
                                      <span>└─ 📊 Semantic search:</span>
                                      <span className="text-cyan-400">
                                        {message.response.detection_info.timing.search.toFixed(2)}s
                                        {message.response.detection_info.candidates?.[0] && (
                                          <span className="text-gray-500 ml-1">
                                            (top: {(message.response.detection_info.candidates[0].similarity * 100).toFixed(1)}%)
                                          </span>
                                        )}
                                      </span>
                                    </div>
                                  )}
                                  {/* LLM DB Selection (indented sub-step) */}
                                  {message.response.detection_info.timing?.llm !== undefined && message.response.detection_info.timing.llm > 0 && (
                                    <div className="flex justify-between pl-4 text-gray-400">
                                      <span>└─ 🤖 LLM selection:</span>
                                      <span className="text-yellow-400">{message.response.detection_info.timing.llm.toFixed(2)}s</span>
                                    </div>
                                  )}
                                  {/* Step 2: SQL Generation */}
                                  {message.response.timing && (
                                    <div className="flex justify-between text-green-400 font-semibold mt-1">
                                      <span>⏱️ [Step 2] SQL Generation:</span>
                                      <span>{message.response.timing.generation.toFixed(2)}s</span>
                                    </div>
                                  )}
                                  {/* Step 3: Execution */}
                                  {message.response.timing && (
                                    <div className="flex justify-between text-orange-400 font-semibold">
                                      <span>⏱️ [Step 3] SQL Execution:</span>
                                      <span>{message.response.timing.execution.toFixed(2)}s</span>
                                    </div>
                                  )}
                                  {/* Total */}
                                  {message.response.timing && (
                                    <div className="flex justify-between text-purple-400 font-bold border-t border-gray-700 pt-1 mt-1">
                                      <span>⏱️ [TOTAL]</span>
                                      <span>{message.response.timing.total.toFixed(2)}s ✅</span>
                                    </div>
                                  )}
                                </div>
                              )}
                              {/* Candidates list */}
                              <div className="space-y-2">
                                <div className="text-gray-600 font-semibold text-sm">🎯 Aday Veritabanları:</div>
                                <div className="space-y-1">
                                  {message.response.detection_info.candidates.slice(0, 5).map((candidate, idx) => (
                                    <div
                                      key={candidate.name}
                                      className={`flex justify-between px-3 py-2 rounded-lg transition-colors ${
                                        candidate.name === message.response?.database
                                          ? 'bg-gradient-to-r from-green-100 to-emerald-100 font-semibold text-green-700 shadow-sm'
                                          : 'bg-white text-gray-600 hover:bg-gray-50'
                                      }`}
                                    >
                                      <span>{idx + 1}. {candidate.name}</span>
                                      <span className="font-mono">{(candidate.similarity * 100).toFixed(1)}%</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </details>
                        )}
                      </div>
                    )}

                    {/* SQL Preview */}
                    {message.response.sql && (
                      <SQLPreview sql={message.response.sql} />
                    )}

                    {/* Explanation */}
                    {message.response.success && message.response.explanation && (
                      <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl shadow-md">
                        <div className="flex items-start space-x-2">
                          <span className="text-2xl">💡</span>
                          <p className="text-blue-900 font-medium text-sm mt-1">
                            {message.response.explanation}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Query Results */}
                    {message.response.success && message.response.rows.length > 0 && (
                      <QueryResult
                        columns={message.response.columns}
                        rows={message.response.rows}
                      />
                    )}

                    {/* Error message */}
                    {!message.response.success && message.response.error && (
                      <div className="p-4 bg-gradient-to-br from-red-50 to-pink-50 border-2 border-red-200 rounded-xl shadow-md">
                        <div className="flex items-start space-x-2">
                          <span className="text-2xl">⚠️</span>
                          <p className="text-red-700 font-medium text-sm mt-1">
                            {message.response.error}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Timestamp */}
                <div
                  className={`text-xs mt-3 flex items-center space-x-1 ${
                    message.type === 'user' ? 'text-indigo-200' : 'text-gray-400'
                  }`}
                >
                  <span>🕐</span>
                  <span>{message.timestamp.toLocaleTimeString('tr-TR')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
