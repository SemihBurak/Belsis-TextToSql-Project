import { Message } from '../types';
import QueryResult from './QueryResult';
import SQLPreview from './SQLPreview';

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-3xl rounded-lg p-4 ${
              message.type === 'user'
                ? 'bg-indigo-600 text-white'
                : 'bg-white shadow-md border'
            }`}
          >
            {/* Message content */}
            <p className={message.type === 'user' ? 'text-white' : 'text-gray-800'}>
              {message.content}
            </p>

            {/* Response details for assistant messages */}
            {message.type === 'assistant' && message.response && (
              <div className="mt-4 space-y-4">
                {/* Database info with similarity */}
                {message.response.success && (
                  <div className="space-y-2">
                    <div className="flex items-center flex-wrap gap-2 text-sm text-gray-500">
                      <span className="px-2 py-1 bg-green-100 text-green-800 rounded">
                        {message.response.database}
                      </span>
                      {message.response.detection_info?.candidates && (() => {
                        const selected = message.response.detection_info?.candidates?.find(
                          c => c.name === message.response?.database
                        );
                        return selected ? (
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                            {(selected.similarity * 100).toFixed(1)}% eşleşme
                          </span>
                        ) : null;
                      })()}
                      <span>veritabanindan {message.response.row_count} sonuc</span>
                      {/* Total timing badge */}
                      {message.response.timing && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs">
                          ⏱️ {message.response.timing.total.toFixed(1)}s
                        </span>
                      )}
                    </div>

                    {/* Detection details - collapsible */}
                    {message.response.detection_info?.candidates && (
                      <details className="text-xs">
                        <summary className="cursor-pointer text-gray-400 hover:text-gray-600">
                          Tespit detaylari ({message.response.detection_info.method})
                          {message.response.timing && ` - Toplam: ${message.response.timing.total.toFixed(2)}s`}
                        </summary>
                        <div className="mt-2 p-2 bg-gray-50 rounded border space-y-2">
                          {/* Step-by-step timing like terminal */}
                          {(message.response.detection_info.timing || message.response.timing) && (
                            <div className="font-mono text-xs space-y-1 pb-2 border-b border-gray-200 bg-gray-900 text-gray-100 p-2 rounded">
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
                          <div className="space-y-1">
                            <div className="text-gray-500 font-medium">Aday veritabanlari:</div>
                            {message.response.detection_info.candidates.slice(0, 5).map((candidate, idx) => (
                              <div
                                key={candidate.name}
                                className={`flex justify-between ${
                                  candidate.name === message.response?.database
                                    ? 'font-semibold text-green-700'
                                    : 'text-gray-600'
                                }`}
                              >
                                <span>{idx + 1}. {candidate.name}</span>
                                <span>{(candidate.similarity * 100).toFixed(1)}%</span>
                              </div>
                            ))}
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

                {/* Query Results */}
                {message.response.success && message.response.rows.length > 0 && (
                  <QueryResult
                    columns={message.response.columns}
                    rows={message.response.rows}
                  />
                )}

                {/* Error message */}
                {!message.response.success && message.response.error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                    {message.response.error}
                  </div>
                )}
              </div>
            )}

            {/* Timestamp */}
            <div
              className={`text-xs mt-2 ${
                message.type === 'user' ? 'text-indigo-200' : 'text-gray-400'
              }`}
            >
              {message.timestamp.toLocaleTimeString('tr-TR')}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
