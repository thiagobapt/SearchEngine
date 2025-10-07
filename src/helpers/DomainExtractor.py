def ExtractDomain(url: str):
    tokens = url.split('/')
    simplified_url = "".join(tokens[1:3])
    domain_and_dot = simplified_url.split('.')[-2:]
    return ".".join(domain_and_dot)