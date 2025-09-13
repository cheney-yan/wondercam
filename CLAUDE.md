# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**WonderCam** is a conversational AI-enhanced webcam application built with Next.js 14+ and TypeScript. It combines real-time camera functionality with AI-powered photo analysis and chat capabilities, using Supabase for authentication and a custom Vertex AI proxy for AI services.

### Architecture

The project consists of three main components:
- **Frontend App** (`/app`): Next.js 14+ with TypeScript, React components, and Tailwind CSS
- **API Proxy** (`/api`): FastAPI service providing Gemini-compatible interface to Vertex AI
- **Docker Infrastructure**: Containerized deployment with docker-compose

## Development Commands

### Frontend Development (app/)
```bash
# Development with hot reload (uses Turbopack)
npm run dev

# Production build (skips lint during build)
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

### API Development (api/)
```bash
# Development with hot reload
DEBUG=True uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production
python run.py

# Setup environment
./setup.sh

# Using Makefile commands
make dev          # Development mode
make run          # Production mode
make test         # Health check
make setup        # Environment setup
```

### Docker Operations
```bash
# Production mode
docker-compose up --build
docker-compose up -d
docker-compose down

# Development mode with hot reload (auto-reloads on code changes)
docker-compose -f docker-compose.dev.yml up --build
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose down
docker-compose -f docker-compose.dev.yml down
```

## Key Architecture Components

### Frontend Structure
- **Main App**: `/app/wondercam/page.tsx` - Core application state and routing
- **Camera Component**: `/components/wondercam/camera.tsx` - WebRTC camera functionality with multi-camera support
- **Chat Component**: `/components/wondercam/chat.tsx` - Real-time streaming AI chat interface
- **Photo Viewer**: `/components/wondercam/photo-viewer.tsx` - Photo display and zoom functionality
- **AI Service V1**: `/lib/ai-service.ts` - V1Beta Gemini-compatible streaming AI service
- **AI Service V2**: `/lib/ai-service-v2.ts` - Simplified V2 API with extensible message types

### Backend Structure  
- **V1Beta API**: `main.py` - Gemini-compatible proxy to Vertex AI (existing)
- **V2 API**: `v2_api.py` - Extensible messaging API with preprocessing support
- **V2 Models**: `v2_models.py` - Pydantic data structures for V2 API
- **V2 Translator**: `v2_translator.py` - Converts V2 ↔ Vertex AI formats with custom logic

### Core Data Types
```typescript
interface CapturedPhoto {
  id: string;
  imageData: string;        // Original base64
  compressedData: string;   // Compressed for AI (max 1024px, 70% quality)
  capturedAt: Date;
  dimensions: { width: number; height: number; aspectRatio: number };
  fileSize: number;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  imageData?: string; // Base64 image for AI-generated images
}

type AppMode = 'camera' | 'chat' | 'photo-actions' | 'zoomed';
type SupportedLanguage = 'en' | 'zh' | 'es' | 'fr' | 'ja';
```

### Authentication Flow
- **Anonymous Users**: Automatic anonymous authentication with IP-based credit tracking
- **Registered Users**: Email/password registration via Supabase Auth with JWT tokens
- **Session Management**: Frontend handles session via `/lib/supabase/client.ts` with automatic refresh
- **Credit System**: Anonymous users get limited credits; registered users get extended limits
- **Protected Routes**: Enforced by `/middleware.ts` with upgrade prompts for anonymous users

### AI Integration
- **Dual API Support**: V1Beta (Gemini-compatible) and V2 (extensible messaging) APIs
- **V1Beta Features**: Existing Gemini-compatible streaming with `x-goog-api-key` authentication
- **V2 Features**: Extensible message types (text/image/voice), preprocessing support, `Authorization: Bearer` auth
- **Dual Image Processing**: Original quality for display, compressed (1024px, 70% quality) for AI
- **Streaming Responses**: Real-time AI response streaming with typewriter effect using async generators
- **Multi-language Support**: AI responses adapt to selected language (en, zh, es, fr, ja)
- **Context Preservation**: Chat history maintained across conversation turns with photo context
- **Image Generation**: Direct chat without photos generates AI images (costs 2 credits)
- **Photo Analysis**: First message with photo analyzes content (costs 1 credit)
- **Preprocessing**: V2 API can interact with client before calling Vertex AI for custom logic

## Common Development Patterns

### Error Handling
- **Camera Errors**: User-friendly messages based on error types (NotAllowedError, NotFoundError, etc.)
- **AI Service Errors**: Content policy, rate limiting, authentication failure handling with fallbacks
- **Credit System Errors**: Graceful degradation with upgrade prompts for anonymous users
- **Network Errors**: Retry mechanisms and offline indicators
- **Error Display**: In-app notifications with dismiss functionality and contextual error messages

### State Management
- **Session-Based**: React hooks and context for session-based state (no server persistence)
- **App State**: Centralized state in `/app/wondercam/page.tsx` with `AppState` interface
- **Component Communication**: Props and callback functions between camera, chat, and photo viewer components
- **Credit Tracking**: Real-time credit updates with local storage synchronization
- **Anonymous/Registered State**: Dynamic UI based on authentication status

### Image Processing Pipeline
```typescript
// Dual compression for different use cases
const displayQuality = canvas.toDataURL('image/jpeg', 0.9);  // High quality for display
const aiProcessing = tempCanvas.toDataURL('image/jpeg', 0.7); // Compressed for AI (max 1024px)
```

### Language Support
- UI translations handled by language selector component
- AI responses use language-specific instructions
- Supported languages: English, Chinese, Spanish, French, Japanese

## Development Guidelines

### Component Structure
- All camera/chat components are client-side (`'use client'`)
- Use TypeScript interfaces for all props and state
- Handle loading states and error boundaries
- Implement proper cleanup for media streams and event listeners

### Performance Considerations
- **Image Processing**: Dual compression pipeline optimized for mobile devices with Canvas API
- **Memory Management**: Proper cleanup of media streams, canvas operations, and event listeners
- **Streaming Optimization**: AI responses with natural pausing and typewriter effects
- **Browser Zoom**: Disabled zoom shortcuts and gestures to prevent UI interference
- **Mobile Optimization**: Touch-friendly interface with gesture handling for photo viewer
- **Resource Cleanup**: Component unmount handlers for streams and event listeners

### Security Notes
- JWT tokens handled securely with automatic refresh
- No persistent photo storage (session-based only)
- HTTPS enforcement in production
- Content Security Policy configured for external API access

### Testing Approach
- Camera functionality requires physical devices with cameras
- AI service includes mock response capability (`useMockResponse` flag)
- Cross-browser testing needed for WebRTC compatibility
- Mobile-first responsive design testing required

## Environment Configuration

### Required Environment Variables
```bash
# Frontend (.env.local)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# AI API Configuration  
NEXT_PUBLIC_BACKEND_API_HOST=your_backend_host

