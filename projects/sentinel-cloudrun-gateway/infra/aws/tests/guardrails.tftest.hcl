mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}
variables {
  image                      = "example.invalid/sentinel@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  runtime_environment        = {}
  region                     = "us-east-1"
  cluster_arn                = "arn:aws:ecs:us-east-1:123456789012:cluster/sentinel"
  private_subnet_ids         = ["subnet-0123456789abcdef0"]
  gateway_security_group_ids = ["sg-0123456789abcdef0"]
  private_target_group_arn   = "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/sentinel/0123456789abcdef"
  ecr_repository_arn         = "arn:aws:ecr:us-east-1:123456789012:repository/sentinel"
  database_secret_arn        = "arn:aws:secretsmanager:us-east-1:123456789012:secret:database-abcdef"
  capability_secret_arn      = "arn:aws:secretsmanager:us-east-1:123456789012:secret:capability-abcdef"
  secret_kms_key_arns        = []
  artifact_bucket_name       = "sentinel-test-only-evidence"
}
run "private_bounded_staging_plan" {
  command = plan
  assert {
    condition     = aws_ecs_service.gateway.network_configuration[0].assign_public_ip == false
    error_message = "Tasks cannot receive public IPs"
  }
  assert {
    condition     = aws_ecs_service.gateway.deployment_circuit_breaker[0].rollback == true
    error_message = "Failed deploy must roll back"
  }
  assert {
    condition     = aws_s3_bucket_public_access_block.evidence.block_public_policy == true
    error_message = "Artifacts must remain private"
  }
  assert {
    condition     = local.runtime.SENTINEL_AUTH_MODE == "oidc"
    error_message = "OIDC required"
  }
}
run "reject_mutable_image" {
  command = plan
  variables { image = "example.invalid/sentinel:latest" }
  expect_failures = [var.image]
}
