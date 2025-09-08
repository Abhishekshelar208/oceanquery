# OceanQuery 🌊🤖📊

**AI-powered web application for interactive exploration and visualization of ARGO ocean float data**

## Overview

OceanQuery enables researchers, students, and policymakers to explore ARGO ocean float data through a natural-language chat interface, eliminating the need for manual NetCDF file handling or complex coding.

### Key Features

- **🗣️ Natural Language Chat** - Ask questions in plain English (e.g., "Show me salinity profiles near 10°N for March 2023")
- **🧠 AI-Powered SQL Translation** - RAG pipeline converts natural language to precise SQL queries
- **📊 Interactive Visualizations** - Temperature/salinity profiles, float trajectories, T-S diagrams
- **🗺️ Interactive Maps** - Real-time float locations and trajectories using Leaflet/Mapbox
- **📤 Data Export** - Export filtered datasets as CSV/NetCDF
- **🔐 Secure Authentication** - Firebase/Auth0 integration
- **⚡ High Performance** - PostgreSQL + vector search for fast queries

## Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│   Flutter Web      │    │   FastAPI Backend   │    │   Databases      │
│   Frontend          │    │                     │    │                  │
│ • Chat Interface    │◄──►│ • NL→SQL Pipeline  │◄──►│ • PostgreSQL     │
│ • Visualizations    │    │ • ARGO Data API     │    │ • FAISS/Chroma   │
│ • Maps & Charts     │    │ • Authentication    │    │   Vector DB      │
│ • Export Tools      │    │ • Export Service    │    │                  │
└─────────────────────┘    └─────────────────────┘    └──────────────────┘
```

## Repository Structure

```
oceanquery/
├── frontend/          # Flutter Web application
│   ├── lib/
│   │   ├── screens/   # Chat, Dashboard, Auth screens
│   │   ├── widgets/   # Charts, Maps, Export components
│   │   ├── services/  # API client, Auth, Storage
│   │   ├── models/    # Data models
│   │   └── themes/    # UI themes and routing
│   └── web/           # Web-specific assets
├── backend/           # Python FastAPI backend
│   ├── src/
│   │   ├── api/       # REST API routes
│   │   ├── db/        # Database models & connections
│   │   ├── services/  # Business logic (RAG, Chat, etc.)
│   │   ├── core/      # Configuration & settings
│   │   └── utils/     # Data processing utilities
│   └── requirements.txt
├── infra/             # Infrastructure (Docker, etc.)
├── docs/              # Documentation
├── sample_data/       # Sample ARGO datasets
└── .github/           # CI/CD workflows
```

## Quick Start

### Prerequisites

- Flutter 3.32+ with web support
- Python 3.13+
- PostgreSQL 15+
- Node.js 18+ (optional, for tooling)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd oceanquery

# Install dependencies
make install

# Start database
make db-up

# Run backend
make dev

# Run frontend (in another terminal)
make front
```

### 2. Environment Setup

Copy `.env.example` files and configure:

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your database URL, OpenAI API key, etc.

# Frontend  
cp frontend/.env.example frontend/.env
# Edit frontend/.env with API URLs and Firebase config
```

### 3. Load Sample Data

```bash
# Load Indian Ocean ARGO subset
make load-sample-data
```

### 4. Access the Application

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## MVP Demo Features

For the hackathon demo, we focus on:

✅ **Indian Ocean ARGO Data** (last 6 months subset)  
✅ **Chat → SQL → Visualization** pipeline  
✅ **Transparent SQL Preview** for users  
✅ **Basic temperature/salinity plots**  
✅ **Float trajectory maps**  
✅ **Data export functionality**

## Extended Roadmap

- 🌍 **Global ARGO + BGC Data**
- 🔍 **Advanced Anomaly Detection**  
- 🔗 **Digital Ocean Portal Integration**
- 🌐 **Multi-language Support**
- 🎤 **Voice-based Chat Interface**
- 📱 **Mobile App (iOS/Android)**

## Technology Stack

- **Frontend**: Flutter Web, fl_chart, flutter_map, Firebase Auth
- **Backend**: Python, FastAPI, SQLAlchemy, LangChain
- **AI/ML**: OpenAI GPT-4 / Ollama LLaMA, FAISS/ChromaDB
- **Database**: PostgreSQL, Vector DB for embeddings
- **Infrastructure**: Docker, AWS/GCP
- **Data Processing**: xarray, pandas, NetCDF4

## Contributing

1. Read [TECH_STACK.md](docs/TECH_STACK.md) for detailed architecture
2. Check [API_CONTRACT.md](docs/API_CONTRACT.md) for API specifications
3. Follow the development workflow in [CONTRIBUTING.md](docs/CONTRIBUTING.md)

## License

[MIT License](LICENSE)

---

**Built with ❤️ for the oceanographic research community**
# oceanquery
