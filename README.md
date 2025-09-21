# 🍺 Here4Beer - AI-Powered Food Supply Chain Optimizer

AI-driven demand forecasting and supply chain optimization for food producers, starting with breweries and food factories.

You can access the application by: http://here4beer-frontend.s3-website.eu-west-3.amazonaws.com

## 🚀 Problem & Solution

### The Problem

Food producers face critical challenges in supply chain management:

- **Overproduction** → Spoilage, waste, and increased costs
- **Underproduction** → Shortages, missed sales opportunities
- **Manual planning** → Time-consuming, error-prone forecasting
- **Poor inventory visibility** → Inefficient raw material ordering
- **Risk blindness** → Lack of early warning systems for supply issues

### Our Solution

Here4Beer provides an intelligent AI assistant that transforms simple data uploads into actionable supply chain insights:

📊 **Smart Data Analysis** - Upload CSV files (sales history, inventory, recipes) for instant AI processing
📈 **Demand Forecasting** - Predict future demand for each product using advanced LLM reasoning
🏭 **Production Planning** - Generate optimized weekly production schedules
🛒 **Procurement Intelligence** - Automated raw material ordering recommendations
⚠️ **Risk Monitoring** - Early alerts for spoilage, shortages, and overstock scenarios
💬 **Natural Language Insights** - Human-friendly summaries for decision makers

## 🏗️ Architecture

The application consists of three core services:

- **Frontend (Clotho)** - React-based dashboard for data visualization and interaction
- **Backend API** - FastAPI service handling data processing and analysis
- **Agent Service** - Specialized AI agent for food industry insights

## ✨ Key Features

- **CSV Data Processing** - Upload and analyze sales history, inventory, and recipe data
- **AI-Powered Forecasting** - Leverage Amazon Bedrock LLMs for demand prediction
- **Provider Database** - Comprehensive food supplier search and management
- **Email Integration** - Parse order emails and generate professional responses
- **Real-time Analytics** - Interactive dashboards with charts and alerts
- **Multi-Service Architecture** - Scalable microservices design

## 🔮 Future Integrations

### Gmail MCP Integration

Integration of Gmail MCP (Model Context Protocol) with the agent service to enable:

- **Direct Email Access** - Connect directly to Gmail accounts for order processing
- **Automated Email Parsing** - Real-time parsing of incoming supplier and customer emails
- **Smart Email Responses** - AI-generated responses based on order context and provider database
- **Email-Driven Workflows** - Trigger forecasting and procurement based on email orders

**Implementation Path**: Integrate Gmail MCP with `agent-service/app/services/agent_class.py` to extend the existing email parsing tools with live Gmail connectivity.

### CSV Upload API Enhancement

Development of a dedicated API endpoint for direct CSV database integration:

- **Bulk Data Import** - Direct upload of supplier and inventory CSV files to the provider database
- **Data Validation** - Automated schema validation and error reporting
- **Real-time Updates** - Live database updates as new supplier data becomes available
- **Batch Processing** - Handle large CSV files with progress tracking

**Implementation Path**: Create new FastAPI endpoints in the backend service for CSV processing and database integration, extending the current provider database functionality.

### AI Agent Routing Implementation

Development of an intelligent routing system to seamlessly switch between forecasting and provider services:

- **Intent Classification** - Automatically classify user queries to determine optimal service routing
- **Smart Query Distribution** - Route forecasting requests to `backend/app/services/bedrock.py` and provider queries to `agent-service/app/services/agent_class.py`
- **Hybrid Workflows** - Handle complex queries requiring both forecasting and provider data through multi-step orchestration
- **Context Preservation** - Maintain conversation history and context across different AI services
- **Performance Optimization** - Implement caching layer for frequently accessed provider data

**Implementation Path**: Create `AgentRouter` class in backend service with lightweight LLM-based intent classification, HTTP client integration for agent service communication, and unified endpoint for seamless user experience.

### Additional Planned Features

- **Multi-tenant Support** - Separate environments for different food producers
- **Advanced Analytics** - Seasonal forecasting and trend analysis
- **Mobile App** - On-the-go access for supply chain managers
- **Third-party Integrations** - ERP, inventory management, and accounting system connections

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- AWS credentials for Bedrock access

### Run the Application

```bash
# Clone the repository
git clone <repository-url>
cd here4beer

# Start all services
docker-compose up --build
```

### Access the Application

- **Frontend**: http://localhost:3000 (or for juries: http://here4beer-frontend.s3-website.eu-west-3.amazonaws.com)
- **Backend API**: http://localhost:8000
- **Agent Service**: http://localhost:8002

### Test the System

1. Upload your CSV files (sales history, inventory, recipes)
2. Request demand forecasts through the chat interface
3. Review generated production plans and procurement recommendations
4. Monitor risk alerts and optimization suggestions

For detailed setup instructions, see [RUN.md](RUN.md)
