import httplib
import ConfigParser
import json
import logging

config = ConfigParser.RawConfigParser()
config.read('/home/localadmin/HASS/compute_node/hass_node.conf')

keystone_port = int(config.get("keystone_auth","port"))

openstack_user_name = config.get("openstack", "openstack_admin_account")
openstack_domain = config.get("openstack", "openstack_user_domain_id")
openstack_password = config.get("openstack", "openstack_admin_password")



REST_host = config.get("RESTful","host")
REST_port = int(config.get("RESTful","port"))

class Authenticator(object):
  def __init__(self):
    self.access_token = self.init_access_token()

  def success(self, token):
    return self.is_token_valid(token)

  def init_access_token(self):
    try:
      data = '{ "auth": { "identity": { "methods": [ "password" ], "password": { "user": { "name": \"%s\", "domain": { "name": \"%s\" }, "password": \"%s\" } } } } }' % (openstack_user_name, openstack_domain, openstack_password)
      headers = {"Content-Type": "application/json"}
      http_client = httplib.HTTPConnection(REST_host, keystone_port, timeout=30)
      http_client.request("POST", "/v3/auth/tokens", body=data, headers=headers)
      return http_client.getresponse().getheaders()[1][1]
    except Exception as e:
      print str(e)
    finally:
      if http_client:
        http_client.close()

  def refresh_access_token(self):
    self.access_token = self.init_access_token()

  def get_access_token(self):
    if not self.is_token_valid(self.access_token):
      self.refresh_access_token()
    return self.access_token

  def is_token_valid(self, token):
    if not token:
      return False
    try:
      headers = {"X-Auth-Token": self.access_token, "X-Subject-Token": token}
      http_client = httplib.HTTPConnection(REST_host, keystone_port, timeout=30)
      http_client.request("GET", "/v3/auth/tokens", headers=headers)
      response = http_client.getresponse()
      if response.status == httplib.UNAUTHORIZED:
        self.refresh_access_token()
        return self.is_token_valid(token)
      map_response = json.loads(response.read())
      if "error" in map_response and \
        map_response["error"]["code"] == httplib.NOT_FOUND:
        return False
      return True
    finally:
      if http_client:
        http_client.close()
