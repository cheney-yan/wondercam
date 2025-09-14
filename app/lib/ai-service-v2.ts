/**
 * WonderCam V2 AI Service
 * Simplified, extensible API client for v2 backend
 */

import { CapturedPhoto, SupportedLanguage } from '@/app/wondercam/page';
import { createClient } from '@/lib/supabase/client';

// V2 API Types - Simplified Gemini-compatible format
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

// Legacy types for backward compatibility
export interface V2MessageContent {
  type: 'text' | 'image' | 'voice';
  data: string;
  mime_type?: string;
}

export interface V2Message {
  role: 'user' | 'assistant' | 'system';
  content: V2MessageContent[];
  timestamp?: string;
  message_id?: string;
}

export interface V2ResponseChunk {
  type: 'text' | 'image' | 'voice' | 'system' | 'error';
  content: any;
  metadata?: Record<string, any>;
  is_final: boolean;
}

export interface V2SystemMessage {
  type: string;
  content: string;
  action?: string;
  options?: string[];
}

export class AIServiceV2 {
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
    
    // Handle case where compressedData might be undefined
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
   * Create V2 content parts with voice (future implementation)
   */
  createVoiceContent(
    text: string,
    audioData: string,
    language?: SupportedLanguage
  ): V2ContentPart[] {
    const textContent = this.createTextContent(text, language);
    
    return [
      ...textContent,
      {
        inlineData: {
          mimeType: 'audio/webm',
          data: audioData.includes(',') ? audioData.split(',')[1] : audioData
        }
      }
    ];
  }

  // Legacy methods for backward compatibility
  /**
   * Create a V2 message from text content (legacy)
   */
  createTextMessage(text: string, role: 'user' | 'assistant' = 'user'): V2Message {
    return {
      role,
      content: [{
        type: 'text',
        data: text
      }],
      timestamp: new Date().toISOString(),
      message_id: crypto.randomUUID()
    };
  }

  /**
   * Create a V2 message with image content (legacy)
   */
  createImageMessage(
    text: string,
    photo: CapturedPhoto,
    role: 'user' | 'assistant' = 'user'
  ): V2Message {
    const content: V2MessageContent[] = [
      {
        type: 'text',
        data: text
      }
    ];

    // Only add image content if compressedData exists
    if (photo.compressedData) {
      content.push({
        type: 'image',
        data: photo.compressedData,
        mime_type: 'image/jpeg'
      });
    } else {
      console.warn('⚠️ Photo compressedData is undefined in createImageMessage');
    }

    return {
      role,
      content,
      timestamp: new Date().toISOString(),
      message_id: crypto.randomUUID()
    };
  }

