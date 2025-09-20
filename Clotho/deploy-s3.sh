#!/bin/bash

# Clotho S3 Deployment Script
set -e

echo "🚀 Deploying Clotho to S3"
echo "========================="

# Configuration - Update these values
S3_BUCKET="your-clotho-bucket"
CLOUDFRONT_DISTRIBUTION_ID=""  # Optional, for CloudFront invalidation
AWS_PROFILE="default"  # Change if using different AWS profile
AWS_REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first:"
    echo "  brew install awscli  # macOS"
    echo "  pip install awscli  # Python"
    exit 1
fi

# Check if bucket name is set
if [ "$S3_BUCKET" = "your-clotho-bucket" ]; then
    print_error "Please update the S3_BUCKET variable in this script with your actual bucket name"
    exit 1
fi

echo ""
print_status "Step 1: Building the application..."
if npm run build; then
    print_success "Build completed successfully"
else
    print_error "Build failed"
    exit 1
fi

echo ""
print_status "Step 2: Checking if S3 bucket exists..."
if aws s3 ls "s3://$S3_BUCKET" --profile "$AWS_PROFILE" > /dev/null 2>&1; then
    print_success "S3 bucket exists: $S3_BUCKET"
else
    print_warning "S3 bucket doesn't exist. Creating it..."
    if aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION" --profile "$AWS_PROFILE"; then
        print_success "S3 bucket created: $S3_BUCKET"
    else
        print_error "Failed to create S3 bucket"
        exit 1
    fi
fi

echo ""
print_status "Step 3: Configuring S3 bucket for static website hosting..."
aws s3 website "s3://$S3_BUCKET" \
    --index-document index.html \
    --error-document index.html \
    --profile "$AWS_PROFILE"

# Create bucket policy for public read access
cat > /tmp/s3-bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::${S3_BUCKET}/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy \
    --bucket "$S3_BUCKET" \
    --policy file:///tmp/s3-bucket-policy.json \
    --profile "$AWS_PROFILE"

print_success "S3 bucket configured for static website hosting"

echo ""
print_status "Step 4: Uploading files to S3..."
aws s3 sync dist/ "s3://$S3_BUCKET" \
    --profile "$AWS_PROFILE" \
    --delete \
    --cache-control "public, max-age=31536000" \
    --exclude "*.html" \
    --exclude "*.json"

# Upload HTML files with shorter cache
aws s3 sync dist/ "s3://$S3_BUCKET" \
    --profile "$AWS_PROFILE" \
    --cache-control "public, max-age=3600" \
    --exclude "*" \
    --include "*.html" \
    --include "*.json"

print_success "Files uploaded to S3"

echo ""
print_status "Step 5: Setting correct content types..."
# Set correct content type for CSS files
aws s3 cp "s3://$S3_BUCKET" "s3://$S3_BUCKET" \
    --recursive \
    --exclude "*" \
    --include "*.css" \
    --content-type "text/css" \
    --metadata-directive REPLACE \
    --profile "$AWS_PROFILE"

# Set correct content type for JS files
aws s3 cp "s3://$S3_BUCKET" "s3://$S3_BUCKET" \
    --recursive \
    --exclude "*" \
    --include "*.js" \
    --content-type "application/javascript" \
    --metadata-directive REPLACE \
    --profile "$AWS_PROFILE"

print_success "Content types configured"

# CloudFront invalidation (optional)
if [ ! -z "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
    echo ""
    print_status "Step 6: Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
        --paths "/*" \
        --profile "$AWS_PROFILE" > /dev/null
    print_success "CloudFront invalidation created"
fi

# Get website URL
WEBSITE_URL="http://${S3_BUCKET}.s3-website-${AWS_REGION}.amazonaws.com"

echo ""
print_success "🎉 Deployment completed!"
echo ""
echo "Your Clotho app is now live at:"
echo "  $WEBSITE_URL"
echo ""
echo "S3 Bucket: $S3_BUCKET"
echo "Region: $AWS_REGION"
echo ""
if [ ! -z "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
    echo "CloudFront: Enabled (cache invalidated)"
else
    echo "💡 Consider setting up CloudFront for better performance and HTTPS"
fi

# Cleanup
rm -f /tmp/s3-bucket-policy.json
