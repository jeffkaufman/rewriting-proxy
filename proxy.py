# Usage:
#   In one terminal:
#     $ python proxy.py localhost 8080 to_uppercase
#   In another terminal:
#     $ http_proxy=localhost:8024 curl -D- http://www.example.com
#
# Based on example code from:
#  http://stackoverflow.com/questions/9465236/ and
#  http://stackoverflow.com/questions/6491932/
#
# Create your own rewriting code, put it in this directory as your_code.py, then
# use "your_code" in place of "to_uppercase"

import sys
import gzip
import StringIO
from twisted.internet import endpoints, reactor
from twisted.python import log
from twisted.web import http, proxy

def gunzip(text):
  tmp_file = StringIO.StringIO()
  tmp_file.write(text)
  tmp_file.seek(0)
  return gzip.GzipFile(fileobj=tmp_file, mode='rb').read()

def proxy_factory(rewrite_fn):
  class ProxyClient(proxy.ProxyClient):
    """Mange returned header, content here.

    Use `self.father` methods to modify request directly.
    """
    def __init__(self, *args, **kwargs):
      self.p_headers = []
      self.p_body = ""
      proxy.ProxyClient.__init__(self, *args, **kwargs)
 
    def handleHeader(self, key, value):
      self.p_headers.append((key, value))
   
    def handleResponsePart(self, buf):
      self.p_body += buf
 
    def handleResponseEnd(self):
      if not self._finished:
        for i, (key, value) in enumerate(self.p_headers):
          if key == "Content-Encoding" and value == "gzip":
            self.p_body = gunzip(self.p_body)
            del self.p_headers[i]
            break

        headers, body = rewrite_fn(self.p_headers, self.p_body)

        for key, value in headers:
          proxy.ProxyClient.handleHeader(self, key, value)

        self.father.responseHeaders.setRawHeaders(
            "content-length", [len(body)])
        self.father.write(body)
      proxy.ProxyClient.handleResponseEnd(self)

  class ProxyClientFactory(proxy.ProxyClientFactory):
    protocol = ProxyClient

  class ProxyRequest(proxy.ProxyRequest):
    protocols = dict(http=ProxyClientFactory)

  class Proxy(proxy.Proxy):
    requestFactory = ProxyRequest

  class ProxyFactory(http.HTTPFactory):
    protocol = Proxy
  
  return ProxyFactory()

def start(hostname, port, rewrite_classname):
  def shutdown(reason, reactor, stopping=[]):
    """Stop the reactor."""
    if stopping:
      return
    stopping.append(True)
    if reason:
      log.msg(reason.value)
    reactor.callWhenRunning(reactor.stop)

  log.startLogging(sys.stdout)

  rewrite_class = __import__(rewrite_classname)
  
  portstr = "tcp:%s:interface=%s" % (port, hostname)
  endpoint = endpoints.serverFromString(reactor, portstr)
  d = endpoint.listen(proxy_factory(rewrite_class.Rewrite))
  d.addErrback(shutdown, reactor)
  reactor.run()

if __name__ == '__main__':
  start(*sys.argv[1:])

