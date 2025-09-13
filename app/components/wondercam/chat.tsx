'use client';

import React, { useState, useRef, useEffect } from 'react';
import { ChatSession, SupportedLanguage } from '@/app/wondercam/page';
import { User } from '@supabase/supabase-js';
import { UserMenu } from '@/components/user-menu';
import { LanguageSelector } from '@/components/wondercam/language-selector';

interface ChatComponentProps {
  session: ChatSession & { user: User | null; isAnonymous: boolean; credits: number };
  onMessage: (message: string) => void;
  onNewPhoto: () => void;
  onPhotoAction: (action: 'zoom' | 'share' | 'store' | 'new') => void;
  onLanguageChange: (language: SupportedLanguage) => void;
  isLoading: boolean;
}

const translations = {
  en: {
    placeholder: "Describe what you'd like to do with this photo...",
    placeholderGenerate: "Describe what you would like to generate...",
    send: "Send",
    newPhoto: "New Photo",
    zoom: "Zoom",
    share: "Share",
    store: "Save",
    thinking: "AI is thinking...",
    photoTaken: "Photo captured!",
    startConversation: "Start a conversation about your photo",
    camera: "Camera",
    photo: "Photo",
    chat: "Chat",
    messages: "messages",
    newConversation: "New conversation",
    backToCamera: "Back to camera",
    clickToZoom: "Click to zoom"
  },
  zh: {
    placeholder: "描述您想对这张照片做什么...",
    placeholderGenerate: "描述您想生成什么内容...",
    send: "发送",
    newPhoto: "新照片",
    zoom: "放大",
    share: "分享",
    store: "保存",
    thinking: "AI正在思考...",
    photoTaken: "照片已拍摄！",
    startConversation: "开始关于您照片的对话",
    camera: "相机",
    photo: "照片",
    chat: "聊天",
    messages: "条消息",
    newConversation: "新对话",
    backToCamera: "返回相机",
    clickToZoom: "点击放大"
  },
  es: {
    placeholder: "Describe qué te gustaría hacer con esta foto...",
    placeholderGenerate: "Describe qué te gustaría generar...",
    send: "Enviar",
    newPhoto: "Nueva Foto",
    zoom: "Ampliar",
    share: "Compartir",
    store: "Guardar",
    thinking: "La IA está pensando...",
    photoTaken: "¡Foto capturada!",
    startConversation: "Inicia una conversación sobre tu foto",
    camera: "Cámara",
    photo: "Foto",
    chat: "Chat",
    messages: "mensajes",
    newConversation: "Nueva conversación",
    backToCamera: "Volver a cámara",
    clickToZoom: "Haz clic para ampliar"
  },
  fr: {
    placeholder: "Décrivez ce que vous aimeriez faire avec cette photo...",
    placeholderGenerate: "Décrivez ce que vous souhaitez générer...",
    send: "Envoyer",
    newPhoto: "Nouvelle Photo",
    zoom: "Zoomer",
    share: "Partager",
    store: "Sauvegarder",
    thinking: "L'IA réfléchit...",
    photoTaken: "Photo capturée !",
    startConversation: "Commencez une conversation sur votre photo",
    camera: "Caméra",
    photo: "Photo",
    chat: "Chat",
    messages: "messages",
    newConversation: "Nouvelle conversation",
    backToCamera: "Retour à la caméra",
    clickToZoom: "Cliquez pour zoomer"
  },
  ja: {
    placeholder: "この写真で何をしたいか説明してください...",
    placeholderGenerate: "生成したいものを説明してください...",
    send: "送信",
    newPhoto: "新しい写真",
    zoom: "ズーム",
    share: "共有",
    store: "保存",
    thinking: "AIが考えています...",
    photoTaken: "写真を撮影しました！",
    startConversation: "あなたの写真について会話を始めましょう",
    camera: "カメラ",
    photo: "写真",
    chat: "チャット",
    messages: "メッセージ",
    newConversation: "新しい会話",
    backToCamera: "カメラに戻る",
    clickToZoom: "クリックで拡大"
  }
};

