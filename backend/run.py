#!/usr/bin/env python3
"""
Multi-Tenant Auth Backend Run Script
Handles environment setup, database initialization, and server startup
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_header(message):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def check_python_version():
    """Check if Python version is 3.8 or higher."""
    if sys.version_info < (3, 8):
        print_error("Python 3.8 or higher is required")
        sys.exit(1)
    print_success(f"Python {sys.version.split()[0]} detected")

def check_venv():
    """Check if virtual environment is activated."""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_warning("Virtual environment not activated")
        print_info("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"])
        
        # Provide activation instructions
        if os.name == 'nt':  # Windows
            activate_cmd = "venv\\Scripts\\activate"
        else:  # Unix/Linux/Mac
            activate_cmd = "source venv/bin/activate"
        
        print_warning(f"Please activate the virtual environment and run this script again:")
        print(f"  {Colors.BOLD}{activate_cmd}{Colors.END}")
        print(f"  {Colors.BOLD}python run.py{Colors.END}")
        sys.exit(0)
    else:
        print_success("Virtual environment is active")

def install_dependencies():
    """Install required dependencies."""
    print_info("Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print_success("Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print_error("Failed to install dependencies")
        sys.exit(1)

def check_env_file():
    """Check if .env file exists and create from example if not."""
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            print_warning(".env file not found")
            print_info("Creating .env from .env.example...")
            
            # Copy .env.example to .env
            with open(".env.example", "r") as src, open(".env", "w") as dst:
                dst.write(src.read())
            
            print_success(".env file created")
            print_warning("Please update .env with your actual configuration before running again")
            sys.exit(0)
        else:
            print_error(".env.example not found. Please create .env file manually")
            sys.exit(1)
    else:
        print_success(".env file found")

async def check_database_connection():
    """Check if database is accessible."""
    print_info("Checking database connection...")
    try:
        from app.db.database import engine
        from sqlalchemy import text
        
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print_success("Database connection successful")
        return True
    except Exception as e:
        print_error(f"Database connection failed: {str(e)}")
        return False

async def init_database():
    """Initialize database tables."""
    print_info("Initializing database tables...")
    try:
        from app.db.database import init_db
        await init_db()
        print_success("Database tables initialized")
    except Exception as e:
        print_error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)

def run_migrations():
    """Run database migrations with Alembic."""
    if not os.path.exists("alembic"):
        print_info("Alembic not initialized. Initializing now...")
        subprocess.run(["alembic", "init", "alembic"], check=True)
        print_success("Alembic initialized")
        print_warning("Please configure alembic/env.py before running migrations")
        return
    
    print_info("Running database migrations...")
    try:
        # Check if there are any existing migrations
        result = subprocess.run(["alembic", "current"], capture_output=True, text=True)
        
        if "head" not in result.stdout:
            # Generate initial migration
            print_info("Generating initial migration...")
            subprocess.run(["alembic", "revision", "--autogenerate", "-m", "Initial migration"], check=True)
        
        # Run migrations
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        print_success("Database migrations completed")
    except subprocess.CalledProcessError as e:
        print_warning(f"Migration warning: {str(e)}")
        print_info("Continuing with direct table creation...")

async def create_demo_data():
    """Create demo tenant and user."""
    print_info("Creating demo data...")
    try:
        from app.db.database import AsyncSessionLocal
        from app.models.models import Tenant, User
        from app.auth.auth import AuthService
        from sqlalchemy.future import select
        
        async with AsyncSessionLocal() as db:
            # Check if demo tenant exists
            result = await db.execute(select(Tenant).filter(Tenant.subdomain == "demo"))
            demo_tenant = result.scalars().first()
            
            if not demo_tenant:
                # Create demo tenant
                demo_tenant = Tenant(name="Demo Company", subdomain="demo")
                db.add(demo_tenant)
                await db.commit()
                print_success("Created demo tenant (subdomain: 'demo')")
            
            # Check if demo user exists
            result = await db.execute(select(User).filter(
                User.email == "demo@example.com",
                User.tenant_id == demo_tenant.id
            ))
            demo_user = result.scalars().first()
            
            if not demo_user:
                # Create demo user
                demo_user = User(
                    email="demo@example.com",
                    username="demo",
                    hashed_password=AuthService.get_password_hash("demo123"),
                    first_name="Demo",
                    last_name="User",
                    tenant_id=demo_tenant.id,
                    is_active=True,
                    is_verified=True,
                    role="admin"
                )
                db.add(demo_user)
                await db.commit()
                print_success("Created demo user (email: demo@example.com, password: demo123)")
        
    except Exception as e:
        print_warning(f"Could not create demo data: {str(e)}")

def start_server(host="0.0.0.0", port=8000, reload=True):
    """Start the FastAPI server."""
    print_header("Starting Multi-Tenant Auth Server")
    
    print_info(f"Server starting on http://{host}:{port}")
    print_info(f"API documentation: http://localhost:{port}/docs")
    print_info(f"Alternative docs: http://localhost:{port}/redoc")
    
    if reload:
        print_info("Running in development mode with auto-reload")
    
    print("\n" + Colors.BOLD + "Demo Credentials:" + Colors.END)
    print(f"  Tenant: demo")
    print(f"  Email:  demo@example.com")
    print(f"  Pass:   demo123")
    print("")
    
    try:
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", host,
            "--port", str(port)
        ]
        if reload:
            cmd.append("--reload")
        
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n" + Colors.YELLOW + "Server stopped by user" + Colors.END)
    except Exception as e:
        print_error(f"Server error: {str(e)}")

async def async_main(args):
    """Asynchronous main function to handle database operations."""
    # Database setup
    if await check_database_connection():
        # Initialize database directly instead of using migrations
        await init_database()
        
        # Create demo data
        if not args.no_demo:
            await create_demo_data()
        
        # Exit if init-only mode
        if args.init_only:
            print_success("Initialization completed successfully")
            sys.exit(0)
        
        # Start server with the port from .env file
        port = int(os.getenv("API_PORT", args.port))
        print_info(f"Using port {port} from environment")
        
        start_server(
            host=args.host,
            port=port,
            reload=not args.no_reload
        )
    else:
        print_error("Cannot proceed without database connection")
        print_info("Please check your DATABASE_URL in .env file")
        sys.exit(1)

def main():
    import asyncio
    
    parser = argparse.ArgumentParser(description="Multi-Tenant Auth Backend Runner")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--skip-checks", action="store_true", help="Skip environment checks")
    parser.add_argument("--init-only", action="store_true", help="Only initialize database and exit")
    parser.add_argument("--no-demo", action="store_true", help="Skip creating demo data")
    
    args = parser.parse_args()
    
    print_header("Multi-Tenant Auth Backend Setup")
    
    # Environment checks
    if not args.skip_checks:
        check_python_version()
        check_venv()
        check_env_file()
        
        # Check if dependencies are installed
        try:
            import fastapi
            import sqlalchemy
            import jose
            print_success("Core dependencies are installed")
        except ImportError:
            install_dependencies()
    
    # Run the async part
    asyncio.run(async_main(args))

if __name__ == "__main__":
    main()
