"""
AWS Lambda function for sending cold emails using Amazon SES.
This module handles the core email sending functionality of the OpportunityMailer application.
"""
import json
import os
import logging
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SES client
ses_client = boto3.client('ses')

def validate_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the incoming Lambda event to ensure it contains all required fields.
    
    Args:
        event: The Lambda event object
        
    Returns:
        Dict containing the validated request data
        
    Raises:
        ValueError: If required fields are missing
    """
    try:
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Required fields
        required_fields = ['recipient_email', 'subject', 'template_name']
        missing_fields = [field for field in required_fields if field not in body]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        return body
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in request body")

def get_template_content(template_name: str, template_data: Dict[str, Any]) -> str:
    """
    Retrieves and personalizes an email template.
    
    Args:
        template_name: Name of the template to use
        template_data: Data for personalizing the template
        
    Returns:
        Personalized email content
    """
    # In a production app, templates could be stored in S3, DynamoDB, or a file system
    # For this example, we'll use a simple dictionary of templates
    templates = {
        "job_application": """
        <html>
        <body>
            <p>Dear {recruiter_name},</p>
            
            <p>I hope this email finds you well. My name is {sender_name}, and I came across the {position} 
            position at {company}. I'm very interested in this opportunity and believe my background in 
            {background} makes me a strong candidate.</p>
            
            <p>{custom_paragraph}</p>
            
            <p>I've attached my resume for your review. I would welcome the opportunity to discuss how 
            my skills and experience align with your team's needs.</p>
            
            <p>Thank you for considering my application. I look forward to the possibility of speaking with you.</p>
            
            <p>Best regards,<br>
            {sender_name}<br>
            {sender_email}<br>
            {sender_phone}</p>
        </body>
        </html>
        """,
        "follow_up": """
        <html>
        <body>
            <p>Dear {recruiter_name},</p>
            
            <p>I hope you're doing well. I'm writing to follow up on my application for the {position} 
            position that I submitted on {application_date}.</p>
            
            <p>I remain very interested in the opportunity to join {company} and contribute to your team. 
            {custom_paragraph}</p>
            
            <p>If you need any additional information from me, please don't hesitate to ask.</p>
            
            <p>Thank you for your time and consideration.</p>
            
            <p>Best regards,<br>
            {sender_name}<br>
            {sender_email}<br>
            {sender_phone}</p>
        </body>
        </html>
        """
    }
    
    if template_name not in templates:
        raise ValueError(f"Template '{template_name}' not found")
    
    template = templates[template_name]
    
    # Replace placeholders with actual data
    # This is a simple implementation; consider using a proper templating engine
    for key, value in template_data.items():
        placeholder = "{" + key + "}"
        template = template.replace(placeholder, str(value))
    
    return template

def send_email(
    recipient_email: str,
    subject: str,
    html_content: str,
    sender_email: Optional[str] = None,
    cc_emails: Optional[List[str]] = None,
    reply_to_emails: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Sends an email using Amazon SES.
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject line
        html_content: HTML content of the email
        sender_email: Email address of the sender (defaults to configured default)
        cc_emails: List of CC email addresses
        reply_to_emails: List of Reply-To email addresses
        
    Returns:
        Dict containing the SES response
        
    Raises:
        ClientError: If there's an error sending the email
    """
    # Use configured sender email if not provided
    if not sender_email:
        sender_email = os.environ.get('DEFAULT_SENDER_EMAIL', 'noreply@example.com')
    
    # Prepare email message
    message = {
        'Subject': {'Data': subject},
        'Body': {'Html': {'Data': html_content}}
    }
    
    # Prepare email parameters
    email_params = {
        'Source': sender_email,
        'Destination': {
            'ToAddresses': [recipient_email]
        },
        'Message': message
    }
    
    # Add CC addresses if provided
    if cc_emails:
        email_params['Destination']['CcAddresses'] = cc_emails
    
    # Add Reply-To addresses if provided
    if reply_to_emails:
        email_params['ReplyToAddresses'] = reply_to_emails
    
    try:
        response = ses_client.send_email(**email_params)
        logger.info(f"Email sent successfully! Message ID: {response['MessageId']}")
        return response
    except ClientError as e:
        logger.error(f"Error sending email: {e}")
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for processing email requests.
    
    Args:
        event: Lambda event object
        context: Lambda context object
        
    Returns:
        API Gateway response object
    """
    try:
        # Validate request
        request_data = validate_request(event)
        
        # Extract required fields
        recipient_email = request_data['recipient_email']
        subject = request_data['subject']
        template_name = request_data['template_name']
        
        # Extract optional fields
        template_data = request_data.get('template_data', {})
        sender_email = request_data.get('sender_email')
        cc_emails = request_data.get('cc_emails', [])
        reply_to_emails = request_data.get('reply_to_emails', [])
        
        # Get personalized email content
        html_content = get_template_content(template_name, template_data)
        
        # Send email
        response = send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            sender_email=sender_email,
            cc_emails=cc_emails,
            reply_to_emails=reply_to_emails
        )
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Email sent successfully',
                'messageId': response['MessageId']
            })
        }
    except ValueError as e:
        # Return validation error response
        logger.error(f"Validation error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Validation error',
                'message': str(e)
            })
        }
    except ClientError as e:
        # Return SES error response
        logger.error(f"SES error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Email sending failed',
                'message': str(e)
            })
        }
    except Exception as e:
        # Return unexpected error response
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
