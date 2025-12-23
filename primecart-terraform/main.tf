# S3 Data Lake for ShopFlow Customer Intelligence Platform
# Three-layer architecture: raw -> staging -> curated

locals {
  bucket_name = "shopflow-de-team"
  
  # Data lake folder structure
  raw_prefixes = [
    "raw/customers/",
    "raw/orders/",
    "raw/products/",
    "raw/events/",
    "raw/inventory/",
    "raw/support_tickets/"
  ]
  
  staging_prefixes = [
    "staging/stg_customers/",
    "staging/stg_orders/",
    "staging/stg_products/",
    "staging/stg_events/",
    "staging/stg_support_tickets/"
  ]
  
  curated_prefixes = [
    "curated/dim_customers/",
    "curated/dim_products/",
    "curated/dim_dates/",
    "curated/fact_orders/",
    "curated/fact_events/",
    "curated/ml_features/"
  ]
}

# S3 Bucket for Data Lake
resource "aws_s3_bucket" "data_lake" {
  bucket = local.bucket_name

  tags = {
    Name        = "ShopFlow Data Lake"
    Project     = var.project_name
    Environment = var.env
    Purpose     = "Customer Intelligence Platform"
    ManagedBy   = "Terraform"
  }
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "data_lake_versioning" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake_encryption" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "data_lake_public_access_block" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "data_lake_lifecycle" {
  bucket = aws_s3_bucket.data_lake.id

  # Transition staging data to IA after 30 days
  rule {
    id     = "staging-transition"
    status = "Enabled"

    filter {
      prefix = "staging/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }

  # Transition raw data to IA after 60 days
  rule {
    id     = "raw-transition"
    status = "Enabled"

    filter {
      prefix = "raw/"
    }

    transition {
      days          = 60
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }

  # Keep curated data in standard storage (frequently accessed)
  rule {
    id     = "curated-expiration"
    status = "Enabled"

    filter {
      prefix = "curated/"
    }

    expiration {
      days = 730  # 2 years
    }
  }
}

# Create placeholder objects for folder structure (optional but helpful for visualization)
resource "aws_s3_object" "raw_folders" {
  for_each = toset(local.raw_prefixes)
  
  bucket  = aws_s3_bucket.data_lake.id
  key     = each.value
  content = ""
}

resource "aws_s3_object" "staging_folders" {
  for_each = toset(local.staging_prefixes)
  
  bucket  = aws_s3_bucket.data_lake.id
  key     = each.value
  content = ""
}

resource "aws_s3_object" "curated_folders" {
  for_each = toset(local.curated_prefixes)
  
  bucket  = aws_s3_bucket.data_lake.id
  key     = each.value
  content = ""
}
