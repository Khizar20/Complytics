from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import database
from routes import auth_router, superadmin_router, admin_router
from routes.team import router as team_router
from config import settings
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBearer
from routes.registration import router as registration_router
from routes.compliance import router as compliance_router
from flask import request, jsonify, send_file


app = FastAPI(docs_url=None, redoc_url=None)
security = HTTPBearer()

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="API Docs",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "docExpansion": "none",
            "tryItOutEnabled": True,
        },
        oauth2_redirect_url=None
    )
    
# CORS setup
origins = [
    "http://localhost:5173",  # React development server
    "http://localhost:3000",  # Alternative React port
    "http://127.0.0.1:5173",  # Alternative localhost format
    "http://127.0.0.1:3000",  # Alternative localhost format
    "http://localhost:5174",  # Additional React port
    "http://127.0.0.1:5174",  # Additional localhost format
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(superadmin_router, prefix="/superadmin", tags=["superadmin"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(registration_router, prefix="/registration", tags=["registration"])
app.include_router(team_router, prefix="/team", tags=["team"])
app.include_router(compliance_router, prefix="/api/compliance", tags=["compliance"])


@app.on_event("startup")
async def startup_db():
    await database.connect()

@app.on_event("shutdown")
async def shutdown_db():
    await database.disconnect()

@app.route('/api/generate/privacy-policy', methods=['POST'])
def generate_privacy_policy():
    try:
        data = request.get_json()
        framework = data.get('framework', 'HIPAA')
        format = data.get('format', 'docx')
        answers = data.get('answers', {})
        
        # If no answers provided, return comprehensive guide
        if not answers:
            guide = get_document_generation_questions('privacy', framework)
            return jsonify({
                'status': 'guide_provided',
                'message': 'Here is a comprehensive guide to help you create your privacy policy',
                'guide': {
                    'steps': guide['steps'],
                    'categories': guide['categories'],
                    'pitfalls': guide['pitfalls'],
                    'best_practices': guide['best_practices']
                }
            })
        
        # Generate document with answers
        result = generate_document_with_answers('privacy', framework, answers, format)
        
        if result.startswith('Document generated and saved as'):
            filename = result.split('as ')[1]
            return jsonify({
                'status': 'success',
                'message': 'Privacy policy generated successfully',
                'filename': filename,
                'download_url': f'/api/download/{filename}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/generate/terms-conditions', methods=['POST'])
def generate_terms_conditions():
    try:
        data = request.get_json()
        framework = data.get('framework', 'HIPAA')
        format = data.get('format', 'docx')
        answers = data.get('answers', {})
        
        # If no answers provided, return comprehensive guide
        if not answers:
            guide = get_document_generation_questions('terms', framework)
            return jsonify({
                'status': 'guide_provided',
                'message': 'Here is a comprehensive guide to help you create your terms and conditions',
                'guide': {
                    'steps': guide['steps'],
                    'categories': guide['categories'],
                    'pitfalls': guide['pitfalls'],
                    'best_practices': guide['best_practices']
                }
            })
        
        # Generate document with answers
        result = generate_document_with_answers('terms', framework, answers, format)
        
        if result.startswith('Document generated and saved as'):
            filename = result.split('as ')[1]
            return jsonify({
                'status': 'success',
                'message': 'Terms and conditions generated successfully',
                'filename': filename,
                'download_url': f'/api/download/{filename}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })