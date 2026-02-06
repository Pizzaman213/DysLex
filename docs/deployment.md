# Deployment Guide

## Development Setup

### Prerequisites
- Node.js 20+
- Python 3.11+
- PostgreSQL 15+
- Docker (optional)

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Database
```bash
createdb dyslex
psql dyslex < database/schema/init.sql
psql dyslex < database/seeds/error_types.sql
```

## Docker Deployment

### Full Stack
```bash
docker compose -f docker/docker-compose.yml up
```

### Development Mode
```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up
```

## Environment Variables

### Backend
- `DATABASE_URL` - PostgreSQL connection string
- `NVIDIA_NIM_API_KEY` - NVIDIA NIM API key
- `JWT_SECRET_KEY` - Secret key for JWT tokens

### Frontend
- `VITE_API_URL` - Backend API URL (default: http://localhost:8000)

## Production Considerations

### Frontend
- Build with `npm run build`
- Serve via Nginx or CDN
- Enable gzip compression
- Set appropriate cache headers

### Backend
- Use Gunicorn with Uvicorn workers
- Enable connection pooling for PostgreSQL
- Set up health check endpoints
- Configure rate limiting

### Database
- Enable connection pooling (PgBouncer)
- Regular backups
- Set up read replicas for scaling

### Security
- HTTPS everywhere
- CORS configuration
- Rate limiting
- Input validation
- SQL injection prevention (handled by SQLAlchemy)
