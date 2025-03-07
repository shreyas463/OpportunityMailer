#!/usr/bin/env python3
"""
Deployment script for the OpportunityMailer application.
This script handles packaging and deploying the application to AWS Lambda.
"""
import os
import sys
import json
import shutil
import argparse
import logging
import subprocess
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('deploy')

# Constants
PACKAGE_DIR = 'package'
LAMBDA_HANDLER = 'src.lambda.email_sender.lambda_handler'
LAMBDA_RUNTIME = 'python3.9'
LAMBDA_FUNCTION_NAME = 'OpportunityMailer'
LAMBDA_ROLE_NAME = 'OpportunityMailerRole'
LAMBDA_POLICY_NAME = 'OpportunityMailerPolicy'


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Deploy OpportunityMailer to AWS Lambda')
    
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--profile', help='AWS CLI profile to use')
    parser.add_argument('--function-name', default=LAMBDA_FUNCTION_NAME, help='Lambda function name')
    parser.add_argument('--create-role', action='store_true', help='Create IAM role for Lambda')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--env-file', default='.env', help='Path to .env file')
    parser.add_argument('--skip-package', action='store_true', help='Skip packaging step')
    parser.add_argument('--skip-deploy', action='store_true', help='Skip deployment step')
    parser.add_argument('--timeout', type=int, default=30, help='Lambda function timeout in seconds')
    parser.add_argument('--memory-size', type=int, default=128, help='Lambda function memory size in MB')
    
    return parser.parse_args()


def create_iam_role(role_name: str, policy_name: str, region: str) -> str:
    """
    Create IAM role for Lambda function with necessary permissions.
    
    Args:
        role_name: Name of the IAM role
        policy_name: Name of the IAM policy
        region: AWS region
        
    Returns:
        ARN of the created role
    """
    logger.info(f"Creating IAM role: {role_name}")
    
    # Initialize IAM client
    iam_client = boto3.client('iam')
    
    # Create trust policy for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Create role
    try:
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for OpportunityMailer Lambda function'
        )
        role_arn = response['Role']['Arn']
        logger.info(f"Created role: {role_arn}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            logger.info(f"Role {role_name} already exists, retrieving ARN")
            response = iam_client.get_role(RoleName=role_name)
            role_arn = response['Role']['Arn']
        else:
            logger.error(f"Error creating role: {str(e)}")
            raise
    
    # Create policy document
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:DeleteObject"
                ],
                "Resource": [
                    "arn:aws:s3:::*/*",
                    "arn:aws:s3:::*"
                ]
            }
        ]
    }
    
    # Create policy
    try:
        policy_response = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document),
            Description='Policy for OpportunityMailer Lambda function'
        )
        policy_arn = policy_response['Policy']['Arn']
        logger.info(f"Created policy: {policy_arn}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            logger.info(f"Policy {policy_name} already exists, retrieving ARN")
            account_id = boto3.client('sts').get_caller_identity().get('Account')
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
        else:
            logger.error(f"Error creating policy: {str(e)}")
            raise
    
    # Attach policy to role
    try:
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
        logger.info(f"Attached policy {policy_arn} to role {role_name}")
    except ClientError as e:
        logger.error(f"Error attaching policy to role: {str(e)}")
        raise
    
    # Wait for role to propagate
    logger.info("Waiting for role to propagate...")
    import time
    time.sleep(10)
    
    return role_arn


def package_application() -> str:
    """
    Package the application for deployment to AWS Lambda.
    
    Returns:
        Path to the created ZIP file
    """
    logger.info("Packaging application...")
    
    # Create package directory
    if os.path.exists(PACKAGE_DIR):
        shutil.rmtree(PACKAGE_DIR)
    os.makedirs(PACKAGE_DIR)
    
    # Install dependencies
    logger.info("Installing dependencies...")
    subprocess.run([
        sys.executable, '-m', 'pip', 'install',
        '-r', 'requirements.txt',
        '--target', PACKAGE_DIR
    ], check=True)
    
    # Copy application code
    logger.info("Copying application code...")
    shutil.copytree('src', os.path.join(PACKAGE_DIR, 'src'))
    shutil.copytree('config', os.path.join(PACKAGE_DIR, 'config'))
    
    # Create ZIP file
    zip_file = 'deployment-package.zip'
    logger.info(f"Creating ZIP file: {zip_file}")
    
    cwd = os.getcwd()
    os.chdir(PACKAGE_DIR)
    subprocess.run(['zip', '-r', f'../{zip_file}', '.'], check=True)
    os.chdir(cwd)
    
    return os.path.abspath(zip_file)


def create_or_update_lambda(
    function_name: str,
    zip_file: str,
    role_arn: str,
    handler: str,
    runtime: str,
    region: str,
    timeout: int,
    memory_size: int,
    environment_variables: Optional[Dict[str, str]] = None
) -> str:
    """
    Create or update AWS Lambda function.
    
    Args:
        function_name: Name of the Lambda function
        zip_file: Path to the ZIP deployment package
        role_arn: ARN of the IAM role
        handler: Lambda function handler
        runtime: Lambda runtime
        region: AWS region
        timeout: Lambda function timeout in seconds
        memory_size: Lambda function memory size in MB
        environment_variables: Environment variables for the Lambda function
        
    Returns:
        ARN of the Lambda function
    """
    logger.info(f"Deploying Lambda function: {function_name}")
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Read ZIP file
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    # Create or update function
    try:
        # Check if function exists
        lambda_client.get_function(FunctionName=function_name)
        
        # Update function
        logger.info(f"Updating existing Lambda function: {function_name}")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        # Update configuration
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Handler=handler,
            Role=role_arn,
            Timeout=timeout,
            MemorySize=memory_size,
            Environment={'Variables': environment_variables or {}}
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # Create function
            logger.info(f"Creating new Lambda function: {function_name}")
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime=runtime,
                Role=role_arn,
                Handler=handler,
                Code={'ZipFile': zip_content},
                Timeout=timeout,
                MemorySize=memory_size,
                Environment={'Variables': environment_variables or {}}
            )
        else:
            logger.error(f"Error deploying Lambda function: {str(e)}")
            raise
    
    function_arn = response['FunctionArn']
    logger.info(f"Lambda function deployed: {function_arn}")
    
    return function_arn


