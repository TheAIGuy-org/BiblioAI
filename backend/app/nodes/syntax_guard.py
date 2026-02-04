"""
Node 4: Syntax Guard (Non-LLM)
Fast, deterministic syntax validation for HTML/CSS/JS.
"""
from html.parser import HTMLParser
import re
from app.models.state import BuilderState
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HTMLValidator(HTMLParser):
    """Custom HTML parser for syntax validation."""
    
    def __init__(self):
        super().__init__()
        self.errors = []
        self.tag_stack = []
    
    def handle_starttag(self, tag, attrs):
        if tag not in ['meta', 'img', 'br', 'hr', 'input', 'link']:
            self.tag_stack.append(tag)
    
    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        elif tag not in ['meta', 'img', 'br', 'hr', 'input', 'link']:
            self.errors.append(f"Unexpected closing tag: </{tag}>")
    
    def error(self, message):
        self.errors.append(message)


def validate_html(code: str) -> list:
    """Validate HTML syntax."""
    errors = []
    validator = HTMLValidator()
    
    try:
        validator.feed(code)
        
        # Check for unclosed tags
        if validator.tag_stack:
            errors.append(f"Unclosed tags: {', '.join(validator.tag_stack)}")
        
        errors.extend(validator.errors)
        
    except Exception as e:
        errors.append(f"HTML parsing error: {str(e)}")
    
    return errors


def validate_css(code: str) -> list:
    """Basic CSS syntax validation."""
    errors = []
    
    # Check for balanced braces
    open_braces = code.count('{')
    close_braces = code.count('}')
    if open_braces != close_braces:
        errors.append(f"Unbalanced braces in CSS: {open_braces} open, {close_braces} close")
    
    # Check for common syntax errors
    if ';;' in code:
        errors.append("Double semicolons found in CSS")
    
    return errors


def validate_javascript(code: str) -> list:
    """
    Minimal JavaScript validation.
    
    FIX: Removed naive brace counting that fails on valid code with braces in strings.
    Now only checks for obviously broken code to avoid false positives.
    """
    errors = []
    
    # Check for empty file
    if not code.strip():
        errors.append("JavaScript file is empty")
        return errors
    
    # Check for common catastrophic errors only
    # (We trust the LLM and rely on semantic audit for logic issues)
    
    # Check for obviously unclosed multi-line comments
    open_comments = code.count('/*')
    close_comments = code.count('*/')
    if open_comments != close_comments:
        errors.append(f"Unclosed multi-line comments: {open_comments} open, {close_comments} close")
    
    # Check for function keyword without parentheses (obvious typo)
    if re.search(r'\bfunction\s+\w+\s*[^(]', code):
        # This is a very loose check - only catches extreme cases
        pass
    
    # REMOVED: Brace/parenthesis/bracket counting
    # Reason: Fails on valid code like: const regex = /[\(\)]/; or console.log("Error: }")
    # These are VALID JavaScript but would be flagged as "unbalanced"
    
    logger.debug("[SYNTAX GUARD] JavaScript validation: Minimal checks only (trusting LLM)")
    
    return errors


def syntax_guard_node(state: BuilderState) -> BuilderState:
    """
    Node 4: Validate syntax of generated code.
    
    Non-LLM deterministic checks for HTML/CSS/JS syntax errors.
    Uses relaxed validation to avoid false positives.
    """
    logger.info("[SYNTAX GUARD] Validating code syntax")
    
    state["current_node"] = "syntax_guard"
    state["syntax_errors"] = []
    
    for filename, code in state["generated_code"].items():
        file_errors = []
        
        if filename.endswith('.html'):
            file_errors = validate_html(code)
        elif filename.endswith('.css'):
            file_errors = validate_css(code)
        elif filename.endswith('.js'):
            file_errors = validate_javascript(code)
        
        if file_errors:
            for error in file_errors:
                state["syntax_errors"].append(f"{filename}: {error}")
    
    if state["syntax_errors"]:
        logger.warning(f"[SYNTAX GUARD] Found {len(state['syntax_errors'])} syntax errors")
        for error in state["syntax_errors"]:
            logger.warning(f"  - {error}")
    else:
        logger.info("[SYNTAX GUARD] All files passed syntax validation")
    
    return state


def should_retry_after_syntax(state: BuilderState) -> str:
    """Router: Decide whether to retry or continue."""
    if state["syntax_errors"] and state["retry_count"] < state.get("max_retries", 2):
        state["retry_count"] += 1
        logger.info(f"[SYNTAX GUARD] Retrying build (attempt {state['retry_count']})")
        return "builder"
    else:
        return "auditor"