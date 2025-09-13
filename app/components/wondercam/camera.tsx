'use client';

import { useState, useEffect, useRef } from 'react';
import { User } from '@supabase/supabase-js';
import { CapturedPhoto, SupportedLanguage } from '@/app/wondercam/page';
import { CreditDisplay } from '@/components/credit-display';

interface CameraComponentProps {
  user: User;
  onPhotoCapture: (photo: CapturedPhoto) => void;
  onError: (error: string) => void;
  isVisible: boolean;
  currentLanguage: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
  onStartChat?: () => void; // Start direct chat without initial photo
}

export function CameraComponent({ user, onPhotoCapture, onError, isVisible, currentLanguage, onLanguageChange, onStartChat }: CameraComponentProps) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [availableCameras, setAvailableCameras] = useState<MediaDeviceInfo[]>([]);
  const [currentCameraIndex, setCurrentCameraIndex] = useState(0);
  const [isCapturing, setIsCapturing] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isSwitching, setIsSwitching] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initialize cameras
  useEffect(() => {
    initializeCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const initializeCamera = async () => {
    try {
      setIsInitializing(true);
      
      // First get user media to trigger permission
      const initialStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      
      // Now enumerate devices (labels will be available after permission)
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cameras = devices.filter(device => device.kind === 'videoinput');
      
      console.log('📹 Available cameras:', cameras.map((c, i) => ({
        index: i,
        deviceId: c.deviceId,
        label: c.label || `Camera ${i + 1}`
      })));
      
      setAvailableCameras(cameras);

      if (cameras.length === 0) {
        onError('No camera devices found. Please connect a camera.');
        return;
      }

      // Stop initial stream and start with proper device
      initialStream.getTracks().forEach(track => track.stop());
      
      // Start first camera with specific deviceId
      await startCamera(cameras[0].deviceId);
      setHasPermission(true);
      
    } catch (error: any) {
      handleCameraError(error);
    } finally {
      setIsInitializing(false);
    }
  };

  const startCamera = async (deviceId?: string) => {
    try {
      // Stop current stream if exists
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }

      const constraints: MediaStreamConstraints = {
        video: deviceId 
          ? { deviceId: { exact: deviceId } }
          : true,
        audio: false
      };

      console.log('📹 Starting camera with constraints:', constraints);

      const newStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(newStream);

      if (videoRef.current) {
        videoRef.current.srcObject = newStream;
        
        // Wait for video to be ready
        await new Promise<void>((resolve) => {
          if (videoRef.current) {
            videoRef.current.onloadedmetadata = () => {
              console.log('📹 Video metadata loaded');
              resolve();
            };
          }
        });
      }

    } catch (error: any) {
      console.error('📹 Camera start error:', error);
      handleCameraError(error);
    }
  };

  const handleCameraError = (error: any) => {
    console.error('Camera error:', error);
    
    switch (error.name) {
      case 'NotAllowedError':
        onError('Camera access denied. Please allow camera permissions and refresh the page.');
        break;
      case 'NotFoundError':
        onError('No camera found. Please connect a camera device.');
        break;
      case 'NotReadableError':
        onError('Camera is being used by another application.');
        break;
      default:
        onError(`Camera error: ${error.message}`);
    }
  };

  const switchCamera = async () => {
    if (availableCameras.length <= 1) {
      console.log('📹 No additional cameras to switch to');
      return;
    }
    
    try {
      setIsSwitching(true);
      
      const nextIndex = (currentCameraIndex + 1) % availableCameras.length;
      console.log('📹 Switching from camera', currentCameraIndex, 'to camera', nextIndex);
      console.log('📹 New camera:', availableCameras[nextIndex]);
      
      setCurrentCameraIndex(nextIndex);
      await startCamera(availableCameras[nextIndex].deviceId);
      
    } catch (error: any) {
      console.error('📹 Camera switch error:', error);
      handleCameraError(error);
    } finally {
      setIsSwitching(false);
    }
  };

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current || isCapturing) return;

    try {
      setIsCapturing(true);
      
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      if (!context) {
        onError('Canvas not supported');
        return;
      }

      // Set canvas dimensions to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      // Draw video frame to canvas
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Get image data
      const imageData = canvas.toDataURL('image/jpeg', 0.9);
      
      // Create compressed version for AI (smaller size)
      const tempCanvas = document.createElement('canvas');
      const tempContext = tempCanvas.getContext('2d');
      if (!tempContext) {
        onError('Canvas not supported');
        return;
      }

      // Compress for AI processing (max 1024px)
      const maxDimension = 1024;
      const scale = Math.min(maxDimension / canvas.width, maxDimension / canvas.height);
      
      tempCanvas.width = canvas.width * scale;
      tempCanvas.height = canvas.height * scale;
      
      tempContext.drawImage(canvas, 0, 0, tempCanvas.width, tempCanvas.height);
      const compressedData = tempCanvas.toDataURL('image/jpeg', 0.7);

      // Create photo object
      const photo: CapturedPhoto = {
        id: crypto.randomUUID(),
        imageData,
        compressedData,
        capturedAt: new Date(),
        dimensions: {
          width: canvas.width,
          height: canvas.height,
          aspectRatio: canvas.width / canvas.height
        },
        fileSize: Math.round(imageData.length * 0.75) // Approximate size
      };

      onPhotoCapture(photo);

    } catch (error: any) {
      onError(`Failed to capture photo: ${error.message}`);
    } finally {
      setIsCapturing(false);
    }
  };

  const handlePhotoSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      onError('Please select a valid image file.');
      return;
    }

    try {
      // Read file as data URL
      const reader = new FileReader();
      reader.onload = async (e) => {
        const imageData = e.target?.result as string;
        if (!imageData) return;

        // Create an image to get dimensions
        const img = new Image();
        img.onload = async () => {
          try {
            // Create canvas to process the image
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            if (!context) {
              onError('Canvas not supported');
              return;
            }

            // Set canvas dimensions
            canvas.width = img.width;
            canvas.height = img.height;
            
            // Draw image to canvas
            context.drawImage(img, 0, 0);
            
            // Get high quality version
            const highQualityData = canvas.toDataURL('image/jpeg', 0.9);
            
            // Create compressed version for AI
            const maxDimension = 1024;
            const scale = Math.min(maxDimension / canvas.width, maxDimension / canvas.height);
            
            const tempCanvas = document.createElement('canvas');
            const tempContext = tempCanvas.getContext('2d');
            if (!tempContext) return;
            
            tempCanvas.width = canvas.width * scale;
            tempCanvas.height = canvas.height * scale;
            
            tempContext.drawImage(canvas, 0, 0, tempCanvas.width, tempCanvas.height);
            const compressedData = tempCanvas.toDataURL('image/jpeg', 0.7);

            // Create photo object
            const photo: CapturedPhoto = {
              id: crypto.randomUUID(),
              imageData: highQualityData,
              compressedData,
              capturedAt: new Date(),
              dimensions: {
                width: img.width,
                height: img.height,
                aspectRatio: img.width / img.height
              },
              fileSize: Math.round(highQualityData.length * 0.75)
            };

            onPhotoCapture(photo);

          } catch (error: any) {
            onError(`Failed to process image: ${error.message}`);
          }
        };
        
        img.onerror = () => {
          onError('Failed to load selected image.');
        };
        
        img.src = imageData;
      };

      reader.onerror = () => {
        onError('Failed to read selected file.');
      };

      reader.readAsDataURL(file);

    } catch (error: any) {
      onError(`Photo selection failed: ${error.message}`);
    }

    // Clear the input
    event.target.value = '';
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="camera-component h-full relative bg-black flex flex-col">
      {/* Language Selector */}
      <div className="absolute top-4 right-4 z-50 flex items-center space-x-4">
        <CreditDisplay />
        <select
          value={currentLanguage}
          onChange={(e) => onLanguageChange(e.target.value as SupportedLanguage)}
          className="bg-gray-800/90 border border-gray-600 rounded-md px-2 py-1 text-sm text-white focus:outline-none focus:ring-2 focus:ring-white/50 hover:bg-gray-700/90 transition-colors backdrop-blur-sm"
        >
          <option value="en">EN</option>
          <option value="zh">中文</option>
          <option value="es">ES</option>
          <option value="fr">FR</option>
          <option value="ja">日本語</option>
        </select>
      </div>

      {/* Video Preview */}
      <div className="camera-preview flex-1 relative overflow-hidden">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
        />
        
        {/* Loading overlay */}
        {isInitializing && (
          <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center">
            <div className="text-center text-white">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
              <p>Initializing camera...</p>
            </div>
          </div>
        )}

        {/* Capture overlay */}
        {isCapturing && (
          <div className="absolute inset-0 bg-white bg-opacity-20 flex items-center justify-center">
            <div className="text-white text-xl font-bold">
              📸 Capturing...
            </div>
          </div>
        )}

        {/* Camera switching overlay */}
        {isSwitching && (
          <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center">
            <div className="text-center text-white">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
              <p>Switching camera...</p>
            </div>
          </div>
        )}

        {/* Hidden canvas for photo capture */}
        <canvas
          ref={canvasRef}
          className="hidden"
        />

        {/* Hidden file input for photo selection */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Camera Controls */}
      <div className="camera-controls p-4 bg-black bg-opacity-50">
        <div className="flex justify-center items-center space-x-6">
          
          {/* Switch Camera Button */}
          <button
            onClick={switchCamera}
            disabled={availableCameras.length <= 1 || isInitializing || isSwitching}
            className="p-3 rounded-full bg-gray-700 text-white disabled:opacity-50 hover:bg-gray-600 transition-colors"
            title={
              isSwitching
                ? 'Switching camera...'
                : availableCameras.length > 1
                  ? `Switch camera (${availableCameras.length} available)`
                  : 'Only one camera available'
            }
          >
            {isSwitching ? '⏳' : '🔄'}
          </button>

          {/* Capture Button */}
          <button
            onClick={capturePhoto}
            disabled={!hasPermission || isCapturing || isInitializing || isSwitching}
            className="w-16 h-16 rounded-full bg-white border-4 border-gray-300 disabled:opacity-50 hover:bg-gray-100 transition-all transform active:scale-95"
            title={
              isCapturing
                ? 'Capturing photo...'
                : isSwitching
                  ? 'Camera switching...'
                  : hasPermission
                    ? 'Take photo'
                    : 'Camera not ready'
            }
          >
            {isCapturing ? '⏳' : isSwitching ? '🔄' : '📷'}
          </button>

          {/* Direct Chat (no photo) */}
          {onStartChat && (
            <button
              onClick={onStartChat}
              disabled={isInitializing || isSwitching || isCapturing}
              className="p-3 rounded-full bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
              title="Start chat without capturing a photo first"
            >
              💬
            </button>
          )}

          {/* Photo Album Selection */}
          <button
            onClick={handlePhotoSelect}
            className="p-3 rounded-full bg-gray-700 text-white hover:bg-gray-600 transition-colors"
            title="Select from album"
          >
            🖼️
          </button>
        </div>

        {/* Camera info */}
        {availableCameras.length > 0 && (
          <div className="text-center text-gray-300 text-sm mt-2">
            Camera {currentCameraIndex + 1} of {availableCameras.length}
            {availableCameras[currentCameraIndex]?.label && (
              <div className="truncate max-w-xs mx-auto">
                {availableCameras[currentCameraIndex].label}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}