#!/usr/bin/env python3
"""
Create security group for ECS tasks (minimal setup for learning)
Uses default VPC for simplicity
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(dotenv_path=project_root / '.env')

def get_my_ip():
    """Get user's public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except Exception as e:
        print(f"⚠️  Could not detect your IP automatically: {e}")
        return input("Enter your public IP address (e.g., 203.0.113.0): ").strip()

def create_security_group():
    """Create security group in default VPC"""
    
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    print("=" * 70)
    print("🔒 Creating Security Group for ECS Tasks")
    print("=" * 70)
    
    ec2 = boto3.client('ec2', region_name=region)
    
    # ===================================================================
    # 1. Get default VPC
    # ===================================================================
    print("\n📡 Finding default VPC...")
    try:
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        if not vpcs['Vpcs']:
            print("❌ No default VPC found. You need to create a VPC first.")
            print("   Run: aws ec2 create-default-vpc")
            return False
        
        vpc_id = vpcs['Vpcs'][0]['VpcId']
        print(f"   ✅ Found default VPC: {vpc_id}")
    except Exception as e:
        print(f"   ❌ Error finding default VPC: {e}")
        return False
    
    # ===================================================================
    # 2. Get public subnets from default VPC
    # ===================================================================
    print("\n📡 Finding public subnets...")
    try:
        subnets = ec2.describe_subnets(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'default-for-az', 'Values': ['true']}
            ]
        )
        
        if not subnets['Subnets']:
            print("❌ No subnets found in default VPC")
            return False
        
        subnet_ids = [s['SubnetId'] for s in subnets['Subnets']]
        print(f"   ✅ Found {len(subnet_ids)} subnets:")
        for subnet in subnets['Subnets']:
            print(f"      - {subnet['SubnetId']} ({subnet['AvailabilityZone']})")
        
    except Exception as e:
        print(f"   ❌ Error finding subnets: {e}")
        return False
    
    # ===================================================================
    # 3. Get user's IP
    # ===================================================================
    print("\n🌍 Getting your public IP address...")
    my_ip = get_my_ip()
    print(f"   ✅ Your IP: {my_ip}")
    
    # ===================================================================
    # 4. Create security group
    # ===================================================================
    sg_name = "movie-recsys-ecs-tasks"
    sg_description = "Security group for Movie Recommendation System ECS tasks"
    
    print(f"\n🔒 Creating security group: {sg_name}")
    
    try:
        # Check if security group already exists
        existing_sgs = ec2.describe_security_groups(
            Filters=[
                {'Name': 'group-name', 'Values': [sg_name]},
                {'Name': 'vpc-id', 'Values': [vpc_id]}
            ]
        )
        
        if existing_sgs['SecurityGroups']:
            sg_id = existing_sgs['SecurityGroups'][0]['GroupId']
            print(f"   ℹ️  Security group already exists: {sg_id}")
        else:
            # Create new security group
            response = ec2.create_security_group(
                GroupName=sg_name,
                Description=sg_description,
                VpcId=vpc_id
            )
            sg_id = response['GroupId']
            print(f"   ✅ Created security group: {sg_id}")
        
        # ===================================================================
        # 5. Configure inbound rules (allow port 8000 from your IP)
        # ===================================================================
        print(f"\n📥 Configuring inbound rules...")
        
        try:
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 8000,
                        'ToPort': 8000,
                        'IpRanges': [
                            {
                                'CidrIp': f'{my_ip}/32',
                                'Description': 'FastAPI port from your IP'
                            }
                        ]
                    }
                ]
            )
            print(f"   ✅ Allow TCP 8000 from {my_ip}/32")
        except ClientError as e:
            if 'InvalidPermission.Duplicate' in str(e):
                print(f"   ℹ️  Rule already exists")
            else:
                raise
        
        # ===================================================================
        # 6. Configure outbound rules (allow HTTPS for S3/ECR)
        # ===================================================================
        print(f"\n📤 Configuring outbound rules...")
        
        # Note: Default security groups allow all outbound traffic
        # We'll verify the default egress rule exists
        sg_details = ec2.describe_security_groups(GroupIds=[sg_id])
        egress_rules = sg_details['SecurityGroups'][0]['IpPermissionsEgress']
        
        if egress_rules:
            print(f"   ✅ Outbound rules already configured (allow all)")
        else:
            # Add outbound rule if needed (shouldn't happen with AWS defaults)
            ec2.authorize_security_group_egress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': '-1',  # All protocols
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            print(f"   ✅ Allow all outbound traffic")
        
        # ===================================================================
        # 7. Save to aws-config.env
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
        
        # Update with new values
        existing_config['VPC_ID'] = vpc_id
        existing_config['SECURITY_GROUP_ID'] = sg_id
        existing_config['SUBNET_IDS'] = ','.join(subnet_ids)
        
        # Write back
        with open(config_file, 'w') as f:
            f.write("# AWS Configuration for Movie Recommendation System\n")
            f.write("# Generated by setup scripts\n\n")
            for key, value in existing_config.items():
                f.write(f"{key}={value}\n")
        
        print(f"✅ Configuration saved to: {config_file.name}")
        print("\n📋 Network Configuration:")
        print(f"   VPC_ID: {vpc_id}")
        print(f"   SECURITY_GROUP_ID: {sg_id}")
        print(f"   SUBNET_IDS: {','.join(subnet_ids)}")
        
        print("\n" + "=" * 70)
        print("✅ Security Group Setup Complete!")
        print("=" * 70)
        
        print(f"\n⚠️  IMPORTANT: Your ECS tasks will only be accessible from {my_ip}")
        print("   To allow access from other IPs, update the security group in AWS Console")
        
        print("\nNext step: Create ECS task definition")
        print("  python3 src/utils/create_task_definition.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating security group: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        success = create_security_group()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
