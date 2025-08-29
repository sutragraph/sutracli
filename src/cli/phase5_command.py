"""
Phase 5 Command Handler

Handles the run-phase5 CLI command for connection matching analysis.
"""

import sys
import os
from pathlib import Path
from loguru import logger
from typing import Dict, Any, Optional

def handle_run_phase5_command() -> None:
    """Handle run-phase5 command for connection matching."""
    try:
        print("🔗 SUTRA PHASE 5 - Connection Matching Analysis")
        print("   Analyzing database connections and finding matches")
        print("=" * 80)

        # Run Phase 5 diagnostics first
        print("🔍 Running Phase 5 diagnostics...")
        diagnostic_result = _run_phase5_diagnostics()
        
        if not diagnostic_result["success"]:
            print(f"❌ Diagnostic failed: {diagnostic_result['error']}")

        # Run Phase 5 connection matching
        print("🚀 Starting Phase 5 connection matching...")
        print("-" * 40)
        
        matching_result = _run_connection_matching()
        
        if matching_result["success"]:
            matches = matching_result.get("results", {}).get("matches", [])
            print(f"✅ Phase 5 completed successfully!")
            print(f"📊 Found {len(matches)} connection matches")
            
            # Display sample matches
            if matches:
                print("\n🔗 Sample matches:")
                for i, match in enumerate(matches[:3]):  # Show first 3 matches
                    confidence = match.get("match_confidence", "unknown")
                    reason = match.get("match_reason", "No reason provided")
                    print(f"   Match {i+1}: {confidence} confidence - {reason[:60]}...")
                
                if len(matches) > 3:
                    print(f"   ... and {len(matches) - 3} more matches")

                print("\n💾 Storing results in database...")
                storage_result = _store_phase5_results(matching_result)
                
                if storage_result["success"]:
                    print(f"✅ Successfully stored {len(matches)} connection mappings")
                else:
                    print(f"❌ Failed to store results: {storage_result['error']}")
                
        else:
            print(f"❌ Phase 5 failed: {matching_result['error']}")
            
            # Provide helpful suggestions
            error_msg = str(matching_result.get('error', '')).lower()
            if "aws_region" in error_msg or "environment variable" in error_msg:
                print("\n💡 Suggestions:")
                print("   • Check your AWS configuration in ~/.sutra/config/system.json")
                print("   • Set AWS_REGION environment variable")
                print("   • Try using a different provider: --provider anthropic")
            elif "baml" in error_msg:
                print("\n💡 Suggestions:")
                print("   • Check BAML configuration")
                print("   • Verify LLM provider credentials")
                print("   • Try running with --log-level DEBUG for more details")

        print("\n🎉 Phase 5 Analysis Completed!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error during Phase 5 execution: {e}")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

def _run_phase5_diagnostics() -> Dict[str, Any]:
    """Run Phase 5 diagnostics to check system readiness."""
    try:
        from graph.sqlite_client import SQLiteConnection

        # Check database connection
        db_client = SQLiteConnection()

        # Check connection data
        incoming_query = "SELECT COUNT(*) as count FROM incoming_connections"
        incoming_result = db_client.execute_query(incoming_query)
        incoming_count = incoming_result[0]['count'] if incoming_result else 0

        outgoing_query = "SELECT COUNT(*) as count FROM outgoing_connections"
        outgoing_result = db_client.execute_query(outgoing_query)
        outgoing_count = outgoing_result[0]['count'] if outgoing_result else 0

        print(f"📊 Database status: {incoming_count} incoming, {outgoing_count} outgoing connections")

        if incoming_count == 0 and outgoing_count == 0:
            return {
                "success": False,
                "error": "No connection data found in database. Run cross-indexing analysis first."
            }
        elif incoming_count == 0:
            return {
                "success": False,
                "error": "No incoming connections found in database"
            }
        elif outgoing_count == 0:
            return {
                "success": False,
                "error": "No outgoing connections found in database"
            }

        return {"success": True}

    except Exception as e:
        return {
            "success": False,
            "error": f"Diagnostic failed: {str(e)}"
        }

def _run_connection_matching() -> Dict[str, Any]:
    """Run the actual Phase 5 connection matching."""
    try:
        from services.cross_indexing.prompts.phase5_connection_matching.phase5_prompt_manager import Phase5PromptManager
        
        # Create Phase 5 manager
        phase5_manager = Phase5PromptManager()
        
        # Run connection matching
        result = phase5_manager.run_connection_matching()
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection matching failed: {str(e)}"
        }

def _store_phase5_results(matching_result: Dict[str, Any]) -> Dict[str, Any]:
    """Store Phase 5 results in database."""
    try:
        from graph.graph_operations import GraphOperations
        
        if not matching_result.get("success"):
            return {
                "success": False,
                "error": "Cannot store failed matching results"
            }
        
        # Get matches
        results = matching_result.get("results", {})
        matches = results.get("matches", [])
        
        if not matches:
            return {
                "success": True,
                "message": "No matches to store"
            }
        
        # Prepare matches for database storage
        graph_ops = GraphOperations()
        db_matches = []
        
        for match in matches:
            db_matches.append({
                'sender_id': match.get('outgoing_id'),
                'receiver_id': match.get('incoming_id'),
                'description': match.get('match_reason', 'Auto-detected connection'),
                'match_confidence': _convert_confidence_to_float(match.get('match_confidence', 'medium'))
            })
        
        # Store mappings
        mapping_result = graph_ops.create_connection_mappings(db_matches)
        
        return mapping_result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Storage failed: {str(e)}"
        }

def _convert_confidence_to_float(confidence: str) -> float:
    """Convert confidence level string to float."""
    confidence_map = {'high': 0.9, 'medium': 0.7, 'low': 0.5}
    return confidence_map.get(confidence.lower(), 0.5)