export function ChatComponent({ 
  session, 
  onMessage, 
  onNewPhoto, 
  onPhotoAction, 
  onLanguageChange,
  isLoading 
}: ChatComponentProps) {
  const [currentMessage, setCurrentMessage] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sendButtonRef = useRef<HTMLButtonElement>(null);

  // Keep the send button exactly the same height as the textarea
  useEffect(() => {
    const syncHeight = () => {
      if (inputRef.current && sendButtonRef.current) {
        // Match the rendered height (including padding & border)
        sendButtonRef.current.style.height = inputRef.current.offsetHeight + 'px';
      }
    };
    syncHeight();
    window.addEventListener('resize', syncHeight);
    return () => window.removeEventListener('resize', syncHeight);
  }, [currentMessage]);

  const t = translations[session.language];
  const dynamicPlaceholder = session.photo ? t.placeholder : (t as any).placeholderGenerate || t.placeholder;

  // Build image carousel list: initial captured photo + any assistant images
  // Build image carousel list:
  // - Include the session.photo (initial or first promoted AI image)
  // - Include subsequent assistant/user images with imageData
  // - Avoid duplicating the first generated image that was promoted to session.photo
  const images = [
    session.photo ? { key: 'initial-photo', data: session.photo.imageData } : null,
    ...session.messages
      .filter(m =>
        m.imageData &&
        !(session.photo && m.imageData === session.photo.imageData) // de-duplicate promoted first AI image
      )
      .map(m => ({ key: m.id, data: m.imageData! }))
  ].filter(Boolean) as { key: string; data: string }[];

  // Current slide index
  const [currentIndex, setCurrentIndex] = useState(0);
  const carouselRef = useRef<HTMLDivElement>(null);

  // Track per-image orientation so we can size to full height or full width
  const [orientationMap, setOrientationMap] = useState<Record<string, 'portrait' | 'landscape' | 'square'>>({});

  const handleImageLoad = (key: string, e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    const { naturalWidth, naturalHeight } = img;
    let orientation: 'portrait' | 'landscape' | 'square' =
      naturalWidth === naturalHeight
        ? 'square'
        : (naturalWidth > naturalHeight ? 'landscape' : 'portrait');
    setOrientationMap(prev => {
      if (prev[key] === orientation) return prev;
      return { ...prev, [key]: orientation };
    });
  };

  /**
   * Zoom & Pan State (per current image)
   * We only keep zoom for the active slide to simplify. Reset when index changes.
   */
  const [zoomScale, setZoomScale] = useState(1);
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [isPanning, setIsPanning] = useState(false);
  const pinchDistanceRef = useRef<number | null>(null);
  const lastPanPointRef = useRef<{ x: number; y: number } | null>(null);
  const imgContainerRef = useRef<HTMLDivElement | null>(null);
  const activeImageRef = useRef<HTMLImageElement | null>(null); // active initial photo image element (for cropping)
  const lastTapTimeRef = useRef<number>(0); // for double-tap reset to default view

  // Reset zoom/pan when slide changes
  useEffect(() => {
    setZoomScale(1);
    setPanX(0);
    setPanY(0);
    setIsPanning(false);
    pinchDistanceRef.current = null;
    lastPanPointRef.current = null;
  }, [currentIndex]);

  const clampPan = (nx: number, ny: number, scale: number) => {
    if (!imgContainerRef.current) return { x: nx, y: ny };
    const rect = imgContainerRef.current.getBoundingClientRect();
    // Effective extra size after scale relative to container
    const maxX = ((scale - 1) * rect.width) / 2;
    const maxY = ((scale - 1) * rect.height) / 2;
    return {
      x: Math.max(-maxX, Math.min(maxX, nx)),
      y: Math.max(-maxY, Math.min(maxY, ny)),
    };
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      // Pinch start (reset double-tap tracking)
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      pinchDistanceRef.current = Math.hypot(dx, dy);
      lastPanPointRef.current = null;
      setIsPanning(false);
      return;
    }
    if (e.touches.length === 1) {
      const now = Date.now();
      const delta = now - lastTapTimeRef.current;
      lastTapTimeRef.current = now;
      // Double tap threshold ~300ms
      if (delta > 0 && delta < 300) {
        // Double tap detected
        if (zoomScale > 1) {
          // Smoothly reset to comfortable default view (scale 1, centered)
            setZoomScale(1);
            setPanX(0);
            setPanY(0);
        }
        // prevent triggering pan on this double tap
        pinchDistanceRef.current = null;
        lastPanPointRef.current = null;
        setIsPanning(false);
        return;
      }
      // If currently zoomed, prepare for panning
      if (zoomScale > 1) {
        lastPanPointRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        setIsPanning(true);
      }
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 2 && pinchDistanceRef.current != null) {
      e.preventDefault();
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.hypot(dx, dy);
      let newScale = zoomScale * (dist / pinchDistanceRef.current);
      pinchDistanceRef.current = dist;
      newScale = Math.min(5, Math.max(1, newScale));
      setZoomScale(newScale);
      // Clamp pan to new boundaries
      const clamped = clampPan(panX, panY, newScale);
      setPanX(clamped.x);
      setPanY(clamped.y);
    } else if (e.touches.length === 1 && zoomScale > 1 && lastPanPointRef.current) {
      e.preventDefault();
      const touch = e.touches[0];
      const dx = touch.clientX - lastPanPointRef.current.x;
      const dy = touch.clientY - lastPanPointRef.current.y;
      const clamped = clampPan(panX + dx, panY + dy, zoomScale);
      setPanX(clamped.x);
      setPanY(clamped.y);
      lastPanPointRef.current = { x: touch.clientX, y: touch.clientY };
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (e.touches.length < 2) {
      pinchDistanceRef.current = null;
    }
    if (e.touches.length === 0) {
      lastPanPointRef.current = null;
      setIsPanning(false);
    }
  };

  // Desktop wheel (optional pinch simulation with ctrlKey)
  const handleWheel = (e: React.WheelEvent) => {
    if (!e.ctrlKey) return; // Only treat ctrl+wheel as zoom (similar to native pinch gesture on trackpads)
    e.preventDefault();
    let newScale = zoomScale - e.deltaY * 0.01;
    newScale = Math.min(5, Math.max(1, newScale));
    setZoomScale(newScale);
    const clamped = clampPan(panX, panY, newScale);
    setPanX(clamped.x);
    setPanY(clamped.y);
  };

  // Desktop mouse drag support (touch devices rely on native inertial horizontal scroll)
  const isMouseDownRef = useRef(false);
  const mouseStartXRef = useRef(0);
  const scrollStartRef = useRef(0);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!carouselRef.current) return;
    isMouseDownRef.current = true;
    mouseStartXRef.current = e.clientX;
    scrollStartRef.current = carouselRef.current.scrollLeft;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isMouseDownRef.current || !carouselRef.current) return;
    const dx = e.clientX - mouseStartXRef.current;
    carouselRef.current.scrollLeft = scrollStartRef.current - dx;
  };

  const handleMouseUp = () => {
    isMouseDownRef.current = false;
  };
  
  // Ephemeral overlay text (AI response)
  const [overlayText, setOverlayText] = useState<string>('');
  const [overlayVisible, setOverlayVisible] = useState(false);
  const fadeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Detect streaming / new assistant responses
  useEffect(() => {
    const assistantMessages = session.messages.filter(m => m.role === 'assistant');
    const latestAssistant = assistantMessages[assistantMessages.length - 1];

    if (!latestAssistant) {
      setOverlayText('');
      setOverlayVisible(false);
      return;
    }

    // While streaming: show live content
    if (latestAssistant.isStreaming) {
      if (fadeTimeoutRef.current) {
        clearTimeout(fadeTimeoutRef.current);
        fadeTimeoutRef.current = null;
      }
      setOverlayText(latestAssistant.content || '');
      setOverlayVisible(true);
      return;
    }

    // When streaming finishes and (optionally) image present: show final text then fade after 5s
    // Start timer only when we have finished streaming (isStreaming false) and we have some content
    if (!latestAssistant.isStreaming) {
      setOverlayText(latestAssistant.content || '');
      setOverlayVisible(true);

      // If an image arrived with this message, start 5 second fade timer
      if (latestAssistant.imageData) {
        if (fadeTimeoutRef.current) clearTimeout(fadeTimeoutRef.current);
        fadeTimeoutRef.current = setTimeout(() => {
          setOverlayVisible(false);
        }, 5000);
      }
    }
  }, [session.messages]);

  const handleSendMessage = () => {
    const message = currentMessage.trim();
    const hasStreamingMessage = session.messages.some(m => m.isStreaming);
    if (!message || isLoading || hasStreamingMessage) return;

    /**
     * When user has zoomed/panned the ORIGINAL photo (slide 0, key 'initial-photo'),
     * capture ONLY the currently visible viewport portion and make it available
     * to the parent (page) via a temporary global. The parent will substitute this
     * cropped view when sending to the AI service so only the visualized region
     * is analyzed.
     */
    try {
      if (
        session.photo &&                         // there is an initial photo
        currentIndex === 0 &&                    // we are on the first slide
        zoomScale > 1 &&                         // user actually zoomed in
        imgContainerRef.current &&
        activeImageRef.current
      ) {
        const container = imgContainerRef.current;
        const imgEl = activeImageRef.current;

        const containerRect = container.getBoundingClientRect();
        const containerWidth = Math.round(containerRect.width);
        const containerHeight = Math.round(containerRect.height);

        // Natural dimensions
        const naturalWidth = imgEl.naturalWidth;
        const naturalHeight = imgEl.naturalHeight;

        // Determine base scale-to-fit factor (before user zoom) similar to object-contain logic
        // We replicate orientation logic: image is sized to fully fit within container.
        const widthRatio = containerWidth / naturalWidth;
        const heightRatio = containerHeight / naturalHeight;
        const scaleToFit = Math.min(widthRatio, heightRatio);

        // Canvas sized to viewport (what user actually sees)
        const canvas = document.createElement('canvas');
        canvas.width = containerWidth;
        canvas.height = containerHeight;
        const ctx = canvas.getContext('2d');

        if (ctx) {
          ctx.save();
          // Translate to center + pan (pan applied prior to scaling in CSS transform order)
            // NOTE: In CSS we apply translate then scale from center. We approximate the same.
          ctx.translate(containerWidth / 2 + panX, containerHeight / 2 + panY);
          ctx.scale(zoomScale, zoomScale);

          // Draw the image centered with the base fit size
          const drawWidth = naturalWidth * scaleToFit;
          const drawHeight = naturalHeight * scaleToFit;
          ctx.drawImage(imgEl, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
          ctx.restore();

          // Export cropped (viewport) JPEG (higher quality since we already limited area)
          const dataUrl = canvas.toDataURL('image/jpeg', 0.9);

          (window as any).wondercamCroppedView = {
            dataUrl,
            width: canvas.width,
            height: canvas.height
          };
          console.log('📐 Captured cropped viewport for AI analysis', {
            canvas: { w: canvas.width, h: canvas.height },
            natural: { w: naturalWidth, h: naturalHeight },
            scaleToFit,
            zoomScale,
            panX,
            panY
          });
        }
      } else {
        // Clear any previous cropped view if conditions no longer apply
        if ((window as any).wondercamCroppedView) {
          delete (window as any).wondercamCroppedView;
        }
      }
    } catch (cropError) {
      console.warn('⚠️ Failed to generate cropped view, falling back to full image.', cropError);
      if ((window as any).wondercamCroppedView) {
        delete (window as any).wondercamCroppedView;
      }
    }

    onMessage(message);
    setCurrentMessage('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Scroll snapping index detection
  const handleCarouselScroll = () => {
    if (!carouselRef.current) return;
    const { scrollLeft, clientWidth } = carouselRef.current;
    const index = Math.round(scrollLeft / clientWidth);
    setCurrentIndex(index);
  };
  
  const scrollToIndex = (idx: number) => {
    if (!carouselRef.current) return;
    carouselRef.current.scrollTo({
      left: idx * carouselRef.current.clientWidth,
      behavior: 'smooth'
    });
  };

  const goPrev = () => {
    if (images.length <= 1) return;
    const target = Math.max(0, currentIndex - 1);
    scrollToIndex(target);
  };

  const goNext = () => {
    if (images.length <= 1) return;
    const target = Math.min(images.length - 1, currentIndex + 1);
    scrollToIndex(target);
  };

  // When new image added, auto-advance to last image
  useEffect(() => {
    if (images.length > 0) {
      // Move to last image if a new one appended
      if (currentIndex === images.length - 2 || currentIndex === images.length - 1) {
        // After assistant image generation, show latest
        scrollToIndex(images.length - 1);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [images.length]); // Only when count changes

  return (
    <div className="chat-component h-full bg-black text-white relative">
      {/* Fixed Top Nav */}
      <div className="fixed top-0 left-0 right-0 z-30 bg-black/70 backdrop-blur-md border-b border-white/10">
        <div className="flex items-center justify-between px-4 py-3">
          {/* Back to Camera */}
            <button
              onClick={onNewPhoto}
              className="flex flex-shrink-0 items-center gap-1 text-white/70 hover:text-white transition-colors"
              title={t.backToCamera}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m15 18-6-6 6-6"/>
              </svg>
              <span className="text-sm font-medium">{t.camera}</span>
            </button>

          {/* Center Title / Indicators */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm font-medium">{t.photo}</span>
              <span className="text-sm font-medium">{t.chat}</span>
            </div>
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            <UserMenu user={session.user} isAnonymous={session.isAnonymous} credits={session.credits} />
            <LanguageSelector
              currentLanguage={session.language}
              onLanguageChange={onLanguageChange}
            />
          </div>
        </div>
      </div>

      {/* Fixed Bottom Input */}
      <div className="fixed bottom-0 left-0 right-0 z-30 bg-black/80 backdrop-blur-md border-t border-white/10">
        <div className="px-4 py-3">
          <div className="flex gap-3 items-stretch">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={currentMessage}
                onChange={(e) => setCurrentMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={dynamicPlaceholder}
                disabled={isLoading || session.messages.some(m => m.isStreaming)}
                className="w-full px-3 py-3 bg-white/10 border border-white/20 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-white/30 disabled:opacity-50 text-sm leading-relaxed placeholder:text-white/40"
                rows={2}
                maxLength={1000}
              />
              <div className="absolute bottom-2 right-2 text-[10px] text-white/40">
                {currentMessage.length}/1000
              </div>
            </div>
            <button
              ref={sendButtonRef}
              onClick={handleSendMessage}
              disabled={!currentMessage.trim() || isLoading || session.messages.some(m => m.isStreaming)}
              className="px-6 bg-white text-black hover:bg-white/90 disabled:opacity-40 disabled:cursor-not-allowed rounded-md font-medium transition-colors flex items-center justify-center min-w-[64px] whitespace-nowrap"
            >
              {(isLoading || session.messages.some(m => m.isStreaming)) ? (
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m22 2-7 20-4-9-9-4Z"/>
                  <path d="M22 2 11 13"/>
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Middle Carousel Area */}
      <div
        className="absolute inset-x-0"
        style={{
          top: '64px', // approximate header height
          bottom: '120px' // space for input (approx)
        }}
      >
        {/* Image Carousel */}
        <div
          ref={carouselRef}
          className="h-full w-full overflow-x-auto overflow-y-hidden flex snap-x snap-mandatory scroll-smooth no-scrollbar select-none cursor-grab active:cursor-grabbing carousel-snap"
          style={{ WebkitOverflowScrolling: 'touch', touchAction: 'pan-x pan-y' }}
          onScroll={handleCarouselScroll}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {images.length === 0 && (
            <div className="min-w-full h-full flex flex-col items-center justify-center text-white/60 px-6">
              <div className="text-5xl mb-6">🤖</div>
              <h3 className="font-medium text-white mb-2">{t.newConversation}</h3>
              <p className="text-sm text-center max-w-xs">{t.startConversation}</p>
            </div>
          )}
          {images.map((img, idx) => {
            const orientation = orientationMap[img.key];
            const sizingClass =
              orientation === 'portrait'
                ? 'h-full w-auto'
                : 'w-full h-auto';

            const isActive = idx === currentIndex;
            const transform = isActive
              ? `translate3d(${panX}px, ${panY}px, 0) scale(${zoomScale})`
              : 'translate3d(0,0,0) scale(1)';

            return (
              <div
                key={img.key}
                className="min-w-full h-full flex items-center justify-center px-4 snap-center relative"
              >
                <div
                  ref={isActive ? imgContainerRef : null}
                  className="relative w-full h-full flex items-center justify-center overflow-hidden"
                  onTouchStart={isActive ? handleTouchStart : undefined}
                  onTouchMove={isActive ? handleTouchMove : undefined}
                  onTouchEnd={isActive ? handleTouchEnd : undefined}
                  onTouchCancel={isActive ? handleTouchEnd : undefined}
                  onWheel={isActive ? handleWheel : undefined}
                  onDoubleClick={isActive ? () => {
                    if (zoomScale > 1) {
                      setZoomScale(1);
                      setPanX(0);
                      setPanY(0);
                    }
                  } : undefined}
                  style={{
                    touchAction: zoomScale > 1 ? 'none' : undefined,
                    WebkitOverflowScrolling: 'touch',
                  }}
                >
                  <img
                    ref={isActive && img.key === 'initial-photo' ? activeImageRef : undefined}
                    src={img.data}
                    alt="WonderCam frame"
                    onLoad={(e) => handleImageLoad(img.key, e)}
                    className={`${sizingClass} object-contain rounded-xl select-none transition-[transform] duration-150 will-change-transform`}
                    style={{
                      maxHeight: '100%',
                      maxWidth: '100%',
                      transform,
                      cursor: zoomScale > 1 ? 'grab' : 'default'
                    }}
                    draggable={false}
                  />
                  {/* Zoom hint / indicator (optional) */}
                  {isActive && zoomScale > 1 && (
                    <div className="absolute bottom-3 right-4 text-[10px] text-white/60">
                      {zoomScale.toFixed(2)}×
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Pagination (Apple style - very narrow) */}
        {images.length > 1 && (
          <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-2 flex items-center gap-1">
            {images.map((_, i) => (
              <div
                key={i}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  scrollToIndex(i);
                }}
                className={`h-[4px] rounded-full transition-all duration-300 cursor-pointer pointer-events-auto ${
                  i === currentIndex ? 'w-8 bg-white' : 'w-2 bg-white/40 hover:bg-white/70'
                }`}
              ></div>
            ))}
          </div>
        )}

        {/* Edge Tap Zones (10% each side) */}
        {images.length > 1 && (
          <>
            <div
              aria-hidden="true"
              onClick={() => {
                if (currentIndex === 0) {
                  // bounce effect at left boundary
                  if (carouselRef.current) {
                    carouselRef.current.classList.add('edge-bounce-left');
                    setTimeout(() => carouselRef.current?.classList.remove('edge-bounce-left'), 350);
                  }
                } else {
                  goPrev();
                }
              }}
              className="absolute top-0 left-0 h-full z-30"
              style={{
                width: '10%',
                cursor: currentIndex === 0 ? 'not-allowed' : 'pointer',
                background: 'linear-gradient(to right, rgba(0,0,0,0.25), rgba(0,0,0,0))',
                opacity: 0.0
              }}
            />
            <div
              aria-hidden="true"
              onClick={() => {
                if (currentIndex === images.length - 1) {
                  // bounce effect at right boundary
                  if (carouselRef.current) {
                    carouselRef.current.classList.add('edge-bounce-right');
                    setTimeout(() => carouselRef.current?.classList.remove('edge-bounce-right'), 350);
                  }
                } else {
                  goNext();
                }
              }}
              className="absolute top-0 right-0 h-full z-30"
              style={{
                width: '10%',
                cursor: currentIndex === images.length - 1 ? 'not-allowed' : 'pointer',
                background: 'linear-gradient(to left, rgba(0,0,0,0.25), rgba(0,0,0,0))',
                opacity: 0.0
              }}
            />
          </>
        )}

        {/* Local bounce animation styles */}
        <style jsx>{`
          @keyframes wc-bounce-left {
            0% { transform: translateX(0); }
            30% { transform: translateX(14px); }
            60% { transform: translateX(-6px); }
            100% { transform: translateX(0); }
          }
          @keyframes wc-bounce-right {
            0% { transform: translateX(0); }
            30% { transform: translateX(-14px); }
            60% { transform: translateX(6px); }
            100% { transform: translateX(0); }
          }
          .edge-bounce-left {
            animation: wc-bounce-left 0.35s ease;
          }
          .edge-bounce-right {
            animation: wc-bounce-right 0.35s ease;
          }
        `}</style>

        {/* Overlay Chat Text */}
        {overlayVisible && overlayText && (
          <div
            className="absolute inset-x-0 top-4 flex justify-center px-4 z-20"
          >
            <div
              className={`max-w-xl text-sm leading-relaxed px-4 py-3 rounded-2xl bg-black/70 backdrop-blur-md border border-white/10 text-white shadow-lg transition-opacity duration-700 ${overlayVisible ? 'opacity-100' : 'opacity-0'}`}
            >
              {overlayText}
              {/* Streaming cursor */}
              {session.messages.some(m => m.role === 'assistant' && m.isStreaming) && (
                <span className="inline-block w-1 h-4 bg-white ml-1 animate-pulse"></span>
              )}
            </div>
          </div>
        )}

        {/* Loading (thinking) indicator if no streaming message bubble now */}
        {isLoading && !session.messages.some(m => m.isStreaming) && (
          <div className="absolute left-1/2 -translate-x-1/2 top-4 text-white/60 text-xs flex items-center gap-2">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-white/50 rounded-full animate-pulse"></div>
              <div className="w-2 h-2 bg-white/50 rounded-full animate-pulse" style={{ animationDelay: '0.15s' }}></div>
              <div className="w-2 h-2 bg-white/50 rounded-full animate-pulse" style={{ animationDelay: '0.3s' }}></div>
            </div>
            <span>{t.thinking}</span>
          </div>
        )}
      </div>
    </div>
  );
}