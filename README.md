# Complytics - AI-Powered Security Compliance Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-18.2.0-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)

Complytics is a comprehensive AI-powered security compliance platform that helps organizations automate and streamline their compliance processes. The platform combines advanced AI capabilities with expert knowledge in various compliance frameworks to provide intelligent compliance assistance, document analysis, and automated compliance solutions.

## 🚀 Features

### Core Capabilities
- **AI-Powered Compliance Chat**: Intelligent chatbot with expertise in multiple compliance domains
- **Document Analysis**: Upload and analyze privacy policies, terms & conditions, and other compliance documents
- **Multi-Framework Support**: GDPR, CCPA, HIPAA, ISO 27001, SOC 2, NIST, PCI DSS, and more
- **Expert System**: Specialized AI experts for different compliance areas
- **Document Generation**: Automated generation of compliant privacy policies and terms & conditions
- **Real-time Compliance Assessment**: Instant analysis and scoring of compliance documents

### User Management & Access Control
- **Multi-Role System**: Superadmin, Admin, and Team Member roles
- **Secure Authentication**: JWT-based authentication with role-based access control
- **User Dashboard**: Personalized dashboards for different user types
- **Session Management**: Secure session handling with conversation history

### Advanced AI Features
- **Expert Selection**: Intelligent routing to domain-specific AI experts
- **Conversation Memory**: Context-aware conversations with historical context
- **Document Intent Analysis**: Smart understanding of user document-related queries
- **Progressive Responses**: Real-time streaming of AI responses
- **Query Classification**: Automatic detection of compliance vs non-compliance queries

## 🏗️ Architecture

### Frontend (React + Vite)
```
src/
├── components/
│   ├── auth/           # Authentication components
│   ├── layout/         # Layout components (Navbar, Footer)
│   ├── sections/       # Landing page sections
│   ├── superadmin/     # Superadmin dashboard components
│   ├── team/           # Team member components
│   └── ui/             # Reusable UI components
├── context/            # React context providers
├── lib/                # Utility libraries
└── routes.jsx          # Application routing
```

### Backend (FastAPI + Python)
```
Complytics Backend/
├── routes/             # API route handlers
│   ├── auth.py         # Authentication routes
│   ├── compliance.py   # Compliance API endpoints
│   ├── admin.py        # Admin management routes
│   ├── superadmin.py   # Superadmin routes
│   ├── team.py         # Team member routes
│   └── registration.py # User registration routes
├── schemas/            # Pydantic data models
├── utils/              # Utility functions
├── compliance_rag.py   # Core AI compliance engine
├── database.py         # Database configuration
└── app.py             # FastAPI application
```

### AI Engine Features
- **RAG (Retrieval-Augmented Generation)**: Advanced document retrieval and generation
- **FAISS Indexing**: High-performance vector similarity search
- **Multi-Expert System**: Domain-specific AI experts for different compliance areas
- **Rate Limiting**: Optimized API usage with intelligent rate limiting
- **Caching System**: Multi-level caching for improved performance

## 🛠️ Technology Stack

### Frontend
- **React 18.2.0**: Modern React with hooks and functional components
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework
- **Material-UI**: React component library
- **Framer Motion**: Animation library
- **React Router**: Client-side routing
- **Axios**: HTTP client for API calls

### Backend
- **FastAPI**: Modern Python web framework
- **MongoDB**: NoSQL database with Motor async driver
- **JWT**: JSON Web Tokens for authentication
- **Pydantic**: Data validation and settings management
- **Uvicorn**: ASGI server

### AI & ML
- **Google Gemini AI**: Advanced language model for compliance analysis
- **Sentence Transformers**: Text embedding generation
- **FAISS**: Vector similarity search and indexing
- **NumPy & SciPy**: Numerical computing
- **Scikit-learn**: Machine learning utilities

### Document Processing
- **PyPDF2 & pdfplumber**: PDF text extraction
- **python-docx**: Microsoft Word document processing
- **OCR Support**: Text extraction from scanned documents

## 📦 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Node.js 16 or higher
- MongoDB instance
- Google Gemini API key

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "complytics-landing with admin New"
   ```

2. **Set up Python environment**
   ```bash
   cd "Complytics Backend"
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file in the `Complytics Backend` directory:
   ```env
   MONGODB_URL=mongodb://localhost:27017
   MONGODB_NAME=complytics
   SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_FROM_EMAIL=your-email@gmail.com
   GOOGLE_API_KEY=your-gemini-api-key
   ```

4. **Start the backend server**
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd ..  # Back to project root
   npm install
   ```

2. **Start the development server**
   ```bash
   npm run dev
   ```

3. **Build for production**
   ```bash
   npm run build
   ```

## 🚀 Usage

### Getting Started

1. **Access the Application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

2. **User Registration & Authentication**
   - Register as a new user through the registration form
   - Login with your credentials
   - Access role-specific dashboards based on your permissions

3. **Compliance Chat**
   - Navigate to the team dashboard
   - Use the AI-powered compliance chat for questions about:
     - GDPR, CCPA, HIPAA compliance
     - Security frameworks (ISO 27001, SOC 2, NIST)
     - Privacy policy requirements
     - Audit procedures and controls

4. **Document Analysis**
   - Upload privacy policies, terms & conditions, or other compliance documents
   - Get instant compliance analysis and scoring
   - Receive improvement suggestions and recommendations

5. **Document Generation**
   - Generate compliant privacy policies based on specific frameworks
   - Create terms & conditions documents
   - Download generated documents in PDF or DOCX format

### API Endpoints

#### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/forgot-password` - Password reset

