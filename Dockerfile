# Multi-stage build for AgentFirst2 MVP Lambda
# Uses AWS Lambda Python 3.11 base image for compatibility

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY app/requirements.txt .

# Install Python dependencies with proper platform tags for Lambda
# Use manylinux2014 to ensure compatibility with Lambda runtime
RUN pip install \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --only-binary=:all: \
    --upgrade \
    --target "${LAMBDA_TASK_ROOT:-.}" \
    -r requirements.txt

# Stage 2: Runtime
FROM public.ecr.aws/lambda/python:3.11

# Copy dependencies from builder
COPY --from=builder /build ${LAMBDA_TASK_ROOT}

# Copy application code
COPY app/ ${LAMBDA_TASK_ROOT}/app/

# Copy Lambda handler entry point
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Copy scripts directory (for ECS polling service)
COPY scripts/ ${LAMBDA_TASK_ROOT}/scripts/

# Set Lambda handler
CMD ["lambda_handler.lambda_handler"]
