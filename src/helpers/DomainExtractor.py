import urllib.parse


def ExtractDomain(url: str):
    tokens = url.split('/')
    simplified_url = "".join(tokens[1:3])
    domain_and_dot = simplified_url.split('.')[-2:]
    return ".".join(domain_and_dot)

def FindRobotsTxt(url: str):
    parsed = urllib.parse.urlparse(url=url, allow_fragments=False)

    url = parsed.geturl().split('?')[0]
    
    tokens = url.split('/')
    simplified_url = "".join(tokens[1:3])
    domain_and_dot = simplified_url.split('.')
    return tokens[0] + "//" + ".".join(domain_and_dot) + "/robots.txt"

def CleanUrl(url: str):
    return url.removesuffix('/')