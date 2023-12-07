from django_hosts import host, patterns

host_patterns = patterns(
    "",
    host(r"", "config.urls", name="root"),  # Handling root domain
    host(r"alt", "config.urls_alt", name="alt"),  # Handling the 'alt' subdomain
)
