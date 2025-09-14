/**
 * AI Service for WonderCam
 * Integrates with vertex.yan.today API using JWT authentication
 */

import { CapturedPhoto, ChatMessage, SupportedLanguage } from '@/app/wondercam/page';
import { createClient } from '@/lib/supabase/client';

export interface AIError {
  code: string;
  message: string;
  isContentPolicy: boolean;
  isRateLimit: boolean;
  apiErrorCode?: string;
}

export class AIService {
  // NOTE: No direct backend host reference; all calls use relative /v1beta/* paths and are rewritten/proxied server-side.
  private readonly useMockResponse = false; // Disable mock for real API calls
  private supabase = createClient();

  private languageInstructions = {
    en: 'Respond in English.',
    zh: '请用中文回答。',
    es: 'Responde en español.',
    fr: 'Répondez en français.',
    ja: '日本語で答えてください。'
  };

  /**
   * Get JWT token for API authentication
   * Restored to use the current Supabase session access token (no hardcoded dev key).
   */
  private async getAuthToken(): Promise<string> {
    const { data: { session }, error } = await this.supabase.auth.getSession();
    
    console.log('🔐 Auth token debug:', {
      hasSession: !!session,
      hasAccessToken: !!session?.access_token,
      tokenLength: session?.access_token?.length || 0,
      tokenPreview: session?.access_token ? `${session.access_token.substring(0, 10)}...` : 'none',
      error: error?.message
    });
    
    if (error) {
      throw new Error(`Authentication error: ${error.message}`);
    }
    
    if (!session?.access_token) {
      throw new Error('User not authenticated - no session or access token');
    }
    return session.access_token;
  }

  /**
   * Analyze photo with AI and start conversation
   */
  analyzePhoto(
    photo: CapturedPhoto,
    message: string,
    language: SupportedLanguage
  ): AsyncGenerator<string | { type: 'image', data: string }> {
    const fullMessage = `${this.languageInstructions[language]} ${message}`;
    
    const contents = [{
      role: 'user',
      parts: [
        { text: fullMessage },
        {
          inlineData: {
            mimeType: 'image/jpeg',
            data: photo.compressedData.split(',')[1] // Remove data:image/jpeg;base64, prefix
          }
        }
      ]
    }];

    return this.streamAIResponse(contents);
  }

  /**
   * Direct chat first message without an initial photo.
   * We let the model optionally generate an image from the user's prompt.
   */
  generateImageFromPrompt(
    message: string,
    language: SupportedLanguage
  ): AsyncGenerator<string | { type: 'image', data: string }> {
    const fullMessage = `${this.languageInstructions[language]} ${message}`;
    const contents = [{
      role: 'user',
      parts: [
        { text: fullMessage }
      ]
    }];
    return this.streamAIResponse(contents);
  }