def load_env_file(env_file: str) -> Dict[str, str]:
    """
    Load environment variables from .env file.
    
    Args:
        env_file: Path to .env file
        
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    
    if os.path.exists(env_file):
        logger.info(f"Loading environment variables from {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    else:
        logger.warning(f"Environment file not found: {env_file}")
    
    return env_vars


def main() -> None:
    """Main deployment function."""
    args = parse_args()
    
    # Set AWS profile if provided
    if args.profile:
        os.environ['AWS_PROFILE'] = args.profile
    
    # Load environment variables
    env_vars = load_env_file(args.env_file)
    
    # Package application
    if not args.skip_package:
        zip_file = package_application()
    else:
        zip_file = 'deployment-package.zip'
        if not os.path.exists(zip_file):
            logger.error(f"Deployment package not found: {zip_file}")
            sys.exit(1)
    
    # Deploy to AWS Lambda
    if not args.skip_deploy:
        # Create IAM role if requested
        if args.create_role:
            role_arn = create_iam_role(LAMBDA_ROLE_NAME, LAMBDA_POLICY_NAME, args.region)
        else:
            # Get existing role ARN
            try:
                iam_client = boto3.client('iam')
                response = iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)
                role_arn = response['Role']['Arn']
                logger.info(f"Using existing role: {role_arn}")
            except ClientError as e:
                logger.error(f"Error getting role: {str(e)}")
                logger.error("Use --create-role to create a new role")
                sys.exit(1)
        
        # Deploy Lambda function
        function_arn = create_or_update_lambda(
            function_name=args.function_name,
            zip_file=zip_file,
            role_arn=role_arn,
            handler=LAMBDA_HANDLER,
            runtime=LAMBDA_RUNTIME,
            region=args.region,
            timeout=args.timeout,
            memory_size=args.memory_size,
            environment_variables=env_vars
        )
        
        logger.info(f"Deployment complete: {function_arn}")
    
    # Clean up
    if os.path.exists(PACKAGE_DIR):
        shutil.rmtree(PACKAGE_DIR)
    
    logger.info("Done!")


if __name__ == '__main__':
    main()
