import axios, { type AxiosResponse } from 'axios';

// API 응답 타입 정의
export interface ChatRequest {
  message: string;
  user_id?: string;
  mode?: string;
  session_id?: string;
}

export interface ChatResponse {
  success: boolean;
  message: string;
  response?: string;
  metadata?: {
    execution_time: number;
    quality_score: number;
    sources_count: number;
    recommendations: string[];
    session_id?: string;
  };
  error?: string;
}

export interface SystemStatus {
  success: boolean;
  status: {
    system_type: string;
    initialized: boolean;
    timestamp: string;
    [key: string]: any;
  };
  system_type: string;
}

export interface ConversationHistory {
  success: boolean;
  user_id: string;
  history: Array<{
    id: string;
    timestamp: string;
    user_query: string;
    ai_response: string;
    quality_score?: number;
    sources?: string[];
  }>;
  count: number;
}

export interface ExportResponse {
  success: boolean;
  user_id: string;
  format: string;
  data: string;
}

// API 클라이언트 클래스
class ApiClient {
  private client: any;
  private baseURL: string;

  constructor(baseURL: string = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.client = axios.create({
      baseURL,
      timeout: 600000, // 10분 타임아웃 (AI 모델 처리 시간 고려)
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 요청 인터셉터
    this.client.interceptors.request.use(
      (config: any) => {
        console.log(`🚀 API 요청: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error: any) => {
        console.error('❌ API 요청 오류:', error);
        return Promise.reject(error);
      }
    );

    // 응답 인터셉터
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        console.log(`✅ API 응답: ${response.status} ${response.config.url}`);
        return response;
      },
      (error: any) => {
        console.error('❌ API 응답 오류:', error);
        if (error.response) {
          console.error('응답 데이터:', error.response.data);
          console.error('응답 상태:', error.response.status);
        }
        return Promise.reject(error);
      }
    );
  }

  // 시스템 건강 상태 확인
  async checkHealth(): Promise<{ status: string; connected: boolean }> {
    try {
      const response = await this.client.get('/health');
      return {
        status: response.data.status,
        connected: response.data.status === 'healthy'
      };
    } catch (error) {
      console.error('건강 상태 확인 실패:', error);
      return {
        status: 'error',
        connected: false
      };
    }
  }

  // 시스템 상태 조회
  async getSystemStatus(): Promise<SystemStatus> {
    try {
      const response = await this.client.get('/status');
      return response.data;
    } catch (error) {
      throw new Error(`시스템 상태 조회 실패: ${error}`);
    }
  }

  // 채팅 메시지 전송
  async sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await this.client.post('/chat', request);
      return response.data;
    } catch (error) {
      throw new Error(`채팅 메시지 전송 실패: ${error}`);
    }
  }

  // 스트리밍 채팅 (향후 확장)
  async sendChatMessageStream(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await this.client.post('/chat/stream', request);
      return response.data;
    } catch (error) {
      throw new Error(`스트리밍 채팅 실패: ${error}`);
    }
  }

  // 시스템 리셋
  async resetSystem(userId: string = 'default'): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.client.post('/reset', { user_id: userId });
      return response.data;
    } catch (error) {
      throw new Error(`시스템 리셋 실패: ${error}`);
    }
  }

  // 대화 히스토리 조회
  async getConversationHistory(userId: string = 'default'): Promise<ConversationHistory> {
    try {
      const response = await this.client.get(`/conversation/${userId}`);
      return response.data;
    } catch (error) {
      throw new Error(`대화 히스토리 조회 실패: ${error}`);
    }
  }

  // 대화 데이터 내보내기
  async exportConversation(userId: string, format: 'json' | 'txt'): Promise<ExportResponse> {
    try {
      const response = await this.client.post(`/export/${userId}?format_type=${format}`);
      return response.data;
    } catch (error) {
      throw new Error(`대화 데이터 내보내기 실패: ${error}`);
    }
  }

  // 사용 가능한 모드 조회
  async getAvailableModes(): Promise<{ success: boolean; modes: any[]; default_mode: string }> {
    try {
      const response = await this.client.get('/modes');
      return response.data;
    } catch (error) {
      throw new Error(`모드 조회 실패: ${error}`);
    }
  }

  // 연결 테스트
  async testConnection(): Promise<boolean> {
    try {
      await this.client.get('/');
      return true;
    } catch (error) {
      return false;
    }
  }

  // 기본 URL 변경
  setBaseURL(url: string) {
    this.baseURL = url;
    this.client.defaults.baseURL = url;
  }

  // 현재 기본 URL 반환
  getBaseURL(): string {
    return this.baseURL;
  }
}

// 기본 인스턴스 생성
export const apiClient = new ApiClient();

export default ApiClient; 