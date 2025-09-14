/**
 * EventSource-based AI Service for immediate OK message delivery
 * Uses native browser EventSource API for true Server-Sent Events streaming
 */

import { CapturedPhoto, SupportedLanguage } from '@/app/wondercam/page';
import { createClient } from '@/lib/supabase/client';

// V2 API Types
export interface V2ContentPart {
  text?: string;
  inlineData?: {
    mimeType: string;
    data: string;
  };
}

export interface V2ChatRequest {
  contents: V2ContentPart[];
  language?: string;
  session_id?: string;
  stream: boolean;
  preprocessing?: Record<string, any>;
}

export class AIServiceEventSource {
  private supabase = createClient();
  
  /**
   * Get JWT token for Authorization header
   */
  private async getAuthToken(): Promise<string> {
    const { data: { session }, error } = await this.supabase.auth.getSession();
    
    if (error) {
      throw new Error(`Authentication error: ${error.message}`);
    }
    
    if (!session?.access_token) {
      throw new Error('User not authenticated - no session or access token');
    }
    
    return session.access_token;
  }

  /**
   * Create V2 content parts from text
   */
  createTextContent(text: string, language?: SupportedLanguage): V2ContentPart[] {
    const languageInstructions = {
      'en': 'Respond in English.',
      'zh': '请用中文回答。',
      'es': 'Responde en español.',
      'fr': 'Répondez en français.',
      'ja': '日本語で答えてください。'
    };

    const instruction = language && language !== 'en' ? languageInstructions[language] : null;
    const finalText = instruction ? `${instruction} ${text}` : text;

    return [{ text: finalText }];
  }

  /**
   * Create V2 content parts with image
   */
  createImageContent(text: string, photo: CapturedPhoto, language?: SupportedLanguage): V2ContentPart[] {
    const textContent = this.createTextContent(text, language);
    
    if (!photo.compressedData) {
      console.warn('⚠️ Photo compressedData is undefined, returning text-only content');
      return textContent;
    }
    
    return [
      ...textContent,
      {
        inlineData: {
          mimeType: 'image/jpeg',
          data: photo.compressedData.includes(',') ?
            photo.compressedData.split(',')[1] : photo.compressedData
        }
      }
    ];
  }

  /**
   * Send chat request using EventSource for true SSE streaming
   */
  async *chatStreamEventSource(
    contents: V2ContentPart[],
    language: SupportedLanguage = 'en',
    sessionId?: string
  ): AsyncGenerator<string | { type: 'text' | 'image', data: string }> {
    
    try {
      const authToken = await this.getAuthToken();
      
      const requestBody: V2ChatRequest = {
        contents,
        language,
        session_id: sessionId,
        stream: true
      };

      const hasImages = contents.some(c => c.inlineData?.mimeType?.startsWith('image/'));
      const hasAudio = contents.some(c => c.inlineData?.mimeType?.startsWith('audio/'));

      console.log('🎯 EventSource V2 Enhanced API Request:', {
        endpoint: '/v2/echat',
        contentParts: contents.length,
        language,
        sessionId,
        hasImages,
        hasAudio,
        timestamp: Date.now()
      });

      // Create a special EventSource endpoint that accepts POST data via query parameters
      // We'll need to create this endpoint on the server
      const encodedRequest = encodeURIComponent(JSON.stringify(requestBody));
      const url = `http://localhost:18000/v2/echat?data=${encodedRequest}&auth=${encodeURIComponent(authToken)}`;

      console.log('🔗 EventSource URL:', url.substring(0, 100) + '...');

      return new Promise<AsyncGenerator<string | { type: 'text' | 'image', data: string }>>(
        (resolve, reject) => {
          const eventSource = new EventSource(url);
          
          const generator = (async function* () {
            let messageCount = 0;
            const startTime = Date.now();
            
            const messagePromises: Promise<any>[] = [];
            let resolved = false;
            
            eventSource.onmessage = (event) => {
              const messageTime = Date.now();
              messageCount++;
              
              const timestamp = new Date().toISOString();
              console.log(`📨 EventSource [${timestamp}] message #${messageCount} at +${messageTime - startTime}ms:`,
                event.data.substring(0, 100) + (event.data.length > 100 ? '...' : ''));
              
              try {
                if (event.data && event.data !== '[DONE]') {
                  const data = JSON.parse(event.data);
                  
                  // Handle different response formats
                  if (typeof data === 'object' && data !== null) {
                    // Handle Vertex AI format (direct streaming)
                    if ('candidates' in data && Array.isArray(data.candidates)) {
                      for (const candidate of data.candidates) {
                        if (candidate.content?.parts) {
                          for (const part of candidate.content.parts) {
                            if (part.text) {
                              const textTimestamp = new Date().toISOString();
                              console.log(`✅ EventSource [${textTimestamp}]: Immediate text received at +${messageTime - startTime}ms:`, part.text);
                              const promise = Promise.resolve(part.text);
                              messagePromises.push(promise);
                              return promise;
                            } else if (part.inlineData?.data) {
                              const imageTimestamp = new Date().toISOString();
                              console.log(`🖼️ EventSource [${imageTimestamp}]: Image chunk received at +${messageTime - startTime}ms`);
                              const promise = Promise.resolve({ type: 'image' as const, data: part.inlineData.data });
                              messagePromises.push(promise);
                              return promise;
                            }
                          }
                        }
                      }
                    }
                    // Handle status message format
                    else if ('type' in data && 'data' in data) {
                      const statusTimestamp = new Date().toISOString();
                      console.log(`📋 EventSource [${statusTimestamp}]: Status message at +${messageTime - startTime}ms:`, data);
                      const promise = Promise.resolve({ type: data.type, data: data.data });
                      messagePromises.push(promise);
                      return promise;
                    }
                  }
                }
              } catch (e) {
                console.warn('⚠️ EventSource: Failed to parse message:', event.data, e);
              }
            };
            
            eventSource.onerror = (error) => {
              console.error('❌ EventSource error:', error);
              eventSource.close();
              reject(new Error('EventSource connection failed'));
            };
            
            // Generator yields promises as they're created
            try {
              while (messagePromises.length > 0) {
                const result = await messagePromises.shift()!;
                yield result;
              }
            } finally {
              eventSource.close();
            }
          })();
          
          resolve(generator);
        }
      );

    } catch (error: any) {
      console.error('❌ EventSource V2 AI Service Error:', error);
      throw error;
    }
  }

  /**
   * Simple text-only chat using EventSource
   */
  async *simpleChat(
    text: string,
    language: SupportedLanguage = 'en',
    conversationHistory: any[] = []
  ): AsyncGenerator<string> {
    
    const contents = this.createTextContent(text, language);
    
    for await (const chunk of this.chatStreamEventSource(contents, language)) {
      if (typeof chunk === 'string') {
        yield chunk;
      } else if (typeof chunk === 'object' && chunk !== null && 'type' in chunk && 'data' in chunk && chunk.type === 'text') {
        yield chunk.data;
      } else {
        console.warn('⚠️ Unhandled EventSource chunk format:', chunk);
      }
    }
  }
}

// Export singleton instance
export const aiServiceEventSource = new AIServiceEventSource();