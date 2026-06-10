# ── Cognito User Pool — read-only reference ───────────────────────────────────
# The User Pool is owned and managed by the Know-It-All CloudFormation stack.
# Terraform references it as a data source only — it will never modify or destroy it.

data "aws_cognito_user_pool" "shared" {
  user_pool_id = var.user_pool_id
}

# ── NOTE: Cognito domain and app client moved to synsug/terraform ─────────────
# The shared auth domain (auth.syntacticallysugary.dev) and both app clients are
# now managed centrally in the synsug repo Terraform workspace "shared-auth".
# This module retains only the User Pool data source reference.
#
# Before applying synsug/terraform for the first time, destroy the old prefix domain:
#   terraform destroy -target module.cognito.aws_cognito_user_pool_domain.private_reading
