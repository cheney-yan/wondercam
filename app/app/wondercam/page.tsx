'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';
import { User } from '@supabase/supabase-js';
import { CameraComponent } from '@/components/wondercam/camera';
import { ChatComponent } from '@/components/wondercam/chat';
import { PhotoViewer } from '@/components/wondercam/photo-viewer';
import { LanguageSelector } from '@/components/wondercam/language-selector';
import { anonymousAuthService } from '@/lib/anonymous-auth';
import { creditService, CreditAction } from '@/lib/credit-service';
import { UpgradePrompt, useUpgradePrompt } from '@/components/upgrade-prompt';
import { getTranslations } from '@/lib/i18n';
import { UserMenu } from '@/components/user-menu';
import { aiServiceV2 } from '@/lib/ai-service-v2';

export type AppMode = 'camera' | 'chat' | 'photo-actions' | 'zoomed';
export type SupportedLanguage = 'en' | 'zh' | 'es' | 'fr' | 'ja';

export interface CapturedPhoto {
  id: string;
  imageData: string;        // Original base64
  compressedData: string;   // Compressed for AI
  capturedAt: Date;
  dimensions: {
    width: number;
    height: number;
    aspectRatio: number;
  };
  fileSize: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  photoContext?: string;
  imageData?: string; // Base64 image data if this message contains an AI-generated image
}

export interface ChatSession {
  sessionId: string;
  photo: CapturedPhoto | null; // Can be null for direct chat without initial photo
  messages: ChatMessage[];
  language: SupportedLanguage;
  isActive: boolean;
  createdAt: Date;
}

export interface AppState {
  currentMode: AppMode;
  user: User | null;
  activeSession: ChatSession | null;
  currentPhoto: CapturedPhoto | null;
  zoomPhoto?: CapturedPhoto | null; // For zooming AI-generated images
  isLoading: boolean;
  error: string | null;
  language: SupportedLanguage;
  credits: number;
  isAnonymous: boolean;
  isInitializing: boolean;
}

