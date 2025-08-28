"""Production API for RAG System with FastAPI"""

from fastapi import FastAPI, HTTPException, Depends, status, Request, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import logging
import os
import hashlib
from pathlib import Path
import sys
import tempfile
import shutil
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import RAGConfig
from src.security import SecurityManager, Token
from src.enhanced_retriever import EnhancedRetriever
from src.optimized_retriever import HybridRetriever
from src.document_processor import DocumentProcessor
from src.audit_logger import AuditLogger, audit_endpoint
from src.feedback_trainer import RAGTrainer, ResponseImprover

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

# Choose retriever based on configuration
use_optimized = os.getenv('USE_OPTIMIZED_RETRIEVER', 'false').lower() == 'true'
if use_optimized:
    retriever = HybridRetriever(config)
    logger.info("Using optimized hybrid retriever")
else:
    retriever = EnhancedRetriever(config)
    logger.info("Using standard enhanced retriever")

document_processor = DocumentProcessor(config)
audit_logger = AuditLogger(config)
rag_trainer = RAGTrainer(config)
response_improver = ResponseImprover(config)

# Store audit logger in app state
app.state.audit_logger = audit_logger

# Initialize FastAPI app with local Swagger UI
app = FastAPI(
    title="Enhanced RAG System API",
    description="Production-ready Retrieval-Augmented Generation System",
    version="1.0.0",
    docs_url=None,  # We'll create custom docs endpoint
    redoc_url="/api/redoc"
)

# Mount static files for Swagger UI if directory exists
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup CORS with secure origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,  # Configured from environment
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
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
    use_expansion: bool = Field(default=True, description="Use query expansion for better results")
    use_cache: bool = Field(default=True, description="Use response caching")

class QueryResponse(BaseModel):
    query: str
    results: List[Dict]
    timestamp: datetime
    processing_time: float
    feedback_id: Optional[str] = None  # For tracking feedback
    response_improved: bool = False    # Whether response was improved

class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    message: str
    document_id: Optional[str] = None

class FeedbackRequest(BaseModel):
    query: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback: str = Field(..., min_length=1, description="User feedback text")
    expected_response: Optional[str] = Field(None, description="What the response should have been")
    helpful_results: Optional[List[str]] = Field(default_factory=list)

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
    health_data = {
        "status": "healthy", 
        "timestamp": datetime.utcnow(),
        "retriever_type": "optimized" if hasattr(retriever, 'get_metrics') else "standard"
    }
    
    # Add cache status if available
    if hasattr(retriever, 'get_metrics'):
        metrics = retriever.get_metrics()
        health_data["cache_status"] = "connected" if metrics.get('redis_connected') else "disconnected"
    
    return health_data

# Root endpoint - Welcome page
@app.get("/")
async def root():
    """API Welcome Page"""
    return {
        "message": "Enhanced RAG System API",
        "version": "1.0.0",
        "description": "Production-ready Retrieval-Augmented Generation System",
        "endpoints": {
            "documentation": {
                "swagger": "/api/docs",
                "redoc": "/api/redoc"
            },
            "health": "/health",
            "authentication": "/api/auth/login",
            "query": "/api/query"
        },
        "timestamp": datetime.utcnow()
    }

# Custom Swagger UI with local assets
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui():
    # Check if we have local swagger assets
    if Path("static/swagger/swagger-ui.css").exists():
        # Use local assets
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link type="text/css" rel="stylesheet" href="/static/swagger/swagger-ui.css">
                <title>{app.title} - Swagger UI</title>
            </head>
            <body>
                <div id="swagger-ui"></div>
                <script src="/static/swagger/swagger-ui-bundle.js"></script>
                <script src="/static/swagger/swagger-ui-standalone-preset.js"></script>
                <script>
                window.onload = function() {{
                    window.ui = SwaggerUIBundle({{
                        url: '/openapi.json',
                        dom_id: '#swagger-ui',
                        deepLinking: true,
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIStandalonePreset
                        ],
                        plugins: [
                            SwaggerUIBundle.plugins.DownloadUrl
                        ],
                        layout: "StandaloneLayout"
                    }})
                }}
                </script>
            </body>
            </html>
            """,
            status_code=200
        )
    else:
        # Fallback to CDN
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
                <title>{app.title} - Swagger UI</title>
            </head>
            <body>
                <div id="swagger-ui"></div>
                <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js" crossorigin></script>
                <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js" crossorigin></script>
                <script>
                window.onload = function() {{
                    window.ui = SwaggerUIBundle({{
                        url: '/openapi.json',
                        dom_id: '#swagger-ui',
                        deepLinking: true,
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIStandalonePreset
                        ],
                        plugins: [
                            SwaggerUIBundle.plugins.DownloadUrl
                        ],
                        layout: "StandaloneLayout"
                    }})
                }}
                </script>
            </body>
            </html>
            """,
            status_code=200
        )

