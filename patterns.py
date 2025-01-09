patterns = [
    # API keys and tokens
    r'api[_-]?key\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?',  # Matches API keys like api_key="xyz" or apiKey: xyz
    r'(?:secret|token)[_-]?key\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?',  # Matches secretKey="xyz" or token_key: xyz

    # Passwords
    r'\b[Pp]assword\s*[:=]\s*[\'"]([^\'"]+)[\'"]',  # Matches password="xyz" or password='xyz'
    r'\b[Pp]assword\s*[:=]\s*([^\s;]+)',  # Matches password=xyz without quotes
    r'\b[Pp]ass(?:word)?\s*[:=]\s*[\'"]([^\'"]+)[\'"]',  # Matches variations like pass="xyz"

    # Authentication secrets
    r'\b[Aa]uth(?:entication)?[_-]?[Kk]ey\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?',  # Matches auth_key="xyz"
    r'\b[Aa]uth[_-]?[Tt]oken\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?',  # Matches auth_token="xyz"

    # OAuth tokens
    r'bearer\s+[A-Za-z0-9\-._~+/]+=*',  # Matches OAuth Bearer tokens
    r'eyJ[A-Za-z0-9\-._~+/]+=*',  # Matches JWT tokens

    # AWS keys
    r'AKIA[0-9A-Z]{16}',  # Matches AWS Access Keys
    r'ASIA[0-9A-Z]{16}',  # Matches AWS Temporary Access Keys
    r'(?<![A-Za-z0-9])([A-Za-z0-9/+=]{40})(?![A-Za-z0-9])',  # Matches AWS Secret Keys

    # Private keys
    r'-----BEGIN PRIVATE KEY-----[\s\S]+?-----END PRIVATE KEY-----',  # Matches PEM private keys
    r'-----BEGIN RSA PRIVATE KEY-----[\s\S]+?-----END RSA PRIVATE KEY-----',  # Matches RSA private keys

    # Database connection strings
    r'\b(?:jdbc|postgres|mysql|oracle|sqlserver|mongodb)://[^\s\'"]+',  # Matches DB connection strings
    r'(?:data[_-]?source|server|host)\s*[:=]\s*[\'"]?([^\s\'"]+)[\'"]?',  # Matches data source strings

    # Generic secrets
    r'[\'"]?([A-Za-z0-9_\-]{32,})[\'"]?',  # Matches long alphanumeric strings (potential secrets)
    r'(?:secret|private|key|token)\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]{16,})[\'"]?',  # Matches generic secrets
]
