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
# Development with hot reload
npm run dev

# Production build
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
- **AI Service**: `/lib/ai-service.ts` - Streaming AI responses with JWT authentication

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
- Uses Supabase Auth with JWT tokens
- Frontend handles session management via `/lib/supabase/client.ts`
- API proxy expects `x-goog-api-key` header with JWT token (currently using hardcoded key for development)
- Protected routes enforced by `/middleware.ts`

### AI Integration
- **Dual Image Processing**: Original quality for display, compressed (1024px, 70% quality) for AI
- **Streaming Responses**: Real-time AI response streaming with typewriter effect
- **Multi-language Support**: AI responses adapt to selected language
- **Context Preservation**: Chat history maintained across conversation turns
- **Image Generation Support**: Handles both text and AI-generated image responses

## Common Development Patterns

### Error Handling
- Camera errors are handled with user-friendly messages based on error types (NotAllowedError, NotFoundError, etc.)
- AI service errors include content policy, rate limiting, and authentication failure handling
- All errors display in-app notifications with dismiss functionality

### State Management
- Uses React hooks and context for session-based state (no persistence)
- Main app state managed in `/app/wondercam/page.tsx` with `AppState` interface
- Camera and chat components receive props and communicate via callback functions

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
- Image compression pipeline optimized for mobile devices
- Streaming AI responses with natural pausing for readability
- Memory-efficient canvas operations with proper cleanup
- Disabled browser zoom to prevent UI interference

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
NEXT_PUBLIC_BACKEND_API_HOST=your_backend_host

# API (.env)
GOOGLE_APPLICATION_CREDENTIALS=path_to_credentials.json
DEBUG=False
HOST=0.0.0.0
PORT=8000
```

## Known Implementation Status

### Implemented Features
- Camera capture with multi-device support
- Photo compression pipeline (dual quality)
- Streaming AI chat with conversation history
- Multi-language UI and AI responses
- Photo zoom/pan functionality
- Supabase authentication integration
- Docker containerization

### Planned Features (from requirements.md)
- Anonymous user credit system
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

## Browser Support
- Chrome 80+ (primary)
- Safari 13+ (iOS/macOS)
- Firefox 75+
- Edge 80+
- Requires WebRTC support for camera functionality