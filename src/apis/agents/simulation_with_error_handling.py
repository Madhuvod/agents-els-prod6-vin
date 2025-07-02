"""
Example simulation endpoint with improved error handling using centralized utilities.

This demonstrates how to integrate the new error handling utilities into 
the existing simulation endpoints for consistent error responses.
"""

import json
import logging
from uuid import uuid4
from typing import Optional, Union, Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

# Import our centralized error handling utilities
from src.utils.error_handler import (
    handle_litellm_error,
    create_error_response,
    log_error,
    ValidationException,
    SimulationException,
    ExternalAPIException,
    ErrorType
)

# Mock app for demonstration
app = FastAPI()

class EnhancePersonaRequest(BaseModel):
    persona: str = Field(..., min_length=1, description="User persona to enhance")
    scenario: str = Field(..., min_length=1, description="Scenario for enhancement")
    model_config: dict = Field(..., description="LLM model configuration")


class EnhancePersonaResponse(BaseModel):
    enhanced_persona: str
    original_persona: str
    scenario: str


@app.post("/api/v1/enhance_persona", response_model=None)
async def enhance_persona_endpoint(payload: EnhancePersonaRequest):
    """
    Enhanced persona endpoint with improved error handling.
    
    This endpoint demonstrates the use of centralized error handling utilities
    to provide consistent error responses across the API.
    """
    try:
        # Validate input data
        if not payload.persona.strip():
            raise ValidationException(
                message="Persona cannot be empty",
                details={"field": "persona", "value": payload.persona}
            )
        
        if not payload.scenario.strip():
            raise ValidationException(
                message="Scenario cannot be empty", 
                details={"field": "scenario", "value": payload.scenario}
            )
        
        # Mock LLM call that might fail
        try:
            # This would be the actual LLM call
            # enhanced_persona = await enhance_persona_with_scenario(...)
            enhanced_persona = f"Enhanced: {payload.persona} in scenario: {payload.scenario}"
            
        except Exception as llm_error:
            # Use centralized LiteLLM error handler
            return handle_litellm_error(llm_error, "persona enhancement")
        
        return EnhancePersonaResponse(
            enhanced_persona=enhanced_persona,
            original_persona=payload.persona,
            scenario=payload.scenario
        )
        
    except ValidationException as e:
        # ValidationException already has proper formatting
        return e.to_response()
    
    except Exception as e:
        # Log the error with context
        log_error(
            error=e,
            context="enhance_persona_endpoint",
            extra_data={
                "persona_length": len(payload.persona) if payload.persona else 0,
                "scenario_length": len(payload.scenario) if payload.scenario else 0
            }
        )
        
        # Return standardized error response
        return create_error_response(
            message=f"Persona enhancement failed: {str(e)}",
            status_code=500,
            error_type=ErrorType.INTERNAL_ERROR
        )


@app.post("/api/v1/simulate_next_turn")
async def generate_next_turn_simulation(payload: dict):
    """
    Simulation endpoint with improved error handling.
    
    This demonstrates how simulation-specific errors can be handled
    consistently using the centralized error handling utilities.
    """
    simulation_id = payload.get("simulation_id")
    
    try:
        # Validate simulation payload
        if not simulation_id:
            raise ValidationException(
                message="Simulation ID is required",
                details={"field": "simulation_id"}
            )
        
        # Mock simulation logic that might fail
        try:
            # This would be the actual simulation logic
            # result = await run_simulation(payload)
            result = {"status": "success", "simulation_id": simulation_id}
            
            return {"result": result, "stop_reason": None}
            
        except Exception as sim_error:
            # Use simulation-specific exception
            raise SimulationException(
                message=f"Simulation turn failed: {str(sim_error)}",
                simulation_id=simulation_id,
                turn_number=payload.get("turn_number")
            )
    
    except ValidationException as e:
        return e.to_response()
    
    except SimulationException as e:
        # Log simulation error with context
        log_error(
            error=e,
            context="generate_next_turn_simulation",
            extra_data={"simulation_id": simulation_id}
        )
        return e.to_response()
    
    except Exception as e:
        # Log unexpected errors
        log_error(
            error=e,
            context="generate_next_turn_simulation",
            extra_data={"simulation_id": simulation_id}
        )
        
        return create_error_response(
            message=f"Simulation failed: {str(e)}",
            status_code=500,
            error_type=ErrorType.SIMULATION_ERROR,
            details={"simulation_id": simulation_id}
        )


# Example of how to add global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler using centralized error handling."""
    log_error(
        error=exc,
        context="global_exception_handler",
        extra_data={"path": str(request.url), "method": request.method}
    )
    
    return create_error_response(
        message="An unexpected error occurred",
        status_code=500,
        error_type=ErrorType.INTERNAL_ERROR
    )