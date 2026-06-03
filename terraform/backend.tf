# Terraform state is stored in HCP Terraform Cloud (free tier).
#
# Bootstrap (one-time, manual):
#   1. Create a free account at https://app.terraform.io
#   2. Create an organization and a workspace named "private-reading"
#      with execution mode set to "Local" (Terraform runs locally, state lives in HCP).
#   3. Create a user API token: User Settings → Tokens → Create an API token.
#   4. Run: terraform login  (or set TF_TOKEN_app_terraform_io env var)
#   5. Run: terraform init
#
# In CI/CD, set TF_TOKEN_app_terraform_io as a secret in Gitea.
# The cloud block below hard-codes the org/workspace — no secrets needed in this file.

terraform {
  cloud {
    organization = "SyntacticallySugary"

    workspaces {
      name = "private-reading"
    }
  }
}
