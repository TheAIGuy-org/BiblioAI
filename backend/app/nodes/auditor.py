"""
Node 5: The Auditor
Semantic verification - ensures code matches user intent.
"""
from app.models.state import BuilderState
from app.core.llm_factory import llm_factory
from app.prompts.auditor_prompts import build_auditor_prompt
from app.utils.logger import get_logger
from app.utils.parsers import parse_llm_json
from app.config import settings

logger = get_logger(__name__)


def auditor_node(state: BuilderState) -> BuilderState:
    """
    Node 5: Verify that generated code matches user requirements.
    
    Checks:
    - Feature completeness
    - Logic correctness
    - No hallucinated libraries
    """
    logger.info("[AUDITOR] Performing semantic verification")
    
    state["current_node"] = "auditor"
    
    try:
        llm = llm_factory.get_auditor_llm()
        prompt = build_auditor_prompt(
            user_query=state["user_query"],
            generated_code=state["generated_code"],
            file_structure=state["file_structure"]
        )
        
        response = llm.invoke(prompt)
        
        # FIX: Use robust JSON parser
        audit_result = parse_llm_json(response.content)
        
        is_approved = audit_result.get("is_approved", False)
        state["semantic_issues"] = audit_result.get("semantic_issues", [])
        
        logger.info(f"[AUDITOR] Audit result: {'APPROVED' if is_approved else 'REJECTED'}")
        
        if state["semantic_issues"]:
            logger.warning(f"[AUDITOR] Found {len(state['semantic_issues'])} issues:")
            for issue in state["semantic_issues"]:
                logger.warning(f"  - {issue}")
        
        # Store audit metadata
        state["audit_result"] = audit_result
        
        return state
        
    except Exception as e:
        logger.error(f"[AUDITOR] Error: {str(e)}")
        # If audit fails, we'll still proceed (non-blocking)
        state["semantic_issues"] = [f"Audit failed: {str(e)}"]
        return state


def should_retry_after_audit(state: BuilderState) -> str:
    """Router: Decide whether to retry or package."""
    max_retries = settings.MAX_RETRY_COUNT
    
    # Retry if semantic issues exist and we haven't exceeded retry limit
    if (state["semantic_issues"] and 
        state["retry_count"] < max_retries and
        state.get("audit_result", {}).get("is_approved", True) is False):
        
        state["retry_count"] += 1
        logger.info(f"[AUDITOR] Retrying build for semantic fixes (attempt {state['retry_count']})")
        return "builder"
    else:
        # Even with minor issues, proceed to packaging after max retries
        if state["semantic_issues"]:
            logger.warning("[AUDITOR] Proceeding to packaging despite minor issues")
        return "packager"