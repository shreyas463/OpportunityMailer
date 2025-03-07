#!/usr/bin/env python3
"""
Local test script for the OpportunityMailer Lambda function.
This script allows testing the Lambda function locally before deployment.
"""
import json
import argparse
import logging
from typing import Dict, Any

from src.lambda.email_sender import lambda_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('local_test')


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test OpportunityMailer locally')
    
    parser.add_argument('--recipient', required=True, help='Recipient email address')
    parser.add_argument('--subject', default='Test Email from OpportunityMailer', help='Email subject')
    parser.add_argument('--template', default='job_application', help='Template name')
    parser.add_argument('--sender', help='Sender email address (must be verified in SES)')
    parser.add_argument('--data', help='JSON file with template data')
    
    return parser.parse_args()


def main() -> None:
    """Main test function."""
    args = parse_args()
    
    # Load template data
    if args.data:
        with open(args.data, 'r') as f:
            template_data = json.load(f)
    else:
        # Default template data
        template_data = {
            'recruiter_name': 'Hiring Manager',
            'sender_name': 'Job Applicant',
            'position': 'Software Engineer',
            'company': 'Example Company',
            'background': 'software development',
            'custom_paragraph': 'I am particularly interested in this role because of the opportunity to work on innovative projects and contribute to your team.',
            'sender_email': args.sender if args.sender else 'applicant@example.com',
            'sender_phone': '123-456-7890'
        }
    
    # Create test event
    event = {
        'body': json.dumps({
            'recipient_email': args.recipient,
            'subject': args.subject,
            'template_name': args.template,
            'template_data': template_data,
            'sender_email': args.sender
        })
    }
    
    # Call Lambda handler
    logger.info(f"Sending test email to {args.recipient}")
    response = lambda_handler(event, {})
    
    # Print response
    logger.info(f"Response status code: {response['statusCode']}")
    logger.info(f"Response body: {response['body']}")


if __name__ == '__main__':
    main()
