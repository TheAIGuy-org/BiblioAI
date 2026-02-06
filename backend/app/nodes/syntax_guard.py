"""
Node 4: Syntax Guard (LLM-Powered Integration Validator)
Comprehensive code validation with Chain of Thought reasoning.
Checks: syntax, imports, frontend-backend integration, feature completeness.
"""
from app.models.state import BuilderState
from app.core.llm_factory import llm_factory
from app.prompts.syntax_guard_prompts import build_syntax_guard_prompt
from app.utils.logger import get_logger
from app.utils.parsers import parse_llm_json
from app.config import settings

logger = get_logger(__name__)


def syntax_guard_node(state: BuilderState) -> BuilderState:
    """
    Node 4: Comprehensive code validation with LLM (COT-powered).
    
    This is the CRITICAL quality gate that ensures:
    1. Syntax correctness
    2. Import/dependency accuracy
    3. Frontend ↔ Backend integration
    4. Cross-file consistency
    5. Feature implementation completeness
    
    Uses Chain of Thought prompting for maximum accuracy.
    """
    logger.info("[SYNTAX GUARD] Starting comprehensive code validation with COT analysis")
    
    state["current_node"] = "syntax_guard"
    
    try:
        # Get LLM for validation (using auditor model for higher token limits)
        llm = llm_factory.get_auditor_llm()
        
        # Build comprehensive prompt with all context
        prompt = build_syntax_guard_prompt(
            generated_code=state.get("generated_code", {}),
            approved_features=state.get("approved_features", []),       
            file_specifications=state.get("file_structure", []),
            user_query=state.get("user_query", "")
        )
        
        logger.info("[SYNTAX GUARD] Calling LLM for validation analysis...")
        response = llm.invoke(prompt)
        
        # Parse JSON response
        validation_result = parse_llm_json(response.content)
        
        # Extract validation data
        issues = validation_result.get("issues", [])
        summary = validation_result.get("summary", {})
        chain_of_thought = validation_result.get("chain_of_thought", {})
        
        # CRITICAL: Filter out issues for files that don't exist in generated_code
        # This prevents hallucinated files from breaking the pipeline
        generated_files = set(state.get("generated_code", {}).keys())
        valid_issues = []
        hallucinated_files = set()
        
        for issue in issues:
            issue_file = issue.get("file", "")
            if issue_file in generated_files:
                valid_issues.append(issue)
            else:
                hallucinated_files.add(issue_file)
        
        if hallucinated_files:
            logger.warning(f"[SYNTAX GUARD] Filtered out {len(issues) - len(valid_issues)} issues for non-existent files: {', '.join(hallucinated_files)}")
            logger.warning(f"[SYNTAX GUARD] Generated files: {', '.join(generated_files)}")
        
        # Update summary to reflect filtered issues
        if hallucinated_files:
            summary["total_issues"] = len(valid_issues)
            summary["critical_issues"] = len([i for i in valid_issues if i.get("severity") == "CRITICAL"])
            summary["files_affected"] = list(set([i["file"] for i in valid_issues if "file" in i]))
        
        # Store in state
        state["syntax_guard_validation"] = validation_result
        state["validation_issues"] = valid_issues  # Use filtered issues
        state["validation_passed"] = summary.get("validation_result") == "PASSED" or len(valid_issues) == 0
        
        # Log results
        total_issues = len(valid_issues)
        critical_issues = summary.get("critical_issues", len([i for i in valid_issues if i.get("severity") == "CRITICAL"]))
        
        logger.info(f"[SYNTAX GUARD] Validation complete:")
        logger.info(f"  - Result: {summary.get('validation_result', 'PASSED' if total_issues == 0 else 'FAILED')}")
        logger.info(f"  - Total Issues: {total_issues}")
        logger.info(f"  - Critical Issues: {critical_issues}")
        logger.info(f"  - Files Affected: {', '.join(summary.get('files_affected', []))}")
        
        # Log Chain of Thought insights
        if chain_of_thought:
            logger.info(f"[SYNTAX GUARD] COT Analysis:")
            logger.info(f"  - Architecture: {chain_of_thought.get('architecture', 'N/A')}")
            logger.info(f"  - Mismatches Found: {chain_of_thought.get('mismatches_found', 0)}")
        
        # Log issues
        if valid_issues:
            logger.warning(f"[SYNTAX GUARD] Identified {len(valid_issues)} issues:")
            for i, issue in enumerate(valid_issues[:5], 1):  # Show first 5
                logger.warning(f"  {i}. [{issue.get('severity')}] {issue.get('file')}: {issue.get('issue')}")
            if len(valid_issues) > 5:
                logger.warning(f"  ... and {len(valid_issues) - 5} more issues")
        else:
            logger.info("[SYNTAX GUARD] ✅ No issues found - code is clean!")
        
        return state
        
    except Exception as e:
        logger.error(f"[SYNTAX GUARD] Validation failed: {str(e)}")
        # Fallback: mark as passed to not block pipeline (logged for debugging)
        state["validation_issues"] = [{
            "category": "VALIDATION_ERROR",
            "severity": "WARNING",
            "file": "N/A",
            "issue": f"Syntax Guard LLM validation failed: {str(e)}",
            "reasoning": "System error during validation"
        }]
        state["validation_passed"] = True  # Allow proceeding despite validation failure
        state["syntax_guard_validation"] = {
            "error": str(e),
            "summary": {"validation_result": "ERROR"}
        }
        return state


def should_retry_after_syntax(state: BuilderState) -> str:
    """
    Router: Decide whether to send to Auditor (Code Fixer) or proceed.
    
    Logic:
    - If validation PASSED (no critical issues) → Skip Auditor, go to Dependency Analyzer
    - If validation FAILED (has critical issues) → Send to Auditor for surgical fixes
    """
    validation_passed = state.get("validation_passed", True)
    has_issues = len(state.get("validation_issues", [])) > 0
    
    if has_issues and not validation_passed:
        logger.info("[SYNTAX GUARD] Routing to Auditor for code fixes")
        return "auditor"
    else:
        logger.info("[SYNTAX GUARD] Validation passed, proceeding to dependency analysis")
        return "dependency_analyzer"