# Security Notice

## Committed Secrets — IMMEDIATE ACTION REQUIRED

A `.env` file containing live API credentials was previously committed to this repository.

**If you are seeing this, rotate ALL credentials immediately:**
- Stripe secret key and webhook secret
- Plaid client ID and secret
- Database credentials
- JWT secret key
- Supabase keys

## Going Forward

- `.env` is now in `.gitignore` — it will not be tracked
- Use `.env.example` as the template for local setup
- Rotate secrets via each provider's dashboard
- Use GitHub Secrets or Supabase Vault for CI/CD

## Contact
security@influwealth.com
