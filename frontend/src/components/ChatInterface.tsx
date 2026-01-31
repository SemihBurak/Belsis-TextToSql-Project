import React, { useState, useRef, useEffect } from 'react';
import { Message } from '../types';
import { sendQuestion } from '../services/api';
import MessageList from './MessageList';

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
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header - Modern Gradient */}
      <header className="bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white p-6 shadow-2xl">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center space-x-3">
            <div className="text-4xl">🤖</div>
            <div>
              <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-blue-100">
                TURSpider Text-to-SQL Chatbot
              </h1>
              <p className="text-indigo-100 text-sm mt-1">
                ✨ Türkçe ile konuşun, veritabanınız cevaplasın
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center mt-12 animate-fade-in">
            <div className="max-w-3xl mx-auto">
              <div className="text-6xl mb-4 animate-bounce">👋</div>
              <h2 className="text-3xl font-bold text-gray-800 mb-3">
                Hoş Geldiniz!
              </h2>
              <p className="text-gray-600 mb-8">
                Türkçe bir soru sorarak başlayabilirsiniz. İşte bazı örnek sorular:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={() => setInput('Sarkicilarin isimleri nelerdir?')}
                  className="group relative overflow-hidden px-6 py-4 bg-white hover:bg-gradient-to-br hover:from-blue-50 hover:to-indigo-50 rounded-2xl text-gray-700 transition-all duration-300 shadow-lg hover:shadow-2xl hover:scale-105 border border-gray-100"
                >
                  <div className="text-3xl mb-2">🎤</div>
                  <div className="font-medium">"Şarkıcıların isimleri nelerdir?"</div>
                </button>
                <button
                  onClick={() => setInput('Hangi departmanda en cok doktor var?')}
                  className="group relative overflow-hidden px-6 py-4 bg-white hover:bg-gradient-to-br hover:from-purple-50 hover:to-pink-50 rounded-2xl text-gray-700 transition-all duration-300 shadow-lg hover:shadow-2xl hover:scale-105 border border-gray-100"
                >
                  <div className="text-3xl mb-2">🏥</div>
                  <div className="font-medium">"Hangi departmanda en çok doktor var?"</div>
                </button>
                <button
                  onClick={() => setInput('En cok satan sarkilar hangileri?')}
                  className="group relative overflow-hidden px-6 py-4 bg-white hover:bg-gradient-to-br hover:from-green-50 hover:to-teal-50 rounded-2xl text-gray-700 transition-all duration-300 shadow-lg hover:shadow-2xl hover:scale-105 border border-gray-100"
                >
                  <div className="text-3xl mb-2">📈</div>
                  <div className="font-medium">"En çok satan şarkılar hangileri?"</div>
                </button>
              </div>
            </div>
          </div>
        )}

        <MessageList messages={messages} />

        {isLoading && (
          <div className="flex flex-col items-center space-y-3 py-8">
            <div className="relative">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-200"></div>
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-t-indigo-600 absolute top-0"></div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-gray-600 font-medium">Sorgu işleniyor</span>
              <span className="animate-pulse">.</span>
              <span className="animate-pulse animation-delay-200">.</span>
              <span className="animate-pulse animation-delay-400">.</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area - Modern Glassmorphism */}
      <form onSubmit={handleSubmit} className="p-6 bg-white/80 backdrop-blur-xl border-t border-gray-200/50 shadow-2xl">
        <div className="flex space-x-3 max-w-5xl mx-auto">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="✍️ Türkçe bir soru sorun..."
            className="flex-1 px-6 py-4 border-2 border-gray-200 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/30 focus:border-indigo-500 transition-all duration-300 text-gray-800 placeholder-gray-400 bg-white shadow-lg"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-2xl hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 font-semibold shadow-lg hover:shadow-xl hover:scale-105 flex items-center space-x-2"
          >
            <span>Gönder</span>
            <span>🚀</span>
          </button>
        </div>
      </form>
    </div>
  );
}
