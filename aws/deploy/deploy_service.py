#!/usr/bin/env python3
"""
Deploy ECS service to Fargate (minimal setup for learning)
"""
import os
import sys
import time
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

def deploy_ecs():
    """Create ECS cluster and deploy service"""
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    config = load_config()
    
    if not config:
        return False
    
    # Validate required config
    required = ['TASK_DEFINITION_FAMILY', 'SECURITY_GROUP_ID', 'SUBNET_IDS']
    missing = [k for k in required if k not in config]
    if missing:
        print(f"❌ Missing required config: {', '.join(missing)}")
        return False
    
    print("=" * 70)
    print("🚀 Deploying to ECS Fargate")
    print("=" * 70)
    
    ecs = boto3.client('ecs', region_name=region)
    ec2 = boto3.client('ec2', region_name=region)
    iam = boto3.client('iam', region_name=region)
    
    cluster_name = "movie-recsys-cluster"
    service_name = "movie-recsys-api"
    
    # ===================================================================
    # 1. Create ECS Service-Linked Role (if not exists)
    # ===================================================================
    print(f"\n🔑 Checking ECS service-linked role...")
    
    role_name = "AWSServiceRoleForECS"
    role_exists = False
    
    # Check if role exists first
    try:
        iam.get_role(RoleName=role_name)
        print(f"   ✅ ECS service-linked role exists")
        role_exists = True
    except ClientError as e:
        if 'NoSuchEntity' in str(e):
            print(f"   ⚠️  ECS service-linked role does not exist")
            
            # Try to create it
            try:
                print(f"   🔨 Creating ECS service-linked role...")
                response = iam.create_service_linked_role(AWSServiceName='ecs.amazonaws.com')
                print(f"   ✅ Successfully created ECS service-linked role")
                print(f"   ARN: {response['Role']['Arn']}")
                role_exists = True
            except ClientError as create_error:
                if 'InvalidInput' in str(create_error) or 'already exists' in str(create_error):
                    print(f"   ℹ️  Role already exists (race condition)")
                    role_exists = True
                else:
                    print(f"   ❌ Failed to create service-linked role: {create_error}")
                    print("\n   Ask your AWS admin to run:")
                    print("   aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com")
                    return False
        else:
            print(f"   ❌ Error checking role: {e}")
            return False
    
    if not role_exists:
        print("\n❌ ECS service-linked role is required but does not exist")
        return False
    
    # ===================================================================
    # 2. Create ECS Cluster
    # ===================================================================
    print(f"\n📦 Creating ECS cluster: {cluster_name}")
    
    try:
        response = ecs.create_cluster(clusterName=cluster_name)
        print(f"   ✅ Created cluster: {cluster_name}")
    except ClientError as e:
        if 'ClusterAlreadyExistsException' in str(e):
            print(f"   ℹ️  Cluster already exists: {cluster_name}")
        else:
            print(f"   ❌ Error creating cluster: {e}")
            return False
    
    # ===================================================================
    # 3. Create ECS Service
    # ===================================================================
    print(f"\n🚢 Creating ECS service: {service_name}")
    
    # Get subnets (use first 2 for high availability)
    subnets = config['SUBNET_IDS'].split(',')[:2]
    
    try:
        # Check if service already exists
        try:
            existing = ecs.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            
            if existing['services'] and existing['services'][0]['status'] != 'INACTIVE':
                print(f"   ℹ️  Service already exists: {service_name}")
                print(f"   📝 Updating service with latest task definition...")
                
                # Update existing service
                response = ecs.update_service(
                    cluster=cluster_name,
                    service=service_name,
                    taskDefinition=config['TASK_DEFINITION_FAMILY'],
                    desiredCount=1,
                    forceNewDeployment=True
                )
                print(f"   ✅ Service updated successfully")
            else:
                raise Exception("Service needs to be created")
                
        except:
            # Create new service
            response = ecs.create_service(
                cluster=cluster_name,
                serviceName=service_name,
                taskDefinition=config['TASK_DEFINITION_FAMILY'],
                desiredCount=1,
                launchType='FARGATE',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': subnets,
                        'securityGroups': [config['SECURITY_GROUP_ID']],
                        'assignPublicIp': 'ENABLED'  # Need public IP to access
                    }
                },
                deploymentConfiguration={
                    'maximumPercent': 200,
                    'minimumHealthyPercent': 0  # Allow complete replacement
                },
                enableECSManagedTags=True,
                tags=[
                    {'key': 'Project', 'value': 'MovieRecommendationSystem'},
                    {'key': 'Environment', 'value': 'learning'}
                ]
            )
            print(f"   ✅ Service created: {service_name}")
        
        # Save to config
        config['ECS_CLUSTER_NAME'] = cluster_name
        config['ECS_SERVICE_NAME'] = service_name
        
        # Write back to aws-config.env
        config_file = project_root / 'aws-config.env'
        with open(config_file, 'w') as f:
            f.write("# AWS Configuration for Movie Recommendation System\n")
            f.write("# Generated by setup scripts\n\n")
            for key, value in config.items():
                f.write(f"{key}={value}\n")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == 'AccessDeniedException':
            print(f"\n❌ Permission denied: {e}")
        else:
            print(f"\n❌ Error creating service: {e}")
        
        return False
    
    # ===================================================================
    # 4. Wait for task to start and get public IP
    # ===================================================================
    print(f"\n⏳ Waiting for task to start (this may take 2-3 minutes)...")
    print("   - Pulling Docker image from ECR")
    print("   - Downloading models from S3 (~43MB)")
    print("   - Starting API server")
    
    max_attempts = 40  # 40 * 15 seconds = 10 minutes
    attempt = 0
    task_arn = None
    
    while attempt < max_attempts:
        attempt += 1
        time.sleep(15)
        
        # List tasks in service
        tasks = ecs.list_tasks(
            cluster=cluster_name,
            serviceName=service_name,
            desiredStatus='RUNNING'
        )
        
        if tasks['taskArns']:
            task_arn = tasks['taskArns'][0]
            
            # Get task details
            task_details = ecs.describe_tasks(
                cluster=cluster_name,
                tasks=[task_arn]
            )
            
            if task_details['tasks']:
                task = task_details['tasks'][0]
                last_status = task['lastStatus']
                
                print(f"   [{attempt}/{max_attempts}] Status: {last_status}")
                
                if last_status == 'RUNNING':
                    # Get ENI ID to find public IP
                    for attachment in task.get('attachments', []):
                        if attachment['type'] == 'ElasticNetworkInterface':
                            for detail in attachment['details']:
                                if detail['name'] == 'networkInterfaceId':
                                    eni_id = detail['value']
                                    
                                    # Get public IP from ENI
                                    eni = ec2.describe_network_interfaces(
                                        NetworkInterfaceIds=[eni_id]
                                    )
                                    
                                    if eni['NetworkInterfaces']:
                                        public_ip = eni['NetworkInterfaces'][0].get('Association', {}).get('PublicIp')
                                        
                                        if public_ip:
                                            print(f"\n✅ Task is RUNNING!")
                                            print("\n" + "=" * 70)
                                            print("🎉 DEPLOYMENT SUCCESSFUL!")
                                            print("=" * 70)
                                            
                                            print(f"\n📍 Your API is accessible at:")
                                            print(f"   http://{public_ip}:8000")
                                            
                                            print(f"\n📚 API Documentation:")
                                            print(f"   http://{public_ip}:8000/docs")
                                            
                                            print(f"\n🏥 Health Check:")
                                            print(f"   http://{public_ip}:8000/health")
                                            
                                            print(f"\n🧪 Test Recommendations:")
                                            print(f"   curl http://{public_ip}:8000/recommend?movie_id=1")
                                            
                                            print("\n💰 Cost: ~$0.01/hour (~$7/month if left running)")
                                            
                                            print("\n🛑 To stop and save costs:")
                                            print(f"   aws ecs update-service --cluster {cluster_name} \\")
                                            print(f"     --service {service_name} --desired-count 0")
                                            
                                            print("\n▶️  To start again:")
                                            print(f"   aws ecs update-service --cluster {cluster_name} \\")
                                            print(f"     --service {service_name} --desired-count 1")
                                            
                                            print("\n📊 View logs:")
                                            print(f"   aws logs tail /ecs/{config['TASK_DEFINITION_FAMILY']} --follow")
                                            
                                            # Save public IP to config
                                            config['PUBLIC_IP'] = public_ip
                                            with open(config_file, 'w') as f:
                                                f.write("# AWS Configuration for Movie Recommendation System\n")
                                                f.write("# Generated by setup scripts\n\n")
                                                for key, value in config.items():
                                                    f.write(f"{key}={value}\n")
                                            
                                            return True
                    
                    print("   Waiting for public IP assignment...")
                
                elif last_status in ['STOPPED', 'DEPROVISIONING']:
                    # Task failed
                    print(f"\n❌ Task failed to start!")
                    print(f"   Status: {last_status}")
                    
                    if 'stoppedReason' in task:
                        print(f"   Reason: {task['stoppedReason']}")
                    
                    print("\n🔍 Check logs for details:")
                    print(f"   aws logs tail /ecs/{config['TASK_DEFINITION_FAMILY']}")
                    
                    return False
        else:
            print(f"   [{attempt}/{max_attempts}] Waiting for task to be scheduled...")
    
    print("\n⏱️  Timeout waiting for task to start")
    print("   Check ECS console for details")
    return False

if __name__ == '__main__':
    try:
        success = deploy_ecs()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
