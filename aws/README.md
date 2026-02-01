# AWS Deployment Guide

Deploy the Movie Recommendation System to AWS ECS Fargate with this minimal learning-focused setup.

## 🎯 What You'll Deploy

- **FastAPI** running on ECS Fargate (serverless containers)
- **Docker image** stored in ECR
- **ML models** stored in S3 (~43MB)
- **Cost**: ~$7/month (24/7) or ~$0.01/hour

---

## 📋 Prerequisites

### 1. AWS Account Setup
- AWS Account with programmatic access
- AWS credentials configured in `.env` file
- Region: `us-east-1`

### 2. IAM Permissions Required

Ask your AWS admin to grant these permissions:

**IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:PassRole",
        "iam:CreateServiceLinkedRole"
      ],
      "Resource": [
        "arn:aws:iam::*:role/ecsTaskExecutionRole-movie-recsys",
        "arn:aws:iam::*:role/ecsTaskRole-movie-recsys",
        "arn:aws:iam::*:role/aws-service-role/ecs.amazonaws.com/AWSServiceRoleForECS"
      ]
    }
  ]
}
```

**ECR Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "ecr:CreateRepository",
    "ecr:DescribeRepositories",
    "ecr:GetAuthorizationToken",
    "ecr:BatchCheckLayerAvailability",
    "ecr:PutImage",
    "ecr:InitiateLayerUpload",
    "ecr:UploadLayerPart",
    "ecr:CompleteLayerUpload"
  ],
  "Resource": "*"
}
```

**EC2/VPC Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:DescribeVpcs",
    "ec2:DescribeSubnets",
    "ec2:CreateSecurityGroup",
    "ec2:DescribeSecurityGroups",
    "ec2:AuthorizeSecurityGroupIngress",
    "ec2:DescribeNetworkInterfaces"
  ],
  "Resource": "*"
}
```

**ECS Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "ecs:RegisterTaskDefinition",
    "ecs:CreateCluster",
    "ecs:CreateService",
    "ecs:UpdateService",
    "ecs:DescribeServices",
    "ecs:DescribeTasks",
    "ecs:ListTasks",
    "ecs:TagResource",
    "logs:CreateLogGroup"
  ],
  "Resource": "*"
}
```

### 3. Environment Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Verify boto3 installed
python3 -c "import boto3; print('✓ boto3 ready')"
```

---

## 🚀 Deployment Steps

### Step 0: Create ECR Repositories

```bash
python3 aws/setup/00_create_ecr_repos.py
```

Creates 3 ECR repositories for Docker images. Saves repo URIs to `aws-config.env`.

---

### Step 1: Create IAM Roles

```bash
python3 aws/setup/01_create_iam_roles.py
```

Creates:
- **Task Execution Role**: Allows ECS to pull images from ECR and write logs
- **Task Role**: Allows containers to read models from S3

Saves role ARNs to `aws-config.env`.

---

### Step 2: Create Security Group

```bash
python3 aws/setup/02_create_security_group.py
```

- Creates security group in default VPC
- Opens port 8000 from your IP only
- Configures outbound rules for S3/ECR access

Saves security group ID to `aws-config.env`.

---

### Step 3: Register Task Definition

```bash
python3 aws/setup/03_register_task_definition.py
```

Registers ECS task definition with:
- **CPU**: 0.5 vCPU (512 units)
- **Memory**: 1 GB (1024 MB)
- **Workers**: 1 (for cost savings)
- **Health check**: `/health` endpoint
- **Environment**: S3 bucket, region, model version

Saves task definition ARN to `aws-config.env`.

---

### Step 4: Build & Push Docker Image

```bash
# Build for Linux AMD64 (required for Fargate)
docker build --platform linux/amd64 --target serving -t movie-recsys-api:latest .

# Push to ECR
python3 aws/deploy/push_image.py
```

Builds and pushes your API Docker image to ECR.

---

### Step 5: Deploy to ECS

```bash
python3 aws/deploy/deploy_service.py
```

- Creates ECS cluster
- Deploys service with 1 task
- Waits for task to start (2-3 minutes)
- Shows public IP when ready

---

### Step 6: Check Status

```bash
python3 aws/utils/check_status.py
```

Shows current deployment status, task health, and public IP.

---

## 🌐 Accessing Your API

Once deployed, you'll get a public IP (e.g., `100.53.26.15`):

```bash
# Health check
curl http://<PUBLIC_IP>:8000/health

# Get recommendations
curl "http://<PUBLIC_IP>:8000/recommend?movie_id=1"

# API documentation
open http://<PUBLIC_IP>:8000/docs
```

---

## 🛠️ Common Operations

### Update API

```bash
# Make code changes, rebuild image
docker build --platform linux/amd64 --target serving -t movie-recsys-api:latest .

