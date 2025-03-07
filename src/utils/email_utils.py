"""
Utility functions for email operations in the OpportunityMailer application.
"""
import re
import logging
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_email(email: str) -> bool:
    """
    Validates an email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if the email is valid, False otherwise
    """
    # Basic email validation regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def personalize_content(template: str, data: Dict[str, Any]) -> str:
    """
    Replaces placeholders in a template with actual data.
    
    Args:
        template: Template string with placeholders in the format {placeholder}
        data: Dictionary of data to replace placeholders
        
    Returns:
        Personalized content with placeholders replaced
    """
    personalized = template
    
    # Replace each placeholder with its corresponding value
    for key, value in data.items():
        placeholder = "{" + key + "}"
        personalized = personalized.replace(placeholder, str(value))
    
    # Check for any remaining placeholders
    remaining_placeholders = re.findall(r'{([^{}]+)}', personalized)
    if remaining_placeholders:
        logger.warning(f"Unfilled placeholders in template: {remaining_placeholders}")
    
    return personalized


def extract_name_from_email(email: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Attempts to extract first and last name from an email address.
    
    Args:
        email: Email address
        
    Returns:
        Tuple of (first_name, last_name) or (None, None) if extraction fails
    """
    if not validate_email(email):
        return None, None
    
    # Extract the username part (before @)
    username = email.split('@')[0]
    
    # Try to split by common separators
    for separator in ['.', '_', '-']:
        if separator in username:
            parts = username.split(separator)
            if len(parts) >= 2:
                return parts[0].capitalize(), parts[1].capitalize()
    
    # If no separator, return the username as first name
    return username.capitalize(), None


def generate_follow_up_subject(original_subject: str) -> str:
    """
    Generates a follow-up subject line based on the original subject.
    
    Args:
        original_subject: Original email subject
        
    Returns:
        Follow-up subject line
    """
    # Check if it already has a follow-up prefix
    if re.match(r'^(Re:|Follow.up:|Following up)', original_subject, re.IGNORECASE):
        return original_subject
    
    return f"Following up: {original_subject}"


def get_email_signature(profile: Dict[str, Any]) -> str:
    """
    Generates an HTML email signature from a profile.
    
    Args:
        profile: Dictionary containing profile information
        
    Returns:
        HTML signature
    """
    # If a custom signature is provided, use it
    if profile.get('signature_html'):
        return profile['signature_html']
    
    # Otherwise, generate a basic signature
    signature = "<p>Best regards,<br>"
    
    if profile.get('first_name') and profile.get('last_name'):
        signature += f"{profile['first_name']} {profile['last_name']}<br>"
    
    if profile.get('email'):
        signature += f"{profile['email']}<br>"
    
    if profile.get('phone'):
        signature += f"{profile['phone']}<br>"
    
    if profile.get('linkedin_url'):
        signature += f"<a href='{profile['linkedin_url']}'>LinkedIn Profile</a><br>"
    
    signature += "</p>"
    
    return signature


def check_spam_triggers(subject: str, content: str) -> List[str]:
    """
    Checks for common spam triggers in email subject and content.
    
    Args:
        subject: Email subject
        content: Email content
        
    Returns:
        List of potential spam triggers found
    """
    # List of common spam trigger words and patterns
    spam_triggers = [
        'free', 'guarantee', 'no obligation', 'no risk', 'offer', 'urgent',
        'winner', 'won', 'congratulations', '100%', 'act now', 'amazing',
        'cash', 'discount', 'earn money', 'eliminate debt', 'extra income',
        'fast cash', 'for only', 'limited time', 'money back', 'no catch',
        'no experience', 'no fees', 'opportunity', 'promise', 'pure profit',
        'risk-free', 'satisfaction guaranteed', 'no spam'
    ]
    
    # Combine subject and content for checking
    combined_text = (subject + ' ' + content).lower()
    
    # Find matches
    found_triggers = []
    for trigger in spam_triggers:
        if f" {trigger.lower()} " in f" {combined_text} ":
            found_triggers.append(trigger)
    
    return found_triggers
