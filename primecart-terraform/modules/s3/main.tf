locals {
  bucket = "${var.project_name}-intel-${var.env}-${replace(var.region, "-", "")}"
}

resource "aws_s3_bucket" "data_lake" {
  bucket = local.bucket
  acl    = "private"

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  lifecycle_rule {
    id      = "curated-transition"
    enabled = true

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 365 * 2
    }
  }

  tags = {
    Project = var.project_name
    Env     = var.env
  }
}

# optional: a small policy restricting public access (prevent accidental public)
resource "aws_s3_bucket_public_access_block" "block" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
