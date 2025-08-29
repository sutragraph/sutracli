from typing import Iterator, Dict, Any
import time
from models.agent import AgentAction

def execute_completion_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """Execute completion tool."""
    
    # Handle both dict and string formats for parameters
    if isinstance(action.parameters, dict):
        result = action.parameters.get("result", "Task completed")
    elif isinstance(action.parameters, str):
        result = action.parameters
    else:
        result = "Task completed"

    # First yield the completion result
    completion_response = {
        "type": "completion",
        "tool_name": "attempt_completion",
        "result": result,
        "success": True,
        "timestamp": time.time(),
    }
    yield completion_response
    
    # Trigger post-requisites automatically for roadmap agent
    try:
        # Import here to avoid circular imports
        from src.agent_management.post_requisites.handlers import get_agent_handler
        
        # Assume this is from roadmap agent (in future, this could be determined from context)
        agent_key = "roadmap"
        
        print(f"\n🔄 Processing post-requisites for {agent_key} agent...")
        
        handler = get_agent_handler(agent_key)
        post_req_result = handler.handle_completion(result)
        
        if post_req_result.get("success"):
            processed_actions = post_req_result.get("processed_actions", [])
            successful_actions = [a for a in processed_actions if a.get("success")]
            
            if successful_actions:
                print(f"✅ Post-requisites completed: {len(successful_actions)} actions processed successfully")
            else:
                print("ℹ️  Post-requisites completed: No actions were required")
        else:
            error_msg = post_req_result.get("error", "Unknown error")
            print(f"⚠️  Post-requisites completed with issues: {error_msg}")
        
        # Yield post-requisites processing result
        yield {
            "type": "post_requisites",
            "tool_name": "post_requisites_processing",
            "result": post_req_result,
            "success": post_req_result.get("success", False),
            "timestamp": time.time(),
        }
        
    except Exception as e:
        print(f"⚠️  Post-requisites processing encountered an error: {str(e)}")
        # If post-requisites fail, yield error but don't fail the completion
        yield {
            "type": "post_requisites_error",
            "tool_name": "post_requisites_processing",
            "result": f"Post-requisites processing failed: {str(e)}",
            "success": False,
            "timestamp": time.time(),
        }
