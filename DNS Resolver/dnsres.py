import dns.resolver

def enumerate_subdomains(domain):
    subdomains = []
    with open("subdomains.txt", "r") as file:
        sub_list = file.readlines()
    for sub in sub_list:
        sub = sub.strip()
        try:
            answers = dns.resolver.resolve(f"{sub}.{domain}", 'A')
            subdomains.append(f"{sub}.{domain}")
        except dns.resolver.NXDOMAIN:
            pass
    return subdomains

print(enumerate_subdomains("outlier.ai"))