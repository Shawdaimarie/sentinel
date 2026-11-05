terraform {
  required_version = "= 1.13.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "= 6.71.0" }
  }
}
provider "aws" { region = var.region }
variable "region" { type = string }
variable "name" { default = "sentinel-staging" }
variable "cluster_arn" { type = string }
variable "private_subnet_ids" { type = set(string) }
variable "gateway_security_group_ids" { type = set(string) }
variable "private_target_group_arn" { type = string }
variable "image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image))
    error_message = "Use an immutable tested ECR image digest."
  }
}
variable "ecr_repository_arn" { type = string }
variable "database_secret_arn" { type = string }
variable "capability_secret_arn" { type = string }
variable "secret_kms_key_arns" { type = list(string) }
variable "artifact_bucket_name" { type = string }
variable "runtime_environment" { type = map(string) }
data "aws_iam_policy_document" "assume_task" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "execution" {
  name               = "${var.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.assume_task.json
}
resource "aws_iam_role" "runtime" {
  name               = "${var.name}-runtime"
  assume_role_policy = data.aws_iam_policy_document.assume_task.json
}
resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/sentinel/${var.name}"
  retention_in_days = 30
}
data "aws_iam_policy_document" "execution" {
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    actions   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
    resources = [var.ecr_repository_arn]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.gateway.arn}:*"]
  }
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.database_secret_arn, var.capability_secret_arn]
  }
  dynamic "statement" {
    for_each = length(var.secret_kms_key_arns) > 0 ? [1] : []
    content {
      actions   = ["kms:Decrypt"]
      resources = var.secret_kms_key_arns
    }
  }
}
resource "aws_iam_role_policy" "execution" {
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.execution.json
}
resource "aws_s3_bucket" "evidence" {
  bucket        = var.artifact_bucket_name
  force_destroy = false
}
resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket                  = aws_s3_bucket.evidence.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_iam_role_policy" "artifacts" {
  role = aws_iam_role.runtime.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = ["s3:PutObject"], Resource = "${aws_s3_bucket.evidence.arn}/runs/*"
  }] })
}
resource "aws_ecs_task_definition" "gateway" {
  family                   = var.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.runtime.arn
  container_definitions = jsonencode([{
    name                   = "gateway", image = var.image, essential = true,
    readonlyRootFilesystem = true,
    portMappings           = [{ containerPort = 8080, protocol = "tcp" }],
    environment            = [for k, v in local.runtime : { name = k, value = v }],
    secrets                = [{ name = "DATABASE_URL", valueFrom = var.database_secret_arn }, { name = "CAPABILITY_SECRET", valueFrom = var.capability_secret_arn }],
    logConfiguration       = { logDriver = "awslogs", options = { awslogs-group = aws_cloudwatch_log_group.gateway.name, awslogs-region = var.region, awslogs-stream-prefix = "gateway" } },
    healthCheck            = { command = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3)"], interval = 30, timeout = 5, retries = 3, startPeriod = 60 }
  }])
}
resource "aws_ecs_service" "gateway" {
  name            = var.name
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.gateway.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = var.gateway_security_group_ids
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = var.private_target_group_arn
    container_name   = "gateway"
    container_port   = 8080
  }
  depends_on = [aws_iam_role_policy.execution]
}
output "service_name" { value = aws_ecs_service.gateway.name }
output "task_definition_arn" { value = aws_ecs_task_definition.gateway.arn }
output "evidence_bucket" { value = aws_s3_bucket.evidence.id }

locals {
  runtime = merge(var.runtime_environment, { SENTINEL_ENVIRONMENT = "staging", SENTINEL_AUTH_MODE = "oidc", SENTINEL_LOCAL_TOKENS = "{}", PYTHONDONTWRITEBYTECODE = "1" })
}
