def ExtractDomain(url: str):
    tokens = url.split('/')
    return "".join(tokens[0:3]).split('.')[-2]