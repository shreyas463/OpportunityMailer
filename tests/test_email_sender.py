"""
Tests for the email_sender Lambda function.
"""
import json
import unittest
from unittest.mock import patch, MagicMock

import boto3
from moto import mock_ses

from src.lambda.email_sender import lambda_handler, validate_request, get_template_content


class TestEmailSender(unittest.TestCase):
    """Test cases for the email_sender Lambda function."""
    
    def setUp(self):
        """Set up test environment."""
        self.valid_event = {
            'body': json.dumps({
                'recipient_email': 'recipient@example.com',
                'subject': 'Test Subject',
                'template_name': 'job_application',
                'template_data': {
                    'recruiter_name': 'John Doe',
                    'sender_name': 'Jane Smith',
                    'position': 'Software Engineer',
                    'company': 'Acme Inc',
                    'background': 'software development',
                    'custom_paragraph': 'This is a custom paragraph.',
                    'sender_email': 'jane@example.com',
                    'sender_phone': '123-456-7890'
                }
            })
        }
        
        self.invalid_event = {
            'body': json.dumps({
                'subject': 'Test Subject',
                'template_name': 'job_application'
                # Missing recipient_email
            })
        }
    
    def test_validate_request_valid(self):
        """Test validate_request with valid input."""
        result = validate_request(self.valid_event)
        self.assertEqual(result['recipient_email'], 'recipient@example.com')
        self.assertEqual(result['subject'], 'Test Subject')
        self.assertEqual(result['template_name'], 'job_application')
    
    def test_validate_request_invalid(self):
        """Test validate_request with invalid input."""
        with self.assertRaises(ValueError):
            validate_request(self.invalid_event)
    
    def test_get_template_content(self):
        """Test get_template_content."""
        template_data = {
            'recruiter_name': 'John Doe',
            'sender_name': 'Jane Smith',
            'position': 'Software Engineer',
            'company': 'Acme Inc',
            'background': 'software development',
            'custom_paragraph': 'This is a custom paragraph.',
            'sender_email': 'jane@example.com',
            'sender_phone': '123-456-7890'
        }
        
        result = get_template_content('job_application', template_data)
        
        # Check that all placeholders were replaced
        self.assertIn('John Doe', result)
        self.assertIn('Jane Smith', result)
        self.assertIn('Software Engineer', result)
        self.assertIn('Acme Inc', result)
        self.assertIn('software development', result)
        self.assertIn('This is a custom paragraph.', result)
        self.assertIn('jane@example.com', result)
        self.assertIn('123-456-7890', result)
    
    def test_get_template_content_invalid_template(self):
        """Test get_template_content with invalid template name."""
        with self.assertRaises(ValueError):
            get_template_content('nonexistent_template', {})
    
    @mock_ses
    def test_lambda_handler_success(self):
        """Test lambda_handler with valid input."""
        # Set up mock SES
        ses_client = boto3.client('ses', region_name='us-east-1')
        ses_client.verify_email_identity(EmailAddress='jane@example.com')
        
        with patch('boto3.client') as mock_client:
            mock_ses = MagicMock()
            mock_ses.send_email.return_value = {'MessageId': 'test-message-id'}
            mock_client.return_value = mock_ses
            
            response = lambda_handler(self.valid_event, {})
            
            self.assertEqual(response['statusCode'], 200)
            self.assertIn('message', json.loads(response['body']))
            self.assertIn('messageId', json.loads(response['body']))
    
    def test_lambda_handler_validation_error(self):
        """Test lambda_handler with invalid input."""
        response = lambda_handler(self.invalid_event, {})
        
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('error', json.loads(response['body']))
        self.assertIn('message', json.loads(response['body']))


if __name__ == '__main__':
    unittest.main()
