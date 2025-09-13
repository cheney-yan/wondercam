'use client';

import { useState, useRef, useEffect } from 'react';
import { CapturedPhoto } from '@/app/wondercam/page';

interface PhotoViewerProps {
  photo: CapturedPhoto;
  onZoom: () => void;
  onShare: () => void;
  onStore: () => void;
  onBack: () => void;
}

export function PhotoViewer({ photo, onZoom, onShare, onStore, onBack }: PhotoViewerProps) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [lastPanPoint, setLastPanPoint] = useState({ x: 0, y: 0 });
  
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          onBack();
          break;
        case '+':
        case '=':
          handleZoomIn();
          break;
        case '-':
          handleZoomOut();
          break;
        case '0':
          resetZoom();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [onBack]);

  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev * 1.5, 5));
  };

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev / 1.5, 0.5));
  };

  const resetZoom = () => {
    setZoomLevel(1);
    setPanPosition({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoomLevel > 1) {
      setIsDragging(true);
      setLastPanPoint({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoomLevel > 1) {
      const deltaX = e.clientX - lastPanPoint.x;
      const deltaY = e.clientY - lastPanPoint.y;
      
      setPanPosition(prev => ({
        x: prev.x + deltaX,
        y: prev.y + deltaY
      }));
      
      setLastPanPoint({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoomLevel(prev => Math.min(Math.max(prev * delta, 0.5), 5));
  };

  const handleShare = async () => {
    try {
      // Convert base64 to blob
      const response = await fetch(photo.imageData);
      const blob = await response.blob();
      const file = new File([blob], `wondercam-photo-${photo.capturedAt.getTime()}.jpg`, { type: 'image/jpeg' });

      if (navigator.share && navigator.canShare({ files: [file] })) {
        await navigator.share({
          title: 'WonderCam Photo',
          text: 'Check out this photo I took with WonderCam! 📸✨',
          files: [file]
        });
        console.log('✅ Photo shared successfully');
      } else if (navigator.share) {
        // Try sharing without files (for unsupported browsers)
        await navigator.share({
          title: 'WonderCam Photo',
          text: 'Check out this photo I took with WonderCam! 📸✨',
          url: window.location.href
        });
        console.log('✅ Link shared successfully');
      } else {
        // Fallback: copy image to clipboard if supported
        if (navigator.clipboard && window.ClipboardItem) {
          const clipboardItem = new ClipboardItem({
            'image/jpeg': blob
          });
          await navigator.clipboard.write([clipboardItem]);
          alert('📋 Photo copied to clipboard!');
          console.log('✅ Photo copied to clipboard');
        } else {
          // Final fallback: download
          await handleStore();
        }
      }
    } catch (error) {
      console.error('❌ Share failed:', error);
      // Fallback to download
      try {
        await handleStore();
        alert('📥 Sharing not supported - photo downloaded instead!');
      } catch (downloadError) {
        console.error('❌ Download also failed:', downloadError);
        alert('❌ Unable to share or download photo. Please try again.');
      }
    }
  };

  const handleStore = async () => {
    try {
      // Create download link
      const link = document.createElement('a');
      link.href = photo.imageData;
      link.download = `wondercam-${photo.capturedAt.toISOString().slice(0, 19).replace(/:/g, '-')}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Store failed:', error);
    }
  };

  return (
    <div className="photo-viewer fixed inset-0 bg-black z-50 flex flex-col">
      
      {/* Header */}
      <div className="photo-viewer-header p-4 bg-black bg-opacity-75 flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 text-white hover:text-gray-300 transition-colors"
        >
          <span className="text-xl">←</span>
          <span>Back to Chat</span>
        </button>
        
        <div className="text-white text-sm">
          {photo.dimensions.width} × {photo.dimensions.height} • {Math.round(photo.fileSize / 1024)}KB
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-white text-sm">
            {Math.round(zoomLevel * 100)}%
          </span>
        </div>
      </div>

      {/* Image Container */}
      <div
        ref={containerRef}
        className="photo-container flex-1 overflow-hidden flex items-center justify-center cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <img
          ref={imageRef}
          src={photo.imageData}
          alt="Captured photo"
          className="max-w-none select-none"
          style={{
            transform: `scale(${zoomLevel}) translate(${panPosition.x / zoomLevel}px, ${panPosition.y / zoomLevel}px)`,
            transition: isDragging ? 'none' : 'transform 0.2s ease-out'
          }}
          draggable={false}
        />
      </div>

      {/* Controls */}
      <div className="photo-controls p-4 bg-black bg-opacity-75 flex items-center justify-center space-x-4">
        
        {/* Zoom Controls */}
        <div className="flex items-center space-x-2 bg-gray-800 rounded-lg p-2">
          <button
            onClick={handleZoomOut}
            disabled={zoomLevel <= 0.5}
            className="p-2 text-white hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Zoom Out (-)"
          >
            🔍➖
          </button>
          
          <button
            onClick={resetZoom}
            className="px-3 py-1 text-white hover:text-gray-300 text-sm"
            title="Reset Zoom (0)"
          >
            Reset
          </button>
          
          <button
            onClick={handleZoomIn}
            disabled={zoomLevel >= 5}
            className="p-2 text-white hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Zoom In (+)"
          >
            🔍➕
          </button>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleShare}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            📤 Share
          </button>
          
          <button
            onClick={handleStore}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
          >
            💾 Save
          </button>
        </div>
      </div>

      {/* Help Text */}
      <div className="absolute bottom-20 left-1/2 transform -translate-x-1/2 text-white text-xs text-center bg-black bg-opacity-50 px-3 py-1 rounded">
        Use mouse wheel to zoom • Drag to pan • ESC to close
      </div>
    </div>
  );
}