export default function WonderCamPage() {
  const [appState, setAppState] = useState<AppState>({
    currentMode: 'camera',
    user: null,
    activeSession: null,
    currentPhoto: null,
    isLoading: false,
    error: null,
    language: 'en',
    credits: 0,
    isAnonymous: true,
    isInitializing: true
  });

  const supabase = createClient();
  const upgradePrompt = useUpgradePrompt();
  const t = getTranslations(appState.language);

  // Initialize API service and log configuration
  useEffect(() => {
    const initializeAPI = async () => {
      try {
        console.log('🔧 Initializing AI Service...');
        const capabilities = await aiServiceV2.getCapabilities();
        const health = await aiServiceV2.healthCheck();
        
        console.log('✅ AI Service initialized:', {
          version: aiServiceV2.getCurrentAPIVersion(),
          capabilities: capabilities?.features || [],
          health
        });
      } catch (error) {
        console.warn('⚠️ AI Service initialization failed:', error);
      }
    };

    initializeAPI();
  }, []);

  useEffect(() => {
    // Initialize anonymous authentication and credits
    const initializeApp = async () => {
      try {
        console.log('🔄 Initializing WonderCam with anonymous auth...');
        
        // Check if there's already a user logged in
        const existingUser = await anonymousAuthService.getCurrentUser();
        
        if (existingUser) {
          console.log('👤 Existing user found, checking credits initialization...', existingUser.id);
          
          try {
            // Try to get current credits to see if user is properly initialized
            const credits = await creditService.getCurrentCredits();
            const isAnonymous = await anonymousAuthService.isAnonymous();
            
            console.log('✅ User already initialized:', { userId: existingUser.id, credits, isAnonymous });
            
            setAppState(prev => ({
              ...prev,
              user: existingUser,
              credits,
              isAnonymous,
              isInitializing: false
            }));
            return;
          } catch (error) {
            console.log('⚠️ User exists but credits not initialized. Logging out to reinitialize...', error);
            
            // Log out the existing user to force fresh initialization
            const { error: signOutError } = await supabase.auth.signOut();
            if (signOutError) {
              console.error('❌ Failed to sign out existing user:', signOutError);
              throw signOutError;
            } else {
              console.log('✅ Successfully logged out existing user');
            }
          }
        }
        
        // Get or create anonymous session (fresh start)
        const user = await anonymousAuthService.getOrCreateAnonymousSession();
        
        // Load current credits
        const credits = await creditService.getCurrentCredits();
        
        // Check if user is anonymous
        const isAnonymous = await anonymousAuthService.isAnonymous();
        
        console.log('✅ App initialized:', { user: user?.id, credits, isAnonymous });
        
        setAppState(prev => ({
          ...prev,
          user,
          credits,
          isAnonymous,
          isInitializing: false
        }));
        
      } catch (error) {
        console.error('❌ Failed to initialize app:', error);
        setAppState(prev => ({
          ...prev,
          error: 'Failed to initialize app. Please refresh the page.',
          isInitializing: false
        }));
      }
    };

    initializeApp();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      try {
        console.log('🔄 Auth state changed:', event, session?.user?.id);
        
        if (session?.user) {
          // Update credits when auth state changes
          const credits = await creditService.getCurrentCredits();
          const isAnonymous = await anonymousAuthService.isAnonymous();
          
          setAppState(prev => ({
            ...prev,
            user: session.user,
            credits,
            isAnonymous
          }));
        } else {
          // Re-initialize anonymous session if needed
          initializeApp();
        }
      } catch (error) {
        console.error('❌ Error handling auth change:', error);
      }
    });

    // Disable zoom keyboard shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === '+' || e.key === '-' || e.key === '0')) {
        e.preventDefault();
      }
    };

    const handleWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
      }
    };

    // Prevent trackpad pinch gestures (macOS)
    const handleGestureStart = (e: any) => {
      e.preventDefault();
    };

    const handleGestureChange = (e: any) => {
      e.preventDefault();
    };

    const handleGestureEnd = (e: any) => {
      e.preventDefault();
    };

    // Prevent touch gestures
    const handleTouchStart = (e: TouchEvent) => {
      if (e.touches.length > 1) {
        e.preventDefault();
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 1) {
        e.preventDefault();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('wheel', handleWheel, { passive: false });
    document.addEventListener('gesturestart', handleGestureStart, { passive: false });
    document.addEventListener('gesturechange', handleGestureChange, { passive: false });
    document.addEventListener('gestureend', handleGestureEnd, { passive: false });
    document.addEventListener('touchstart', handleTouchStart, { passive: false });
    document.addEventListener('touchmove', handleTouchMove, { passive: false });

    return () => {
      subscription.unsubscribe();
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('wheel', handleWheel);
      document.removeEventListener('gesturestart', handleGestureStart);
      document.removeEventListener('gesturechange', handleGestureChange);
      document.removeEventListener('gestureend', handleGestureEnd);
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchmove', handleTouchMove);
    };
  }, [supabase]);

  useEffect(() => {
    const handleStorageChange = () => {
      creditService.getCurrentCredits().then(credits => {
        setAppState(prev => ({ ...prev, credits }));
      });
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  /**
   * One-off IP tracking: after we have a user (anonymous or registered),
   * call server API which records last_login_ip via RPC (set_last_login_ip).
   * (Browser cannot reliably know its public IP; server derives from headers.)
   */
  useEffect(() => {
    if (appState.user?.id) {
      fetch('/api/track-ip', { method: 'POST' })
        .then(res => {
          if (!res.ok) {
            console.warn('⚠️ Failed to track IP: HTTP', res.status);
          }
        })
        .catch(err => console.error('❌ IP tracking request failed:', err));
    }
  }, [appState.user?.id]);

  const handlePhotoCapture = (photo: CapturedPhoto) => {
    console.log('Photo captured:', photo);
    setAppState(prev => ({
      ...prev,
      currentPhoto: photo,
      currentMode: 'chat',
      activeSession: {
        sessionId: crypto.randomUUID(),
        photo,
        messages: [],
        language: prev.language,
        isActive: true,
        createdAt: new Date()
      }
    }));
  };

  // Start a direct chat WITHOUT a captured photo
  const handleStartDirectChat = () => {
    console.log('📝 Starting direct chat without initial photo');
    setAppState(prev => ({
      ...prev,
      currentPhoto: null,
      currentMode: 'chat',
      activeSession: {
        sessionId: crypto.randomUUID(),
        photo: null,
        messages: [],
        language: prev.language,
        isActive: true,
        createdAt: new Date()
      }
    }));
  };

  const handleNewPhoto = () => {
    // Clear conversation history when starting new photo session
    aiServiceV2.clearConversationHistory();
    
    setAppState(prev => ({
      ...prev,
      currentMode: 'camera',
      currentPhoto: null,
      activeSession: null,
      error: null
    }));
  };

  const handlePhotoAction = (action: 'zoom' | 'share' | 'store' | 'new') => {
    console.log('Photo action:', action);
    
    switch (action) {
      case 'zoom':
        // Check if a specific image was selected for zooming
        const selectedImage = (window as any).selectedImageForZoom;
        if (selectedImage) {
          // Create a temporary photo object for the selected AI-generated image
          setAppState(prev => ({ 
            ...prev, 
            currentMode: 'zoomed',
            zoomPhoto: {
              id: 'ai-generated-' + Date.now(),
              imageData: selectedImage,
              compressedData: selectedImage,
              capturedAt: new Date(),
              dimensions: {
                width: 1024, // Default dimensions for AI images
                height: 1024,
                aspectRatio: 1
              },
              fileSize: Math.round(selectedImage.length * 0.75)
            }
          }));
          // Clear the selected image
          delete (window as any).selectedImageForZoom;
        } else {
          // Use the original photo
          setAppState(prev => ({ ...prev, currentMode: 'zoomed' }));
        }
        break;
      case 'share':
        // TODO: Implement sharing
        console.log('Share functionality to be implemented');
        break;
      case 'store':
        // TODO: Implement storage
        console.log('Store functionality to be implemented');
        break;
      case 'new':
        handleNewPhoto();
        break;
    }
  };

  const handleMessage = async (message: string) => {
    if (!appState.activeSession || !appState.user) return;

    console.log('Sending message:', message);

    // Determine which photo the user is currently viewing and should be sent to AI
    let effectivePhoto: CapturedPhoto | null = null;
    try {
      // Check if we have current photo context (which image user is viewing)
      const photoContext = (window as any).wondercamCurrentPhotoContext;
      const croppedView = (window as any).wondercamCroppedView;

      console.log('📷 Photo context analysis:', {
        hasPhotoContext: !!photoContext,
        hasCroppedView: !!croppedView,
        hasSessionPhoto: !!appState.currentPhoto,
        sessionPhotoId: appState.currentPhoto?.id
      });

      if (photoContext) {
        // User is viewing a specific photo - determine which one to use
        if (photoContext.isInitialPhoto && appState.currentPhoto) {
          // User is viewing the original photo
          effectivePhoto = appState.currentPhoto;
          
          // Check if they've zoomed/cropped it
          if (croppedView) {
            console.log('🔍 Using cropped viewport of original photo');
            effectivePhoto = {
              id: appState.currentPhoto.id + '-cropped-' + Date.now(),
              imageData: croppedView.dataUrl,
              compressedData: croppedView.dataUrl, // Already viewport-sized JPEG
              capturedAt: new Date(),
              dimensions: {
                width: croppedView.width,
                height: croppedView.height,
                aspectRatio: croppedView.width / croppedView.height
              },
              fileSize: Math.round(croppedView.dataUrl.length * 0.75)
            };
          }
        } else if (!photoContext.isInitialPhoto) {
          // User is viewing an AI-generated image - create photo object from it
          console.log('🤖 User is viewing AI-generated image:', photoContext.imageKey);
          effectivePhoto = {
            id: photoContext.imageKey,
            imageData: photoContext.imageData,
            compressedData: photoContext.imageData, // AI images are already appropriately sized
            capturedAt: new Date(),
            dimensions: {
              width: 1024, // Default AI image dimensions
              height: 1024,
              aspectRatio: 1
            },
            fileSize: Math.round(photoContext.imageData.length * 0.75)
          };
        }
      } else {
        // Fallback to session photo if no context available
        effectivePhoto = appState.currentPhoto;
        console.log('⚠️ No photo context, falling back to session photo:', effectivePhoto?.id);
      }

      console.log('✅ Final effective photo:', {
        id: effectivePhoto?.id,
        hasImageData: !!effectivePhoto?.imageData,
        hasCompressedData: !!effectivePhoto?.compressedData,
        dimensions: effectivePhoto?.dimensions
      });

    } catch (contextErr) {
      console.warn('⚠️ Failed to determine photo context; falling back to session photo.', contextErr);
      effectivePhoto = appState.currentPhoto;
    }

    const isFirstMessage = appState.activeSession.messages.length === 0;
    const hasInitialPhoto = !!effectivePhoto;

    // Add user message (this doesn't cost credits)
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
      photoContext: effectivePhoto?.id
    };

    setAppState(prev => ({
      ...prev,
      activeSession: prev.activeSession ? {
        ...prev.activeSession,
        messages: [...prev.activeSession.messages, userMessage]
      } : null,
      isLoading: true
    }));

    try {
      console.log('🔄 Starting AI message processing...', {
        message,
        language: appState.language,
        hasPhoto: hasInitialPhoto,
        isFirstMessage,
        messagesCount: appState.activeSession.messages.length,
        usingCropped: effectivePhoto && effectivePhoto.id !== appState.currentPhoto?.id
      });

      console.log(`✅ Using V2 AI service (${aiServiceV2.getCurrentAPIVersion()})`);
      
      const streamingMessageId = crypto.randomUUID();
      let accumulatedContent = '';

      // Add initial streaming assistant placeholder
      setAppState(prev => ({
        ...prev,
        activeSession: prev.activeSession ? {
          ...prev.activeSession,
          messages: [...prev.activeSession.messages, {
            id: streamingMessageId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            isStreaming: true,
            photoContext: effectivePhoto?.id || undefined
          }]
        } : null,
        isLoading: false
      }));

      let responseStream;
      try {
        if (isFirstMessage) {
          if (hasInitialPhoto && effectivePhoto) {
            console.log('🖼️ First message with (possibly cropped) photo -> analyzePhoto');
            responseStream = aiServiceV2.analyzePhoto(
              effectivePhoto,
              message,
              appState.language
            );
          } else {
            console.log('🆕 First direct-chat message without photo -> generateImageFromPrompt');
            responseStream = aiServiceV2.generateImageFromPrompt(
              message,
              appState.language
            );
          }
        } else {
          console.log('💬 Continuing conversation');
          responseStream = aiServiceV2.continueConversation(
            appState.activeSession.messages,
            message,
            appState.language,
            effectivePhoto || undefined // convert null to undefined
          );
        }
        console.log('✅ Response stream created');
      } catch (streamError) {
        console.error('❌ Error creating response stream:', streamError);
        throw streamError;
      }

      let hasImageData = false;
      let imageData: string | undefined;
      
      for await (const chunk of responseStream) {
        if (typeof chunk === 'string') {
          accumulatedContent += chunk;
          setAppState(prev => ({
            ...prev,
            activeSession: prev.activeSession ? {
              ...prev.activeSession,
              messages: prev.activeSession.messages.map(msg =>
                msg.id === streamingMessageId
                  ? { ...msg, content: accumulatedContent }
                  : msg
              )
            } : null
          }));
        } else if (chunk.type === 'image') {
          hasImageData = true;
          imageData = chunk.data;
          console.log('🖼️ Received AI-generated image chunk:', imageData?.substring(0, 50) + '...');
        }
      }

      // Finalize streaming assistant message
      setAppState(prev => {
        let updated = {
          ...prev,
          activeSession: prev.activeSession ? {
            ...prev.activeSession,
            messages: prev.activeSession.messages.map(msg =>
              msg.id === streamingMessageId
                ? {
                    ...msg,
                    isStreaming: false,
                    ...(hasImageData && imageData ? { imageData: `data:image/png;base64,${imageData}` } : {})
                  }
                : msg
            )
          } : null
        };

        // If this was a direct chat (no photo) and first image arrived, promote it to currentPhoto
        if (!prev.currentPhoto && hasImageData && imageData) {
          const promotedPhoto: CapturedPhoto = {
            id: 'generated-' + Date.now(),
            imageData: `data:image/png;base64,${imageData}`,
            compressedData: `data:image/png;base64,${imageData}`,
            capturedAt: new Date(),
            dimensions: {
              width: 1024,
              height: 1024,
              aspectRatio: 1
            },
            fileSize: Math.round(imageData.length * 0.75)
          };
          updated = {
            ...updated,
            currentPhoto: promotedPhoto,
            activeSession: updated.activeSession ? {
              ...updated.activeSession,
              photo: promotedPhoto
            } : null
          };
          console.log('🌟 Promoted first generated image to session photo');
        }
        return updated;
      });

    } catch (error: any) {
      console.error('AI Service Error:', error);
      
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ Sorry, I encountered an error: ${error.message}. Please try again.`,
        timestamp: new Date(),
        photoContext: appState.currentPhoto?.id
      };

      setAppState(prev => ({
        ...prev,
        activeSession: prev.activeSession ? {
          ...prev.activeSession,
          messages: [...prev.activeSession.messages, errorMessage]
        } : null,
        isLoading: false
      }));
    }
  };

  const handleLanguageChange = (language: SupportedLanguage) => {
    setAppState(prev => ({
      ...prev,
      language,
      activeSession: prev.activeSession ? {
        ...prev.activeSession,
        language
      } : null
    }));
  };

  const handleError = (error: string) => {
    setAppState(prev => ({ ...prev, error }));
  };

  // Handle upgrade from anonymous to registered
  const handleUpgrade = () => {
    // Redirect to signup/registration page
    window.location.href = '/auth/sign-up';
  };

  if (appState.isInitializing) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <h1 className="text-2xl font-bold mb-2">WonderCam</h1>
          <p>Initializing...</p>
        </div>
      </div>
    );
  }

  if (!appState.user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-black text-white">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">WonderCam</h1>
          <p>Failed to initialize. Please refresh the page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="wondercam-app h-screen bg-black text-white overflow-hidden relative" style={{touchAction: 'manipulation'}}>
      
      {/* Error Display */}
      {appState.error && (
        <div className="absolute top-16 right-4 z-40 bg-red-600 text-white p-3 rounded-lg">
          {appState.error}
          <button 
            onClick={() => setAppState(prev => ({ ...prev, error: null }))}
            className="ml-2 text-white hover:text-gray-200"
          >
            ×
          </button>
        </div>
      )}

      {/* Camera Mode */}
      {appState.currentMode === 'camera' && (
        <div className="camera-section h-full w-full">
          <CameraComponent
            user={appState.user}
            onPhotoCapture={handlePhotoCapture}
            onError={handleError}
            isVisible={true}
            currentLanguage={appState.language}
            onLanguageChange={handleLanguageChange}
            onStartChat={handleStartDirectChat}
          />
        </div>
      )}

      {/* Chat Mode */}
      {appState.activeSession && appState.currentMode === 'chat' && (
        <div className="chat-section h-full w-full">
          <ChatComponent
            session={{
              ...appState.activeSession,
              user: appState.user,
              isAnonymous: appState.isAnonymous,
              credits: appState.credits,
            }}
            onMessage={handleMessage}
            onNewPhoto={handleNewPhoto}
            onPhotoAction={handlePhotoAction}
            onLanguageChange={handleLanguageChange}
            isLoading={appState.isLoading}
          />
        </div>
      )}

      {/* Photo Viewer (Zoomed) */}
      {appState.currentMode === 'zoomed' && (appState.zoomPhoto || appState.currentPhoto) && (
        <PhotoViewer
          photo={appState.zoomPhoto || appState.currentPhoto!}
          onZoom={() => setAppState(prev => ({ ...prev, currentMode: 'zoomed' }))}
          onShare={() => handlePhotoAction('share')}
          onStore={() => handlePhotoAction('store')}
          onBack={() => setAppState(prev => ({ ...prev, currentMode: 'chat', zoomPhoto: null }))}
        />
      )}

      {/* Upgrade Prompt */}
      <UpgradePrompt
        isOpen={upgradePrompt.isOpen}
        onClose={upgradePrompt.hidePrompt}
        onUpgrade={handleUpgrade}
        trigger={upgradePrompt.trigger}
        remainingCredits={upgradePrompt.remainingCredits}
        language={appState.language}
      />
    </div>
  );
}