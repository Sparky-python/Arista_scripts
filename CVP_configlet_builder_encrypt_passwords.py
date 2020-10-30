from cvplibrary import CVPGlobalVariables,GlobalVariableNames
from cvprac.cvp_client import CvpClient
import crypt
import ssl

try:
  _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
# Legacy Python that doesn't verify HTTPS certificates by default
  pass
else:
# Handle target environment that doesn't support HTTPS verification
  ssl._create_default_https_context = _create_unverified_https_context

ssl._create_default_https_context = ssl._create_unverified_context
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

cvp_username = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
cvp_password = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)

clnt = CvpClient()
clnt.connect(['localhost'], cvp_username, cvp_password)

output = clnt.api.get_configlet_by_name(name = "cvp_1_site_users_pwd_config")
config = output["config"]
key = output["key"]

new_config = ""

for line in config.splitlines():
  if "secret" in line or "enable" in line:
    words = line.split()
    for x in range(len(words)):
      if words[x] == "secret" and words[x+1] != "sha512":
        words[x+1] = "sha512 " + crypt.crypt(words[x+1], "$6$saltsalt$")
      elif words[x] == "enable" and words[x+1] == "password" and words[x+2] != "sha512":
        words[x+2] = "sha512 " + crypt.crypt(words[x+2], "$6$saltsalt$")
    line = " ".join(words)
    new_config += line + "\n"
  else:
    new_config += line + "\n"

clnt.api.update_configlet(config=new_config, key = key, name = "cvp_1_site_users_pwd_config")