# Authentication endpoints
@app.post("/api/auth/login", response_model=Token)
async def login(request_data: LoginRequest, request: Request):
    user_ip = request.client.host
    user_agent = request.headers.get('user-agent', 'Unknown')
    
    user = security_manager.authenticate_user(request_data.username, request_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {request_data.username}")
        audit_logger.log_authentication(
            username=request_data.username,
            success=False,
            request_ip=user_ip,
            user_agent=user_agent,
            reason="Invalid credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Check if password needs to be changed
    if security_manager.check_password_age(request_data.username):
        logger.info(f"User {request_data.username} needs to change password")
        # In production, you might want to return a special response here
    
    access_token = security_manager.create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    refresh_token = security_manager.create_refresh_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    
    # Log successful authentication
    audit_logger.log_authentication(
        username=request_data.username,
        success=True,
        request_ip=user_ip,
        user_agent=user_agent
    )
    
    logger.info(f"Successful login for user: {request_data.username}")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": config.token_expire_hours * 3600
    }

# Token refresh endpoint
@app.post("/api/auth/refresh")
async def refresh_token(refresh_token: str = Form(...)):
    """Refresh access token using refresh token"""
    result = security_manager.refresh_access_token(refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    return result

# Logout endpoint
@app.post("/api/auth/logout")
async def logout(current_user = Depends(get_current_user)):
    """Logout user and invalidate refresh tokens"""
    security_manager.invalidate_refresh_tokens(current_user.username)
    logger.info(f"User {current_user.username} logged out")
    return {"message": "Successfully logged out"}

# Get current user info endpoint
@app.get("/api/auth/me")
async def get_me(current_user = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "is_active": True  # Default to true for authenticated users
    }

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
        
        # Perform query with role-based filtering and optimizations
        if hasattr(retriever, 'query_with_expansion'):  # Optimized retriever
            results = await retriever.query(
                query=query_request.query,
                max_results=query_request.max_results,
                user_role=role,
                use_expansion=query_request.use_expansion,
                use_cache=query_request.use_cache
            )
        else:  # Standard retriever
            results = await retriever.query(
                query=query_request.query,
                max_results=query_request.max_results,
                user_role=role,
                filters=query_request.filters
            )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log document query
        audit_logger.log_document_access(
            username=current_user.username,
            document_id="query",
            action="query",
            request_ip=request.client.host,
            user_agent=request.headers.get('user-agent', 'Unknown'),
            metadata={"query": query_request.query, "results_count": len(results)}
        )
        
        logger.info(f"Query processed for user {current_user.username}: '{query_request.query}'")
        
        # Attempt to improve response if we have training data
        response_improved = False
        
        if results and len(results) > 0 and results[0].get('metadata', {}).get('type') == 'generated':
            original_content = results[0]['content']
            improved_content, improvement_score = response_improver.improve_response(
                query_request.query, original_content
            )
            
            if improvement_score > 0.8:  # High confidence improvement
                results[0]['content'] = improved_content
                results[0]['metadata']['improved'] = True
                results[0]['metadata']['improvement_score'] = improvement_score
                response_improved = True
                logger.info(f"Response improved with {improvement_score:.2f} confidence")
        
        # Generate feedback ID for tracking
        feedback_id = hashlib.md5(
            f"{query_request.query}:{datetime.utcnow().isoformat()}:{current_user.username}".encode()
        ).hexdigest()[:12]
        
        return QueryResponse(
            query=query_request.query,
            results=results,
            timestamp=datetime.utcnow(),
            processing_time=processing_time,
            feedback_id=feedback_id,
            response_improved=response_improved
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
        result = document_processor.process_document(file_path)
        
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

# Document upload endpoint with file upload (admin only)
@app.post("/api/documents/upload-file", response_model=DocumentUploadResponse)
async def upload_document_file(
    current_user = Depends(get_current_user),
    file: UploadFile = File(..., description="Document file to upload"),
    category: str = Form(default="service", description="Document category")
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can upload documents"
        )
    
    # Validate file size
    if file.size > config.get_max_file_size_bytes():
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file.size / (1024*1024):.1f}MB) exceeds maximum allowed size ({config.max_file_size_mb}MB)"
        )
    
    # Validate file type
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in config.allowed_file_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not supported. Allowed: {', '.join(config.allowed_file_extensions)}"
        )
    
    # Validate file content (basic magic number check)
    await file.seek(0)
    file_header = await file.read(1024)
    await file.seek(0)
    
    # Basic file type validation based on magic numbers
    if not _validate_file_content(file_header, file_extension):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match the file extension"
        )
    
    # Save uploaded file to temporary location
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            temp_file = tmp.name
            shutil.copyfileobj(file.file, tmp)
        
        # Process the document
        result = document_processor.process_document(temp_file, category)
        
        return DocumentUploadResponse(
            filename=file.filename,
            status="success",
            message="Document processed successfully",
            document_id=result.get("document_id")
        )
    
    except Exception as e:
        logger.error(f"Error processing uploaded document: {e}")
        return DocumentUploadResponse(
            filename=file.filename,
            status="error",
            message=str(e)
        )
    
    finally:
        # Clean up temporary file
        if temp_file and Path(temp_file).exists():
            try:
                Path(temp_file).unlink()
            except Exception:
                pass