# Push new image
python3 aws/deploy/push_image.py

# Force redeploy
python3 aws/deploy/deploy_service.py
```

### Stop Service (Save Costs)

```bash
# Stop all tasks (cost = $0)
aws ecs update-service --cluster movie-recsys-cluster \
  --service movie-recsys-api --desired-count 0 --region us-east-1
```

### Start Service

```bash
# Start 1 task
aws ecs update-service --cluster movie-recsys-cluster \
  --service movie-recsys-api --desired-count 1 --region us-east-1
```

### View Logs

Go to CloudWatch:
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Fecs$252Fmovie-recsys-api

Or use AWS CLI:
```bash
aws logs tail /ecs/movie-recsys-api --follow --region us-east-1
```

### Add Your IP to Security Group

If you change networks or can't connect:

```bash
# Get your IP and add to security group
curl https://api.ipify.org  # Get your IP
# Then manually add in AWS Console or update security group
```

---

## 💰 Cost Breakdown

**ECS Fargate (0.5 vCPU, 1GB RAM):**
- Per hour: ~$0.01
- Per day: ~$0.24
- Per month (24/7): ~$7

**S3 Storage (models ~43MB):**
- Storage: ~$0.001/month
- Requests: Negligible

**ECR Storage:**
- ~$0.10/month per image

**Total: ~$7-8/month** if running 24/7

**Cost Savings:**
- Run only 8 hours/day: ~$2.30/month
- Stop when not testing: Pay only when running

---

## 🔒 Security Best Practices

1. **Never commit credentials**: `.env` and `aws-config.env` are in `.gitignore`
2. **Rotate AWS keys** regularly in IAM Console
3. **Restrict security group**: Only allow your IP, not `0.0.0.0/0`
4. **Use IAM roles**: Task Role handles S3 access (no hardcoded keys)
5. **Enable AWS CloudTrail**: Monitor API calls for security audits

---

## 🐛 Troubleshooting

### Can't connect to API

1. **Verify public IP** in ECS Console
2. **Check security group** allows your IP on port 8000
3. **View logs** in CloudWatch for container errors
4. **Verify task is healthy**: `python3 aws/utils/check_status.py`

### Image pull errors

```bash
# Rebuild for correct platform
docker build --platform linux/amd64 --target serving -t movie-recsys-api:latest .

# Push again
python3 aws/deploy/push_image.py
```

### Permission errors

- Check IAM permissions listed in Prerequisites
- Verify AWS credentials in `.env` are correct
- Ensure you're in `us-east-1` region

### Task fails to start

- Check CloudWatch logs for error messages
- Verify S3 bucket exists and models are uploaded
- Ensure task role has S3 read permissions

---

## 📁 Project Structure

```
aws/
├── README.md                    # This file
├── setup/                       # One-time setup scripts
│   ├── 00_create_ecr_repos.py   # Create ECR repositories
│   ├── 01_create_iam_roles.py   # Create IAM roles
│   ├── 02_create_security_group.py  # Create security group
│   └── 03_register_task_definition.py  # Register task definition
├── deploy/                      # Deployment scripts
│   ├── push_image.py            # Push Docker image to ECR
│   └── deploy_service.py        # Deploy/update ECS service
└── utils/                       # Helper scripts
    └── check_status.py          # Check deployment status

aws-config.env                   # Generated config (gitignored)
```

---

## 🧹 Cleanup (Delete Everything)

When done learning, delete all AWS resources:

```bash
# Delete ECS service
aws ecs delete-service --cluster movie-recsys-cluster \
  --service movie-recsys-api --force --region us-east-1

# Delete ECS cluster
aws ecs delete-cluster --cluster movie-recsys-cluster --region us-east-1

# Delete ECR images and repositories
aws ecr delete-repository --repository-name movie-recsys/api --force --region us-east-1
aws ecr delete-repository --repository-name movie-recsys/training --force --region us-east-1
aws ecr delete-repository --repository-name movie-recsys/retraining --force --region us-east-1

# Delete S3 bucket
aws s3 rb s3://movie-recsys-models-prod --force

# Delete security group (get ID from aws-config.env)
aws ec2 delete-security-group --group-id sg-xxxxxxxxx --region us-east-1

# Delete IAM roles
aws iam delete-role --role-name ecsTaskExecutionRole-movie-recsys
aws iam delete-role --role-name ecsTaskRole-movie-recsys
```

---

## 📚 Next Steps

- Add Application Load Balancer for production
- Implement CI/CD with GitHub Actions
- Add CloudWatch alarms and monitoring
- Scale to multiple tasks with auto-scaling
- Set up custom domain with Route 53

---

**Deployed**: February 1, 2026  
**Region**: us-east-1  
**Cost**: ~$7/month (0.5 vCPU, 1GB RAM)
