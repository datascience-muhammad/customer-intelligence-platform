# ShopFlow Data Lake Outputs

output "s3_bucket_name" {
  description = "Name of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.arn
}

output "s3_bucket_region" {
  description = "AWS region of the S3 bucket"
  value       = aws_s3_bucket.data_lake.region
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.data_lake.bucket_domain_name
}

output "s3_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket"
  value       = aws_s3_bucket.data_lake.bucket_regional_domain_name
}

output "raw_layer_path" {
  description = "S3 path for raw data layer"
  value       = "s3://${aws_s3_bucket.data_lake.id}/raw/"
}

output "staging_layer_path" {
  description = "S3 path for staging data layer"
  value       = "s3://${aws_s3_bucket.data_lake.id}/staging/"
}

output "curated_layer_path" {
  description = "S3 path for curated data layer"
  value       = "s3://${aws_s3_bucket.data_lake.id}/curated/"
}
