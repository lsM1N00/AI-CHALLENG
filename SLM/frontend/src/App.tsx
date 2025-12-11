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
  Clock,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Scale,
  FileText,
  Search,
  HelpCircle,
  ArrowLeft,
  ExternalLink,
  BarChart3,
  Download
} from 'lucide-react';

import './App.css';
import { apiClient, type ChatRequest } from './api/client';

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



function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 카테고리별 특화 모드 상태
  const [specializedMode, setSpecializedMode] = useState<'general' | 'loan' | 'insurance' | 'card' | 'housing' | 'investment'>('general');
  
  // 상담 내역 화면 상태
  const [showHistory, setShowHistory] = useState(false);

  // 채팅 시작 전 배경화면 표시 상태
  const [showBackgroundGuide, setShowBackgroundGuide] = useState(true);

  // 스크롤 위치 저장
  const [scrollPosition, setScrollPosition] = useState(0);

  // 상담 종료 및 만족도 조사 상태
  const [showEndConsultation, setShowEndConsultation] = useState(false);
  const [showSatisfactionSurvey, setShowSatisfactionSurvey] = useState(false);
  const [satisfactionRating, setSatisfactionRating] = useState(0);
  const [satisfactionComment, setSatisfactionComment] = useState('');

  // 시스템 상태 확인
  useEffect(() => {
    checkSystemHealth();
    
    // 5초마다 시스템 상태 체크
    const interval = setInterval(() => {
      checkSystemHealth();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // 메시지 스크롤
  useEffect(() => {
    if (showBackgroundGuide) {
      // 배경 가이드가 표시될 때는 스크롤을 맨 위로 유지
      const questionTypes = document.querySelector('.main-question-types');
      if (questionTypes) {
        questionTypes.scrollTop = 0;
      }
    } else if (messages.length > 0) {
      // 메시지가 있을 때만 맨 아래로 스크롤
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, showBackgroundGuide]);

  // 터치/드래그 스크롤 개선
  const handleTouchStart = (e: React.TouchEvent) => {
    const target = e.currentTarget as HTMLElement;
    target.style.userSelect = 'none';
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const target = e.currentTarget as HTMLElement;
    target.style.userSelect = 'auto';
  };

  // 스크롤 위치 저장
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    setScrollPosition(target.scrollTop);
  };

  // 카테고리별 특화 모드 시작 함수들
  const startLoanMode = () => {
    setSpecializedMode('loan');
    setInputValue('');
    setShowBackgroundGuide(true);
    setMessages([]);
    
    // 스크롤을 맨 위로 이동
    setTimeout(() => {
      const questionTypes = document.querySelector('.main-question-types');
      if (questionTypes) {
        questionTypes.scrollTop = 0;
      }
    }, 100);
  };

  const startInsuranceMode = () => {
    setSpecializedMode('insurance');
    setInputValue('');
    setShowBackgroundGuide(true);
    setMessages([]);
    
    // 스크롤을 맨 위로 이동
    setTimeout(() => {
      const questionTypes = document.querySelector('.main-question-types');
      if (questionTypes) {
        questionTypes.scrollTop = 0;
      }
    }, 100);
  };

  const startCardMode = () => {
    setSpecializedMode('card');
    setInputValue('');
    setShowBackgroundGuide(true);
    setMessages([]);
    
    // 스크롤을 맨 위로 이동
    setTimeout(() => {
      const questionTypes = document.querySelector('.main-question-types');
      if (questionTypes) {
        questionTypes.scrollTop = 0;
      }
    }, 100);
  };

  const startHousingMode = () => {
    setSpecializedMode('housing');
    setInputValue('');
    setShowBackgroundGuide(true);
    setMessages([]);
    
    // 스크롤을 맨 위로 이동
    setTimeout(() => {
      const questionTypes = document.querySelector('.main-question-types');
      if (questionTypes) {
        questionTypes.scrollTop = 0;
      }
    }, 100);
  };

  const startInvestmentMode = () => {
    setSpecializedMode('investment');
    setInputValue('');
    setShowBackgroundGuide(true);
    setMessages([]);
    
    // 스크롤을 맨 위로 이동
    setTimeout(() => {
      const questionTypes = document.querySelector('.main-question-types');
      if (questionTypes) {
        questionTypes.scrollTop = 0;
      }
    }, 100);
  };

  // 일반 모드로 돌아가기
  const resetToGeneralMode = () => {
    setSpecializedMode('general');
    setMessages([]);
    setInputValue('');
    setShowBackgroundGuide(true);
  };

  // 상담 내역 화면으로 이동
  const showConsultationHistory = () => {
    setShowHistory(true);
  };

  // 상담 내역에서 돌아가기
  const backFromHistory = () => {
    setShowHistory(false);
  };

  const checkSystemHealth = async () => {
    try {
      const health = await apiClient.checkHealth();
      setIsConnected(health.connected);
    } catch (error) {
      setIsConnected(false);
      console.error('시스템 연결 확인 실패:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    // 배경화면 숨기기
    setShowBackgroundGuide(false);

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
      const chatRequest: ChatRequest = {
        message: inputValue,
        user_id: "default",
        mode: specializedMode,
        session_id: `session-${Date.now()}`
      };

      const response = await apiClient.sendChatMessage(chatRequest);

      const botMessage: Message = {
        id: `bot-${Date.now()}`,
        type: 'bot',
        content: response.response || '죄송합니다. 응답을 생성할 수 없습니다.',
        timestamp: new Date(),
        metadata: {
          success: response.success,
          quality: response.metadata?.quality_score,
          sources: response.metadata?.sources_count,
          agents: response.metadata?.recommendations,
          executionTime: response.metadata?.execution_time
        }
      };

      setMessages(prev => [...prev, botMessage]);
      
      if (response.success) {
        toast.success('응답이 성공적으로 생성되었습니다!');
      } else {
        toast.error('응답 생성 중 문제가 발생했습니다.');
      }

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
      await apiClient.resetSystem("default");
      toast.success('시스템이 리셋되었습니다.');
      setMessages([]);
      setShowBackgroundGuide(true);
    } catch (error) {
      toast.error('시스템 리셋에 실패했습니다.');
    }
  };

    const loadConsultation = async (messageId: string) => {
    try {
      const response = await apiClient.getConversationHistory("default");
      // 대화 히스토리에서 해당 메시지 찾기
      const conversation = response.history?.find((conv: any) => conv.id === messageId);
      
      if (conversation) {
        const botMessage: Message = {
          id: `bot-${Date.now()}`,
          type: 'bot',
          content: conversation.ai_response || '상담 내용을 불러올 수 없습니다.',
          timestamp: new Date(conversation.timestamp || Date.now()),
          metadata: {
            success: true,
            quality: conversation.quality_score,
            sources: conversation.sources?.length || 0
          }
        };
        setMessages(prev => [...prev, botMessage]);
        toast.success('상담 내용을 불러왔습니다.');
      } else {
        toast.error('해당 상담 내용을 찾을 수 없습니다.');
      }
    } catch (error) {
      console.error('상담 내용 불러오기 실패:', error);
      toast.error('상담 내용을 불러올 수 없습니다.');
    }
  };

  // 상담 종료 확인 화면 표시
  const handleEndConsultation = () => {
    setShowEndConsultation(true);
  };

  // 상담 종료 확인
  const confirmEndConsultation = () => {
    setShowEndConsultation(false);
    setShowSatisfactionSurvey(true);
  };

  // 상담 종료 취소
  const cancelEndConsultation = () => {
    setShowEndConsultation(false);
    // 상담 계속 - 입력 영역 다시 표시
  };

  // 만족도 제출
  const submitSatisfaction = async () => {
    if (satisfactionRating === 0) {
      toast.error('만족도를 선택해주세요.');
      return;
    }

    try {
      // 1. 로컬에 저장 (즉시)
      const satisfactionData = {
        rating: satisfactionRating,
        comment: satisfactionComment,
        consultationId: `consultation_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        category: specializedMode,
        timestamp: new Date().toISOString(),
        messageCount: messages.length,
        messages: messages.map(msg => ({
          type: msg.type,
          content: msg.content,
          timestamp: msg.timestamp.toISOString()
        }))
      };
      
      saveToLocalStorage(satisfactionData);
      
      // 2. 서버에 전송 (백그라운드) - 향후 구현 예정
      console.log('만족도 데이터가 로컬에 저장되었습니다.');
      
      toast.success('만족도 조사가 완료되었습니다. 감사합니다!');
      
      // 3. 메인 화면으로 복귀
      setTimeout(() => {
        resetToMainScreen();
      }, 1000);
      
    } catch (error) {
      console.error('만족도 제출 실패:', error);
      toast.error('만족도 제출에 실패했습니다.');
    }
  };

  // 로컬 스토리지에 만족도 데이터 저장
  const saveToLocalStorage = (data: any) => {
    try {
      const existing = JSON.parse(localStorage.getItem('satisfactionData') || '[]');
      existing.push(data);
      localStorage.setItem('satisfactionData', JSON.stringify(existing));
      console.log('만족도 데이터가 로컬에 저장되었습니다:', data);
    } catch (error) {
      console.error('로컬 저장 실패:', error);
    }
  };

  // 로컬 스토리지에서 만족도 데이터 불러오기
  const loadSatisfactionData = () => {
    try {
      const data = localStorage.getItem('satisfactionData');
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error('로컬 데이터 불러오기 실패:', error);
      return [];
    }
  };

  // 만족도 데이터 CSV 다운로드
  const downloadSatisfactionData = () => {
    try {
      const data = loadSatisfactionData();
      if (data.length === 0) {
        toast.error('다운로드할 만족도 데이터가 없습니다.');
        return;
      }

      // CSV 헤더 생성
      const headers = ['만족도', '의견', '카테고리', '메시지수', '상담ID', '제출시간'];
      const csvRows = [headers.join(',')];

      // 데이터 행 생성
      data.forEach((item: any) => {
        const row = [
          item.rating,
          `"${item.comment || ''}"`,
          item.category || 'general',
          item.messageCount || 0,
          item.consultationId,
          item.timestamp
        ];
        csvRows.push(row.join(','));
      });

      const csv = csvRows.join('\n');
      const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `만족도조사_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      toast.success('만족도 데이터가 다운로드되었습니다.');
    } catch (error) {
      console.error('CSV 다운로드 실패:', error);
      toast.error('다운로드에 실패했습니다.');
    }
  };

  // 만족도 조사 취소 (메인 화면으로 복귀)
  const cancelSatisfactionSurvey = () => {
    setShowSatisfactionSurvey(false);
    setShowBackgroundGuide(true);
    setMessages([]);
    setSatisfactionRating(0);
    setSatisfactionComment('');
    setSpecializedMode('general');
    setInputValue('');
    setIsLoading(false);
  };

  // 메인 화면으로 복귀 (상태 초기화)
  const resetToMainScreen = () => {
    setShowSatisfactionSurvey(false);
    setShowBackgroundGuide(true);
    setMessages([]);
    setSatisfactionRating(0);
    setSatisfactionComment('');
    setSpecializedMode('general');
    setInputValue('');
    setIsLoading(false);
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
                  src="/logo.jpeg" 
                  alt="금융분쟁 해결 AI 로고" 
                  className="kb-logo-image"
                />
              </div>
              <div>
                <h1 className="header-title">
                  KB국민은행이 도와드릴게요
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
          
          {/* 나의 상담내역 */}
          <div className="sidebar-section">
            <div className="sidebar-card">
              <button 
                onClick={showConsultationHistory}
                className="history-section-btn"
              >
                <h3 className="sidebar-title">
                  <FileText className="w-5 h-5" />
                  나의 상담내역
                </h3>
                
                <div className="history-preview">
                  {messages.length > 0 ? (
                    <div className="preview-content">
                      <div className="preview-text">
                        최근 상담: {messages.filter(msg => msg.type === 'user').length}건
                      </div>
                      <div className="preview-latest">
                        {(() => {
                          const latestUserMessage = messages
                            .filter(msg => msg.type === 'user')
                            .pop();
                          return latestUserMessage 
                            ? `${latestUserMessage.content.substring(0, 30)}...`
                            : '상담을 시작해보세요';
                        })()}
                      </div>
                    </div>
                  ) : (
                    <div className="preview-empty">
                      아직 상담 내역이 없습니다
                    </div>
                  )}
                </div>
              </button>
            </div>
          </div>

          {/* 만족도 데이터 관리 */}
          <div className="sidebar-section">
            <div className="sidebar-card">
              <h3 className="sidebar-title">
                <BarChart3 className="w-5 h-5" />
                만족도 데이터
              </h3>
              
              <div className="satisfaction-data-info">
                <div className="satisfaction-count">
                  총 {loadSatisfactionData().length}건의 만족도 조사
                </div>
                <div className="satisfaction-actions">
                  <button
                    onClick={downloadSatisfactionData}
                    className="download-satisfaction-btn"
                    title="만족도 데이터 CSV 다운로드"
                  >
                    <Download className="w-4 h-4" />
                    <span>데이터 다운로드</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* 전문 기관 연결 */}
          <div className="sidebar-section">
            <div className="sidebar-card">
              <h3 className="sidebar-title">
                <ExternalLink className="w-5 h-5" />
                분쟁 유형별 바로가기
              </h3>
              
              {/* 분쟁 유형별 바로가기 */}
              <div className="dispute-links">
                <button
                  onClick={startLoanMode}
                  className="dispute-link"
                >
                  <Scale className="w-4 h-4" />
                  <span>대출 분쟁 상담</span>
                </button>
                
                <button
                  onClick={startInsuranceMode}
                  className="dispute-link"
                >
                  <FileText className="w-4 h-4" />
                  <span>보험 분쟁 상담</span>
                </button>
                
                <button
                  onClick={startCardMode}
                  className="dispute-link"
                >
                  <HelpCircle className="w-4 h-4" />
                  <span>카드 분쟁 상담</span>
                </button>
                
                <button
                  onClick={startHousingMode}
                  className="dispute-link"
                >
                  <Search className="w-4 h-4" />
                  <span>주택 분쟁 상담</span>
                </button>
                
                <button
                  onClick={startInvestmentMode}
                  className="dispute-link"
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>투자 분쟁 상담</span>
                </button>
              </div>
              
              {/* 전문 기관 연결 */}
              <div className="institution-quick-links">
                <div className="institution-divider">
                  <span>전문 기관 연결</span>
                </div>
                
                <div className="institution-links">
                  <a 
                    href="https://www.fss.or.kr/fss/main/contents.do?menuNo=201179" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="institution-link-simple"
                  >
                    <div className="institution-icon-simple fss">
                      <img src="/kem.jpeg" alt="금융감독원 로고" className="institution-logo" />
                    </div>
                    <div className="institution-content-simple">
                      <div className="institution-name-simple">금융감독원</div>
                      <div className="institution-service-simple">금융민원신청</div>
                    </div>
                    <ExternalLink className="institution-external-icon-simple" />
                  </a>
                  
                  <a 
                    href="https://www.kca.go.kr/odr/" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="institution-link-simple"
                  >
                    <div className="institution-icon-simple kca">
                      <img src="/so.png" alt="소비자보호원 로고" className="institution-logo" />
                    </div>
                    <div className="institution-content-simple">
                      <div className="institution-name-simple">소비자보호원</div>
                      <div className="institution-service-simple">온라인 분쟁조정</div>
                    </div>
                    <ExternalLink className="institution-external-icon-simple" />
                  </a>
                  
                  <a 
                    href="https://obank.kbstar.com/quics?page=C044215#loading" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="institution-link-simple"
                  >
                    <div className="institution-icon-simple kb">
                      <img src="/logo.jpeg" alt="KB국민은행 로고" className="institution-logo" />
                    </div>
                    <div className="institution-content-simple">
                      <div className="institution-name-simple">KB국민은행</div>
                      <div className="institution-service-simple">온라인 민원접수</div>
                    </div>
                    <ExternalLink className="institution-external-icon-simple" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 메인 채팅 영역 */}
        <div className="chat-container">
          <div className="chat-wrapper">
            
            {/* 상담 내역 화면 */}
            {showHistory ? (
              <div className="history-screen">
                {/* 상담 내역 헤더 */}
                <div className="chat-header">
                  <button
                    onClick={backFromHistory}
                    className="back-to-menu-button"
                    title="상담 화면으로 돌아가기"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>뒤로가기</span>
                  </button>
                  
                  <div className="chat-header-left">
                    <h2 className="chat-title">
                      <FileText className="w-6 h-6 mr-2" style={{ color: '#BF9264' }} />
                      나의 상담내역
                    </h2>
                    <div className="chat-counter">
                      총 {messages.filter(msg => msg.type === 'user').length}건의 상담
                    </div>
                  </div>
                </div>

                {/* 상담 내역 목록 */}
                <div className="history-screen-content">
                  {messages.filter(msg => msg.type === 'user').length > 0 ? (
                    <div className="full-history-list">
                      {messages
                        .filter(msg => msg.type === 'user')
                        .map((message, index) => {
                          const botResponse = messages.find(msg => 
                            msg.type === 'bot' && 
                            messages.indexOf(msg) > messages.indexOf(message) &&
                            messages.indexOf(msg) === messages.indexOf(message) + 1
                          );
                          
                          return (
                            <div key={message.id} className="full-history-item">
                              <div className="history-item-header">
                                <div className="history-item-meta">
                                  <span className="history-item-number">#{messages.filter(msg => msg.type === 'user').length - index}</span>
                                  <span className="history-item-time">
                                    {message.timestamp.toLocaleDateString()} {message.timestamp.toLocaleTimeString()}
                                  </span>
                                </div>
                                <button
                                  onClick={() => loadConsultation(message.id)}
                                  className="history-load-btn"
                                  title="이 상담 내용 불러오기"
                                >
                                  <Search className="w-4 h-4" />
                                  <span>불러오기</span>
                                </button>
                              </div>
                              
                              <div className="history-item-content">
                                <div className="history-question">
                                  <strong>질문:</strong> {message.content}
                                </div>
                                {botResponse && (
                                  <div className="history-answer">
                                    <strong>답변:</strong> {botResponse.content.length > 200 
                                      ? `${botResponse.content.substring(0, 200)}...` 
                                      : botResponse.content}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  ) : (
                    <div className="empty-history-screen">
                      <div className="empty-history-icon">
                        <FileText className="w-16 h-16" />
                      </div>
                      <div className="empty-history-text">
                        아직 상담 내역이 없습니다
                      </div>
                      <div className="empty-history-subtext">
                        상담을 시작하면 여기에 기록됩니다
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <>
                {/* 상담종료 확인 화면 */}
                {showEndConsultation && (
                  <div className="end-consultation-modal">
                    <div className="end-consultation-content">
                      <div className="end-consultation-header">
                        <CheckCircle className="w-12 h-12 text-green-500" />
                        <h3 className="end-consultation-title">상담을 종료하시겠습니까?</h3>
                        <p className="end-consultation-subtitle">
                          상담 종료 후 만족도 조사를 진행합니다.
                        </p>
                      </div>
                      <div className="end-consultation-actions">
                        <button
                          onClick={cancelEndConsultation}
                          className="end-consultation-cancel-btn"
                        >
                          계속 상담하기
                        </button>
                        <button
                          onClick={confirmEndConsultation}
                          className="end-consultation-confirm-btn"
                        >
                          상담 종료하기
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 만족도 조사 화면 */}
                {showSatisfactionSurvey && (
                  <div className="satisfaction-survey-modal">
                    <div className="satisfaction-survey-content">
                      <div className="satisfaction-survey-header">
                        <div className="satisfaction-survey-icon">⭐</div>
                        <h3 className="satisfaction-survey-title">만족도 조사</h3>
                        <p className="satisfaction-survey-subtitle">
                          오늘의 상담은 어떠셨나요? 소중한 의견을 들려주세요.
                        </p>
                      </div>
                      
                      <div className="satisfaction-rating-section">
                        <h4 className="satisfaction-rating-title">전체적인 만족도</h4>
                        <div className="satisfaction-stars">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              onClick={() => setSatisfactionRating(star)}
                              className={`satisfaction-star ${satisfactionRating >= star ? 'active' : ''}`}
                            >
                              {satisfactionRating >= star ? '★' : '☆'}
                            </button>
                          ))}
                        </div>
                        <div className="satisfaction-rating-text">
                          {satisfactionRating === 0 && '별을 클릭하여 만족도를 선택해주세요'}
                          {satisfactionRating === 1 && '매우 불만족'}
                          {satisfactionRating === 2 && '불만족'}
                          {satisfactionRating === 3 && '보통'}
                          {satisfactionRating === 4 && '만족'}
                          {satisfactionRating === 5 && '매우 만족'}
                        </div>
                      </div>

                      <div className="satisfaction-comment-section">
                        <h4 className="satisfaction-comment-title">추가 의견 (선택사항)</h4>
                        <textarea
                          value={satisfactionComment}
                          onChange={(e) => setSatisfactionComment(e.target.value)}
                          placeholder="상담에 대한 의견이나 개선사항을 자유롭게 작성해주세요..."
                          className="satisfaction-comment-textarea"
                          rows={4}
                        />
                      </div>

                      <div className="satisfaction-survey-actions">
                        <button
                          onClick={cancelSatisfactionSurvey}
                          className="satisfaction-survey-cancel-btn"
                        >
                          건너뛰기
                        </button>
                        <button
                          onClick={submitSatisfaction}
                          disabled={satisfactionRating === 0}
                          className="satisfaction-survey-submit-btn"
                        >
                          제출하기
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* 채팅 헤더 */}
                <div className="chat-header">
                  {specializedMode !== 'general' && (
                    <button
                      onClick={resetToGeneralMode}
                      className="back-to-menu-button"
                      title="카테고리 선택으로 돌아가기"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      <span>뒤로가기</span>
                    </button>
                  )}
                  
                  <div className="chat-header-left">
                    <h2 className="chat-title">
                      <Zap className="w-6 h-6 mr-2" style={{ color: '#BF9264' }} />
                      {specializedMode === 'general' ? 'AI 어시스턴트와 대화' : 
                       specializedMode === 'loan' ? '🏦 대출 분쟁 전문 상담' :
                       specializedMode === 'insurance' ? '🛡️ 보험 분쟁 전문 상담' :
                       specializedMode === 'card' ? '💳 카드 분쟁 전문 상담' :
                       specializedMode === 'housing' ? '🏠 주택 분쟁 전문 상담' :
                       '📈 투자 분쟁 전문 상담'}
                  </h2>
                    <div className="chat-counter">
                    {messages.length > 0 && `${messages.length}개 메시지`}
                    </div>
                  </div>

                  {/* 상담종료 버튼 - 헤더 우측에 배치 */}
                  {messages.length > 0 && !showBackgroundGuide && !showEndConsultation && !showSatisfactionSurvey && (
                    <button
                      onClick={handleEndConsultation}
                      className="end-consultation-header-button"
                      title="상담 종료하기"
                    >
                      <CheckCircle className="w-4 h-4" />
                      <span>상담종료</span>
                    </button>
                  )}
                </div>

                {/* 메시지 영역 */}
                <div className="chat-messages" onScroll={handleScroll}>
                  {/* 배경 설명문 - 메시지가 있어도 표시 */}
                  {showBackgroundGuide && (
                    <div className="empty-chat-container">
                      <div className="background-guide">
                        {specializedMode === 'general' && (
                          <>
                            <div className="guide-icon">💬</div>
                            <h3 className="guide-title">어떤 금융분쟁으로 도움이 필요하신가요?</h3>
                            <p className="guide-subtitle">왼쪽 사이드바에서 분쟁 유형을 선택하시거나, 직접 상황을 설명해주세요</p>
                          </>
                        )}
                        
                        {specializedMode === 'loan' && (
                          <>
                            <div className="guide-icon">🏦</div>
                            <h3 className="guide-title">대출 분쟁 전문 상담</h3>
                            <p className="guide-subtitle">대출 관련 문제를 해결해드립니다</p>
                            
                            {/* 주요 질문 유형 */}
                            <div className="main-question-types"
                                 onTouchStart={handleTouchStart}
                                 onTouchEnd={handleTouchEnd}
                                 onScroll={handleScroll}>
                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">계약 내용 및 불완전판매</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    계약 조건이 제대로 설명되지 않았거나, 중요한 정보를 숨긴 경우
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "설명도 제대로 안 해주고 대출을 받게 했는데, 이거 불완전판매 아닌가요?"
                                  </div>
                                </div>
                              </div>
                              
                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">대출 상환/연체 문제</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    이자율 변동, 상환 조건 변경, 연체 상황 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "이자율이 갑자기 올랐는데 원래 이런 건가요?"
                                  </div>
                                </div>
                              </div>
                              
                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">보증 및 담보 관련</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    보증인 책임, 담보 처리, 연대보증 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "가족 명의로 보증을 서달라고 해서 했는데, 지금 문제가 생겼어요. 책임져야 하나요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">사기/사채 의심 상황</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    불법사채, 사기성 대출, 과도한 이자율 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "지인을 통해 소개받은 업체인데 이자가 너무 높아요. 불법사채인가요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">채무조정/회생/파산 관련</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    채무조정, 개인회생, 파산 신청 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "대출이 많아서 감당이 안 돼요. 채무조정이나 회생 신청이 가능할까요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">대출 중복/대출 비교</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    다중 대출, 대출 한도, 신용도 영향 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "다른 은행에서도 대출을 받으려고 하는데 기존 대출에 문제 있나요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">대출 관련 서류/계약 해지</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    계약서 요구, 철회권, 해지 조건 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "대출계약서를 안 줬는데 요구할 수 있나요?", "대출받고 나서 3일 이내면 철회 가능한가요?"
                                  </div>
                                </div>
                              </div>
                            </div>
                          </>
                        )}
                        
                        {specializedMode === 'insurance' && (
                          <>
                            <div className="guide-icon">🛡️</div>
                            <h3 className="guide-title">보험 분쟁 전문 상담</h3>
                            <p className="guide-subtitle">보험 관련 문제를 해결해드립니다</p>
                            
                            {/* 주요 질문 유형 */}
                            <div className="main-question-types"
                                 onTouchStart={handleTouchStart}
                                 onTouchEnd={handleTouchEnd}
                                 onScroll={handleScroll}>
                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">보험금 청구 거절 관련</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    보험금 지급 거부, 청구 서류 문제, 약관 해석 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "진단서도 냈는데 보험금이 왜 안 나와요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">계약 해지/무효 관련</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    계약 무효, 해지, 고지의무 위반 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "제가 고지 안 했다고 계약을 무효로 한다는데, 이게 가능한가요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">보험설계사 설명 부족/불완전판매</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    설명 부족, 불완전판매, 약관 미고지 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "가입할 때 암이면 무조건 나온다 했는데, 지금 와서 안 된대요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">보험료 납입 관련</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    보험료 미납, 납입 유예, 계약 효력 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "경제사정이 어려워서 보험료를 못 내고 있어요. 불이익 있나요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">보험 사기 의심/부당한 조사</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    과도한 조사 요구, 사기 의심, 개인정보 침해 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "보험금 청구했는데 너무 과도한 조사를 요구해요. 이게 정상인가요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">보험 상품 변경/환급금</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    상품 변경, 환급금 지급, 해지환급금 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "보험을 해지하려고 하는데 환급금이 얼마나 나올까요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">보험 약관 해석/적용</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    약관 해석, 보장 범위, 면책 사유 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "약관에 이런 내용이 있다고 하는데, 제가 이해한 게 맞나요?"
                                  </div>
                                </div>
                              </div>
                            </div>
                          </>
                        )}
                        
                        {specializedMode === 'card' && (
                          <>
                            <div className="guide-icon">💳</div>
                            <h3 className="guide-title">카드 분쟁 전문 상담</h3>
                            <p className="guide-subtitle">카드 관련 문제를 해결해드립니다</p>
                            
                            {/* 주요 질문 유형 */}
                            <div className="main-question-types"
                                 onTouchStart={handleTouchStart}
                                 onTouchEnd={handleTouchEnd}
                                 onScroll={handleScroll}>
                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">부정사용/도난/해킹 결제</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    카드 도난, 부정사용, 해킹으로 인한 결제 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "카드 도난 당했는데 누가 결제했어요. 이거 제가 다 갚아야 해요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">결제 취소/환불 문제</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    결제 취소, 환불, 청구서 정정 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "가맹점에서 결제를 취소해준다더니 아직 카드 청구에 찍혀 있어요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">할부 관련 문제</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    자동 할부, 할부 조건 변경, 할부 수수료 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "1회 결제인 줄 알았는데 자동으로 할부로 되어버렸어요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">연회비/수수료 관련</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    연회비, 수수료, 부당한 요금 청구 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "카드를 안 썼는데 연회비가 청구됐어요. 환불 가능할까요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">서비스 미제공/부실 제공</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    상품 미배송, 서비스 미제공, 품질 문제 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "결제한 상품이 배송되지 않았어요. 카드사에 취소 요청할 수 있나요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">중복 결제/미승인 거래</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    중복 결제, 미승인 거래, 승인 오류 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "같은 결제가 두 번 찍혔어요. 중복 결제 아닌가요?"
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">카드 발급/해지 관련</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    카드 발급 거절, 해지 조건, 신용도 영향 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "카드 해지하려고 하는데 남은 할부가 있어서 안 된다고 해요."
                                  </div>
                                </div>
                              </div>
                            </div>
                          </>
                        )}
                        
                        {specializedMode === 'housing' && (
                          <>
                            <div className="guide-icon">🏠</div>
                            <h3 className="guide-title">주택 분쟁 전문 상담</h3>
                            <p className="guide-subtitle">주택 관련 문제를 해결해드립니다</p>
                            
                            {/* 주요 질문 유형 */}
                            <div className="main-question-types"
                                 onTouchStart={handleTouchStart}
                                 onTouchEnd={handleTouchEnd}
                                 onScroll={handleScroll}>
                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">보증금 미반환</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    전세보증금, 월세보증금 미반환, 반환 조건 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "계약 끝났는데 집주인이 보증금을 안 돌려줘요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">하자 미보수</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    시설 하자, 수리 거부, 보수 책임 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "입주했는데 벽에 곰팡이가 심해요. 수리 안 해줘요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">계약해지 분쟁</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    임대인 해지, 임차인 해지, 해지 조건 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "집주인이 계약 중간에 나가라고 해요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">층간소음/생활 분쟁</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    층간소음, 생활방해, 소음 민원 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "위층 소음 때문에 살 수가 없어요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">관리비/공과금 분쟁</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    관리비 청구, 공과금 분담, 부당 요금 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "퇴거했는데도 관리비가 계속 청구돼요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">전입신고 제한</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    전입신고 거부, 주민등록, 거주지 등록 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "집주인이 전입신고 하지 말라고 해요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">특약 사항 분쟁</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    특약 추가, 계약서 수정, 구두 약정 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "계약서에 없던 특약을 나중에 주장해요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">경매/매매 시 권리보호</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    경매, 매매, 임차권 보호, 우선매수권 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "전세계약했는데 집이 경매로 넘어갔어요."
                                  </div>
                                </div>
                              </div>
                            </div>
                          </>
                        )}
                        
                        {specializedMode === 'investment' && (
                          <>
                            <div className="guide-icon">📈</div>
                            <h3 className="guide-title">투자 분쟁 전문 상담</h3>
                            <p className="guide-subtitle">투자 관련 문제를 해결해드립니다</p>
                            
                            {/* 주요 질문 유형 */}
                            <div className="main-question-types"
                                 onTouchStart={handleTouchStart}
                                 onTouchEnd={handleTouchEnd}
                                 onScroll={handleScroll}>
                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">불완전판매/설명 부족</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    투자 상품 설명 부족, 위험성 미고지, 수익률 과장 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "투자 상품을 가입할 때 위험성을 제대로 설명 안 해줬어요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">투자 손실/원금 손실</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    투자 손실, 원금 손실, 보장되지 않은 수익 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "원금 보장된다고 했는데 손실이 났어요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">펀드/신탁 관련 분쟁</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    펀드 손실, 신탁 해지, 수수료 문제 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "펀드 가입했는데 예상과 다르게 손실이 났어요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">주식/채권 투자 분쟁</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    주식 투자 손실, 채권 만기, 이자 지급 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "주식 투자 상담받고 샀는데 큰 손실이 났어요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">해지/환매 관련</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    투자 상품 해지, 환매 수수료, 해지 조건 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "투자 상품을 해지하려고 하는데 수수료가 너무 높아요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">투자 사기/부당 판매</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    투자 사기, 부당 판매, 허위 광고 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "높은 수익률을 약속받고 투자했는데 사기인 것 같아요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">투자 상담/자문 분쟁</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    투자 상담 책임, 자문 서비스, 전문성 부족 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "투자 상담사가 잘못된 정보를 줘서 손실이 났어요."
                                  </div>
                                </div>
                              </div>

                              <div className="main-question-type">
                                <div className="main-question-type-left">
                                  <div className="main-question-type-header">
                                    <h4 className="main-question-type-title">외환/해외투자 분쟁</h4>
                                  </div>
                                  <div className="main-question-type-description">
                                    외환 투자, 해외 펀드, 환율 손실 등
                                  </div>
                                </div>
                                <div className="main-question-type-right">
                                  <div className="main-question-type-example">
                                    "해외 펀드에 투자했는데 환율 손실이 너무 커요."
                                  </div>
                                </div>
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* 실제 채팅 메시지들 렌더링 */}
                  {messages.map((message) => (
                    <div key={message.id} className={`chat-message ${message.type}`}>
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                        message.type === 'user' 
                          ? 'bg-gradient-to-r from-green-500 to-blue-500' 
                          : 'bg-gradient-to-r from-blue-600 to-purple-600'
                      }`}>
                        {message.type === 'user' ? (
                          <User className="w-5 h-5 text-white" />
                        ) : (
                          <Bot className="w-5 h-5 text-white" />
                        )}
                      </div>
                      <div className="chat-message-content">
                        <div className="message-text">
                          {message.content}
                        </div>
                        {message.metadata && (
                          <div className="message-metadata">
                            {message.metadata.sources && message.metadata.sources.length > 0 && (
                              <div className="message-sources">
                                <strong>참고 자료:</strong>
                                <ul>
                                  {message.metadata.sources.map((source, index) => (
                                    <li key={index}>{source}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {message.metadata.agents && message.metadata.agents.length > 0 && (
                              <div className="message-agents">
                                <strong>처리 과정:</strong>
                                <ul>
                                  {message.metadata.agents.map((agent, index) => (
                                    <li key={index}>{agent}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {message.metadata.executionTime && (
                              <div className="message-execution-time">
                                <Clock className="w-4 h-4" />
                                <span>{message.metadata.executionTime.toFixed(2)}초</span>
                              </div>
                            )}
                          </div>
                        )}
                        <div className="message-timestamp">
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {isLoading && (
                    <div className="chat-message bot">
                      <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                        <Bot className="w-5 h-5 text-white" />
                      </div>
                      <div className="chat-message-content">
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
                {!showEndConsultation && !showSatisfactionSurvey && (
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
                          <Activity className="w-4 h-4 animate-spin" />
                        ) : (
                          <Send className="w-4 h-4" />
                        )}
                        <span>전송</span>
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
