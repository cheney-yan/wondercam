# WonderCam

WonderCam is a conversational AI-enhanced webcam application that combines real-time camera functionality with AI-powered photo analysis and chat capabilities.

## Quick Start

### Development Mode (Hot Reload)

For active development with automatic code reloading:

```bash
# Start development environment with hot reload
docker-compose -f docker-compose.dev.yml up --build

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

**Development Features:**
- 🔄 **Frontend Hot Reload**: Next.js dev server automatically reloads on code changes
- 🔄 **Backend Hot Reload**: FastAPI with uvicorn --reload restarts on Python code changes
- 📁 **Volume Mounting**: Source code mounted for real-time development
- 🐛 **Debug Mode**: Enhanced logging and error reporting

### Production Mode

For production deployment:

```bash
# Start production environment
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop production environment
docker-compose down
```

## Environment Setup

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure environment variables** in `.env`:
   ```bash
   # Supabase Configuration
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_OR_ANON_KEY=your_supabase_anon_key
   
   # Backend Configuration  
   NEXT_PUBLIC_BACKEND_API_HOST=http://localhost:18000
   
   # Google Cloud Credentials
   GOOGLE_APPLICATION_CREDENTIALS=./api/credentials.json
   
   # Debug Mode (for development)
   DEBUG=True
   ```

3. **Add Google Cloud credentials**:
   - Place your service account key file as `./api/credentials.json`

## Architecture

- **Frontend**: Next.js 14+ with TypeScript, React, and Tailwind CSS
- **Backend**: FastAPI proxy service for Vertex AI integration  
- **Authentication**: Supabase Auth with JWT tokens
- **AI Service**: Streaming responses via custom Vertex AI proxy
- **Deployment**: Docker containers with docker-compose

## Key Features

- 📹 **Multi-Camera Support**: Switch between available camera devices
- 🤖 **Streaming AI Chat**: Real-time AI responses with typewriter effect
- 🌍 **Multi-Language**: Support for English, Chinese, Spanish, French, Japanese
- 🔐 **Secure Authentication**: Supabase JWT integration
- 📱 **Mobile-First**: Responsive design optimized for all devices
- 🖼️ **Photo Processing**: Dual-quality compression for display and AI analysis

## Development

### Local Development (Without Docker)

**Frontend**:
```bash
cd app
npm install
npm run dev  # Runs on http://localhost:3000
```

**Backend**:
```bash
cd api
pip install -r requirements.txt
DEBUG=True uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Development Commands

```bash
# Frontend
cd app
npm run dev      # Development server
npm run build    # Production build
npm run lint     # Code linting

# Backend  
cd api
./setup.sh                    # Environment setup
python run.py                 # Production server
uvicorn main:app --reload     # Development server
```

## File Structure

```
├── app/                          # Next.js frontend
│   ├── components/wondercam/     # Core components
│   ├── lib/                      # Services and utilities
│   ├── app/                      # App router pages
│   └── Dockerfile.dev            # Development Docker image
├── api/                          # FastAPI backend
│   ├── main.py                   # FastAPI application
│   ├── auth_handler.py           # Authentication service
│   └── Dockerfile.dev            # Development Docker image
├── docker-compose.yml            # Production deployment
├── docker-compose.dev.yml        # Development with hot reload
└── .env.example                  # Environment template
```

For detailed development guidance, see [CLAUDE.md](./CLAUDE.md).