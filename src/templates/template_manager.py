"""
Template management module for the OpportunityMailer application.
Handles loading, storing, and retrieving email templates.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TemplateManager:
    """
    Manages email templates for the OpportunityMailer application.
    Templates can be stored locally or in AWS S3.
    """
    
    def __init__(self, storage_type: str = 'local', s3_bucket: Optional[str] = None):
        """
        Initialize the template manager.
        
        Args:
            storage_type: Type of storage to use ('local' or 's3')
            s3_bucket: S3 bucket name for template storage (required if storage_type is 's3')
        """
        self.storage_type = storage_type
        self.s3_bucket = s3_bucket
        
        if storage_type == 's3' and not s3_bucket:
            raise ValueError("S3 bucket name is required when storage_type is 's3'")
        
        if storage_type == 's3':
            self.s3_client = boto3.client('s3')
        
        # Default templates (built-in)
        self.default_templates = {
            "job_application": {
                "name": "job_application",
                "subject": "Application for {position} position at {company}",
                "description": "Initial job application email to a recruiter or hiring manager",
                "html_content": """
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
                """
            },
            "follow_up": {
                "name": "follow_up",
                "subject": "Following up on {position} application at {company}",
                "description": "Follow-up email after submitting an application",
                "html_content": """
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
            },
            "thank_you": {
                "name": "thank_you",
                "subject": "Thank you for the interview - {position} position",
                "description": "Thank you email after an interview",
                "html_content": """
                <html>
                <body>
                    <p>Dear {recruiter_name},</p>
                    
                    <p>Thank you for taking the time to interview me for the {position} position at {company} today. 
                    I appreciated the opportunity to learn more about the role and the team.</p>
                    
                    <p>{interview_highlights}</p>
                    
                    <p>Our conversation reinforced my enthusiasm for the position and my confidence that my skills in 
                    {skills} would enable me to make valuable contributions to your team.</p>
                    
                    <p>Thank you again for your consideration. I'm looking forward to hearing about the next steps 
                    in the process.</p>
                    
                    <p>Best regards,<br>
                    {sender_name}<br>
                    {sender_email}<br>
                    {sender_phone}</p>
                </body>
                </html>
                """
            },
            "connection_request": {
                "name": "connection_request",
                "subject": "Connecting with a fellow {industry} professional",
                "description": "Email to request a professional connection",
                "html_content": """
                <html>
                <body>
                    <p>Dear {recipient_name},</p>
                    
                    <p>I hope this email finds you well. My name is {sender_name}, and I {introduction_context}.</p>
                    
                    <p>I'm reaching out because {connection_reason}. Given your experience in {recipient_expertise}, 
                    I would greatly value the opportunity to connect with you.</p>
                    
                    <p>{specific_request}</p>
                    
                    <p>I understand you're busy, and I appreciate any time you can spare. Thank you for considering 
                    my request.</p>
                    
                    <p>Best regards,<br>
                    {sender_name}<br>
                    {sender_email}<br>
                    {sender_phone}</p>
                </body>
                </html>
                """
            }
        }
    
    def get_template(self, template_name: str) -> Dict[str, Any]:
        """
        Retrieves a template by name.
        
        Args:
            template_name: Name of the template to retrieve
            
        Returns:
            Template dictionary
            
        Raises:
            ValueError: If template is not found
        """
        # First check default templates
        if template_name in self.default_templates:
            return self.default_templates[template_name]
        
        # Then check storage based on storage_type
        if self.storage_type == 'local':
            return self._get_local_template(template_name)
        elif self.storage_type == 's3':
            return self._get_s3_template(template_name)
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    def save_template(self, template: Dict[str, Any]) -> bool:
        """
        Saves a template.
        
        Args:
            template: Template dictionary to save
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If template is missing required fields
        """
        # Validate template
        required_fields = ['name', 'subject', 'html_content']
        missing_fields = [field for field in required_fields if field not in template]
        
        if missing_fields:
            raise ValueError(f"Template missing required fields: {', '.join(missing_fields)}")
        
        # Save based on storage_type
        if self.storage_type == 'local':
            return self._save_local_template(template)
        elif self.storage_type == 's3':
            return self._save_s3_template(template)
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        Lists all available templates.
        
        Returns:
            List of template dictionaries
        """
        templates = list(self.default_templates.values())
        
        # Add templates from storage
        if self.storage_type == 'local':
            templates.extend(self._list_local_templates())
        elif self.storage_type == 's3':
            templates.extend(self._list_s3_templates())
        
        return templates
    
    def delete_template(self, template_name: str) -> bool:
        """
        Deletes a template.
        
        Args:
            template_name: Name of the template to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If attempting to delete a default template
        """
        # Prevent deletion of default templates
        if template_name in self.default_templates:
            raise ValueError(f"Cannot delete default template: {template_name}")
        
        # Delete based on storage_type
        if self.storage_type == 'local':
            return self._delete_local_template(template_name)
        elif self.storage_type == 's3':
            return self._delete_s3_template(template_name)
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    def _get_local_template(self, template_name: str) -> Dict[str, Any]:
        """
        Retrieves a template from local storage.
        
        Args:
            template_name: Name of the template to retrieve
            
        Returns:
            Template dictionary
            
        Raises:
            ValueError: If template is not found
        """
        template_dir = os.path.join(os.path.dirname(__file__), 'custom')
        template_path = os.path.join(template_dir, f"{template_name}.json")
        
        if not os.path.exists(template_path):
            raise ValueError(f"Template not found: {template_name}")
        
        try:
            with open(template_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {str(e)}")
            raise ValueError(f"Error loading template: {str(e)}")
    
    def _save_local_template(self, template: Dict[str, Any]) -> bool:
        """
        Saves a template to local storage.
        
        Args:
            template: Template dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        template_dir = os.path.join(os.path.dirname(__file__), 'custom')
        
        # Create directory if it doesn't exist
        os.makedirs(template_dir, exist_ok=True)
        
        template_path = os.path.join(template_dir, f"{template['name']}.json")
        
        try:
            with open(template_path, 'w') as f:
                json.dump(template, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving template {template['name']}: {str(e)}")
            return False
    
    def _list_local_templates(self) -> List[Dict[str, Any]]:
        """
        Lists templates from local storage.
        
        Returns:
            List of template dictionaries
        """
        templates = []
        template_dir = os.path.join(os.path.dirname(__file__), 'custom')
        
        # Create directory if it doesn't exist
        os.makedirs(template_dir, exist_ok=True)
        
        try:
            for filename in os.listdir(template_dir):
                if filename.endswith('.json'):
                    template_path = os.path.join(template_dir, filename)
                    with open(template_path, 'r') as f:
                        templates.append(json.load(f))
        except Exception as e:
            logger.error(f"Error listing templates: {str(e)}")
        
        return templates
    
    def _delete_local_template(self, template_name: str) -> bool:
        """
        Deletes a template from local storage.
        
        Args:
            template_name: Name of the template to delete
            
        Returns:
            True if successful, False otherwise
        """
        template_dir = os.path.join(os.path.dirname(__file__), 'custom')
        template_path = os.path.join(template_dir, f"{template_name}.json")
        
        if not os.path.exists(template_path):
            raise ValueError(f"Template not found: {template_name}")
        
        try:
            os.remove(template_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting template {template_name}: {str(e)}")
            return False
    
    def _get_s3_template(self, template_name: str) -> Dict[str, Any]:
        """
        Retrieves a template from S3 storage.
        
        Args:
            template_name: Name of the template to retrieve
            
        Returns:
            Template dictionary
            
        Raises:
            ValueError: If template is not found
        """
        if not self.s3_bucket:
            raise ValueError("S3 bucket not configured")
        
        template_key = f"templates/{template_name}.json"
        
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=template_key)
            template_data = response['Body'].read().decode('utf-8')
            return json.loads(template_data)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise ValueError(f"Template not found: {template_name}")
            else:
                logger.error(f"Error retrieving template {template_name}: {str(e)}")
                raise ValueError(f"Error retrieving template: {str(e)}")
    
    def _save_s3_template(self, template: Dict[str, Any]) -> bool:
        """
        Saves a template to S3 storage.
        
        Args:
            template: Template dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        if not self.s3_bucket:
            raise ValueError("S3 bucket not configured")
        
        template_key = f"templates/{template['name']}.json"
        
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=template_key,
                Body=json.dumps(template, indent=2),
                ContentType='application/json'
            )
            return True
        except Exception as e:
            logger.error(f"Error saving template {template['name']}: {str(e)}")
            return False
    
    def _list_s3_templates(self) -> List[Dict[str, Any]]:
        """
        Lists templates from S3 storage.
        
        Returns:
            List of template dictionaries
        """
        if not self.s3_bucket:
            raise ValueError("S3 bucket not configured")
        
        templates = []
        prefix = "templates/"
        
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=prefix)
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.json'):
                        template_response = self.s3_client.get_object(
                            Bucket=self.s3_bucket,
                            Key=obj['Key']
                        )
                        template_data = template_response['Body'].read().decode('utf-8')
                        templates.append(json.loads(template_data))
        except Exception as e:
            logger.error(f"Error listing templates: {str(e)}")
        
        return templates
    
    def _delete_s3_template(self, template_name: str) -> bool:
        """
        Deletes a template from S3 storage.
        
        Args:
            template_name: Name of the template to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.s3_bucket:
            raise ValueError("S3 bucket not configured")
        
        template_key = f"templates/{template_name}.json"
        
        try:
            # Check if template exists
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=template_key)
            
            # Delete template
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=template_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ValueError(f"Template not found: {template_name}")
            else:
                logger.error(f"Error deleting template {template_name}: {str(e)}")
                return False
