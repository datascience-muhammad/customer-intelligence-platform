# ShopFlow Customer Intelligence Platform - Terraform Variables
# Data Engineering Infrastructure (S3 Data Lake Only)

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "shopflow"
}

variable "env" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for S3 bucket"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS access key (use environment variable or AWS CLI profile instead)"
  type        = string
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS secret key (use environment variable or AWS CLI profile instead)"
  type        = string
  sensitive   = true
}