  /**
   * Send chat request to V2 API with streaming support
   */
  async *chatStream(
    contents: V2ContentPart[],
    language: SupportedLanguage = 'en',
    sessionId?: string
  ): AsyncGenerator<V2ResponseChunk | { type: 'text' | 'image', data: string }> {
    
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

      console.log('🚀 V2 Enhanced API Request:', {
        endpoint: '/v2/echat',
        contentParts: contents.length,
        language,
        sessionId,
        hasImages,
        hasAudio
      });

      // Use direct API server connection to avoid Next.js proxy buffering
      const backendHost = process.env.NEXT_PUBLIC_BACKEND_API_HOST || 'http://localhost:18000';
      const response = await fetch(`${backendHost}/v2/echat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
          'Cache-Control': 'no-cache',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ V2 API Error:', {
          status: response.status,
          statusText: response.statusText,
          body: errorText
        });
        throw new Error(`V2 API error: ${response.status} - ${errorText}`);
      }

      // Parse streaming response
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Process chunks immediately as they arrive
          const chunk = decoder.decode(value, { stream: true });
          const timestamp = new Date().toISOString();
          const relativeTime = Date.now();
          console.log(`📨 V2 API [${timestamp}]: Received raw chunk:`, chunk.length, 'bytes at', relativeTime);
          
          buffer += chunk;
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          console.log(`🔍 V2 API [${timestamp}]: Split ${chunk.length}-byte chunk into ${lines.length} lines, buffer remaining: ${buffer.length} chars`);
          
          // Show first 200 chars of the raw chunk for debugging
          const chunkPreview = chunk.substring(0, 200).replace(/\n/g, '\\n').replace(/\r/g, '\\r');
          console.log(`🔍 RAW CHUNK PREVIEW: "${chunkPreview}${chunk.length > 200 ? '...' : ''}"`);

          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const lineTimestamp = new Date().toISOString();
            const lineIndex = i + 1;
            
            console.log(`📋 V2 API [${lineTimestamp}]: Processing line ${lineIndex}/${lines.length}: "${line.substring(0, 50)}${line.length > 50 ? '...' : ''}"`);
              if (line.startsWith('data:')) {
                try {
                  const jsonStr = line.substring(5).trim();
                  const dataTimestamp = new Date().toISOString();
                  const dataRelativeTime = Date.now();
                  console.log(`📡 V2 API [${dataTimestamp}]: Processing SSE data line at`, dataRelativeTime, ':', jsonStr.substring(0, 100) + (jsonStr.length > 100 ? '...' : ''));
                
                if (jsonStr && jsonStr !== '[DONE]') {
                  const data = JSON.parse(jsonStr);
                  console.log('📦 V2 API: Parsed data structure:', {
                    type: typeof data,
                    isNull: data === null,
                    keys: data && typeof data === 'object' ? Object.keys(data) : [],
                    hasCandidates: data && 'candidates' in data,
                    hasType: data && 'type' in data,
                    hasData: data && 'data' in data
                  });
                  
                  // Handle different response formats
                  if (typeof data === 'object' && data !== null) {
                    // Handle V2ResponseChunk format (preprocessing messages)
                    if ('type' in data && 'content' in data && 'is_final' in data) {
                      // This is a V2ResponseChunk (preprocessing/system message)
                      const chunkTimestamp = new Date().toISOString();
                      console.log(`🔧 V2ResponseChunk [${chunkTimestamp}] detected:`, { type: data.type, content: data.content?.substring(0, 50) });
                      if (data.type === 'system') {
                        const systemTimestamp = new Date().toISOString();
                        console.log(`🔧 System message [${systemTimestamp}]:`, data.content);
                        yield data;
                      } else if (data.type === 'error') {
                        console.error('❌ V2 API chunk error:', data.content);
                        throw new Error(data.content);
                      } else {
                        yield { type: data.type, data: data.content };
                      }
                    }
                    // Handle status message format
                    else if ('type' in data && 'data' in data) {
                      // This is a simple status message like {"type": "text", "data": "Received, processing..."}
                      const statusTimestamp = new Date().toISOString();
                      console.log(`📋 Status message [${statusTimestamp}] detected:`, { type: data.type, data: data.data?.substring(0, 50) });
                      yield { type: data.type, data: data.data };
                    }
                    // Handle raw Vertex AI format (direct streaming)
                    else if ('candidates' in data && Array.isArray(data.candidates)) {
                      for (const candidate of data.candidates) {
                        if (candidate.content?.parts) {
                          for (const part of candidate.content.parts) {
                            if (part.text) {
                              const textTimestamp = new Date().toISOString();
                              const textRelativeTime = Date.now();
                              console.log(`📨 V2 API [${textTimestamp}]: Received text chunk at ${textRelativeTime}:`, part.text);
                              yield part.text;
                            } else if (part.inlineData?.data) {
                              const imageTimestamp = new Date().toISOString();
                              const imageRelativeTime = Date.now();
                              console.log(`🖼️ V2 API [${imageTimestamp}]: Received image chunk at ${imageRelativeTime}`);
                              yield { type: 'image', data: part.inlineData.data };
                            }
                          }
                        }
                      }
                    }
                  } else {
                    // Handle raw string data (shouldn't happen with proper JSON parsing)
                    console.warn('⚠️ Unexpected raw data format:', data);
                  }
                }
                } catch (e) {
                  console.warn('⚠️ Failed to parse V2 streaming data:', line, e);
                }
              } else if (line.startsWith(':')) {
                // SSE comment line (our padding)
                console.log(`💬 V2 API [${lineTimestamp}]: SSE comment (padding): ${line.length} chars`);
              } else if (line.trim() === '') {
                // Empty line (event separator)
                console.log(`📄 V2 API [${lineTimestamp}]: Empty line (event separator)`);
              } else if (line.trim() !== '') {
                // Non-empty, non-data, non-comment line
                console.log(`❓ V2 API [${lineTimestamp}]: Unknown line type: "${line}"`);
              }
            }
        }
      } finally {
        reader.releaseLock();
      }

    } catch (error: any) {
      console.error('❌ V2 AI Service Error:', error);
      throw error;
    }
  }

  /**
   * Simple text-only chat (backward compatibility)
   */
  async *simpleChat(
    text: string,
    language: SupportedLanguage = 'en',
    conversationHistory: any[] = [] // Accept any message format for flexibility
  ): AsyncGenerator<string> {
    
    const contents = this.createTextContent(text, language);
    
    for await (const chunk of this.chatStream(contents, language)) {
      console.log('🔍 DEBUG simpleChat chunk:', {
        type: typeof chunk,
        value: chunk,
        isObject: typeof chunk === 'object',
        isNull: chunk === null,
        hasType: chunk !== null && typeof chunk === 'object' && 'type' in chunk,
        hasData: chunk !== null && typeof chunk === 'object' && 'data' in chunk
      });
      
      if (typeof chunk === 'string') {
        yield chunk;
      } else if (typeof chunk === 'object' && chunk !== null && 'type' in chunk && 'data' in chunk && chunk.type === 'text') {
        yield chunk.data;
      } else {
        console.warn('⚠️ Unhandled chunk format in simpleChat:', chunk);
      }
    }
  }

  /**
   * Photo analysis with V2 API
   */
  async *analyzePhoto(
    photo: CapturedPhoto,
    prompt: string,
    language: SupportedLanguage = 'en'
  ): AsyncGenerator<string | { type: 'image', data: string }> {
    
    const contents = this.createImageContent(prompt, photo, language);
    
    for await (const chunk of this.chatStream(contents, language)) {
      console.log('🔍 DEBUG analyzePhoto chunk:', {
        type: typeof chunk,
        value: chunk,
        isObject: typeof chunk === 'object',
        isNull: chunk === null,
        hasType: chunk !== null && typeof chunk === 'object' && 'type' in chunk,
        hasData: chunk !== null && typeof chunk === 'object' && 'data' in chunk
      });
      
      if (typeof chunk === 'string') {
        yield chunk;
      } else if (typeof chunk === 'object' && chunk !== null && 'type' in chunk && 'data' in chunk) {
        if (chunk.type === 'text') {
          yield chunk.data;
        } else if (chunk.type === 'image') {
          yield { type: 'image', data: chunk.data };
        }
      } else {
        console.warn('⚠️ Unhandled chunk format in analyzePhoto:', chunk);
      }
    }
  }

  /**
   * Continue conversation with V2 API - accepts ChatMessage[] for frontend compatibility
   * Uses the photo determined by the parent component (already handles current view context)
   */
  async *continueConversation(
    messages: any[], // Accept ChatMessage[] from frontend
    newText: string,
    language: SupportedLanguage = 'en',
    photo?: CapturedPhoto
  ): AsyncGenerator<string | { type: 'image', data: string }> {
    
    console.log('🔄 continueConversation called with:', {
      messagesCount: messages.length,
      hasPhoto: !!photo,
      photoId: photo?.id,
      newText: newText.substring(0, 50) + '...'
    });

    // Use the photo passed from parent (parent handles current view context and cropping)
    const contents = photo
      ? this.createImageContent(newText, photo, language)
      : this.createTextContent(newText, language);
    
    console.log('📤 Sending to AI with:', {
      hasImage: !!photo,
      imageId: photo?.id,
      contentParts: contents.length,
      language
    });
    
    for await (const chunk of this.chatStream(contents, language)) {
      console.log('🔍 DEBUG continueConversation chunk:', {
        type: typeof chunk,
        value: chunk,
        isObject: typeof chunk === 'object',
        isNull: chunk === null,
        hasType: chunk !== null && typeof chunk === 'object' && 'type' in chunk,
        hasData: chunk !== null && typeof chunk === 'object' && 'data' in chunk
      });
      
      if (typeof chunk === 'string') {
        yield chunk;
      } else if (typeof chunk === 'object' && chunk !== null && 'type' in chunk && 'data' in chunk) {
        if (chunk.type === 'text') {
          yield chunk.data;
        } else if (chunk.type === 'image') {
          yield { type: 'image', data: chunk.data };
        }
      } else {
        console.warn('⚠️ Unhandled chunk format in continueConversation:', chunk);
      }
    }
  }

  /**
   * Get API capabilities
   */
  async getCapabilities(): Promise<any> {
    try {
      const backendHost = process.env.NEXT_PUBLIC_BACKEND_API_HOST || 'http://localhost:18000';
      const response = await fetch(`${backendHost}/v2/ecapabilities`);
      if (!response.ok) {
        throw new Error(`Failed to get capabilities: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('❌ Failed to get V2 capabilities:', error);
      throw error;
    }
  }

