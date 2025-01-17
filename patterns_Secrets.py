# patterns_extended.py

"""
This file consolidates regex patterns for detecting various sensitive strings:
- Passwords, secrets, keys
- API tokens for cloud providers and popular services
- Private keys and common environment variables

Usage:
  import re
  from patterns_extended import all_patterns

  compiled_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in all_patterns]
  # Then apply these compiled patterns in your scanning logic.
"""

all_patterns = [
    # ========================
    # 1) Common Password/Key Assignments
    # ========================
    # Password assignments
    r'\b[Pp]assword\s*=\s*["\']([^"\']+)["\']',         # password="value"
    r'\b[Pp]assword\s*=\s*([^\s\'";]+)',                # password=value (unquoted)

    # Generic key/token assignments
    r'\b[Kk]ey\s*=\s*["\']([^"\']+)["\']',              # key="value"
    r'\b[Tt]oken\s*=\s*["\']([^"\']+)["\']',            # token="value"

    # Secret key assignments
    r'\b[Ss]ecret[_-]?[Kk]ey\s*=\s*["\']([^"\']+)["\']', # secretKey="value"

    # API key assignments
    r'\b[Aa]pi[_-]?[Kk]ey\s*=\s*["\']([^"\']+)["\']',    # apiKey="value" or api_key='value'
    r'\b[Aa]pi[_-]?[Tt]oken\s*=\s*["\']([^"\']+)["\']',  # apiToken="value" or api_token='value'

    # Other auth data (authKey, authToken)
    r'\b[Aa]uth[_-]?[Kk]ey\s*=\s*["\']([^"\']+)["\']',
    r'\b[Aa]uth[_-]?[Tt]oken\s*=\s*["\']([^"\']+)["\']',

    # Auth secrets with length constraints
    r'\b[Aa]uth(?:entication)?[_-]?[Kk]ey\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?',
    r'\b[Aa]uth[_-]?[Tt]oken\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?',

    # ========================
    # 2) Generic Key/Token Patterns
    # ========================
    # Generic secrets of length >= 16
    r'(?:secret|private|key|token)\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?',

    # Generic long alphanumeric strings (>= 32 chars) that might be secrets
    r'[\'"]?([A-Za-z0-9_\-]{32,})[\'"]?',

    # ========================
    # 3) OAuth / JWT / Bearer Tokens
    # ========================
    # Bearer tokens
    r'\bbearer\s+[A-Za-z0-9\-_~+/]+=*',
    # Basic JWT (old pattern)
    r'eyJ[A-Za-z0-9\-_~+/]+=*',
    # Enhanced JWT (three segments)
    r'eyJ[A-Za-z0-9\-_~+/]+\.eyJ[A-Za-z0-9\-_~+/]+\.?[A-Za-z0-9\-_~+/]*',

    # ========================
    # 4) AWS
    # ========================
    # AWS Access Keys
    r'AKIA[0-9A-Z]{16}',
    # AWS Temporary Access Keys
    r'ASIA[0-9A-Z]{16}',
    # AWS Secret Keys (40-char base64ish)
    r'(?<![A-Za-z0-9])([A-Za-z0-9/+=]{40})(?![A-Za-z0-9])',

    # ========================
    # 5) Private Keys
    # ========================
    # PEM private keys
    r'-----BEGIN PRIVATE KEY-----[\s\S]+?-----END PRIVATE KEY-----',
    r'-----BEGIN RSA PRIVATE KEY-----[\s\S]+?-----END RSA PRIVATE KEY-----',
    # OpenSSH Private Key (newer format)
    r'-----BEGIN OPENSSH PRIVATE KEY-----[\s\S]+?-----END OPENSSH PRIVATE KEY-----',

    # ========================
    # 6) Database Connection Strings
    # ========================
    r'\b(?:jdbc|postgres|mysql|oracle|sqlserver|mongodb)://[^\s\'"]+',
    r'(?:data[_-]?source|server|host)\s*[:=]\s*[\'"]?([^\s\'"]+)[\'"]?',

    # ========================
    # 7) Slack
    # ========================
    r'(xox[bap]-[0-9a-zA-Z]{10,48}-[0-9a-zA-Z]{10,48}-[0-9a-zA-Z]{24,64})',
    r'(xapp-[0-9a-zA-Z]{32,64}-[0-9a-zA-Z]{32,64})',

    # ========================
    # 8) Heroku
    # ========================
    r'(?i)heroku.*[ \t]*(api_key|api-key|key)\s*[:=]\s*["\']?([A-Za-z0-9]{32})["\']?',

    # ========================
    # 9) GCP / Firebase
    # ========================
    # GCP service account type indicator
    r'"type"\s*:\s*"service_account"',
    # Could add more GCP-specific patterns as needed...

    # ========================
    # 10) Azure
    # ========================
    r'AccountKey\s*=\s*([A-Za-z0-9+/=]+)',
    r'SharedAccessSignature\s*=\s*([A-Za-z0-9%]+)',

    # ========================
    # 11) GitHub
    # ========================
    # GitHub Personal Access Tokens (PAT) (ghp_, gho_, ghs_, etc.)
    r'(gh[pousr]_[A-Za-z0-9]{36,})',

    # ========================
    # 12) DigitalOcean
    # ========================
    # DigitalOcean token (64-hex)
    r'(do|digitalocean)_?(token|access_token)\s*=\s*["\']?([A-Fa-f0-9]{64})["\']?',

    # ========================
    # 13) Environment Variables (Generic)
    # ========================
    # Any uppercase var that ends in _SECRET, _TOKEN, or _KEY
    r'\b[A-Z0-9_]+(?:_SECRET|_TOKEN|_KEY)\s*=\s*["\']?([^"\']+)["\']?',

    # ========================
    # 14) Stripe
    # ========================
    r'(sk_(?:live|test)_[0-9a-zA-Z]{24,})',

    # ========================
    # 15) Twilio
    # ========================
    r'\bTWILIO_AUTH_TOKEN\s*=\s*["\']?([A-Za-z0-9]{32})["\']?',

    # ========================
    # 16) SendGrid
    # ========================
    r'(SG\.[A-Za-z0-9_\-]{22,}\.[A-Za-z0-9_\-]{43,})',

    # ========================
    # 17) Cloudflare
    # ========================
    r'(CF_API_TOKEN|CLOUDFLARE_API_TOKEN)\s*=\s*["\']?([A-Za-z0-9_-]{30,})["\']?',

    # ========================
    # 18) PayPal / Braintree
    # ========================
    r'(?:PAYPAL|BRAINTREE)_(CLIENT_ID|CLIENT_SECRET|ACCESS_TOKEN)\s*=\s*["\']?([^"\']+)["\']?',

    # ========================
    # 19) Okta
    # ========================
    r'(?i)\bSSWS\s+([A-Za-z0-9_\-\.=]+)',  # Tokens in HTTP headers
    r'(OKTA_API_TOKEN)\s*=\s*["\']?([^"\']+)["\']?',

    # ========================
    # 20) Salesforce
    # ========================
    r'(sf|salesforce)_(consumer_key|consumer_secret)\s*=\s*["\']?([^"\']+)["\']?',
    r'\brefresh_token\s*=\s*["\']([^"\']+)["\']',

    # ========================
    # 21) Vault (HashiCorp)
    # ========================
    r'(VAULT_TOKEN|vault_token)\s*=\s*["\']?([^"\']+)["\']?',

    # domain\username (NetBIOS style)
    r'[A-Za-z0-9._\-$]+\\[A-Za-z0-9._\-$]+',

    # username@domain.tld (UPN style)
    r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',

    # Potential environment variables for AD/LDAP passwords
    r'(?:AD|LDAP|DOMAIN)_PASSWORD\s*=\s*["\']?([^"\']+)["\']?',

    # (Optional) Bind credentials
    r'(bind_dn|bind_user|bind_pass|bind_pw)\s*=\s*["\']([^"\']+)["\']',
]

