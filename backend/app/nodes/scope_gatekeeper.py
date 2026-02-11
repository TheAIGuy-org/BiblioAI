"""
Node 1: Scope Gatekeeper
Classifies queries and protects the system from out-of-scope requests.
"""
from app.models.state import BuilderState
from app.core.llm_factory import llm_factory
from app.prompts.gatekeeper_prompts import build_gatekeeper_prompt
from app.utils.logger import get_logger
from app.utils.parsers import parse_llm_json, validate_json_schema

logger = get_logger(__name__)


def scope_gatekeeper_node(state: BuilderState) -> BuilderState:
    """
    Node 1: Classify the user query into HOMEWORK, PRODUCTION, or MALICIOUS.
    
    Flow:
    - HOMEWORK → Continue to Architect
    - PRODUCTION/MALICIOUS → Stop with refusal message
    """
    logger.info(f"[GATEKEEPER] Analyzing query: {state['user_query'][:100]}")
    
    state["current_node"] = "scope_gatekeeper"
    
    try:
        llm = llm_factory.get_gatekeeper_llm()
        prompt = build_gatekeeper_prompt(state["user_query"])
        
        response = llm.invoke(prompt)
        
        # FIX: Use robust JSON parser to handle markdown-wrapped responses
        result = parse_llm_json(response.content)
        
        # Validate required fields
        required_keys = ["classification", "confidence", "reasoning"]
        if not validate_json_schema(result, required_keys):
            raise ValueError("Missing required fields in gatekeeper response")
        
        classification = result["classification"]
        state["classification"] = classification
        
        logger.info(f"[GATEKEEPER] Classification: {classification} (confidence: {result['confidence']})")
        
        if classification == "HOMEWORK":
            state["is_feasible"] = True
            state["refusal_reason"] = None
        else:
            state["is_feasible"] = False
            state["refusal_reason"] = result.get("refusal_message", "Request out of scope")
            state["is_complete"] = True
            logger.warning(f"[GATEKEEPER] Request rejected: {state['refusal_reason']}")
        
        return state
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[GATEKEEPER] Error: {error_msg}")
        
        # Friendly error messages for common issues
        if "401" in error_msg or "AuthenticationError" in error_msg:
            friendly_msg = "Authentication failed. Please check your GROQ_API_KEY in .env."
        elif "429" in error_msg:
            friendly_msg = "Rate limit exceeded. Please try again later."
        elif "Connection error" in error_msg or "ConnectError" in error_msg:
            friendly_msg = "Connection failed. Check internet connection or firewall settings."
        else:
            friendly_msg = f"Gatekeeper Error: {error_msg}"

        state["is_feasible"] = False
        state["refusal_reason"] = friendly_msg # Use refusal reason to show in UI
        state["error_message"] = friendly_msg
        state["is_complete"] = True
        return state


def should_continue_after_gatekeeper(state: BuilderState) -> str:
    """Router: Decide next node based on classification."""
    if state["is_feasible"]:
        return "architect"
    else:
        return "end"