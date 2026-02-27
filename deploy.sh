#!/bin/bash
set -e

echo "=========================================="
echo "Nova Guard Deployment Script"
echo "=========================================="

REQUIRED_VARS=("AWS_ACCOUNT_ID" "AWS_REGION" "CLUSTER_NAME" "SERVICE_NAME" "DATABASE_URL" "NOVA_API_KEY")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set"
        exit 1
    fi
done

AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-$(aws configure get aws_access_key_id)}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-$(aws configure get aws_secret_access_key)}"

ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_NAME="${ECR_REPO}/nova-guard-api:${IMAGE_TAG}"

echo "Configuration:"
echo "  AWS Account: ${AWS_ACCOUNT_ID}"
echo "  Region: ${AWS_REGION}"
echo "  Cluster: ${CLUSTER_NAME}"
echo "  Service: ${SERVICE_NAME}"
echo "  Image: ${IMAGE_NAME}"
echo ""

echo "Step 1: Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}

echo "Step 2: Building Docker image..."
docker build -t nova-guard-api:latest .

echo "Step 3: Tagging image..."
docker tag nova-guard-api:latest ${IMAGE_NAME}

echo "Step 4: Pushing image to ECR..."
docker push ${IMAGE_NAME}

echo "Step 5: Updating ECS task definition..."
TASK_DEFINITION=$(cat aws/task-definition.json | \
    sed "s/\${AWS_ACCOUNT_ID}/${AWS_ACCOUNT_ID}/g" | \
    sed "s/\${AWS_REGION}/${AWS_REGION}/g" | \
    sed "s|\${DATABASE_URL}|${DATABASE_URL}|g" | \
    sed "s|\${AWS_ACCESS_KEY_ID}|${AWS_ACCESS_KEY_ID}|g" | \
    sed "s|\${AWS_SECRET_ACCESS_KEY}|${AWS_SECRET_ACCESS_KEY}|g" | \
    sed "s|\${NOVA_API_KEY}|${NOVA_API_KEY}|g" | \
    sed "s|\${OPENFDA_API_KEY}|${OPENFDA_API_KEY:-}|g")

TASK_REVISION=$(aws ecs register-task-definition \
    --cli-input-json "${TASK_DEFINITION}" \
    --region ${AWS_REGION} \
    --query 'taskDefinition.revision' \
    --output text)

echo "  Task revision: ${TASK_REVISION}"

echo "Step 6: Updating ECS service..."
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME} \
    --task-definition nova-guard-api:${TASK_REVISION} \
    --region ${AWS_REGION} \
    --force-new-deployment

echo "Step 7: Waiting for deployment..."
aws ecs wait services-stable \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME} \
    --region ${AWS_REGION}

echo ""
echo "=========================================="
echo "Deployment completed!"
echo "=========================================="
