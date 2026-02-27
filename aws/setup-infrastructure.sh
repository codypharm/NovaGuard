#!/bin/bash
set -e

echo "=========================================="
echo "Nova Guard AWS Infrastructure Setup"
echo "=========================================="

REQUIRED_VARS=("AWS_ACCOUNT_ID" "AWS_REGION")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set"
        exit 1
    fi
done

VPC_CIDR="10.1.0.0/16"
PUBLIC_SUBNET_1="10.1.1.0/24"
PUBLIC_SUBNET_2="10.1.2.0/24"
PRIVATE_SUBNET_1="10.1.10.0/24"
PRIVATE_SUBNET_2="10.1.11.0/24"

echo "Step 1: Creating VPC..."
VPC_ID=$(aws ec2 create-vpc --cidr-block $VPC_CIDR --query 'Vpc.VpcId' --output text --region $AWS_REGION)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=nova-guard-vpc --region $AWS_REGION
echo "  VPC: $VPC_ID"

echo "Step 2: Creating subnets..."
PUBLIC_SUBNET_1_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $PUBLIC_SUBNET_1 --availability-zone ${AWS_REGION}a --query 'Subnet.SubnetId' --output text --region $AWS_REGION)
PUBLIC_SUBNET_2_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $PUBLIC_SUBNET_2 --availability-zone ${AWS_REGION}b --query 'Subnet.SubnetId' --output text --region $AWS_REGION)
PRIVATE_SUBNET_1_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $PRIVATE_SUBNET_1 --availability-zone ${AWS_REGION}a --query 'Subnet.SubnetId' --output text --region $AWS_REGION)
PRIVATE_SUBNET_2_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block $PRIVATE_SUBNET_2 --availability-zone ${AWS_REGION}b --query 'Subnet.SubnetId' --output text --region $AWS_REGION)
echo "  Public: $PUBLIC_SUBNET_1_ID, $PUBLIC_SUBNET_2_ID"
echo "  Private: $PRIVATE_SUBNET_1_ID, $PRIVATE_SUBNET_2_ID"

echo "Step 3: Creating Internet Gateway..."
IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text --region $AWS_REGION)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID --region $AWS_REGION
echo "  IGW: $IGW_ID"

echo "Step 4: Creating public route table..."
PUBLIC_RT_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text --region $AWS_REGION)
aws ec2 create-route --route-table-id $PUBLIC_RT_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID --region $AWS_REGION
aws ec2 associate-route-table --route-table-id $PUBLIC_RT_ID --subnet-id $PUBLIC_SUBNET_1_ID --region $AWS_REGION
aws ec2 associate-route-table --route-table-id $PUBLIC_RT_ID --subnet-id $PUBLIC_SUBNET_2_ID --region $AWS_REGION

echo "Step 5: Creating NAT Gateways..."
EIP_1=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text --region $AWS_REGION)
NAT_GW_1_ID=$(aws ec2 create-nat-gateway --subnet-id $PUBLIC_SUBNET_1_ID --allocation-id $EIP_1 --query 'NatGateway.NatGatewayId' --output text --region $AWS_REGION)
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW_1_ID --region $AWS_REGION

EIP_2=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text --region $AWS_REGION)
NAT_GW_2_ID=$(aws ec2 create-nat-gateway --subnet-id $PUBLIC_SUBNET_2_ID --allocation-id $EIP_2 --query 'NatGateway.NatGatewayId' --output text --region $AWS_REGION)
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW_2_ID --region $AWS_REGION

echo "Step 6: Creating private route tables..."
PRIVATE_RT_1_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text --region $AWS_REGION)
aws ec2 create-route --route-table-id $PRIVATE_RT_1_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_GW_1_ID --region $AWS_REGION
aws ec2 associate-route-table --route-table-id $PRIVATE_RT_1_ID --subnet-id $PRIVATE_SUBNET_1_ID --region $AWS_REGION

PRIVATE_RT_2_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text --region $AWS_REGION)
aws ec2 create-route --route-table-id $PRIVATE_RT_2_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_GW_2_ID --region $AWS_REGION
aws ec2 associate-route-table --route-table-id $PRIVATE_RT_2_ID --subnet-id $PRIVATE_SUBNET_2_ID --region $AWS_REGION

echo "Step 7: Creating ECS Cluster..."
aws ecs create-cluster --cluster-name nova-guard-cluster --region $AWS_REGION --query 'cluster.clusterArn' --output text

echo "Step 8: Creating ECR repositories..."
aws ecr create-repository --repository-name nova-guard-api --region $AWS_REGION || true
aws ecr create-repository --repository-name nova-guard-frontend --region $AWS_REGION || true

echo "=========================================="
echo "Infrastructure setup complete!"
echo "=========================================="