#### Compliance
- `POST /api/compliance/chat` - AI compliance chat
- `POST /api/compliance/upload` - Document upload and analysis
- `POST /api/compliance/generate` - Document generation
- `GET /api/compliance/download/{filename}` - Document download

#### Admin Management
- `GET /admin/users` - List all users
- `PUT /admin/users/{user_id}` - Update user roles
- `DELETE /admin/users/{user_id}` - Delete users

## 🔧 Configuration

### AI Model Configuration
The platform uses Google Gemini AI for advanced compliance analysis. Configure the model in `compliance_rag.py`:

```python
# Model configuration
generation_config = {
    "temperature": 0.1,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 3200,
}

# Rate limiting
CALLS_PER_MINUTE = 40
DELAY_BETWEEN_CALLS = 1.5
```

### Expert System Configuration
The platform includes specialized AI experts for different compliance domains:

- **Security Controls Expert**: Azure AD, identity management, cybersecurity
- **Privacy Regulations Expert**: GDPR, CCPA, data protection
- **Audit Compliance Expert**: ISO 27001, SOC 2, NIST frameworks
- **Financial Compliance Expert**: PCI DSS, SOX, banking regulations
- **Healthcare Compliance Expert**: HIPAA, medical device regulations
- **International Compliance Expert**: Cross-border data transfers
- **Operational Compliance Expert**: Business processes, vendor management

## 📊 Performance Optimization

### Caching Strategy
- **Query Cache**: Caches AI responses for similar queries
- **Embedding Cache**: Stores document embeddings for fast retrieval
- **FAISS Index**: Optimized vector search for document similarity

### Rate Limiting
- Intelligent rate limiting to prevent API quota exhaustion
- Exponential backoff for retry attempts
- Request queuing for high-traffic scenarios

### Database Optimization
- Indexed queries for user management
- Efficient document storage and retrieval
- Session management optimization

## 🔒 Security Features

### Authentication & Authorization
- JWT-based authentication with secure token handling
- Role-based access control (RBAC)
- Password hashing with bcrypt
- Session management with automatic expiration

### Data Protection
- Input validation and sanitization
- CORS configuration for secure cross-origin requests
- Environment variable management for sensitive data
- Secure file upload handling

### API Security
- Rate limiting to prevent abuse
- Request validation with Pydantic models
- Error handling without sensitive information exposure
- Secure headers and CORS policies

## 🧪 Testing

### Backend Testing
```bash
cd "Complytics Backend"
python -m pytest tests/
```

### Frontend Testing
```bash
npm test
```

### API Testing
Use the interactive API documentation at http://localhost:8000/docs for testing endpoints.

## 📈 Monitoring & Logging

### Logging Configuration
The application includes comprehensive logging for:
- API requests and responses
- AI model interactions
- Database operations
- Error tracking and debugging

### Performance Monitoring
- Response time tracking
- Cache hit/miss ratios
- API usage statistics
- Error rate monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use ESLint and Prettier for JavaScript/React code
- Write comprehensive tests for new features
- Update documentation for API changes

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- API Documentation: http://localhost:8000/docs
- Interactive API Explorer: http://localhost:8000/docs

### Common Issues
1. **MongoDB Connection**: Ensure MongoDB is running and accessible
2. **API Key Issues**: Verify Google Gemini API key is valid and has sufficient quota
3. **CORS Errors**: Check CORS configuration in backend settings
4. **File Upload Issues**: Verify file size limits and supported formats

### Getting Help
- Check the API documentation for endpoint details
- Review the logs for error messages
- Ensure all environment variables are properly configured
- Verify all dependencies are installed correctly

## 🚀 Deployment

### Production Deployment
1. Set up a production MongoDB instance
2. Configure environment variables for production
3. Set up a reverse proxy (nginx) for the backend
4. Build and deploy the frontend to a static hosting service
5. Configure SSL certificates for HTTPS
6. Set up monitoring and logging for production

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d
```

## 📊 Roadmap

### Planned Features
- [ ] Advanced compliance reporting and analytics
- [ ] Integration with popular compliance tools
- [ ] Automated compliance monitoring and alerts
- [ ] Multi-language support
- [ ] Mobile application
- [ ] Advanced document comparison tools
- [ ] Compliance audit trail and history
- [ ] Real-time compliance scoring dashboard

### Performance Improvements
- [ ] Enhanced caching strategies
- [ ] Database query optimization
- [ ] AI model fine-tuning
- [ ] Advanced rate limiting algorithms

---

**Complytics** - Making Security Compliance Simple and Intelligent 🛡️✨