import React, { useState, useRef, useEffect } from 'react';
import { Message, ChatResponse } from '../types';
import { sendQuestion } from '../services/api';
import MessageList from './MessageList';
import QueryResult from './QueryResult';
import SQLPreview from './SQLPreview';

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || isLoading) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendQuestion(question);

      // Add assistant message with response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.success
          ? `Veritabani: ${response.database}`
          : response.error || 'Bir hata olustu.',
        timestamp: new Date(),
        response,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Sunucu ile baglanti kurulamadi. Lutfen backend\'in calistigini kontrol edin.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-indigo-600 text-white p-4 shadow-md">
        <h1 className="text-xl font-bold">Chatbot</h1>
        <p className="text-indigo-200 text-sm">
          Turkce sorularinizi SQL sorgularina donusturun
        </p>
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-lg mb-2">Hosgeldiniz!</p>
            <p className="text-sm">
              Turkce bir soru sorarak baslayabilirsiniz. Ornegin:
            </p>
            <div className="mt-4 space-y-2">
              <button
                onClick={() => setInput('Sarkicilarin isimleri nelerdir?')}
                className="block mx-auto px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition"
              >
                "Sarkicilarin isimleri nelerdir?"
              </button>
              <button
                onClick={() => setInput('Hangi departmanda en cok doktor var?')}
                className="block mx-auto px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition"
              >
                "Hangi departmanda en cok doktor var?"
              </button>
              <button
                onClick={() => setInput('En cok satan sarkilar hangileri?')}
                className="block mx-auto px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 transition"
              >
                "En cok satan sarkilar hangileri?"
              </button>
            </div>
          </div>
        )}

        <MessageList messages={messages} />

        {isLoading && (
          <div className="flex items-center space-x-2 text-gray-500">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600"></div>
            <span>Sorgu isleniyor...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="p-4 bg-white border-t shadow-lg">
        <div className="flex space-x-2 max-w-4xl mx-auto">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Turkce bir soru sorun..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            Gonder
          </button>
        </div>
      </form>
    </div>
  );
}
