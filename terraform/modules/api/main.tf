locals {
  prefix = "${var.app_name}-${var.environment}"
}

resource "oci_apigateway_gateway" "this" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.prefix}-gateway"
  endpoint_type  = "PUBLIC"
  subnet_id      = var.subnet_id
}

resource "oci_apigateway_deployment" "this" {
  # Skipped until the function is deployed in Step 2.
  count = var.function_id != "" ? 1 : 0

  compartment_id = var.compartment_ocid
  gateway_id     = oci_apigateway_gateway.this.id
  display_name   = "${local.prefix}-deployment"
  path_prefix    = "/v1"

  specification {

    request_policies {
      cors {
        allowed_origins              = [regex("^https?://[^/]+", var.spa_origin)]
        allowed_methods              = ["GET", "POST", "DELETE", "OPTIONS"]
        allowed_headers              = ["Authorization", "Content-Type"]
        exposed_headers              = ["Content-Disposition"]
        is_allow_credentials_enabled = true
        max_age_in_seconds           = 3600
      }

      # Deployment-level JWT authenticator. Worker routes override with ANONYMOUS.
      authentication {
        type                        = "JWT_AUTHENTICATION"
        is_anonymous_access_allowed = true
        token_header                = "Authorization"
        token_auth_scheme           = "Bearer"
        issuers   = [var.cognito_issuer]
        audiences = [var.cognito_client_id]

        public_keys {
          type                        = "REMOTE_JWKS"
          uri                         = var.cognito_jwks_uri
          is_ssl_verify_disabled      = false
          max_cache_duration_in_hours = 1
        }
      }
    }

    # ── User routes — Cognito JWT required ────────────────────────────────────

    routes {
      path    = "/jobs"
      methods = ["POST", "OPTIONS"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }

    routes {
      path    = "/jobs/current"
      methods = ["GET", "DELETE", "OPTIONS"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }

    routes {
      path    = "/jobs/current/url"
      methods = ["GET", "OPTIONS"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }

    # ── Worker routes — anonymous (OCI request signature validated in-function) ─

    routes {
      path    = "/worker/jobs/pending"
      methods = ["GET"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }

    routes {
      path    = "/worker/jobs/{job_id}/claim"
      methods = ["POST"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }

    routes {
      path    = "/worker/jobs/{job_id}/complete"
      methods = ["POST"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }

    routes {
      path    = "/worker/jobs/{job_id}/fail"
      methods = ["POST"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }

    routes {
      path    = "/worker/jobs/{job_id}/progress"
      methods = ["POST"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }

    # ── Voice routes — Cognito JWT validated in-function ──────────────────────

    routes {
      path    = "/voice"
      methods = ["GET", "POST", "DELETE", "OPTIONS"]
      backend {
        type        = "ORACLE_FUNCTIONS_BACKEND"
        function_id = var.function_id
      }
      request_policies {
        authorization {
          type = "ANONYMOUS"
        }
      }
    }
  }
}
