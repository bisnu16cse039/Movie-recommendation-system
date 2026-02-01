#!/usr/bin/env python3
"""
Check ECS deployment status and get public IP
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
import boto3

# Load environment
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(dotenv_path=project_root / '.env')

def load_config():
    """Load configuration from aws-config.env"""
    config = {}
    config_file = project_root / 'aws-config.env'
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key] = value
    
    return config

def check_status():
    """Check ECS service status"""
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    config = load_config()
    
    cluster_name = config.get('ECS_CLUSTER_NAME', 'movie-recsys-cluster')
    service_name = config.get('ECS_SERVICE_NAME', 'movie-recsys-api')
    
    print("=" * 70)
    print("📊 ECS Deployment Status")
    print("=" * 70)
    
    ecs = boto3.client('ecs', region_name=region)
    ec2 = boto3.client('ec2', region_name=region)
    
    # Get service status
    print(f"\n🔍 Checking service: {service_name}")
    
    try:
        services = ecs.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )
        
        if not services['services']:
            print(f"   ❌ Service not found")
            return False
        
        service = services['services'][0]
        
        print(f"   Status: {service['status']}")
        print(f"   Desired: {service['desiredCount']} tasks")
        print(f"   Running: {service['runningCount']} tasks")
        print(f"   Pending: {service['pendingCount']} tasks")
        
        # Get task details
        tasks = ecs.list_tasks(
            cluster=cluster_name,
            serviceName=service_name,
            desiredStatus='RUNNING'
        )
        
        if not tasks['taskArns']:
            print(f"\n⏳ No running tasks yet")
            
            # Check for stopped tasks (failures)
            stopped_tasks = ecs.list_tasks(
                cluster=cluster_name,
                serviceName=service_name,
                desiredStatus='STOPPED'
            )
            
            if stopped_tasks['taskArns']:
                print(f"\n⚠️  Found {len(stopped_tasks['taskArns'])} stopped tasks")
                
                # Get details of most recent stopped task
                task_details = ecs.describe_tasks(
                    cluster=cluster_name,
                    tasks=[stopped_tasks['taskArns'][0]]
                )
                
                if task_details['tasks']:
                    task = task_details['tasks'][0]
                    print(f"\n❌ Last task failed:")
                    print(f"   Status: {task['lastStatus']}")
                    if 'stoppedReason' in task:
                        print(f"   Reason: {task['stoppedReason']}")
                    
                    if 'containers' in task and task['containers']:
                        for container in task['containers']:
                            if 'reason' in container:
                                print(f"   Container: {container['reason']}")
            
            print(f"\n💡 Tips:")
            print(f"   - Wait 2-3 minutes for task to start")
            print(f"   - Check logs: aws logs tail /ecs/movie-recsys-api --follow")
            print(f"   - View in console: https://console.aws.amazon.com/ecs/v2/clusters/{cluster_name}/services/{service_name}")
            
            return False
        
        # Get running task details
        task_arn = tasks['taskArns'][0]
        task_details = ecs.describe_tasks(
            cluster=cluster_name,
            tasks=[task_arn]
        )
        
        if not task_details['tasks']:
            print(f"   ❌ Could not get task details")
            return False
        
        task = task_details['tasks'][0]
        print(f"\n📋 Task Details:")
        print(f"   Task ARN: {task_arn.split('/')[-1]}")
        print(f"   Status: {task['lastStatus']}")
        print(f"   Health: {task.get('healthStatus', 'UNKNOWN')}")
        
        # Get public IP
        public_ip = None
        private_ip = None
        eni_id = None
        
        for attachment in task.get('attachments', []):
            if attachment['type'] == 'ElasticNetworkInterface':
                for detail in attachment['details']:
                    if detail['name'] == 'networkInterfaceId':
                        eni_id = detail['value']
                        
                        try:
                            eni = ec2.describe_network_interfaces(
                                NetworkInterfaceIds=[eni_id]
                            )
                            
                            if eni['NetworkInterfaces']:
                                ni = eni['NetworkInterfaces'][0]
                                private_ip = ni.get('PrivateIpAddress')
                                assoc = ni.get('Association', {})
                                public_ip = assoc.get('PublicIp')
                        except Exception as e:
                            print(f"   ⚠️  Error getting ENI details: {e}")
        
        if eni_id:
            print(f"   ENI: {eni_id}")
        if private_ip:
            print(f"   Private IP: {private_ip}")
        if public_ip:
            print(f"   Public IP: {public_ip}")
            
            print("\n" + "=" * 70)
            print("✅ Deployment Successful!")
            print("=" * 70)
            
            print(f"\n🌐 Access Your API:")
            print(f"   API: http://{public_ip}:8000")
            print(f"   Docs: http://{public_ip}:8000/docs")
            print(f"   Health: http://{public_ip}:8000/health")
            
            print(f"\n🧪 Test:")
            print(f"   curl http://{public_ip}:8000/recommend?movie_id=1")
            
            print(f"\n📊 Logs:")
            print(f"   aws logs tail /ecs/movie-recsys-api --follow")
            
            print(f"\n💰 Cost: ~$0.01/hour (~$7/month)")
            
            print(f"\n🛑 Stop to save costs:")
            print(f"   aws ecs update-service --cluster {cluster_name} \\")
            print(f"     --service {service_name} --desired-count 0 --region {region}")
            
            return True
        else:
            print(f"   ⏳ Waiting for public IP assignment...")
            print(f"\n   Run this script again in 30 seconds")
            return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == '__main__':
    try:
        success = check_status()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
