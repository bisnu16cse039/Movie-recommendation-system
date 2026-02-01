#!/usr/bin/env python3
"""
Create and register ECS task definition (minimal setup - 0.5 vCPU / 1GB RAM)
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

def load_config():
    """Load configuration from aws-config.env"""
    config = {}
    config_file = project_root / 'aws-config.env'
    
    if not config_file.exists():
        print("❌ aws-config.env not found. Run setup scripts first.")
        return None
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key] = value
    
    return config

def create_task_definition():
    """Register ECS task definition"""
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    config = load_config()
    
    if not config:
        return False
    
    # Validate required config
    required = ['MOVIE_RECSYS_API_REPO', 'TASK_EXECUTION_ROLE_ARN', 'TASK_ROLE_ARN', 'S3_BUCKET_NAME']
    missing = [k for k in required if k not in config]
    if missing:
        print(f"❌ Missing required config: {', '.join(missing)}")
        return False
    
    print("=" * 70)
    print("📋 Creating ECS Task Definition")
    print("=" * 70)
    
    ecs = boto3.client('ecs', region_name=region)
    
    # Task definition configuration
    family_name = "movie-recsys-api"
    
    task_definition = {
        "family": family_name,
        "networkMode": "awsvpc",
        "requiresCompatibilities": ["FARGATE"],
        "cpu": "512",  # 0.5 vCPU (lowest cost option)
        "memory": "1024",  # 1 GB
        "executionRoleArn": config['TASK_EXECUTION_ROLE_ARN'],
        "taskRoleArn": config['TASK_ROLE_ARN'],
        "containerDefinitions": [
            {
                "name": "api",
                "image": f"{config['MOVIE_RECSYS_API_REPO']}:latest",
                "essential": True,
                "portMappings": [
                    {
                        "containerPort": 8000,
                        "protocol": "tcp"
                    }
                ],
                "environment": [
                    {"name": "RECSYS_ENVIRONMENT", "value": "production"},
                    {"name": "RECSYS_API__HOST", "value": "0.0.0.0"},
                    {"name": "RECSYS_API__PORT", "value": "8000"},
                    {"name": "RECSYS_API__WORKERS", "value": "1"},  # 1 worker for cost savings
                    {"name": "RECSYS_API__RELOAD", "value": "false"},
                    {"name": "RECSYS_LOGGING__LEVEL", "value": "INFO"},
                    {"name": "S3_BUCKET_NAME", "value": config['S3_BUCKET_NAME']},
                    {"name": "AWS_DEFAULT_REGION", "value": region},
                    {"name": "RECSYS_MODEL__VERSION", "value": "v1.0.0"}
                ],
                "healthCheck": {
                    "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                    "interval": 30,
                    "timeout": 5,
                    "retries": 3,
                    "startPeriod": 90  # Extra time for S3 download + model loading
                },
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": f"/ecs/{family_name}",
                        "awslogs-region": region,
                        "awslogs-stream-prefix": "api",
                        "awslogs-create-group": "true"
                    }
                }
            }
        ]
    }
    
    print("\n📦 Task Definition Configuration:")
    print(f"   Family: {family_name}")
    print(f"   CPU: 512 (0.5 vCPU)")
    print(f"   Memory: 1024 MB (1 GB)")
    print(f"   Network Mode: awsvpc")
    print(f"   Image: {config['MOVIE_RECSYS_API_REPO']}:latest")
    print(f"   Workers: 1")
    print(f"   S3 Bucket: {config['S3_BUCKET_NAME']}")
    
    try:
        print("\n🚀 Registering task definition...")
        response = ecs.register_task_definition(**task_definition)
        
        task_def = response['taskDefinition']
        task_def_arn = task_def['taskDefinitionArn']
        revision = task_def['revision']
        
        print(f"   ✅ Registered: {family_name}:{revision}")
        print(f"   ARN: {task_def_arn}")
        
        # Save to config
        config['TASK_DEFINITION_ARN'] = task_def_arn
        config['TASK_DEFINITION_FAMILY'] = family_name
        config['TASK_DEFINITION_REVISION'] = str(revision)
        
        # Write back to aws-config.env
        config_file = project_root / 'aws-config.env'
        with open(config_file, 'w') as f:
            f.write("# AWS Configuration for Movie Recommendation System\n")
            f.write("# Generated by setup scripts\n\n")
            for key, value in config.items():
                f.write(f"{key}={value}\n")
        
        print(f"\n💾 Configuration saved to: aws-config.env")
        
        print("\n" + "=" * 70)
        print("✅ Task Definition Created Successfully!")
        print("=" * 70)
        
        print("\n💰 Cost Estimate:")
        print("   0.5 vCPU × 1GB RAM")
        print("   ~$7/month (24/7 running)")
        print("   ~$0.23/day")
        print("   ~$0.01/hour")
        
        print("\n💡 Cost Savings Tips:")
        print("   1. Stop service when not testing:")
        print("      aws ecs update-service --cluster movie-recsys-cluster \\")
        print("        --service movie-recsys-api --desired-count 0")
        print("   2. Start when needed:")
        print("      aws ecs update-service --cluster movie-recsys-cluster \\")
        print("        --service movie-recsys-api --desired-count 1")
        
        print("\nNext step: Deploy to ECS")
        print("  python3 src/utils/deploy_ecs.py")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'AccessDeniedException':
            print(f"\n❌ Permission denied. Ask your AWS admin to add:")
            print("   Action: ecs:RegisterTaskDefinition")
            print("   Resource: *")
        else:
            print(f"\n❌ Error registering task definition: {e}")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        success = create_task_definition()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