  /**
   * Get current API version
   */
  getCurrentAPIVersion(): string {
    return 'V2';
  }

  /**
   * Health check for V2 API
   */
  async healthCheck(): Promise<{ status: string; version: string; timestamp: string }> {
    try {
      const backendHost = process.env.NEXT_PUBLIC_BACKEND_API_HOST || 'http://localhost:18000';
      const response = await fetch(`${backendHost}/v2/ehealth`);
      if (!response.ok) {
        return {
          status: 'error',
          version: 'V2',
          timestamp: new Date().toISOString()
        };
      }
      const data = await response.json();
      return {
        status: 'ok',
        version: 'V2',
        timestamp: new Date().toISOString(),
        ...data
      };
    } catch (error) {
      console.error('❌ V2 health check failed:', error);
      return {
        status: 'error',
        version: 'V2',
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Clear conversation history (V2 API doesn't maintain server-side history)
   */
  clearConversationHistory(): void {
    console.log('🔄 V2 API: Conversation history cleared (client-side only)');
  }

  /**
   * Generate image from prompt (alias for simpleChat for compatibility)
   */
  async *generateImageFromPrompt(
    message: string,
    language: SupportedLanguage = 'en'
  ): AsyncGenerator<string | { type: 'image', data: string }> {
    const contents = this.createTextContent(message, language);
    
    for await (const chunk of this.chatStream(contents, language)) {
      if (typeof chunk === 'string') {
        yield chunk;
      } else if (typeof chunk === 'object' && chunk !== null && 'type' in chunk && 'data' in chunk) {
        if (chunk.type === 'text') {
          yield chunk.data;
        } else if (chunk.type === 'image') {
          yield { type: 'image', data: chunk.data };
        }
      }
    }
  }

  /**
   * Convert legacy ChatMessage to V2Message (for migration)
   */
  convertLegacyMessage(legacyMessage: any, photo?: CapturedPhoto): V2Message {
    const content: V2MessageContent[] = [
      {
        type: 'text',
        data: legacyMessage.content
      }
    ];

    // Add image if present and compressedData exists
    if (photo && legacyMessage.photoContext === photo.id && photo.compressedData) {
      content.push({
        type: 'image',
        data: photo.compressedData,
        mime_type: 'image/jpeg'
      });
    }

    return {
      role: legacyMessage.role,
      content,
      timestamp: legacyMessage.timestamp?.toISOString(),
      message_id: legacyMessage.id
    };
  }
}

// Export singleton instance
export const aiServiceV2 = new AIServiceV2();