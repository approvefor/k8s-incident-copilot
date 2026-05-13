output "public_ip" {
  description = "Public IP for Ansible inventory."
  value       = aws_instance.devops_vm.public_ip
}
