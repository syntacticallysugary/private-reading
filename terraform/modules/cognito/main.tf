# ── Cognito User Pool — read-only reference ───────────────────────────────────
# The User Pool is owned and managed by the Know-It-All CloudFormation stack.
# Terraform references it as a data source only — it will never modify or destroy it.

data "aws_cognito_user_pool" "shared" {
  user_pool_id = var.user_pool_id
}

# ── Hosted UI domain ─────────────────────────────────────────────────────────
# Associates a custom domain prefix with the shared User Pool so the Cognito
# Hosted UI is reachable. This creates the domain — it does not modify the pool.

resource "aws_cognito_user_pool_domain" "private_reading" {
  domain       = var.domain_prefix
  user_pool_id = data.aws_cognito_user_pool.shared.id
}

# ── Private Reading app client ────────────────────────────────────────────────
# A new app client scoped to this application. The User Pool itself is unchanged.

resource "aws_cognito_user_pool_client" "private_reading" {
  name         = var.app_name
  user_pool_id = data.aws_cognito_user_pool.shared.id

  # Public client — no client secret (SPA cannot keep secrets)
  generate_secret = false

  # OAuth 2.0 Authorization Code + PKCE
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]

  # USER_PASSWORD_AUTH for native in-app login; REFRESH for token renewal
  explicit_auth_flows = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]

  callback_urls = ["${var.spa_origin}/index.html"]
  logout_urls   = ["${var.spa_origin}/index.html"]

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 30
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # Do not allow user existence errors to leak (prevents account enumeration)
  prevent_user_existence_errors = "ENABLED"
}