# V2 API Settings
NEXT_PUBLIC_USE_V2_API=true
NEXT_PUBLIC_V2_API_FALLBACK=true
NEXT_PUBLIC_API_VERSION=v2

# API (.env)
GOOGLE_APPLICATION_CREDENTIALS=path_to_credentials.json
DEBUG=False
HOST=0.0.0.0
PORT=8000
PROXY_API_KEY=your_proxy_api_key

# Docker Environment
# Copy from .env.example and configure all values
```

### Credit System Architecture
- **Anonymous Users**: IP-based credit tracking with daily reset
- **Credit Actions**: Photo analysis (1 credit), image generation (2 credits)  
- **Database Functions**: Automated credit management via Supabase RPC functions
- **Upgrade Prompts**: Contextual prompts when credits are low/exhausted
- **Session Management**: Credits synchronized across browser tabs

## Known Implementation Status

### Implemented Features
- **Dual AI APIs**: V2 extensible messaging API with V1Beta Gemini-compatible fallback
- **Authentication**: Anonymous users with credit system + Supabase registration
- **Camera**: Multi-device support with device switching and file upload fallback
- **Image Processing**: Dual compression pipeline with viewport cropping support
- **AI Integration**: Streaming chat with photo analysis and image generation (both APIs)
- **Multi-language**: Full UI and AI response support (5 languages)
- **Photo Viewer**: Zoom/pan functionality with share and download actions
- **Credit System**: IP-based anonymous credits with upgrade prompts
- **Responsive Design**: Mobile-first with touch gestures and proper viewport handling
- **API Monitoring**: Real-time API health status and version indicator

### Planned Features (from requirements.md)
- Gallery interface replacing chat history
- Voice input with Web Speech API
- Pre-set message templates
- Enhanced photo sharing with Web Share API
- Progressive Web App capabilities
- Advanced error handling and retry mechanisms

## Performance Targets
- Page load: < 3 seconds on 3G
- Camera initialization: < 1 second
- AI response time: < 30 seconds
- Photo capture response: < 500ms

## Development Guidelines

### Component Architecture
- All camera/chat components are client-side (`'use client'`)
- TypeScript interfaces for all props and state (see core data types above)
- Proper cleanup for media streams, event listeners, and canvas operations
- Loading states and error boundaries with user feedback
- **Unified AI Service**: Automatic V2/V1Beta selection based on environment configuration
- **API Status Indicator**: Real-time monitoring and health display for both API versions

### Testing Approach
- Camera functionality requires physical devices with cameras
- AI service includes mock response capability (`useMockResponse` flag in ai-service.ts)
- **V2 API Testing**: Use API status indicator to verify V2 usage and health
- **Fallback Testing**: Test V2 → V1Beta fallback scenarios by breaking V2 endpoints
- Cross-browser testing needed for WebRTC compatibility
- Mobile-first responsive design testing required
- Test with anonymous and registered user scenarios
- **Environment Testing**: Test different API configurations (V1-only, V2-only, V2-with-fallback)

### Security and Privacy
- No persistent photo storage (session-based only)
- Secure JWT token handling with automatic refresh
- Content Security Policy configured for external API access
- Camera permissions handled with clear user messaging

## Browser Support
- Chrome 80+ (primary target)
- Safari 13+ (iOS/macOS)
- Firefox 75+
- Edge 80+
- Requires WebRTC support for camera functionality
- Mobile browsers with touch gesture support