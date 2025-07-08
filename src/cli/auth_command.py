"""
Authentication CLI commands for SutraKnowledge.

This module provides command-line interfaces for managing authentication
tokens for various LLM providers.
"""

import sys
import webbrowser
from typing import Optional
from loguru import logger
import click
import requests
from ..services.auth.token_manager import get_token_manager


@click.group()
def auth():
    """Authentication management commands."""
    pass


@auth.command()
@click.option('--provider', default='superllm', help='Provider name (default: superllm)')
@click.option('--token', help='Firebase token (if not provided, will prompt)')
@click.option('--api-endpoint', default='http://localhost:8000', help='SuperLLM API endpoint')
@click.option('--web-url', default='http://localhost:3000', help='SuperLLM web interface URL')
@click.option('--auto-open', is_flag=True, help='Automatically open web interface')
def login(provider: str, token: Optional[str], api_endpoint: str, web_url: str, auto_open: bool):
    """
    Authenticate with SuperLLM and store the token.
    
    This command helps you authenticate with SuperLLM by:
    1. Opening the web interface (optional)
    2. Prompting for your Firebase token
    3. Validating the token
    4. Storing it securely
    """
    click.echo(f"🔐 Authenticating with {provider.upper()}")
    click.echo("=" * 50)
    
    # Open web interface if requested
    if auto_open:
        click.echo(f"🌐 Opening SuperLLM web interface: {web_url}")
        try:
            webbrowser.open(web_url)
        except Exception as e:
            click.echo(f"⚠️  Could not open browser: {e}")
            click.echo(f"   Please manually open: {web_url}")
    else:
        click.echo(f"📱 Please open the SuperLLM web interface: {web_url}")
    
    click.echo("\n📋 Steps to get your token:")
    click.echo("   1. Sign in or create an account")
    click.echo("   2. Copy the Firebase authentication token")
    click.echo("   3. Paste it below")
    
    # Get token from user if not provided
    if not token:
        click.echo()
        token = click.prompt("🔑 Enter your Firebase token", hide_input=True)
    
    if not token or not token.strip():
        click.echo("❌ No token provided. Exiting.")
        sys.exit(1)
    
    token = token.strip()
    
    # Validate token by making a test API call
    click.echo("\n🔍 Validating token...")
    
    if _validate_token(token, api_endpoint):
        # Store the token
        token_manager = get_token_manager()
        metadata = {
            'api_endpoint': api_endpoint,
            'web_url': web_url,
            'validated_at': None  # Will be set by token manager
        }
        
        token_manager.store_token(provider, token, metadata)
        
        click.echo("✅ Token validated and stored successfully!")
        click.echo(f"   Provider: {provider}")
        click.echo(f"   API Endpoint: {api_endpoint}")
        click.echo("\n🎉 You can now use SutraKnowledge with SuperLLM!")
        click.echo("   Set your provider to 'superllm' in the configuration.")
        
    else:
        click.echo("❌ Token validation failed.")
        click.echo("   Please check:")
        click.echo("   • Token is correct and not expired")
        click.echo("   • SuperLLM server is running")
        click.echo(f"   • API endpoint is correct: {api_endpoint}")
        sys.exit(1)


@auth.command()
@click.option('--provider', help='Specific provider to check (default: all)')
def status(provider: Optional[str]):
    """Check authentication status for providers."""
    token_manager = get_token_manager()
    providers = token_manager.list_providers()
    
    if not providers:
        click.echo("🔓 No authentication tokens stored.")
        return
    
    click.echo("🔐 Authentication Status")
    click.echo("=" * 50)
    
    for prov_name, info in providers.items():
        if provider and prov_name != provider:
            continue
        
        click.echo(f"\n📡 Provider: {prov_name}")
        click.echo(f"   Status: {'✅ Authenticated' if info['has_token'] else '❌ No token'}")
        
        if info['stored_at']:
            click.echo(f"   Stored: {info['stored_at']}")
        
        if info['metadata']:
            metadata = info['metadata']
            if 'api_endpoint' in metadata:
                click.echo(f"   Endpoint: {metadata['api_endpoint']}")
            if 'web_url' in metadata:
                click.echo(f"   Web URL: {metadata['web_url']}")


@auth.command()
@click.option('--provider', default='superllm', help='Provider to logout from')
@click.confirmation_option(prompt='Are you sure you want to remove the authentication token?')
def logout(provider: str):
    """Remove authentication token for a provider."""
    token_manager = get_token_manager()
    
    if token_manager.remove_token(provider):
        click.echo(f"✅ Logged out from {provider}")
    else:
        click.echo(f"⚠️  No token found for {provider}")


@auth.command()
@click.option('--provider', default='superllm', help='Provider to test')
@click.option('--api-endpoint', help='Override API endpoint for testing')
def test(provider: str, api_endpoint: Optional[str]):
    """Test authentication with a provider."""
    token_manager = get_token_manager()
    token = token_manager.get_token(provider)
    
    if not token:
        click.echo(f"❌ No token found for {provider}")
        click.echo(f"   Run 'sutra auth login --provider {provider}' first")
        return
    
    # Get API endpoint
    if not api_endpoint:
        providers = token_manager.list_providers()
        if provider in providers and 'api_endpoint' in providers[provider]['metadata']:
            api_endpoint = providers[provider]['metadata']['api_endpoint']
        else:
            api_endpoint = 'http://localhost:8000'  # Default
    
    click.echo(f"🧪 Testing authentication with {provider}")
    click.echo(f"   Endpoint: {api_endpoint}")
    
    if _validate_token(token, api_endpoint):
        click.echo("✅ Authentication test successful!")
    else:
        click.echo("❌ Authentication test failed!")
        click.echo("   Token may be expired or invalid.")
        click.echo(f"   Try: sutra auth login --provider {provider}")


@auth.command()
@click.confirmation_option(prompt='Are you sure you want to clear ALL authentication tokens?')
def clear():
    """Clear all stored authentication tokens."""
    token_manager = get_token_manager()
    token_manager.clear_all_tokens()
    click.echo("✅ All authentication tokens cleared")


def _validate_token(token: str, api_endpoint: str) -> bool:
    """
    Validate a Firebase token by making a test API call.
    
    Args:
        token: Firebase token to validate
        api_endpoint: SuperLLM API endpoint
        
    Returns:
        True if token is valid, False otherwise
    """
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Try to get models list (lightweight endpoint)
        response = requests.get(
            f"{api_endpoint}/api/v1/models",
            headers=headers,
            timeout=10
        )
        
        return response.status_code == 200
        
    except requests.exceptions.ConnectionError:
        click.echo(f"⚠️  Could not connect to {api_endpoint}")
        click.echo("   Make sure SuperLLM server is running")
        return False
    except requests.exceptions.Timeout:
        click.echo("⚠️  Request timed out")
        return False
    except Exception as e:
        logger.debug(f"Token validation error: {e}")
        return False


# Add to main CLI if this is being used as a standalone module
if __name__ == '__main__':
    auth()
