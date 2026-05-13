variable "aws_region" {
  description = "AWS region for the demo node."
  type        = string
  default     = "eu-central-1"
}

variable "instance_type" {
  description = "Instance type for the k3s demo node."
  type        = string
  default     = "t3.small"
}

variable "admin_cidr" {
  description = "CIDR allowed to reach SSH/HTTP/HTTPS. Set this to your public IP, for example 203.0.113.10/32."
  type        = string
  default     = "203.0.113.10/32"
}
