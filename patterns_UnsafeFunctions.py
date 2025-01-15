cppPatterns = [
    # String handling
    r'\bstrcpy\s*\(',       # Matches strcpy(
    r'\bstrncpy\s*\(',      # Matches strncpy(
    r'\bstrcat\s*\(',       # Matches strcat(
    r'\bstrncat\s*\(',      # Matches strncat(
    r'\bsprintf\s*\(',      # Matches sprintf(
    r'\bvsprintf\s*\(',     # Matches vsprintf(
    r'\bgets\s*\(',         # Matches gets(

    # Memory handling
    r'\bmalloc\s*\(',       # Matches malloc(
    r'\brealloc\s*\(',      # Matches realloc(
    r'\bcalloc\s*\(',       # Matches calloc(
    r'\bfree\s*\(',         # Matches free(

    # File handling
    r'\btmpfile\s*\(',      # Matches tmpfile(
    r'\btmpnam\s*\(',       # Matches tmpnam(
    r'\bfopen\s*\([^,]+,\s*["\']w[bt]?\+?["\']\)',  # Matches fopen with write modes

    # General unsafe constructs
    r'\bsystem\s*\(',       # Matches system(
    r'\bpopen\s*\(',        # Matches popen(
    r'\bexec[lvep]{0,2}\s*\(',  # Matches execl, execv, execle, etc.
]
