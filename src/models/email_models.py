"""
Data models for the OpportunityMailer application.
These models define the structure of data used throughout the application.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field


class EmailTemplate(BaseModel):
    """Model representing an email template"""
    name: str = Field(..., description="Unique name of the template")
    subject: str = Field(..., description="Default subject line for the template")
    html_content: str = Field(..., description="HTML content of the template with placeholders")
    plain_content: Optional[str] = Field(None, description="Plain text version of the template")
    description: Optional[str] = Field(None, description="Description of when to use this template")


class EmailRequest(BaseModel):
    """Model representing a request to send an email"""
    recipient_email: EmailStr = Field(..., description="Email address of the recipient")
    subject: str = Field(..., description="Subject line of the email")
    template_name: str = Field(..., description="Name of the template to use")
    template_data: Dict[str, Any] = Field(default_factory=dict, description="Data for personalizing the template")
    sender_email: Optional[EmailStr] = Field(None, description="Email address of the sender")
    cc_emails: List[EmailStr] = Field(default_factory=list, description="List of CC email addresses")
    reply_to_emails: List[EmailStr] = Field(default_factory=list, description="List of Reply-To email addresses")
    attachments: List[str] = Field(default_factory=list, description="List of attachment file paths or S3 URIs")


class EmailResponse(BaseModel):
    """Model representing a response after sending an email"""
    message_id: str = Field(..., description="SES message ID of the sent email")
    status: str = Field(..., description="Status of the email sending operation")
    timestamp: str = Field(..., description="Timestamp when the email was sent")
    recipient: EmailStr = Field(..., description="Email address of the recipient")


class RecipientInfo(BaseModel):
    """Model representing information about a recipient"""
    email: EmailStr = Field(..., description="Email address of the recipient")
    first_name: Optional[str] = Field(None, description="First name of the recipient")
    last_name: Optional[str] = Field(None, description="Last name of the recipient")
    company: Optional[str] = Field(None, description="Company name of the recipient")
    position: Optional[str] = Field(None, description="Position/title of the recipient")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn URL of the recipient")
    notes: Optional[str] = Field(None, description="Additional notes about the recipient")


class SenderProfile(BaseModel):
    """Model representing a sender profile"""
    email: EmailStr = Field(..., description="Email address of the sender")
    first_name: str = Field(..., description="First name of the sender")
    last_name: str = Field(..., description="Last name of the sender")
    phone: Optional[str] = Field(None, description="Phone number of the sender")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn URL of the sender")
    resume_url: Optional[str] = Field(None, description="URL to the sender's resume")
    signature_html: Optional[str] = Field(None, description="HTML signature of the sender")
