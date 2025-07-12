"""
Environment Variable Validation for Security

Validates environment variables to ensure proper configuration
and prevent security issues from missing or invalid credentials.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from app.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates environment variables for security and functionality"""
    
    def __init__(self):
        """Initialize the environment validator"""
        
        # Required API keys and their patterns
        self.api_key_validations = {
            "OPENAI_API_KEY": {
                "pattern": r"^sk-(proj-)?[a-zA-Z0-9_-]{40,}$",
                "required": True,
                "description": "OpenAI API key for AI model access"
            },
            "DEEPGRAM_API_KEY": {
                "pattern": r"^[a-f0-9]{32,}$",
                "required": False,  # Only required if telephony is enabled
                "description": "Deepgram API key for speech-to-text"
            },
            "ELEVENLABS_API_KEY": {
                "pattern": r"^(sk_)?[a-f0-9]{32,}$",
                "required": False,  # Only required if using ElevenLabs
                "description": "ElevenLabs API key for text-to-speech"
            },
            "SENDGRID_API_KEY": {
                "pattern": r"^SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}$",
                "required": False,  # Only required for email features
                "description": "SendGrid API key for email services"
            },
            "STRIPE_SECRET_KEY": {
                "pattern": r"^sk_(test_|live_)[a-zA-Z0-9]{99}$",
                "required": False,  # Only required for billing
                "description": "Stripe secret key for payment processing"
            },
            "TWILIO_AUTH_TOKEN": {
                "pattern": r"^[a-f0-9]{32}$",
                "required": False,  # Only required if telephony is enabled
                "description": "Twilio auth token for telephony services"
            }
        }
        
        # Database URL patterns
        self.db_url_patterns = {
            "postgresql": r"^postgresql(\+asyncpg)?://[^:]+:[^@]+@[^/]+:\d+/\w+$",
            "mysql": r"^mysql(\+pymysql)?://[^:]+:[^@]+@[^/]+:\d+/\w+$",
            "sqlite": r"^sqlite:///.*\.db$"
        }
        
        # Security-critical environment variables
        self.security_vars = [
            "JWT_SECRET_KEY",
            "DATABASE_URL", 
            "CORS_ORIGINS",
            "ENVIRONMENT"
        ]
        
        # Default/placeholder values that should never be used in production
        self.dangerous_defaults = [
            "your-secret-key",
            "changeme",
            "password",
            "secret",
            "default",
            "test123",
            "admin",
            "root",
            "NOT_SET",
            "NONE",
            "YOU_GOT_NOTHIN"
        ]
    
    def validate_all_environment_vars(self) -> Dict[str, Any]:
        """
        Validate all environment variables
        
        Returns:
            Dictionary containing validation results and recommendations
        """
        validation_results = {
            "status": "unknown",
            "critical_issues": [],
            "warnings": [],
            "api_keys": {},
            "security_vars": {},
            "recommendations": []
        }
        
        try:
            # Validate API keys
            api_validation = self._validate_api_keys()
            validation_results["api_keys"] = api_validation
            
            # Validate security-critical variables
            security_validation = self._validate_security_vars()
            validation_results["security_vars"] = security_validation
            
            # Check for dangerous defaults
            defaults_check = self._check_dangerous_defaults()
            validation_results["dangerous_defaults"] = defaults_check
            
            # Determine overall status
            validation_results["status"] = self._determine_overall_status(
                api_validation, security_validation, defaults_check
            )
            
            # Generate recommendations
            validation_results["recommendations"] = self._generate_recommendations(
                api_validation, security_validation, defaults_check
            )
            
            # Log validation results
            self._log_validation_results(validation_results)
            
        except Exception as e:
            logger.error(f"Environment validation failed: {e}")
            validation_results["status"] = "error"
            validation_results["critical_issues"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    def _validate_api_keys(self) -> Dict[str, Any]:
        """Validate API keys"""
        results = {}
        
        for key_name, validation_config in self.api_key_validations.items():
            key_value = os.getenv(key_name)
            
            result = {
                "present": key_value is not None,
                "valid_format": False,
                "required": validation_config["required"],
                "description": validation_config["description"],
                "issues": []
            }
            
            if not key_value:
                if validation_config["required"]:
                    result["issues"].append("Required API key is missing")
            else:
                # Check if it's a dangerous default
                if key_value in self.dangerous_defaults:
                    result["issues"].append("Using dangerous default value")
                
                # Validate format
                pattern = validation_config["pattern"]
                if re.match(pattern, key_value):
                    result["valid_format"] = True
                else:
                    result["issues"].append("Invalid API key format")
                    
                # Check key length (most API keys should be reasonably long)
                if len(key_value) < 20:
                    result["issues"].append("API key appears too short")
            
            results[key_name] = result
        
        return results
    
    def _validate_security_vars(self) -> Dict[str, Any]:
        """Validate security-critical environment variables"""
        results = {}
        
        for var_name in self.security_vars:
            var_value = os.getenv(var_name)
            
            result = {
                "present": var_value is not None,
                "secure": False,
                "issues": []
            }
            
            if var_name == "JWT_SECRET_KEY":
                result.update(self._validate_jwt_secret(var_value))
            elif var_name == "DATABASE_URL":
                result.update(self._validate_database_url(var_value))
            elif var_name == "CORS_ORIGINS":
                result.update(self._validate_cors_origins(var_value))
            elif var_name == "ENVIRONMENT":
                result.update(self._validate_environment_var(var_value))
            
            results[var_name] = result
        
        return results
    
    def _validate_jwt_secret(self, secret_value: Optional[str]) -> Dict[str, Any]:
        """Validate JWT secret key"""
        result = {"secure": False, "issues": []}
        
        if not secret_value:
            result["issues"].append("JWT secret key is not set")
            return result
        
        if secret_value in self.dangerous_defaults:
            result["issues"].append("Using dangerous default JWT secret")
            return result
        
        if len(secret_value) < 32:
            result["issues"].append("JWT secret key is too short (minimum 32 characters)")
        
        # Check for complexity
        if not re.search(r'[A-Z]', secret_value):
            result["issues"].append("JWT secret should contain uppercase letters")
        if not re.search(r'[a-z]', secret_value):
            result["issues"].append("JWT secret should contain lowercase letters")
        if not re.search(r'[0-9]', secret_value):
            result["issues"].append("JWT secret should contain numbers")
        if not re.search(r'[^A-Za-z0-9]', secret_value):
            result["issues"].append("JWT secret should contain special characters")
        
        result["secure"] = len(result["issues"]) == 0
        return result
    
    def _validate_database_url(self, db_url: Optional[str]) -> Dict[str, Any]:
        """Validate database URL"""
        result = {"secure": False, "issues": []}
        
        if not db_url:
            result["issues"].append("Database URL is not set")
            return result
        
        # Check for dangerous patterns
        if "password" in db_url.lower() or "root" in db_url.lower():
            result["issues"].append("Database URL may contain unsafe credentials")
        
        # Validate format
        valid_format = False
        for db_type, pattern in self.db_url_patterns.items():
            if re.match(pattern, db_url):
                valid_format = True
                break
        
        if not valid_format:
            result["issues"].append("Database URL format appears invalid")
        
        # Check for localhost in production
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" and "localhost" in db_url:
            result["issues"].append("Using localhost database in production")
        
        result["secure"] = len(result["issues"]) == 0
        return result
    
    def _validate_cors_origins(self, cors_value: Optional[str]) -> Dict[str, Any]:
        """Validate CORS origins"""
        result = {"secure": False, "issues": []}
        
        if not cors_value:
            result["issues"].append("CORS origins not configured")
            return result
        
        # Check for wildcard in production
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" and "*" in cors_value:
            result["issues"].append("Wildcard CORS origins in production is insecure")
        
        result["secure"] = len(result["issues"]) == 0
        return result
    
    def _validate_environment_var(self, env_value: Optional[str]) -> Dict[str, Any]:
        """Validate ENVIRONMENT variable"""
        result = {"secure": False, "issues": []}
        
        if not env_value:
            result["issues"].append("ENVIRONMENT variable not set")
            return result
        
        valid_environments = ["development", "staging", "production", "test"]
        if env_value not in valid_environments:
            result["issues"].append(f"Invalid environment value: {env_value}")
        
        result["secure"] = len(result["issues"]) == 0
        return result
    
    def _check_dangerous_defaults(self) -> Dict[str, Any]:
        """Check for dangerous default values across all environment variables"""
        dangerous_vars = []
        
        for key, value in os.environ.items():
            if value in self.dangerous_defaults:
                dangerous_vars.append({
                    "variable": key,
                    "value": value,
                    "risk": "high" if key in self.security_vars else "medium"
                })
        
        return {
            "found_dangerous_defaults": len(dangerous_vars) > 0,
            "dangerous_variables": dangerous_vars,
            "count": len(dangerous_vars)
        }
    
    def _determine_overall_status(
        self, 
        api_validation: Dict[str, Any],
        security_validation: Dict[str, Any], 
        defaults_check: Dict[str, Any]
    ) -> str:
        """Determine overall validation status"""
        
        # Check for critical issues
        critical_issues = 0
        
        # Count API key issues
        for key_result in api_validation.values():
            if key_result["required"] and not key_result["present"]:
                critical_issues += 1
            if key_result["present"] and not key_result["valid_format"]:
                critical_issues += 1
        
        # Count security variable issues
        for var_result in security_validation.values():
            if not var_result["secure"]:
                critical_issues += 1
        
        # Check dangerous defaults
        if defaults_check["found_dangerous_defaults"]:
            dangerous_security_vars = [
                var for var in defaults_check["dangerous_variables"]
                if var["risk"] == "high"
            ]
            critical_issues += len(dangerous_security_vars)
        
        # Determine status
        if critical_issues == 0:
            return "secure"
        elif critical_issues <= 2:
            return "warning"
        else:
            return "critical"
    
    def _generate_recommendations(
        self,
        api_validation: Dict[str, Any],
        security_validation: Dict[str, Any],
        defaults_check: Dict[str, Any]
    ) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        # API key recommendations
        for key_name, result in api_validation.items():
            if result["required"] and not result["present"]:
                recommendations.append(
                    f"Set {key_name} environment variable for {result['description']}"
                )
            elif result["present"] and result["issues"]:
                recommendations.append(
                    f"Fix {key_name}: {', '.join(result['issues'])}"
                )
        
        # Security variable recommendations
        for var_name, result in security_validation.items():
            if result["issues"]:
                recommendations.append(
                    f"Fix {var_name}: {', '.join(result['issues'])}"
                )
        
        # Dangerous defaults recommendations
        if defaults_check["found_dangerous_defaults"]:
            for var_info in defaults_check["dangerous_variables"]:
                recommendations.append(
                    f"Replace dangerous default value in {var_info['variable']}"
                )
        
        # General recommendations
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production":
            recommendations.extend([
                "Use strong, unique secrets for all production credentials",
                "Enable secure logging and monitoring",
                "Regularly rotate API keys and secrets",
                "Use environment-specific configuration files"
            ])
        
        return recommendations
    
    def _log_validation_results(self, results: Dict[str, Any]):
        """Log validation results for auditing"""
        status = results["status"]
        
        if status == "critical":
            logger.error(f"CRITICAL: Environment validation failed with {len(results.get('critical_issues', []))} critical issues")
            audit_logger.log_security_policy_violation(
                policy_type="environment_configuration",
                violation_details=f"Critical environment validation issues: {results.get('critical_issues', [])}"
            )
        elif status == "warning":
            logger.warning(f"WARNING: Environment validation found issues: {results.get('warnings', [])}")
        else:
            logger.info("Environment validation passed - configuration appears secure")
    
    def validate_specific_key(self, key_name: str) -> Dict[str, Any]:
        """Validate a specific API key"""
        if key_name not in self.api_key_validations:
            return {"error": f"Unknown API key: {key_name}"}
        
        validation_config = self.api_key_validations[key_name]
        key_value = os.getenv(key_name)
        
        result = {
            "key_name": key_name,
            "present": key_value is not None,
            "valid_format": False,
            "description": validation_config["description"],
            "issues": []
        }
        
        if key_value:
            pattern = validation_config["pattern"]
            result["valid_format"] = bool(re.match(pattern, key_value))
            
            if not result["valid_format"]:
                result["issues"].append("Invalid format")
            
            if key_value in self.dangerous_defaults:
                result["issues"].append("Using dangerous default value")
        
        return result


# Global validator instance
env_validator = EnvironmentValidator()