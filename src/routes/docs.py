"""
Documentation routes with access control.

This module provides routes for API documentation with authentication
and authorization support for production environments.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from src.config import settings, is_production, is_development
from src.config.documentation import (
    verify_docs_access,
    get_custom_openapi_schema,
    get_swagger_ui_oauth2_redirect_url,
    get_swagger_ui_init_oauth,
)


# Create documentation router
router = APIRouter(
    prefix="",
    tags=["documentation"],
    include_in_schema=False,  # Don't include docs routes in the schema
)


@router.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def custom_swagger_ui_html(
    request: Request,
    authorized: bool = Depends(verify_docs_access)
) -> HTMLResponse:
    """
    Custom Swagger UI with comprehensive features and authentication support.

    This endpoint provides an enhanced Swagger UI interface with:
    - Interactive API testing
    - Authentication support (JWT, API Key, OAuth2)
    - Request/response examples
    - Comprehensive error documentation
    - Rate limiting information

    Args:
        request: FastAPI request object
        authorized: Authorization check result

    Returns:
        HTML response with enhanced Swagger UI
    """
    # Get OAuth2 configuration
    oauth2_redirect_url = get_swagger_ui_oauth2_redirect_url()
    init_oauth = get_swagger_ui_init_oauth()

    # Comprehensive Swagger UI parameters
    swagger_ui_parameters = {
        # Navigation and display
        "deepLinking": True,
        "displayRequestDuration": True,
        "docExpansion": "list" if is_development() else "none",
        "operationsSorter": "method",
        "tagsSorter": "alpha",
        "filter": True,
        "showExtensions": not is_production(),
        "showCommonExtensions": not is_production(),

        # Interaction features
        "tryItOutEnabled": True,
        "supportedSubmitMethods": ["get", "post", "put", "delete", "patch", "head", "options"],

        # Authentication
        "persistAuthorization": True,
        "oauth2RedirectUrl": oauth2_redirect_url,

        # Validation and security
        "validatorUrl": None,  # Disable validator for security
        "syntaxHighlight": {
            "activated": True,
            "theme": "agate"
        },

        # UI customization
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "displayOperationId": is_development(),
        "showMutatedRequest": is_development(),

        # Performance
        "maxDisplayedTags": 50,
        "showRequestHeaders": True,
        "showResponseHeaders": True,

        # Custom styling
        "customCss": """
            .swagger-ui .topbar { display: none; }
            .swagger-ui .info { margin: 20px 0; }
            .swagger-ui .info .title { color: #3b4151; }
            .swagger-ui .scheme-container { background: #f7f7f7; padding: 15px; margin: 20px 0; border-radius: 4px; }
            .swagger-ui .auth-wrapper { margin: 20px 0; }
            .swagger-ui .errors-wrapper { margin: 20px 0; }
            .swagger-ui .response-col_status { font-weight: bold; }
            .swagger-ui .response.highlighted { background: rgba(61, 142, 185, 0.1); }
        """
    }

    # Create custom HTML with proper JavaScript function handling
    import json

    # Remove customCss from parameters since we'll handle it separately
    swagger_params_clean = {k: v for k, v in swagger_ui_parameters.items() if k != 'customCss'}
    swagger_params_json = json.dumps(swagger_params_clean)
    custom_css = swagger_ui_parameters.get('customCss', '')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css">
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
        <title>{getattr(settings, 'app_name', 'Production API Framework')} - Interactive Documentation</title>
        <style>
            {custom_css}
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script>
            const ui = SwaggerUIBundle({{
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                layout: 'BaseLayout',
                ...{swagger_params_json},
                requestInterceptor: (req) => {{
                    req.headers['X-Requested-With'] = 'SwaggerUI';
                    return req;
                }},
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ]
            }});

            {f"ui.initOAuth({json.dumps(init_oauth)});" if init_oauth else ""}
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
async def custom_redoc_html(
    request: Request,
    authorized: bool = Depends(verify_docs_access)
) -> HTMLResponse:
    """
    Custom ReDoc documentation with comprehensive features and authentication support.

    This endpoint provides an enhanced ReDoc interface with:
    - Clean, professional documentation layout
    - Comprehensive API reference
    - Interactive examples
    - Authentication documentation
    - Error handling guidelines

    Args:
        request: FastAPI request object
        authorized: Authorization check result

    Returns:
        HTML response with enhanced ReDoc
    """
    # Custom ReDoc options for enhanced documentation
    redoc_options = {
        "theme": {
            "colors": {
                "primary": {
                    "main": "#3b4151"
                }
            },
            "typography": {
                "fontSize": "14px",
                "lineHeight": "1.5em",
                "code": {
                    "fontSize": "13px"
                },
                "headings": {
                    "fontFamily": "Montserrat, sans-serif",
                    "fontWeight": "600"
                }
            },
            "sidebar": {
                "backgroundColor": "#fafafa",
                "width": "300px"
            },
            "rightPanel": {
                "backgroundColor": "#263238",
                "width": "40%"
            }
        },
        "scrollYOffset": 0,
        "hideDownloadButton": is_production(),
        "disableSearch": False,
        "expandResponses": "200,201",
        "jsonSampleExpandLevel": 2,
        "hideSingleRequestSampleTab": True,
        "menuToggle": True,
        "nativeScrollbars": False,
        "pathInMiddlePanel": True,
        "requiredPropsFirst": True,
        "sortPropsAlphabetically": True,
        "showExtensions": not is_production(),
        "hideHostname": False,
        "expandDefaultServerVariables": True,
        "maxDisplayedEnumValues": 10,
        "ignoreNamedSchemas": [],
        "hideSchemaPattern": False,
        "generatedPayloadSamplesMaxDepth": 3,
        "nativeScrollbars": True
    }

    # Create custom HTML with ReDoc options
    import json
    redoc_options_json = json.dumps(redoc_options)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{getattr(settings, 'app_name', 'Production API Framework')} - API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap" rel="stylesheet">
        <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Montserrat', sans-serif;
            }}
            .redoc-wrap {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .api-info-wrapper {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <div id="redoc-container"></div>
        <script src="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js"></script>
        <script>
            Redoc.init('/openapi.json', {redoc_options_json}, document.getElementById('redoc-container'));
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.get("/openapi.json", include_in_schema=False)
async def custom_openapi(
    request: Request,
    authorized: bool = Depends(verify_docs_access)
) -> Dict[str, Any]:
    """
    Custom OpenAPI schema with enhanced documentation.

    Args:
        request: FastAPI request object
        authorized: Authorization check result

    Returns:
        OpenAPI schema dictionary
    """
    # Get the FastAPI app instance from the request
    app = request.app

    # Generate custom OpenAPI schema
    return get_custom_openapi_schema(app)


@router.get("/docs/oauth2-redirect", response_class=HTMLResponse, include_in_schema=False)
async def swagger_ui_oauth2_redirect() -> HTMLResponse:
    """
    OAuth2 redirect handler for Swagger UI.

    Returns:
        HTML response for OAuth2 redirect
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Swagger UI OAuth2 Redirect</title>
    </head>
    <body>
        <script>
            'use strict';
            function run () {
                var oauth2 = window.opener.swaggerUIRedirectOauth2;
                var sentState = oauth2.state;
                var redirectUrl = oauth2.redirectUrl;
                var isValid, qp, arr;

                if (/code|token|error/.test(window.location.hash)) {
                    qp = window.location.hash.substring(1);
                } else {
                    qp = location.search.substring(1);
                }

                arr = qp.split("&");
                arr.forEach(function (v,i,_arr) { _arr[i] = '"' + v.replace('=', '":"') + '"';});
                qp = qp ? JSON.parse('{' + arr.join() + '}',
                        function (key, value) {
                            return key === "" ? value : decodeURIComponent(value);
                        }
                ) : {};

                isValid = qp.state === sentState;

                if ((
                  oauth2.auth.schema.get("flow") === "accessCode" ||
                  oauth2.auth.schema.get("flow") === "authorizationCode" ||
                  oauth2.auth.schema.get("flow") === "authorization_code"
                ) && !oauth2.auth.code) {
                    if (!isValid) {
                        oauth2.errCb({
                            authId: oauth2.auth.name,
                            source: "auth",
                            level: "warning",
                            message: "Authorization may be unsafe, passed state was changed in server Passed state wasn't returned from auth server"
                        });
                    }

                    if (qp.code) {
                        delete oauth2.state;
                        oauth2.auth.code = qp.code;
                        oauth2.callback({auth: oauth2.auth, redirectUrl: redirectUrl});
                    } else {
                        let oauthErrorMsg;
                        if (qp.error) {
                            oauthErrorMsg = "["+qp.error+"]: " +
                                (qp.error_description ? qp.error_description+ ". " : "no accessCode received from the server. ") +
                                (qp.error_uri ? "More info: "+qp.error_uri : "");
                        }

                        oauth2.errCb({
                            authId: oauth2.auth.name,
                            source: "auth",
                            level: "error",
                            message: oauthErrorMsg || "[Authorization failed]: no accessCode received from the server"
                        });
                    }
                } else {
                    oauth2.callback({auth: oauth2.auth, token: qp, isValid: isValid, redirectUrl: redirectUrl});
                }
                window.close();
            }

            window.addEventListener('DOMContentLoaded', function () {
                run();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/docs/info", include_in_schema=False)
async def docs_info(
    request: Request,
    authorized: bool = Depends(verify_docs_access)
) -> Dict[str, Any]:
    """
    Get information about the API documentation.

    Args:
        request: FastAPI request object
        authorized: Authorization check result

    Returns:
        Dictionary with documentation information
    """
    return {
        "title": getattr(settings, "app_name", "Production API Framework"),
        "version": getattr(settings, "version", "0.1.0"),
        "environment": getattr(settings, "env", "development"),
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "authentication_required": is_production(),
        "supported_auth_methods": [
            "Bearer Token (JWT)",
            "API Key (Header)",
            "OAuth2 (Authorization Code)"
        ],
        "features": [
            "Interactive API testing",
            "Request/response examples",
            "Schema validation",
            "Authentication support",
            "Rate limiting information",
            "Error response examples"
        ]
    }


@router.get("/docs/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def documentation_dashboard(
    request: Request,
    authorized: bool = Depends(verify_docs_access)
) -> HTMLResponse:
    """
    Comprehensive documentation dashboard with links to all documentation resources.

    Args:
        request: FastAPI request object
        authorized: Authorization check result

    Returns:
        HTML response with documentation dashboard
    """
    app_name = getattr(settings, 'app_name', 'Production API Framework')
    version = getattr(settings, 'version', '0.1.0')
    environment = getattr(settings, 'env', 'development')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{app_name} - Documentation Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 50px;
                color: white;
            }}
            .header h1 {{
                font-size: 3rem;
                font-weight: 700;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            .header p {{
                font-size: 1.2rem;
                opacity: 0.9;
                font-weight: 300;
            }}
            .version-badge {{
                display: inline-block;
                background: rgba(255,255,255,0.2);
                padding: 5px 15px;
                border-radius: 20px;
                margin-top: 10px;
                font-size: 0.9rem;
                backdrop-filter: blur(10px);
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                margin-bottom: 50px;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            .card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            }}
            .card-icon {{
                font-size: 2.5rem;
                margin-bottom: 20px;
                color: #667eea;
            }}
            .card h3 {{
                font-size: 1.5rem;
                margin-bottom: 15px;
                color: #333;
                font-weight: 600;
            }}
            .card p {{
                color: #666;
                margin-bottom: 20px;
                line-height: 1.6;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 24px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 500;
                transition: all 0.3s ease;
                border: none;
                cursor: pointer;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }}
            .features {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 40px;
                margin-bottom: 30px;
                backdrop-filter: blur(10px);
            }}
            .features h2 {{
                text-align: center;
                margin-bottom: 30px;
                color: #333;
                font-size: 2rem;
                font-weight: 600;
            }}
            .feature-list {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
            }}
            .feature-item {{
                display: flex;
                align-items: center;
                padding: 15px;
                background: rgba(102, 126, 234, 0.1);
                border-radius: 8px;
                transition: background 0.3s ease;
            }}
            .feature-item:hover {{
                background: rgba(102, 126, 234, 0.15);
            }}
            .feature-item i {{
                color: #667eea;
                margin-right: 15px;
                font-size: 1.2rem;
                width: 20px;
                text-align: center;
            }}
            .auth-info {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 30px;
                backdrop-filter: blur(10px);
            }}
            .auth-info h3 {{
                color: #333;
                margin-bottom: 20px;
                font-size: 1.3rem;
                font-weight: 600;
            }}
            .auth-methods {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }}
            .auth-method {{
                background: rgba(102, 126, 234, 0.1);
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 0.9rem;
                color: #667eea;
                font-weight: 500;
            }}
            .footer {{
                text-align: center;
                color: rgba(255, 255, 255, 0.8);
                font-size: 0.9rem;
            }}
            @media (max-width: 768px) {{
                .header h1 {{ font-size: 2rem; }}
                .container {{ padding: 20px 15px; }}
                .card {{ padding: 20px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1><i class="fas fa-code"></i> {app_name}</h1>
                <p>Comprehensive API Documentation & Interactive Tools</p>
                <div class="version-badge">
                    <i class="fas fa-tag"></i> Version {version} | Environment: {environment}
                </div>
            </div>

            <div class="grid">
                <div class="card">
                    <div class="card-icon">
                        <i class="fas fa-play-circle"></i>
                    </div>
                    <h3>Interactive API Explorer</h3>
                    <p>Test API endpoints directly in your browser with Swagger UI. Includes authentication support and real-time response testing.</p>
                    <a href="/docs" class="btn">
                        <i class="fas fa-external-link-alt"></i> Open Swagger UI
                    </a>
                </div>

                <div class="card">
                    <div class="card-icon">
                        <i class="fas fa-book"></i>
                    </div>
                    <h3>API Reference</h3>
                    <p>Comprehensive API documentation with detailed descriptions, examples, and schema definitions using ReDoc.</p>
                    <a href="/redoc" class="btn">
                        <i class="fas fa-external-link-alt"></i> Open ReDoc
                    </a>
                </div>

                <div class="card">
                    <div class="card-icon">
                        <i class="fas fa-code-branch"></i>
                    </div>
                    <h3>OpenAPI Schema</h3>
                    <p>Download the complete OpenAPI 3.0 specification for code generation, testing, and integration.</p>
                    <a href="/openapi.json" class="btn">
                        <i class="fas fa-download"></i> Download Schema
                    </a>
                </div>

                <div class="card">
                    <div class="card-icon">
                        <i class="fas fa-heartbeat"></i>
                    </div>
                    <h3>Health Monitoring</h3>
                    <p>Monitor API health and readiness status for production deployments and system monitoring.</p>
                    <a href="/healthz" class="btn">
                        <i class="fas fa-external-link-alt"></i> Check Health
                    </a>
                </div>
            </div>

            <div class="auth-info">
                <h3><i class="fas fa-shield-alt"></i> Authentication Methods</h3>
                <div class="auth-methods">
                    <span class="auth-method"><i class="fas fa-key"></i> JWT Bearer Token</span>
                    <span class="auth-method"><i class="fas fa-id-card"></i> API Key</span>
                    <span class="auth-method"><i class="fab fa-oauth"></i> OAuth2</span>
                </div>
            </div>

            <div class="features">
                <h2><i class="fas fa-star"></i> Documentation Features</h2>
                <div class="feature-list">
                    <div class="feature-item">
                        <i class="fas fa-lock"></i>
                        <span>Secure authentication support</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-examples"></i>
                        <span>Comprehensive request/response examples</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-shield-check"></i>
                        <span>Input validation documentation</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>Detailed error handling guides</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-tachometer-alt"></i>
                        <span>Rate limiting information</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-code"></i>
                        <span>Code generation support</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-mobile-alt"></i>
                        <span>Mobile-responsive design</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-search"></i>
                        <span>Searchable documentation</span>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p>
                    <i class="fas fa-info-circle"></i>
                    For support or questions, contact our development team.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.get("/docs/health", include_in_schema=False)
async def docs_health() -> Dict[str, Any]:
    """
    Health check for documentation endpoints.

    Returns:
        Dictionary with comprehensive documentation health status
    """
    from datetime import datetime

    return {
        "status": "healthy",
        "service": "api-documentation",
        "version": getattr(settings, "version", "0.1.0"),
        "environment": getattr(settings, "env", "development"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "endpoints": {
            "dashboard": "/docs/dashboard",
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json",
            "oauth2_redirect": "/docs/oauth2-redirect",
            "info": "/docs/info",
            "health": "/docs/health"
        },
        "features": {
            "authentication_support": True,
            "interactive_testing": True,
            "comprehensive_examples": True,
            "error_documentation": True,
            "rate_limiting_info": True,
            "mobile_responsive": True
        },
        "authentication": {
            "required": getattr(settings, "docs_require_auth", is_production()),
            "methods": ["Bearer Token", "API Key", "OAuth2"]
        }
    }
