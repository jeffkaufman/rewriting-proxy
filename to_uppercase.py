# Example rewriting module.

# headers: [(key, value), (key, value), ...]
# body: raw body
def Rewrite(headers, body):
  headers.append(("X-Proxy-Modification", "uppercase"))
  return headers, body.upper()
