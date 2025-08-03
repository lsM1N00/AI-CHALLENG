import React, { useState, useEffect, useRef } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { 
  Send, 
  Bot, 
  User, 
  Activity, 
  Brain, 
  Zap, 
  Settings,
  BarChart3,
  Clock,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Scale,
  FileText,
  Search,
  HelpCircle
} from 'lucide-react';
import axios from 'axios';
import clsx from 'clsx';
import './App.css';

// 타입 정의
interface Message {
  id: string;
  type: 'user' | 'bot';
  content: string;
  timestamp: Date;
  metadata?: {
    success?: boolean;
    quality?: any;
    sources?: string[];
    agents?: string[];
    executionTime?: number;
  };
}

interface SystemStats {
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  average_response_time: number;
  system_health: string;
}

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 시스템 상태 확인
  useEffect(() => {
    checkSystemHealth();
    fetchSystemStats();
    
    // 5초마다 시스템 상태 체크
    const interval = setInterval(() => {
      fetchSystemStats();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // 메시지 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const checkSystemHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setIsConnected(response.data.status === 'healthy');
    } catch (error) {
      setIsConnected(false);
      console.error('시스템 연결 확인 실패:', error);
    }
  };

  const fetchSystemStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/system/stats`);
      setSystemStats(response.data);
    } catch (error) {
      console.error('시스템 통계 조회 실패:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/query`, {
        query: inputValue
      });

      const botMessage: Message = {
        id: `bot-${Date.now()}`,
        type: 'bot',
        content: response.data.final_answer || '죄송합니다. 응답을 생성할 수 없습니다.',
        timestamp: new Date(),
        metadata: {
          success: response.data.success,
          quality: response.data.response_quality,
          sources: response.data.consolidated_sources,
          agents: response.data.execution_path,
          executionTime: response.data.execution_time
        }
      };

      setMessages(prev => [...prev, botMessage]);
      
      if (response.data.success) {
        toast.success('응답이 성공적으로 생성되었습니다!');
      } else {
        toast.error('응답 생성 중 문제가 발생했습니다.');
      }

      // 통계 갱신
      fetchSystemStats();

    } catch (error) {
      console.error('API 호출 실패:', error);
      toast.error('서버와의 연결에 문제가 발생했습니다.');
      
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'bot',
        content: '죄송합니다. 서버와의 연결에 문제가 발생했습니다. 나중에 다시 시도해주세요.',
        timestamp: new Date(),
        metadata: { success: false }
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const resetSystem = async () => {
    try {
      await axios.post(`${API_BASE_URL}/system/reset`);
      toast.success('시스템이 리셋되었습니다.');
      setMessages([]);
      fetchSystemStats();
    } catch (error) {
      toast.error('시스템 리셋에 실패했습니다.');
    }
  };

  return (
    <div className="main-container">
      <Toaster position="top-right" />
      
      {/* 헤더 */}
      <header className="main-header">
        <div className="header-container">
          <div className="header-content">
            <div className="header-left">
              <div className="header-logo">
                <img 
                  src="/kb-logo.png" 
                  alt="KB국민은행 로고" 
                  className="kb-logo-image"
                />
              </div>
              <div>
                <h1 className="header-title">
                  KB금융이 도와드릴게요
                </h1>
                <p className="header-subtitle">
                  금융분쟁 해결 AI에이전트
                </p>
              </div>
            </div>
            
            <div className="header-right">
              {/* 연결 상태 */}
              <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                <div className={`connection-dot ${isConnected ? 'connected' : 'disconnected'}`} />
                <span>{isConnected ? '연결됨' : '연결 안됨'}</span>
              </div>
              
              {/* 시스템 리셋 */}
              <button
                onClick={resetSystem}
                className="reset-button"
                title="시스템 리셋"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="main-content">
        
        {/* 사이드바 - 시스템 정보 */}
        <div className="sidebar">
          
          {/* 시스템 통계 */}
          <div className="sidebar-section">
            <div className="sidebar-card">
              <h3 className="sidebar-title">
                <BarChart3 className="w-5 h-5" />
                시스템 통계
              </h3>
              
              {systemStats ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">총 질의</span>
                    <span className="font-semibold">{systemStats.total_queries}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">성공률</span>
                    <span className="font-semibold text-green-600">
                      {systemStats.total_queries > 0 
                        ? Math.round((systemStats.successful_queries / systemStats.total_queries) * 100)
                        : 0}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">평균 응답 시간</span>
                    <span className="font-semibold">{systemStats.average_response_time.toFixed(2)}s</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">시스템 상태</span>
                    <span className={clsx(
                      "px-2 py-1 rounded-full text-xs font-medium",
                      systemStats.system_health === 'healthy' 
                        ? "bg-green-100 text-green-800"
                        : "bg-yellow-100 text-yellow-800"
                    )}>
                      {systemStats.system_health}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500">로딩 중...</div>
              )}
            </div>
          </div>

          {/* 에이전트 정보 */}
          <div className="sidebar-section">
            <div className="sidebar-card">
              <h3 className="sidebar-title">
                <Bot className="w-5 h-5" />
                활성 에이전트
              </h3>
              
              <div className="space-y-3">
                <div className="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">법</span>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">법률 전문가</div>
                    <div className="text-xs text-gray-600">금융법, 소비자보호법</div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-4 bg-green-50 rounded-lg border border-green-100">
                  <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">기</span>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">기술 분석가</div>
                    <div className="text-xs text-gray-600">시스템 아키텍처, 개발</div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3 p-4 bg-purple-50 rounded-lg border border-purple-100">
                  <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-bold">일</span>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">일반 지식</div>
                    <div className="text-xs text-gray-600">폭넓은 지식 기반</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 채팅 영역 */}
        <div className="chat-container">
          <div className="chat-wrapper">
            
            {/* 채팅 헤더 */}
            <div className="chat-header">
              <h2 className="chat-title">
                <Zap className="w-6 h-6 mr-2" style={{ color: '#BF9264' }} />
                AI 어시스턴트와 대화
              </h2>
              <div className="chat-counter">
                {messages.length > 0 && `${messages.length}개 메시지`}
              </div>
            </div>

            {/* 메시지 영역 */}
            <div className="chat-messages">
              {messages.length === 0 ? (
                <div className="empty-chat-container">
                  <div className="action-buttons-grid">
                    <button
                      onClick={() => setInputValue('내가 겪고 있는 금융분쟁에서 내 권리가 무엇인지 알려주세요')}
                      className="action-button action-button-blue"
                    >
                      <div className="action-button-icon">
                        <Scale className="w-6 h-6" />
                      </div>
                      <div className="action-button-title">내 권리 찾기</div>
                    </button>
                    
                    <button
                      onClick={() => setInputValue('금융분쟁 해결 절차를 단계별로 안내해주세요')}
                      className="action-button action-button-green"
                    >
                      <div className="action-button-icon">
                        <FileText className="w-6 h-6" />
                      </div>
                      <div className="action-button-title">분쟁 해결 절차 안내</div>
                    </button>
                    
                    <button
                      onClick={() => setInputValue('금융분쟁 관련해서 자주 묻는 질문들을 알려주세요')}
                      className="action-button action-button-orange"
                    >
                      <div className="action-button-icon">
                        <HelpCircle className="w-6 h-6" />
                      </div>
                      <div className="action-button-title">자주 묻는 질문</div>
                    </button>
                    
                    <button
                      onClick={() => setInputValue('비슷한 금융분쟁 과거 사례와 해결책을 찾아주세요')}
                      className="action-button action-button-purple"
                    >
                      <div className="action-button-icon">
                        <Search className="w-6 h-6" />
                      </div>
                      <div className="action-button-title">과거 사례 검색</div>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={clsx(
                        "flex gap-4",
                        message.type === 'user' ? "justify-end" : "justify-start"
                      )}
                    >
                      {message.type === 'bot' && (
                        <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                          <Bot className="w-5 h-5 text-white" />
                        </div>
                      )}
                      
                      <div className={clsx(
                        "max-w-[75%] rounded-xl px-6 py-4",
                        message.type === 'user'
                          ? "bg-blue-600 text-white"
                          : "bg-white/80 backdrop-blur-sm border border-gray-200"
                      )}>
                        <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
                        
                        {/* 메타데이터 */}
                        {message.metadata && message.type === 'bot' && (
                          <div className="mt-4 pt-4 border-t border-gray-100 text-xs space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-gray-500">
                                {message.metadata.success ? (
                                  <CheckCircle className="w-4 h-4 text-green-500 inline mr-1" />
                                ) : (
                                  <AlertCircle className="w-4 h-4 text-red-500 inline mr-1" />
                                )}
                                {message.metadata.success ? '성공' : '실패'}
                              </span>
                              {message.metadata.executionTime && (
                                <span className="text-gray-500 flex items-center">
                                  <Clock className="w-3 h-3 mr-1" />
                                  {message.metadata.executionTime.toFixed(2)}s
                                </span>
                              )}
                            </div>
                            
                            {message.metadata.quality && (
                              <div className="text-gray-600">
                                품질: {message.metadata.quality.quality_level || 'N/A'} 
                                ({message.metadata.quality.overall_score?.toFixed(2) || 'N/A'})
                              </div>
                            )}
                            
                            {message.metadata.agents && message.metadata.agents.length > 0 && (
                              <div className="text-gray-600">
                                실행 경로: {message.metadata.agents.join(' → ')}
                              </div>
                            )}
                          </div>
                        )}
                        
                        <div className="text-xs text-gray-400 mt-3">
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                      
                      {message.type === 'user' && (
                        <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center flex-shrink-0">
                          <User className="w-5 h-5 text-gray-600" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              {isLoading && (
                <div className="flex gap-4 justify-start">
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white/80 backdrop-blur-sm border border-gray-200 rounded-xl px-6 py-4">
                    <div className="flex items-center space-x-3">
                      <div className="loading-dots">
                        <div></div>
                        <div></div>
                        <div></div>
                      </div>
                      <span className="text-gray-600 text-sm">AI가 생각하고 있습니다...</span>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* 입력 영역 */}
            <div className="message-input-container">
              <div className="message-input-wrapper">
                <div className="message-input-field">
                  <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="메시지를 입력하세요... (Shift + Enter로 줄바꿈)"
                    className="message-textarea"
                    disabled={isLoading}
                  />
                </div>
                <button
                  onClick={handleSendMessage}
                  disabled={isLoading || !inputValue.trim()}
                  className="send-button"
                >
                  {isLoading ? (
                    <Activity className="w-5 h-5 animate-spin" />
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                  <span>전송</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