  /**
   * Get the latest image from the conversation (either original photo or latest AI-generated image)
   */
  private getLatestImage(
    messages: ChatMessage[],
    originalPhoto: CapturedPhoto | null
  ): { data: string; mimeType: string } | null {
    // Look for the most recent AI-generated image in the messages
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];
      if (message.role === 'assistant' && message.imageData) {
        return {
          data: message.imageData.includes(',')
            ? message.imageData.split(',')[1]
            : message.imageData,
          mimeType: 'image/png'
        };
      }
    }

    if (originalPhoto) {
      return {
        data: originalPhoto.compressedData.split(',')[1],
        mimeType: 'image/jpeg'
      };
    }

    return null;
  }

  /**
   * Continue conversation with existing chat history
   */
  continueConversation(
    messages: ChatMessage[],
    newMessage: string,
    language: SupportedLanguage,
    photo: CapturedPhoto | null
  ): AsyncGenerator<string | { type: 'image', data: string }> {
    const contents: any[] = [];

    if (photo) {
      // Conversation with an originating photo
      const latestImage = this.getLatestImage(messages, photo);
      if (latestImage) {
        contents.push({
          role: 'user',
            parts: [
              { text: `${this.languageInstructions[language]} Here's the current image:` },
              {
                inlineData: {
                  mimeType: latestImage.mimeType,
                  data: latestImage.data
                }
              }
            ]
        });
      }

      // Skip initial photo analysis pair if present
      let startIndex = 0;
      if (messages.length > 0 && messages[0].role === 'user') {
        startIndex = 2;
      }

      for (let i = startIndex; i < messages.length; i++) {
        const msg = messages[i];
        contents.push({
          role: msg.role === 'assistant' ? 'model' : 'user',
          parts: [{ text: msg.content }]
        });
      }

    } else {
      // Direct text/image generation chat without an initial photo
      for (const msg of messages) {
        contents.push({
          role: msg.role === 'assistant' ? 'model' : 'user',
          parts: [{ text: msg.content }]
        });
      }
    }

    // Add the new user message
    contents.push({
      role: 'user',
      parts: [{ text: `${this.languageInstructions[language]} ${newMessage}` }]
    });

    return this.streamAIResponse(contents);
  }

  /**
   * Generate mock AI response for testing
   */
  private async *generateMockResponse(contents: any[], language: SupportedLanguage): AsyncGenerator<string> {
    console.log('🧪 Using mock AI response for testing');
    
    // Check if this is a photo analysis (has image data)
    const hasImage = contents.some(c => c.parts.some((p: any) => p.inlineData));
    
    let responses = {
      en: hasImage 
        ? "I can see your photo! It looks interesting. What would you like to know about it or discuss?"
        : "I'm here to help you with your photo. What would you like to explore?",
      zh: hasImage
        ? "我看到了你的照片！看起来很有趣。你想了解什么或讨论什么呢？"
        : "我在这里帮助你处理照片。你想探索什么呢？",
      es: hasImage
        ? "¡Puedo ver tu foto! Se ve interesante. ¿Qué te gustaría saber o discutir?"
        : "Estoy aquí para ayudarte con tu foto. ¿Qué te gustaría explorar?",
      fr: hasImage
        ? "Je peux voir votre photo ! Elle semble intéressante. Qu'aimeriez-vous savoir ou discuter ?"
        : "Je suis là pour vous aider avec votre photo. Qu'aimeriez-vous explorer ?",
      ja: hasImage
        ? "あなたの写真が見えます！面白そうですね。何について知りたいですか？"
        : "写真についてお手伝いします。何を探求したいですか？"
    };

    const response = responses[language];
    
    // Simulate streaming by yielding chunks
    const words = response.split(' ');
    for (let i = 0; i < words.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 100)); // Simulate network delay
      yield words[i] + (i < words.length - 1 ? ' ' : '');
    }
  }

  /**
   * Stream AI response from vertex.yan.today API
   */
  private async *streamAIResponse(contents: any[]): AsyncGenerator<string | { type: 'image', data: string }> {
    // Use mock response for testing if enabled
    if (this.useMockResponse) {
      // Extract language from contents if available
      const userMessage = contents.find(c => c.role === 'user')?.parts?.find((p: any) => p.text)?.text || '';
      let language: SupportedLanguage = 'en';
      
      if (userMessage.includes('中文')) language = 'zh';
      else if (userMessage.includes('español')) language = 'es'; 
      else if (userMessage.includes('français')) language = 'fr';
      else if (userMessage.includes('日本語')) language = 'ja';
      
      yield* this.generateMockResponse(contents, language);
      return;
    }

    try {
      const requestBody = {
        contents,
        safetySettings: [
          { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "OFF" },
          { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "OFF" },
          { category: "HARM_CATEGORY_HARASSMENT", threshold: "OFF" },
          { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "OFF" },
          { category: "HARM_CATEGORY_CIVIC_INTEGRITY", threshold: "BLOCK_NONE" }
        ],
        tools: [],
        generationConfig: {
          temperature: 1,
          topP: 1,
          responseModalities: ["TEXT", "IMAGE"]
        }
      };

      const forceLogout = async (reason: string) => {
        try {
          console.warn('🔁 Forcing logout due to auth failure:', reason);
          await this.supabase.auth.signOut();
          // Attempt silent anonymous sign-in if available (Supabase v2 anon)
          // If you have an explicit anonymous sign-in flow, trigger it here instead.
          // Fallback: reload to re-init session state.
          setTimeout(() => {
            window.location.reload();
          }, 300);
        } catch (e) {
          console.error('Failed during forced logout sequence', e);
          window.location.reload();
        }
      };

      console.log('🤖 Calling AI API (relative) with:', {
        endpoint: '/v1beta/models/* (rewrite/proxy)',
        contentCount: contents.length,
        hasImage: contents.some(c => c.parts.some((p: any) => p.inlineData)),
        firstContentParts: contents[0]?.parts?.length || 0,
        firstContentRole: contents[0]?.role,
        hasTextInFirstContent: !!contents[0]?.parts?.find((p: any) => p.text),
        hasImageInFirstContent: !!contents[0]?.parts?.find((p: any) => p.inlineData),
        imageDataPreview: contents[0]?.parts?.find((p: any) => p.inlineData)?.inlineData?.data?.substring(0, 50) + '...'
      });
      
      console.log('📋 Full request body:', JSON.stringify(requestBody, null, 2));

      const authToken = await this.getAuthToken();
      
      const response = await fetch(
        `/v1beta/models/gemini-2.5-flash-image-preview:streamGenerateContent?alt=sse`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-goog-api-key': authToken,
            ...(authToken.startsWith('eyJ') ? { Authorization: `Bearer ${authToken}` } : {})
          },
          body: JSON.stringify(requestBody)
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ AI API Error:', {
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries()),
          body: errorText
        });

        if (response.status === 401) {
          // Force logout & session reset path
            await forceLogout('Received 401 from AI backend');
        }
        throw this.createAIError(response.status, errorText);
      }

      // Parse streaming response
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let hasYieldedContent = false;
      let accumulatedImageData = null;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data:')) {
              try {
                const jsonStr = line.substring(5).trim();
                if (jsonStr && jsonStr !== '[DONE]') {
                  const data = JSON.parse(jsonStr);
                  
                  // Check for text content
                  if (data.candidates?.[0]?.content?.parts) {
                    for (const part of data.candidates[0].content.parts) {
                      if (part.text) {
                        hasYieldedContent = true;
                        
                        // Add natural pauses for breathing effect
                        const words = part.text.split(' ');
                        for (let i = 0; i < words.length; i++) {
                          const word = words[i] + (i < words.length - 1 ? ' ' : '');
                          
                          // Add slight pause every few words for natural rhythm
                          if (i > 0 && (i % 3 === 0 || word.includes('.') || word.includes('!') || word.includes('?'))) {
                            await new Promise(resolve => setTimeout(resolve, Math.random() * 100 + 50));
                          }
                          
                          yield word;
                        }
                      }
                      if (part.inlineData?.data) {
                        accumulatedImageData = part.inlineData.data;
                      }
                    }
                  }
                }
              } catch (e) {
                console.warn('⚠️ Failed to parse streaming data:', line, e);
              }
            }
          }
        }

        // Handle final buffer
        if (buffer.length > 0) {
          const lines = buffer.split('\n');
          for (const line of lines) {
            if (line.startsWith('data:')) {
              try {
                const jsonStr = line.substring(5).trim();
                if (jsonStr && jsonStr !== '[DONE]') {
                  const data = JSON.parse(jsonStr);
                  
                  if (data.candidates?.[0]?.content?.parts) {
                    for (const part of data.candidates[0].content.parts) {
                      if (part.text) {
                        hasYieldedContent = true;
                        
                        // Add natural pauses for breathing effect
                        const words = part.text.split(' ');
                        for (let i = 0; i < words.length; i++) {
                          const word = words[i] + (i < words.length - 1 ? ' ' : '');
                          
                          // Add slight pause every few words for natural rhythm
                          if (i > 0 && (i % 3 === 0 || word.includes('.') || word.includes('!') || word.includes('?'))) {
                            await new Promise(resolve => setTimeout(resolve, Math.random() * 100 + 50));
                          }
                          
                          yield word;
                        }
                      }
                      if (part.inlineData?.data) {
                        accumulatedImageData = part.inlineData.data;
                      }
                    }
                  }
                }
              } catch (e) {
                console.warn('⚠️ Failed to parse final streaming data:', line, e);
              }
            }
          }
        }

        // If we have image data, yield it at the end
        if (accumulatedImageData) {
          yield { type: 'image', data: accumulatedImageData };
        }

        if (!hasYieldedContent && !accumulatedImageData) {
          console.warn('⚠️ No content received from AI API');
          yield 'I apologize, but I couldn\'t generate a response. Please try again.';
        }

      } finally {
        reader.releaseLock();
      }

    } catch (error: any) {
      console.error('❌ AI Service Error:', error);
      
      // Yield error message for user
      if (error.isContentPolicy) {
        yield '🚫 I cannot process this request due to content policy restrictions. Please try a different approach.';
      } else if (error.isRateLimit) {
        yield '⏳ I\'m receiving too many requests right now. Please wait a moment and try again.';
      } else if (error.message?.includes('Authentication failed')) {
        yield `🔐 ${error.message}`;
      } else if (error.message?.includes('Access forbidden')) {
        yield `⛔ ${error.message}`;
      } else {
        yield `❌ Sorry, I encountered an error: ${error.message}. Please try again.`;
      }
    }
  }

  /**
   * Create structured AI error from API response
   */
  private createAIError(status: number, errorText: string): AIError {
    const isContentPolicy = errorText.includes('content policy') || 
                           errorText.includes('safety') ||
                           errorText.includes('inappropriate');
    const isRateLimit = status === 429 || errorText.includes('rate limit');

    return {
      code: isContentPolicy ? 'CONTENT_POLICY' : isRateLimit ? 'RATE_LIMIT' : 'API_ERROR',
      message: this.getErrorMessage(status, errorText, isContentPolicy, isRateLimit),
      isContentPolicy,
      isRateLimit,
      apiErrorCode: status.toString()
    };
  }

  /**
   * Get user-friendly error message
   */
  private getErrorMessage(status: number, errorText: string, isContentPolicy: boolean, isRateLimit: boolean): string {
    if (isContentPolicy) {
      return 'Content policy restriction - please try a different approach';
    }
    
    if (isRateLimit) {
      return 'Rate limit exceeded - please wait and try again';
    }

    switch (status) {
      case 401:
        return `Authentication failed - something is wrong: ${errorText}`;
      case 403:
        return `Access forbidden - something is wrong: ${errorText}`;
      case 404:
        return 'AI service not found - check endpoint configuration';
      case 500:
        return 'AI service temporarily unavailable';
      default:
        return `AI service error (${status}): ${errorText.slice(0, 200)}`;
    }
  }
}

// Export singleton instance
export const aiService = new AIService();