def _validate_file_content(file_header: bytes, extension: str) -> bool:
    """Validate file content matches extension using magic numbers"""
    magic_numbers = {
        '.pdf': [b'%PDF'],
        '.png': [b'\x89PNG\x0d\x0a\x1a\x0a'],
        '.jpg': [b'\xff\xd8\xff'],
        '.jpeg': [b'\xff\xd8\xff'],
        '.docx': [b'PK\x03\x04'],  # ZIP-based formats
        '.xlsx': [b'PK\x03\x04'],
        '.doc': [b'\xd0\xcf\x11\xe0'],  # OLE format
        '.xls': [b'\xd0\xcf\x11\xe0']
    }
    
    # For text files, just check they're valid UTF-8 or ASCII
    if extension in ['.txt', '.md']:
        try:
            file_header.decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False
    
    # Check magic numbers for binary files
    if extension in magic_numbers:
        return any(file_header.startswith(magic) for magic in magic_numbers[extension])
    
    return True  # Allow unknown extensions to pass

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

# Performance metrics endpoint (admin only)
@app.get("/api/metrics/retriever")
async def get_retriever_metrics(current_user = Depends(get_current_user)):
    """Get retriever performance metrics"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view metrics"
        )
    
    if hasattr(retriever, 'get_metrics'):
        return retriever.get_metrics()
    else:
        return {"message": "Metrics not available for current retriever"}

# Feedback collection endpoint
@app.post("/api/feedback")
async def submit_feedback(
    feedback_request: FeedbackRequest,
    current_user = Depends(get_current_user)
):
    """Submit feedback for query-response pairs to improve the system"""
    
    try:
        feedback_id = rag_trainer.collect_feedback(
            query=feedback_request.query,
            response=feedback_request.response,
            rating=feedback_request.rating,
            feedback=feedback_request.feedback,
            expected_response=feedback_request.expected_response,
            helpful_results=feedback_request.helpful_results,
            user_role=current_user.role
        )
        
        if feedback_id:
            # Log feedback collection
            audit_logger.log_admin_action(
                username=current_user.username,
                action="submit_feedback",
                target="training_system",
                request_ip=request.client.host,
                user_agent=request.headers.get('user-agent', 'Unknown'),
                details={
                    "feedback_id": feedback_id,
                    "rating": feedback_request.rating,
                    "has_expected_response": bool(feedback_request.expected_response)
                }
            )
            
            return {
                "message": "Feedback submitted successfully",
                "feedback_id": feedback_id,
                "status": "success"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store feedback"
            )
            
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing feedback"
        )

# Training management endpoints (admin only)
@app.post("/api/training/process-feedback")
async def process_training_feedback(
    request: Request,
    current_user = Depends(get_current_user)
):
    """Process unprocessed feedback into training data"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can manage training"
        )
    
    try:
        processed_count = rag_trainer.process_feedback_to_training_data()
        
        # Log training action
        audit_logger.log_admin_action(
            username=current_user.username,
            action="process_feedback",
            target="training_system",
            request_ip=request.client.host,
            user_agent=request.headers.get('user-agent', 'Unknown'),
            details={"processed_entries": processed_count}
        )
        
        return {
            "message": f"Processed {processed_count} feedback entries",
            "processed_count": processed_count,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Training processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing training data"
        )

@app.get("/api/training/stats")
async def get_training_stats(
    current_user = Depends(get_current_user)
):
    """Get training system statistics"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view training stats"
        )
    
    try:
        stats = rag_trainer.get_training_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Training stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving training stats"
        )

@app.post("/api/training/export")
async def export_training_data(
    request: Request,
    format: str = "jsonl",
    min_quality: float = 3.0,
    current_user = Depends(get_current_user)
):
    """Export training data for external fine-tuning"""
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can export training data"
        )
    
    try:
        output_file = rag_trainer.export_training_data(
            format=format,
            min_quality=min_quality
        )
        
        # Log export action
        audit_logger.log_admin_action(
            username=current_user.username,
            action="export_training_data",
            target="training_system",
            request_ip=request.client.host,
            user_agent=request.headers.get('user-agent', 'Unknown'),
            details={
                "format": format,
                "min_quality": min_quality,
                "output_file": output_file
            }
        )
        
        return {
            "message": "Training data exported successfully",
            "output_file": output_file,
            "format": format,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Training export error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while exporting training data"
        )

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