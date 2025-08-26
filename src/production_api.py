"""Production API for RAG System with FastAPI"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import logging
from pathlib import Path
import sys
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.security import SecurityManager, Token
from src.enhanced_retriever import EnhancedRetriever
from src.document_processor import DocumentProcessor

# Setup logging
log_handlers = [logging.StreamHandler()]  # Always include console handler

# Try to set up file logging
try:
    log_dir = Path('/data/logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'api.log'
    log_handlers.append(logging.FileHandler(str(log_file)))
except (PermissionError, OSError) as e:
    print(f"Warning: Unable to create log file: {e}")
    print("Continuing with console-only logging")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Initialize configuration
config = RAGConfig()

# Initialize components
security_manager = SecurityManager(config)
retriever = EnhancedRetriever(config)
document_processor = DocumentProcessor(config)

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced RAG System API",
    description="Production-ready Retrieval-Augmented Generation System",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security scheme
security = HTTPBearer()

# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    max_results: int = Field(default=5, ge=1, le=20)
    filters: Optional[Dict] = None

class QueryResponse(BaseModel):
    query: str
    results: List[Dict]
    timestamp: datetime
    processing_time: float

class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    message: str
    document_id: Optional[str] = None

# Dependency to verify token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_data = security_manager.verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Authentication endpoints
@app.post("/api/auth/login", response_model=Token)
async def login(request: LoginRequest):
    user = security_manager.authenticate_user(request.username, request.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Check if password needs to be changed
    if security_manager.check_password_age(request.username):
        logger.info(f"User {request.username} needs to change password")
        # In production, you might want to return a special response here
    
    access_token = security_manager.create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    
    logger.info(f"Successful login for user: {request.username}")
    return {"access_token": access_token, "token_type": "bearer"}

# Query endpoint with rate limiting
@app.post("/api/query", response_model=QueryResponse)
@limiter.limit("5/minute")  # Default rate limit
async def query_documents(
    request: Request,
    query_request: QueryRequest,
    current_user = Depends(get_current_user)
):
    start_time = datetime.utcnow()
    
    try:
        # Apply role-based rate limits
        role = current_user.role
        rate_limit = config.rate_limits.get(role, 5)
        
        # Perform query with role-based filtering
        results = await retriever.query(
            query=query_request.query,
            max_results=query_request.max_results,
            user_role=role,
            filters=query_request.filters
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Query processed for user {current_user.username}: '{query_request.query}'")
        
        return QueryResponse(
            query=query_request.query,
            results=results,
            timestamp=datetime.utcnow(),
            processing_time=processing_time
        )
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing query"
        )

# Document upload endpoint (admin only)
@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file_path: str,
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can upload documents"
        )
    
    try:
        result = await document_processor.process_document(file_path)
        
        return DocumentUploadResponse(
            filename=Path(file_path).name,
            status="success",
            message="Document processed successfully",
            document_id=result.get("document_id")
        )
    
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return DocumentUploadResponse(
            filename=Path(file_path).name,
            status="error",
            message=str(e)
        )

# User profile endpoint
@app.get("/api/user/profile")
async def get_user_profile(current_user = Depends(get_current_user)):
    user = security_manager.get_user(current_user.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove sensitive information
    profile = {
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "full_name": user.get("full_name"),
        "created_at": user["created_at"],
        "last_login": user.get("last_login")
    }
    
    return profile

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting RAG System API...")
    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        workers=config.api_workers,
        log_level="info"
    )