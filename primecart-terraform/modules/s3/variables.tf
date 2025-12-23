variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "db_name" {
  type = string
}

variable "username" {
  type = string
}

variable "password" {
  type      = string
  sensitive = true
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "allowed_cidrs" {
  type        = list(string)
  description = "CIDR ranges allowed to connect (Airflow, dev machine)"
}
