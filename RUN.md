# Here4Beer - Running the Application

This guide explains how to run the Here4Beer application using Docker Compose.

## Prerequisites

1. **Docker & Docker Compose**: Install Docker Desktop from [docker.com](https://docker.com)
2. **Environment Variables**: Ensure your `.env` file is properly configured (see below)

## Environment Setup

The application requires AWS credentials for Bedrock access. Make sure your `.env` file contains:

```env
# AWS configuration for Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_SESSION_TOKEN=your_session_token  # if using temporary credentials
BEDROCK_MODEL_ID=your_bedrock_model_id
PORT=8000
```

## Quick Start

1. **Clone and navigate to the project directory**:
   ```bash
   cd here4beer
   ```

2. **Build and start all services**:
   ```bash
   docker-compose up --build
   ```

3. **Access the applications**:
   - **Frontend (Clotho)**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **Agent Service**: http://localhost:8002

## Service Architecture

The application consists of three main services:

### Frontend (Clotho)
- **Port**: 3000
- **Technology**: React + Vite + TypeScript
- **Description**: AI-powered supply chain optimizer interface

### Backend API
- **Port**: 8000
- **Technology**: FastAPI + Python
- **Description**: Main backend service with chat and analysis endpoints
- **Health Check**: http://localhost:8000/health

### Agent Service
- **Port**: 8002
- **Technology**: FastAPI + Python
- **Description**: Food provider agent API
- **Health Check**: http://localhost:8002/health

## Development Commands

### Start services in detached mode:
```bash
docker-compose up -d
```

### View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f backend
docker-compose logs -f agent-service
```

### Stop services:
```bash
docker-compose down
```

### Rebuild specific service:
```bash
docker-compose up --build frontend
```

### Remove all containers and volumes:
```bash
docker-compose down -v
```

## Health Monitoring

All services include health checks:
- **Frontend**: Checks if the web server responds on port 3000
- **Backend**: Checks `/health` endpoint
- **Agent Service**: Checks `/health` endpoint

Monitor service health with:
```bash
docker-compose ps
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: If ports 3000, 8000, or 8002 are in use, modify the port mappings in `docker-compose.yml`

2. **AWS credentials**: Ensure your AWS credentials are valid and have access to Bedrock

3. **Build failures**: Run `docker-compose down` and then `docker-compose up --build` to rebuild from scratch

4. **Database issues**: The backend uses SQLite. If you encounter database issues, remove the volume:
   ```bash
   docker-compose down -v
   docker-compose up --build
   ```

### Logs and Debugging

Check service-specific logs:
```bash
# Backend API logs
docker-compose logs backend

# Agent service logs
docker-compose logs agent-service

# Frontend logs
docker-compose logs frontend
```

### Manual Service Testing

Test individual services:
```bash
# Test backend health
curl http://localhost:8000/health

# Test agent service health
curl http://localhost:8002/health

# Test frontend
curl http://localhost:3000
```

## Production Considerations

For production deployment:

1. **Environment Security**: Move sensitive variables to proper secret management
2. **CORS**: Update CORS settings in the backend for specific origins
3. **Health Checks**: Monitor service health externally
4. **Scaling**: Consider using Docker Swarm or Kubernetes for scaling
5. **SSL/TLS**: Add reverse proxy with SSL termination

## Support

If you encounter issues:
1. Check the logs using `docker-compose logs`
2. Verify your `.env` configuration
3. Ensure Docker has sufficient resources allocated