#!/usr/bin/env python3
"""
Create IAM roles for ECS deployment (minimal setup for learning)
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(dotenv_path=project_root / '.env')

def create_iam_roles():
    """Create ECS Task Execution Role and Task Role"""
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    account_id = os.getenv('AWS_ACCOUNT_ID')
    bucket_name = os.getenv('S3_BUCKET_NAME')
    
    if not account_id:
        print("❌ AWS_ACCOUNT_ID not found in .env or aws-config.env")
        print("   Please add it to .env file")
        return False
    
    print("=" * 70)
    print("🔐 Creating IAM Roles for ECS")
    print("=" * 70)
    
    iam = boto3.client('iam', region_name=region)
    
    # Trust policy for ECS tasks
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    roles_created = {}
    
    # ===================================================================
    # 1. Task Execution Role (for ECS to pull images and write logs)
    # ===================================================================
    exec_role_name = "ecsTaskExecutionRole-movie-recsys"
    
    try:
        print(f"\n📋 Creating Task Execution Role: {exec_role_name}")
        
        try:
            response = iam.create_role(
                RoleName=exec_role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="ECS Task Execution Role for Movie Recommendation System"
            )
            exec_role_arn = response['Role']['Arn']
            print(f"   ✅ Created: {exec_role_arn}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                response = iam.get_role(RoleName=exec_role_name)
                exec_role_arn = response['Role']['Arn']
                print(f"   ℹ️  Already exists: {exec_role_arn}")
            else:
                raise
        
        # Attach AWS managed policy for ECS task execution
        iam.attach_role_policy(
            RoleName=exec_role_name,
            PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'
        )
        print(f"   ✅ Attached: AmazonECSTaskExecutionRolePolicy")
        
        # Add custom policy for ECR and CloudWatch Logs
        exec_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:CreateLogGroup"
                    ],
                    "Resource": f"arn:aws:logs:{region}:{account_id}:log-group:/ecs/movie-recsys*"
                }
            ]
        }
        
        try:
            iam.put_role_policy(
                RoleName=exec_role_name,
                PolicyName='ECR-CloudWatch-Access',
                PolicyDocument=json.dumps(exec_policy)
            )
            print(f"   ✅ Added inline policy: ECR-CloudWatch-Access")
        except ClientError as e:
            print(f"   ℹ️  Policy already exists or updated")
        
        roles_created['TASK_EXECUTION_ROLE_ARN'] = exec_role_arn
        
    except Exception as e:
        print(f"   ❌ Error creating Task Execution Role: {e}")
        return False
    
    # ===================================================================
    # 2. Task Role (for application to access S3)
    # ===================================================================
    task_role_name = "ecsTaskRole-movie-recsys"
    
    try:
        print(f"\n📋 Creating Task Role: {task_role_name}")
        
        try:
            response = iam.create_role(
                RoleName=task_role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="ECS Task Role for Movie Recommendation System - S3 access"
            )
            task_role_arn = response['Role']['Arn']
            print(f"   ✅ Created: {task_role_arn}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                response = iam.get_role(RoleName=task_role_name)
                task_role_arn = response['Role']['Arn']
                print(f"   ℹ️  Already exists: {task_role_arn}")
            else:
                raise
        
        # Add S3 read access policy
        s3_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ]
                }
            ]
        }
        
        try:
            iam.put_role_policy(
                RoleName=task_role_name,
                PolicyName='S3-ModelAccess',
                PolicyDocument=json.dumps(s3_policy)
            )
            print(f"   ✅ Added inline policy: S3-ModelAccess")
            print(f"   📦 S3 Bucket: {bucket_name}")
        except ClientError as e:
            print(f"   ℹ️  Policy already exists or updated")
        
        roles_created['TASK_ROLE_ARN'] = task_role_arn
        
    except Exception as e:
        print(f"   ❌ Error creating Task Role: {e}")
        return False
    
    # ===================================================================
    # 3. Save to aws-config.env
    # ===================================================================
    print("\n" + "=" * 70)
    print("💾 Saving configuration to aws-config.env")
    print("=" * 70)
    
    config_file = project_root / 'aws-config.env'
    
    # Read existing config
    existing_config = {}
    if config_file.exists():
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_config[key] = value
    
    # Update with new roles
    existing_config.update(roles_created)
    
    # Write back
    with open(config_file, 'w') as f:
        f.write("# AWS Configuration for Movie Recommendation System\n")
        f.write("# Generated by setup_iam_roles.py\n\n")
        for key, value in existing_config.items():
            f.write(f"{key}={value}\n")
    
    print(f"✅ Configuration saved to: {config_file.name}")
    print("\n📋 Created Roles:")
    for key, value in roles_created.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 70)
    print("✅ IAM Roles Setup Complete!")
    print("=" * 70)
    print("\nNext step: Create security group")
    print("  python3 src/utils/setup_security_group.py")
    
    return True

if __name__ == '__main__':
    try:
        success = create_iam_roles()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
