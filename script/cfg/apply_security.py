from pathlib import Path
from io import StringIO
import xml.etree.ElementTree as ET
from collections import OrderedDict
import subprocess
import re
import yaml
import json
import os
import shutil
import urllib.request

# import security_configuration_checker as checker


# This function merges the security configuration
# into broker instance. The config files include:
#
# * etc/login.config
# - if properties login module is configured
# * user/role properties file
#   * etc/artemis-users.properties
#   * etc/artemis-roles.properties
# * etc/artemis.profile
# * etc/broker.xml
# * etc/management.xml
# * etc/bootstrap.xml

LOGIN_CONFIG_NAME = 'login.config'
USERS_PROP_FILE_NAME = 'artemis-users.properties'
ROLES_PROP_FILE_NAME = 'artemis-roles.properties'
ARTEMIS_PROFILE_NAME = 'artemis.profile'
BROKER_XML_NAME = 'broker.xml'
MANAGEMENT_XML_NAME = 'management.xml'
BOOTSTRAP_NAME = 'bootstrap.xml'

LOGIN_CONFIG = 'etc/' + LOGIN_CONFIG_NAME
USERS_PROP_FILE = 'etc/' + USERS_PROP_FILE_NAME
ROLES_PROP_FILE = 'etc/' + ROLES_PROP_FILE_NAME
ARTEMIS_PROFILE = 'etc/' + ARTEMIS_PROFILE_NAME
BROKER_XML = 'etc/' + BROKER_XML_NAME
MANAGEMENT_XML = 'etc/' + MANAGEMENT_XML_NAME
BOOTSTRAP = 'etc/' + BOOTSTRAP_NAME


class ExtraResource:
    def create(self, dest_dir):
        pass


class PropUsersFile:
    def __init__(self, prop_file):
        self.prop_file = prop_file

    def merge_from(self, new_users):
        comments = []
        users = OrderedDict()
        with open(self.prop_file, 'rt') as dst_user_file:
            for line in dst_user_file:
                if line.startswith('#'):
                    comments.append(line)
                elif line and line.strip():
                    ulist = line.split('=')
                    user = ulist[0].strip()
                    password = ulist[1].strip()
                    users[user] = self.encrypt_password(password)
        for each_user in new_users:
            user = each_user['name']
            password = each_user['password']
            users[user] = self.encrypt_password(password)
        with open(self.prop_file, 'wt') as dst:
            dst.writelines(comments)
            for key in users:
                dst.write(key)
                dst.write(' = ')
                dst.write(users[key])
                dst.write('\n')

    def encrypt_password(self, password):
        artemis_tool = Path(os.path.join(os.path.dirname(os.path.dirname(self.prop_file)), 'bin', 'artemis'))
        if not artemis_tool.is_file():
            # in unit tests environment the artemis tool is not available.
            return password
        if not password.startswith('ENC('):
            process = subprocess.run([os.path.join(os.path.dirname(os.path.dirname(self.prop_file)), 'bin', 'artemis'), 'mask', '--hash', password],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            result = process.stdout.strip();

            if result.startswith('result: '):
                return 'ENC(' + result.replace('result: ', '') + ')'
            else:
                print('Error on encrypting a password: ' + result + '/' + process.stderr.strip())

        return password


class PropRolesFile:
    def __init__(self, prop_file):
        self.prop_file = prop_file

    def merge_from(self, new_users):
        comments = []
        roles = OrderedDict()
        with open(self.prop_file, 'rt') as dst_role_file:
            for line in dst_role_file:
                if line.startswith('#'):
                    comments.append(line)
                elif line and line.strip():
                    # role line
                    user_set = {}
                    rlist = line.split('=')
                    role = rlist[0].strip()
                    users = rlist[1].split(',')
                    for u in users:
                        user_set[u.strip()] = u.strip()
                    roles[role] = user_set
        for each_user in new_users:
            if len(each_user['roles']) == 0:
                print("WARNING: user", each_user['name'], "doesn't have any roles defined!")
            for r in each_user['roles']:
                if r in roles:
                    existing_user_set = roles[r]
                    existing_user_set[each_user['name']] = each_user['name']
                else:
                    user_set = {each_user['name']: each_user['name']}
                    roles[r] = user_set
        with open(self.prop_file, 'wt') as dst:
            dst.writelines(comments)
            for key in roles:
                dst.write(key)
                dst.write(' = ')
                first = True
                for user in roles[key]:
                    if not first:
                        dst.write(',')
                    dst.write(user)
                    first = False
                dst.write('\n')


class LoginModule:
    def __init__(self, name):
        self.name = name
        self.class_name = ''
        self.flag = ''
        self.properties = []
        self.debug = None
        self.reload = None

    def set_flag(self, f):
        self.flag = f

    def get_flag(self):
        return self.flag

    def set_class_name(self, name):
        self.class_name = name

    def set_debug(self, debug):
        self.debug = debug

    def get_debug(self):
        return self.debug

    def set_reload(self, reload):
        self.reload = reload

    def get_reload(self):
        return self.reload

    def get_class_name(self):
        return self.class_name

    def get_properties(self):
        return self.properties

    def add_property(self, key, value):
        self.properties.append((key, value))

    def generate_specific_tunes(self):
        pass

    def get_dependent_modules(self, for_domain):
        pass

    def configure(self, context, target_domain_type):
        pass


class PrincipalConversionLoginModule(LoginModule):
    def __init__(self):
        LoginModule.__init__(self, "internal_principal_conversion")
        self.set_flag('required')

    def get_class_name(self):
        return 'org.apache.activemq.artemis.spi.core.security.jaas.PrincipalConversionLoginModule'

    def get_properties(self):
        return [["principalClassList", "org.keycloak.KeycloakPrincipal"]]


class PropertiesLoginModule(LoginModule):
    def __init__(self, name, module1):
        LoginModule.__init__(self, name)
        self.module = module1

    def get_class_name(self):
        return 'org.apache.activemq.artemis.spi.core.security.jaas.PropertiesLoginModule'

    def get_properties(self):
        return [['org.apache.activemq.jaas.properties.user', 'artemis-users.properties'], ['org.apache.activemq.jaas'
                                                                                           '.properties.role',
                                                                                           'artemis-roles.properties']]

    def configure(self, context, target_domain_type):
        if len(self.module['users']) > 0:
            dst_prop_users_cfg = context.get_users_prop_file()
            dst_prop_users = PropUsersFile(dst_prop_users_cfg.absolute())
            dst_prop_users.merge_from(self.module['users'])
            dst_prop_roles_cfg = context.get_roles_prop_file()
            dst_prop_roles = PropRolesFile(dst_prop_roles_cfg)
            dst_prop_roles.merge_from(self.module['users'])


class GuestLoginModule(LoginModule):
    def __init__(self, name, module1):
        LoginModule.__init__(self, name)
        self.module = module1

    def get_class_name(self):
        return 'org.apache.activemq.artemis.spi.core.security.jaas.GuestLoginModule'

    def get_properties(self):
        key_guest_user = 'org.apache.activemq.jaas.guest.user'
        guest_user = self.module['guestuser']
        key_guest_role = 'org.apache.activemq.jaas.guest.role'
        guest_role = self.module['guestrole']
        return [[key_guest_user, guest_user], [key_guest_role, guest_role]]


class CopyKeycloakDependencies(ExtraResource):
    def create(self, dest_dir):
        # for upstream may download
        yacfg_profile_name = os.environ['YACFG_PROFILE_NAME']
        if yacfg_profile_name == 'artemis':
            print("downloading keycloak dep jars")
            lib_dest_dir = dest_dir.joinpath('lib')
            download_links = self.get_keycloak_deps(lib_dest_dir)
            for dlink in download_links:
                if dlink[1].is_file():
                    print('file exists', dlink[1])
                    continue
                print('Downloading ', dlink[0])
                with urllib.request.urlopen(dlink[0]) as response, open(dlink[1], 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)

    def get_keycloak_deps(self, lib_dir):
        keycloak_deps = []
        keycloak_common_jar = 'keycloak-common-12.0.3.jar'
        dest_file_name = lib_dir.joinpath(keycloak_common_jar)
        d_url = 'https://repo1.maven.org/maven2/org/keycloak/keycloak-common/12.0.3/keycloak-common-12.0.3.jar'
        keycloak_deps.append((d_url, dest_file_name))
        keycloak_adapter_core_jar = 'keycloak-adapter-core-12.0.3.jar'
        dest_file_name = lib_dir.joinpath(keycloak_adapter_core_jar)
        d_url = 'https://repo1.maven.org/maven2/org/keycloak/keycloak-adapter-core/12.0.3/keycloak-adapter-core-12.0.3.jar'
        keycloak_deps.append((d_url, dest_file_name))
        keycloak_core_jar = 'keycloak-core-12.0.3.jar'
        dest_file_name = lib_dir.joinpath(keycloak_core_jar)
        d_url = 'https://repo1.maven.org/maven2/org/keycloak/keycloak-core/12.0.3/keycloak-core-12.0.3.jar'
        keycloak_deps.append((d_url, dest_file_name))
        bcprov_jar = 'bcprov-jdk15on-1.65.jar'
        dest_file_name = lib_dir.joinpath(bcprov_jar)
        d_url = 'https://repo1.maven.org/maven2/org/bouncycastle/bcprov-jdk15on/1.65/bcprov-jdk15on-1.65.jar'
        keycloak_deps.append((d_url, dest_file_name))
        httpcore_jar = 'httpcore-4.4.13.jar'
        dest_file_name = lib_dir.joinpath(httpcore_jar)
        d_url = 'https://repo1.maven.org/maven2/org/apache/httpcomponents/httpcore/4.4.13/httpcore-4.4.13.jar'
        keycloak_deps.append((d_url, dest_file_name))
        httpclient_jar = 'httpclient-4.5.13.jar'
        dest_file_name = lib_dir.joinpath(httpclient_jar)
        d_url = 'https://repo1.maven.org/maven2/org/apache/httpcomponents/httpclient/4.5.13/httpclient-4.5.13.jar'
        keycloak_deps.append((d_url, dest_file_name))
        jackson_anno_jar = 'jackson-annotations-2.10.5.jar'
        dest_file_name = lib_dir.joinpath(jackson_anno_jar)
        d_url = 'https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-annotations/2.10.5/jackson-annotations-2.10.5.jar'
        keycloak_deps.append((d_url, dest_file_name))
        jackson_core_jar = 'jackson-core-2.10.5.jar'
        dest_file_name = lib_dir.joinpath(jackson_core_jar)
        d_url = 'https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.10.5/jackson-core-2.10.5.jar'
        keycloak_deps.append((d_url, dest_file_name))
        jackson_databind_jar = 'jackson-databind-2.10.5.jar'
        dest_file_name = lib_dir.joinpath(jackson_databind_jar)
        d_url = 'https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.10.5/jackson-databind-2.10.5.jar'
        keycloak_deps.append((d_url, dest_file_name))
        return keycloak_deps


class ModifyArtemisProfileForKeycloak(ExtraResource):
    def __init__(self, keycloak_cfg, js_client_cfg, console_realm):
        self.keycloak_cfg = keycloak_cfg
        self.js_client_cfg = js_client_cfg
        self.hawtio_realm = console_realm

    def create(self, dest_dir):
        artemis_profile = Path(dest_dir).joinpath(ARTEMIS_PROFILE)
        if os.path.isfile(artemis_profile.absolute()):
            args_str = StringIO()
            args_str.write('\n')
            args_str.write('# hawtio keycloak integration java opts\n')
            args_str.write('JAVA_ARGS="${JAVA_ARGS} ')
            args_str.write('-Dhawtio.keycloakEnabled=true')
            args_str.write(' -Dhawtio.keycloakClientConfig=${ARTEMIS_INSTANCE_ETC_URI}')
            args_str.write(self.js_client_cfg)
            args_str.write(' -Dhawtio.authenticationEnabled=true')
            args_str.write(' -Dhawtio.realm=')
            args_str.write(self.hawtio_realm)
            args_str.write('"\n')

            with open(artemis_profile.absolute(), "rt") as profile_file:
                profile_content = profile_file.read()
                profile_content = re.sub(r'-Dhawtio.disableProxy=true ', '', profile_content)
                profile_content = re.sub(r'-Dhawtio.realm=activemq ', '', profile_content)
                profile_content = re.sub(r'-Dhawtio.offline=true ', '', profile_content)

            with open(artemis_profile.absolute(), "wt") as profile_file:
                profile_file.write(profile_content)
                profile_file.write(args_str.getvalue())


# keycloak login module is from keycloak
# and it needs a PrincipalConversionLoginModule to work
# do it automatically to save user from error
class KeycloakLoginModule(LoginModule):
    def __init__(self, name, keycloak_module):
        LoginModule.__init__(self, name)
        self.module = keycloak_module
        self.cfg_keymap = OrderedDict([
            ('realm', 'realm'),
            ('realmpublickey', 'realm-public-key'),
            ('authserverurl', 'auth-server-url'),
            ('sslrequired', 'ssl-required'),
            ('credentials', 'credentials'),
            ('resource', 'resource'),
            ('publicclient', 'public-client'),
            ('useresourcerolemappings', 'use-resource-role-mappings'),
            ('enablecors', 'enable-cors'),
            ('corsmaxage', 'cors-max-age'),
            ('corsallowedmethods', 'cors-allowed-methods'),
            ('corsallowedheaders', 'cors-allowed-headers'),
            ('corsexposedheaders', 'cors-exposed-headers'),
            ('exposetoken', 'expose-token'),
            ('beareronly', 'bearer-only'),
            ('autodetectbeareronly', 'autodetect-bearer-only'),
            ('connectionpoolsize', 'connection-pool-size'),
            ('allowanyhostname', 'allow-any-hostname'),
            ('disabletrustmanager', 'disable-trust-manager'),
            ('truststore', 'truststore'),
            ('truststorepassword', 'truststore-password'),
            ('clientkeystore', 'client-keystore'),
            ('clientkeystorepassword', 'client-keystore-password'),
            ('clientkeypassword', 'client-key-password'),
            ('alwaysrefreshtoken', 'always-refresh-token'),
            ('registernodeatstartup', 'register-node-at-startup'),
            ('registernodeperiod', 'register-node-period'),
            ('tokenstore', 'token-store'),
            ('tokencookiepath', 'token-cookie-path'),
            ('principalattribute', 'principal-attribute'),
            ('proxyurl', 'proxy-url'),
            ('turnoffchangesessionidonlogin', 'turn-off-change-session-id-on-login'),
            ('tokenminimumtimetolive', 'token-minimum-time-to-live'),
            ('mintimebetweenjwksrequests', 'min-time-between-jwks-requests'),
            ('publickeycachettl', 'public-key-cache-ttl'),
            ('ignoreoauthqueryparameter', 'ignore-oauth-query-parameter'),
            ('verifytokenaudience', 'verify-token-audience'),
            ('enablebasicauth', 'enable-basic-auth'),
            ('confidentialport', 'confidential-port'),
            ('redirectrewriterules', 'redirect-rewrite-rules')
        ])

    def get_class_name(self):
        if self.module['moduletype'] == 'directAccess':
            return 'org.keycloak.adapters.jaas.DirectAccessGrantsLoginModule'
        return 'org.keycloak.adapters.jaas.BearerTokenLoginModule'

    def get_properties(self):
        cfg_file = "${artemis.instance}/etc/keycloak-" + self.module['name'] + ".json"
        props = [["keycloak-config-file", cfg_file], ["role-principal-class",
                                                      "org.apache.activemq.artemis.spi.core.security.jaas.RolePrincipal"]]
        if self.module['moduletype'] == 'directAccess' and 'scope' in self.module['configuration']:
            mod_scope = self.module['configuration']['scope']
            if mod_scope is not None:
                props.append(["scope", self.module['configuration']['scope']])
        return props

    def get_dependent_modules(self, for_domain):
        if self.module['moduletype'] == 'directAccess' or for_domain == 'broker':
            return [PrincipalConversionLoginModule()]
        return []

    def del_none(self, kc_cfg):
        simple_data = {}
        for prop_key in self.cfg_keymap:
            if prop_key == 'credentials' or prop_key == 'redirectrewriterules':
                # credentials is a list of key-values
                if len(kc_cfg[prop_key]) > 0:
                    real_value = OrderedDict()
                    for entry in kc_cfg[prop_key]:
                        real_value[entry['key']] = entry['value']
                    simple_data[self.cfg_keymap[prop_key]] = real_value
            elif kc_cfg[prop_key] is not None:
                simple_data[self.cfg_keymap[prop_key]] = kc_cfg[prop_key]
        return simple_data

    def get_json_str(self, data):
        simple_data = self.del_none(data)
        cfg_content = json.dumps(simple_data, indent=2)
        return cfg_content

    def get_json_str_for_js_client(self, cfg):
        client_js_json = OrderedDict()
        client_js_json['realm'] = cfg['realm']
        client_js_json['clientId'] = cfg['resource']
        client_js_json['url'] = cfg['authserverurl']
        return json.dumps(client_js_json, indent=2)

    def configure(self, context, taget_domain_type):
        cfg_file = "keycloak-" + self.module['name'] + ".json"
        keycloak_cfg = self.module['configuration']
        keycloak_cfg_json = self.get_json_str(keycloak_cfg)
        context.add_extra_resources(TextExtraResource(keycloak_cfg_json, cfg_file))
        if self.module['moduletype'] == 'bearerToken' and context.console_domain is not None:
            console_js = "keycloak-js-client-" + self.module['name'] + ".json"
            js_cfg_json = self.get_json_str_for_js_client(keycloak_cfg)
            context.add_extra_resources(TextExtraResource(js_cfg_json, console_js))
            context.add_extra_resources(ModifyArtemisProfileForKeycloak(keycloak_cfg, console_js,
                                                                        context.console_domain.get_name()))
            context.add_extra_resources(CopyKeycloakDependencies())


class JaasLoginConfig:
    def __init__(self, file_path):
        self.file = file_path
        self.license = []
        self.domain_list = []

    def update_broker_domain(self, new_domain, context):
        self.update_domain(0, new_domain, context)

    def update_console_domain(self, new_domain, context):
        self.update_domain(1, new_domain, context)

    def update_domain(self, position, new_domain, context):
        self.load(context)
        if len(self.domain_list) > position:
            self.domain_list[position] = new_domain
        else:
            self.domain_list.append(new_domain)
        self.save()

    def save(self):
        with open(self.file, "wt") as login_config_stream:
            for line in self.license:
                login_config_stream.write(line)
            for domain in self.domain_list:
                login_config_stream.write(domain.get_name() + " {\n")
                for m in domain.get_login_modules():
                    login_config_stream.write("   " + m.get_class_name() + " " + m.get_flag() + "\n")
                    if m.get_debug() is not None:
                        if m.get_debug() is True:
                            login_config_stream.write("       debug=true\n")
                        else:
                            login_config_stream.write("       debug=false\n")
                    if m.get_reload() is not None:
                        if m.get_reload() is True:
                            login_config_stream.write("       reload=true\n")
                        else:
                            login_config_stream.write("       reload=false\n")
                    i = 0
                    size = len(m.get_properties())
                    for prop in m.get_properties():
                        i += 1
                        login_config_stream.write("       " + prop[0] + '="' + prop[1] + '"')
                        if i == size:
                            # last one
                            login_config_stream.write(";\n\n")
                        else:
                            login_config_stream.write("\n")
                login_config_stream.write("};\n\n")

    def load(self, context):
        stage = "license"
        current_domain = None
        current_module = None
        with open(self.file, "rt") as login_config_stream:
            for each_line in login_config_stream:
                if stage == "license":
                    if each_line.startswith(" */"):
                        self.license.append(each_line)
                        self.license.append("\n")
                        stage = "domain"
                        continue
                    if each_line.startswith("/*") or each_line.startswith(" *"):
                        self.license.append(each_line)
                        continue
                elif stage == "domain":
                    # strip() will remove new line as well
                    if each_line.strip() == "":
                        continue
                    if each_line.endswith("{\n"):
                        # new domain
                        s_domain_name = each_line.split(' ')[0]
                        current_domain = SecurityDomain(None, "unspecified", context)
                        current_domain.set_name(s_domain_name)
                        self.domain_list.append(current_domain)
                    elif each_line.endswith("};") or each_line.endswith("};\n"):
                        # domain end
                        pass
                    else:
                        if each_line.find('=') == -1:
                            current_module = LoginModule("")
                            # the class
                            class_fields = each_line.strip().split(" ")
                            current_module.set_class_name(class_fields[0])
                            current_module.set_flag(class_fields[1])
                            current_domain.add_login_module(current_module)
                        else:
                            # properties
                            prop_pair = each_line.strip().split('=')
                            if prop_pair[0] == 'debug':
                                current_module.set_debug(bool(prop_pair[1]))
                            elif prop_pair[0] == 'reload':
                                current_module.set_reload(bool(prop_pair[1]))
                            else:
                                if prop_pair[1].endswith(";"):
                                    prop_pair[1] = prop_pair[1][0:(len(prop_pair[1]) - 1)]
                                current_module.add_property(prop_pair[0], prop_pair[1].strip('"'))


class SecurityDomain:
    def __init__(self, domain, domain_type, context):
        self.context = context
        self.domain = domain
        self.domain_name = ""
        self.domain_type = domain_type
        self.login_modules = []
        self.load_login_modules()

    def load_login_modules(self):
        if self.domain is None:
            return
        self.set_name(self.domain['name'])
        mod_refs = self.domain['loginmodules']
        for m in mod_refs:
            lm = self.context.get_login_module(m['name'])
            lm.flag = m['flag']
            lm.set_debug(m['debug'])
            lm.set_reload(m['reload'])
            self.login_modules.append(lm)

    def set_name(self, new_name):
        self.domain_name = new_name

    def get_name(self):
        return self.domain_name

    def add_login_module(self, m):
        self.login_modules.append(m)

    def get_login_modules(self):
        all_modules = []
        for m in self.login_modules:
            all_modules.append(m)
            deps = m.get_dependent_modules(self.domain_type)
            if deps is not None:
                for dm in deps:
                    all_modules.append(dm)
        return all_modules

    def is_empty(self):
        return len(self.login_modules) == 0

    def configure(self, config_context):
        pass


class BrokerSecurityDomain(SecurityDomain):
    def __init__(self, domain, domain_type, context):
        SecurityDomain.__init__(self, domain, domain_type, context)

    def configure(self, config_context):
        # this has to be first domain section
        print("configuring broker domain", self.get_name())
        if self.get_name() is not None and len(self.get_name()) > 0:
            login_config = JaasLoginConfig(config_context.get_login_config_file())
            login_config.update_broker_domain(self, config_context)

            dst_bootstrap = config_context.get_bootstrap_file()

            with open(dst_bootstrap.absolute(), 'rt') as bootstrap_xml:
                bootstrap = bootstrap_xml.read()
                new_bootstrap = re.sub(r'<jaas-security domain="activemq"/>',
                                       '<jaas-security domain="' + self.get_name() + '"/>', bootstrap)
            with open(dst_bootstrap.absolute(), 'wt') as bootstrap_xml:
                bootstrap_xml.write(new_bootstrap)
            for lm in self.login_modules:
                lm.configure(config_context, 'broker')


class ConsoleDomain(SecurityDomain, ExtraResource):
    def __init__(self, domain, domain_type, context):
        SecurityDomain.__init__(self, domain, domain_type, context)

    def configure(self, config_context):
        login_config = JaasLoginConfig(config_context.get_login_config_file())
        login_config.update_console_domain(self, config_context)
        for lm in self.login_modules:
            lm.configure(config_context, self.domain_type)
        config_context.add_extra_resources(self)

    def create(self, dest_dir):
        self.update_hawtio_flag()

    def update_hawtio_flag(self):
        dst_artemis_profile = Path(self.context.dst_root).joinpath(ARTEMIS_PROFILE)
        lines = []
        with open(dst_artemis_profile.absolute(), "rt") as artemis_profile:
            for line in artemis_profile:
                if line.find("-Dhawtio.realm=activemq") >= 0:
                    line = line.replace("-Dhawtio.realm=activemq", "-Dhawtio.realm=" + self.domain_name)
                lines.append(line)
        with open(dst_artemis_profile.absolute(), "wt") as artemis_profile:
            artemis_profile.writelines(lines)


class ManagementSetting:
    def __init__(self, data):
        self.data = data
        self.hawtio_roles = []
        self.connector = {}
        self.allowed_list = []
        self.default_list = []
        self.role_access_list = []
        self.load()

    def add_hawtio_role(self, role):
        self.hawtio_roles.append(role)

    def get_hawtio_roles(self):
        return self.hawtio_roles

    def set_management_connector(self, connector):
        self.connector = connector

    def get_management_connector(self):
        return self.connector

    def set_management_allowed_list(self, allowed_list):
        self.allowed_list = allowed_list

    def get_management_allowed_list(self):
        return self.allowed_list

    def set_management_default_list(self, default_list):
        self.default_list = default_list

    def get_management_default_list(self):
        return self.default_list

    def set_management_role_access_list(self, role_access_list):
        self.role_access_list = role_access_list

    def get_management_role_access_list(self):
        return self.role_access_list

    def load(self):
        if 'hawtioroles' in self.data:
            for hirole in self.data['hawtioroles']:
                self.add_hawtio_role(hirole)
        if 'connector' in self.data:
            self.set_management_connector(self.data['connector'])
        if len(self.data['authorisation']['allowedlist']) > 0:
            self.set_management_allowed_list(self.data['authorisation']['allowedlist'])
        if len(self.data['authorisation']['defaultaccess']) > 0:
            self.set_management_default_list(self.data['authorisation']['defaultaccess'])
        if len(self.data['authorisation']['roleaccess']) > 0:
            self.set_management_role_access_list(self.data['authorisation']['roleaccess'])

    def configure(self, context):
        if len(self.hawtio_roles) > 0:
            self.configure_hawtio_roles(context)
        if len(self.connector) > 0:
            self.configure_connector(context)
        if len(self.allowed_list) > 0:
            self.configure_allowed_list(context)
        if len(self.default_list) > 0:
            self.configure_default_list(context)
        if len(self.role_access_list) > 0:
            self.configure_role_access_list(context)

    def configure_hawtio_roles(self, context):
        if len(self.hawtio_roles) == 0:
            return
        dst_artemis_profile = Path(context.dst_root).joinpath(ARTEMIS_PROFILE)
        lines = []
        with open(dst_artemis_profile.absolute(), "rt") as artemis_profile:
            for line in artemis_profile:
                if line.startswith('HAWTIO_ROLE=') and len(self.hawtio_roles) > 0:
                    new_line = StringIO()
                    new_line.write('HAWTIO_ROLE="')
                    first_role = True
                    for role in self.hawtio_roles:
                        if not first_role:
                            new_line.write(',')
                        new_line.write(role)
                        first_role = False
                    new_line.write('"\n')
                    lines.append(new_line.getvalue())
                else:
                    lines.append(line)
        with open(dst_artemis_profile.absolute(), "wt") as artemis_profile:
            artemis_profile.writelines(lines)

    def configure_connector(self, context):
        dst_mgmt_xml = Path(context.dst_root).joinpath(MANAGEMENT_XML)
        dst_mgmt = ManagementXml(dst_mgmt_xml.absolute(), False)
        dst_mgmt.merge_connector_from(self.get_management_connector())

    def configure_allowed_list(self, context):
        dst_mgmt_xml = Path(context.dst_root).joinpath(MANAGEMENT_XML)
        dst_mgmt = ManagementXml(dst_mgmt_xml.absolute(), False)
        dst_mgmt.merge_allowed_list_from(self.get_management_allowed_list())

    def configure_default_list(self, context):
        dst_mgmt_xml = Path(context.dst_root).joinpath(MANAGEMENT_XML)
        dst_mgmt = ManagementXml(dst_mgmt_xml.absolute(), False)
        dst_mgmt.merge_default_list_from(self.get_management_default_list())

    def configure_role_access_list(self, context):
        dst_mgmt_xml = Path(context.dst_root).joinpath(MANAGEMENT_XML)
        dst_mgmt = ManagementXml(dst_mgmt_xml.absolute(), False)
        dst_mgmt.merge_role_access_list_from(self.get_management_role_access_list())


# create content files under ${instanceDir}/etc
class TextExtraResource(ExtraResource):
    def __init__(self, text, name):
        self.content = text
        self.file_name = name

    def create(self, dest_dir):
        target_path = Path(dest_dir).joinpath('etc/' + self.file_name).absolute()
        with open(target_path, "wt") as extra_file:
            extra_file.write(self.content)


class BaseArtemisXml:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.namespaces = {'amq': 'urn:activemq', 'core': 'urn:activemq:core'}
        self.xml_indent = '   '


class ManagementXml(BaseArtemisXml):
    def __init__(self, mgmtxml, is_from_yacfg):
        BaseArtemisXml.__init__(self, mgmtxml)
        if is_from_yacfg:
            # NOW yacfg is gone, always false!
            # yacfg still uses old namespace to parse management.xml
            # so not to use the new namespce http://activemq.apache.org/schema
            self.namespaces = {'mgmt': "http://activemq.org/schema"}
        else:
            self.namespaces = {'mgmt': "http://activemq.apache.org/schema"}
        self.connector_keymap = OrderedDict([
            ('host', 'connector-host'),
            ('port', 'connector-port'),
            ('rmiregistryport', 'rmi-registry-port'),
            ('jmxrealm', 'jmx-realm'),
            ('objectname', 'object-name'),
            ('authenticatortype', 'authenticator-type'),
            ('secured', 'secured'),
            ('keystoreprovider', 'key-store-provider'),
            ('keystoretype', 'key-store-type'),
            ('keystorepath', 'key-store-path'),
            ('keystorepassword', 'key-store-password'),
            ('truststoreprovider', 'trust-store-provider'),
            ('truststoretype', 'trust-store-type'),
            ('truststorepath', 'trust-store-path'),
            ('truststorepassword', 'trust-store-password'),
            ('passwordcodec', 'password-codec')
        ])

    def merge_connector_from(self, new_connector):
        new_connector_str = StringIO()
        new_connector_str.write('<connector ')
        something_written = False
        for prop_key, prop_name in self.connector_keymap.items():
            prop_value = new_connector.get(prop_key)
            if prop_value is not None:
                new_connector_str.write(prop_name)
                new_connector_str.write('=\"')
                if isinstance(prop_value, str):
                    new_connector_str.write(prop_value)
                else:
                    new_connector_str.write(str(prop_value).lower())
                new_connector_str.write('\" ')
                something_written = True
        new_connector_str.write('/>\n')
        if something_written:
            with open(self.xml_file, 'rt') as mgmtxml:
                original_xml = mgmtxml.read()
                new_xml = re.sub(r'<authorisation>', new_connector_str.getvalue() + "   <authorisation>", original_xml)
            with open(self.xml_file, 'wt') as mgmtxml:
                mgmtxml.write(new_xml)

    def get_connector(self):
        with open(self.xml_file, "rt") as mgmt_tmp:
            data = mgmt_tmp.read()
            print(data)
        src_mgmt_tree = ET.parse(self.xml_file)
        src_mgmt_tree_root = src_mgmt_tree.getroot()
        connector = src_mgmt_tree_root.findall('mgmt:connector', self.namespaces)
        return connector

    def merge_allowed_list_from(self, new_allowed_list):
        new_allowed_list_str = StringIO()
        new_allowed_list_str.write('<allowlist>\n')
        for entry in new_allowed_list:
            new_allowed_list_str.write(self.xml_indent * 3)
            new_allowed_list_str.write('<entry')
            if 'domain' in entry and entry['domain'] is not None:
                new_allowed_list_str.write(' domain=\"')
                new_allowed_list_str.write(entry['domain'])
                new_allowed_list_str.write('\"')
            if 'key' in entry and entry['key'] is not None:
                new_allowed_list_str.write(' key=\"')
                new_allowed_list_str.write(entry.attrib['key'])
                new_allowed_list_str.write('\"')
            new_allowed_list_str.write(' />\n')
        new_allowed_list_str.write(self.xml_indent * 2)
        new_allowed_list_str.write('</allowlist>')
        with open(self.xml_file, 'rt') as mgmtxml:
            original_xml = mgmtxml.read()
            new_xml = re.sub(r'<allowlist>[\s\S]*</allowlist>', new_allowed_list_str.getvalue(), original_xml, re.M)
        with open(self.xml_file, 'wt') as mgmtxml:
            mgmtxml.write(new_xml)

    def get_allowed_list(self):
        src_mgmt_tree = ET.parse(self.xml_file)
        src_mgmt_tree_root = src_mgmt_tree.getroot()
        allowed_list = src_mgmt_tree_root.findall('mgmt:authorisation/mgmt:whitelist/mgmt:entry', self.namespaces)
        return allowed_list

    def merge_default_list_from(self, new_default_list):
        new_default_list_str = StringIO()
        new_default_list_str.write('<default-access>\n')
        for entry in new_default_list:
            new_default_list_str.write(self.xml_indent * 3)
            new_default_list_str.write('<access')
            if 'method' in entry and entry['method'] is not None:
                new_default_list_str.write(' method=\"')
                new_default_list_str.write(entry['method'])
                new_default_list_str.write('\"')
            if 'roles' in entry:
                new_default_list_str.write(' roles=\"')
                new_default_list_str.write(','.join(entry['roles']))
                new_default_list_str.write('\"')
            new_default_list_str.write(' />\n')
        new_default_list_str.write(self.xml_indent * 2)
        new_default_list_str.write('</default-access>')
        with open(self.xml_file, 'rt') as mgmtxml:
            original_xml = mgmtxml.read()
            new_xml = re.sub(r'<default-access>[\s\S]*</default-access>', new_default_list_str.getvalue(), original_xml,
                             re.M)
        with open(self.xml_file, 'wt') as mgmtxml:
            mgmtxml.write(new_xml)

    def get_default_list(self):
        src_mgmt_tree = ET.parse(self.xml_file)
        src_mgmt_tree_root = src_mgmt_tree.getroot()
        default_list = src_mgmt_tree_root.findall('mgmt:authorisation/mgmt:default-access/mgmt:access', self.namespaces)
        return default_list

    def merge_role_access_list_from(self, new_role_access_list):
        new_role_access_list_str = StringIO()
        new_role_access_list_str.write('<role-access>\n')
        for access_entry in new_role_access_list:
            new_role_access_list_str.write(self.xml_indent * 3)
            new_role_access_list_str.write('<match ')
            for prop in ['domain', 'key']:
                if prop in access_entry and access_entry[prop] is not None:
                    new_role_access_list_str.write(prop)
                    new_role_access_list_str.write('=\"')
                    new_role_access_list_str.write(access_entry[prop])
                    new_role_access_list_str.write('\" ')
            new_role_access_list_str.write('>\n')
            new_access_list = access_entry['accesslist']
            for access in new_access_list:
                new_role_access_list_str.write(self.xml_indent * 4)
                new_role_access_list_str.write('<access ')
                if 'method' in access:
                    new_role_access_list_str.write('method')
                    new_role_access_list_str.write('=\"')
                    new_role_access_list_str.write(access['method'])
                    new_role_access_list_str.write('\" ')
                if 'roles' in access:
                    new_role_access_list_str.write('roles')
                    new_role_access_list_str.write('=\"')
                    new_role_access_list_str.write(','.join(access['roles']))
                    new_role_access_list_str.write('\" ')
                new_role_access_list_str.write('/>\n')
            new_role_access_list_str.write(self.xml_indent * 3)
            new_role_access_list_str.write('</match>\n')
        new_role_access_list_str.write(self.xml_indent * 2)
        new_role_access_list_str.write('</role-access>')
        with open(self.xml_file, 'rt') as mgmtxml:
            original_xml = mgmtxml.read()
            new_xml = re.sub(r'<role-access>[\s\S]*</role-access>', new_role_access_list_str.getvalue(), original_xml,
                             re.M)
        with open(self.xml_file, 'wt') as mgmtxml:
            mgmtxml.write(new_xml)

    def get_role_access_list(self):
        src_mgmt_tree = ET.parse(self.xml_file)
        src_mgmt_tree_root = src_mgmt_tree.getroot()
        role_access_list = src_mgmt_tree_root.findall('mgmt:authorisation/mgmt:role-access/mgmt:match', self.namespaces)
        return role_access_list


class BrokerXml(BaseArtemisXml):
    def __init__(self, brokerxml):
        BaseArtemisXml.__init__(self, brokerxml)

    def merge_security_settings(self, new_security_settings):
        print("Merging security settings")
        new_settings = StringIO()
        new_settings.write('<security-settings>')
        new_settings.write('\n')
        for each_match in new_security_settings.get_match_list():
            new_settings.write(self.xml_indent * 3)
            new_settings.write('<security-setting match=\"')
            new_settings.write(each_match.get_key())
            new_settings.write('\">\n')
            permissions = each_match.get_permissions()
            for perm in permissions:
                new_settings.write(self.xml_indent * 4)
                new_settings.write('<permission type=\"')
                new_settings.write(perm.get_operation_type())
                new_settings.write('\" roles=\"')
                new_settings.write(','.join(perm.get_roles()))
                new_settings.write('\"/>')
                new_settings.write('\n')
            new_settings.write(self.xml_indent * 3)
            new_settings.write('</security-setting>\n')
        new_settings.write(self.xml_indent * 2)
        new_settings.write("</security-settings>\n")

        with open(self.xml_file, 'rt') as brokerxml:
            original_xml = brokerxml.read()
            new_xml = re.sub(r'<security-settings>[\s\S]*</security-settings>', new_settings.getvalue(),
                             original_xml, re.M)
        with open(self.xml_file, 'wt') as brokerxml:
            brokerxml.write(new_xml)

    def get_security_settings(self):
        src_broker_tree = ET.parse(self.xml_file)
        src_broker_tree_root = src_broker_tree.getroot()

        elem_security_settings = src_broker_tree_root.findall('core:core/core:security-settings', self.namespaces)
        settings = OrderedDict()
        for elem in elem_security_settings:
            sec_setting_list = elem.findall('core:security-setting', self.namespaces)
            for setting in sec_setting_list:
                match = setting.attrib['match']
                settings[match] = setting
        return settings


class PermissionEntry:
    def __init__(self, data):
        self.operation_type = data['operationtype']
        self.roles = data['roles']

    def get_operation_type(self):
        return self.operation_type

    def get_roles(self):
        return self.roles


class MatchEntry:
    def __init__(self, key):
        self.key = key
        self.permissions = []

    def get_key(self):
        return self.key

    def set_permissions(self, perm_list):
        for p in perm_list:
            pm = PermissionEntry(p)
            self.permissions.append(pm)

    def get_permissions(self):
        return self.permissions


class BrokerSecuritySettings:
    def __init__(self, settings):
        self.settings = settings
        self.match_list = []

    def get_match_list(self):
        for match in self.settings:
            match_entry = MatchEntry(match['match'])
            match_entry.set_permissions(match['permissions'])
            self.match_list.append(match_entry)
        return self.match_list

    def configure(self, context):
        dst_broker_xml = context.get_broker_xml_file()
        dst_broker = BrokerXml(dst_broker_xml.absolute())
        dst_broker.merge_security_settings(self)


class ConfigContext:
    def __init__(self, target_root):
        self.security_cr = None
        self.dst_root = target_root
        self.login_modules = {}
        self.broker_security_settings = None
        self.broker_domain = None
        self.console_domain = None
        self.management_setting = None
        self.extra_resources = []

    def get_config_file_path(self, cfg_file_name):
        return Path(self.dst_root).joinpath('etc').joinpath(cfg_file_name)

    def get_artemis_profile_file(self):
        return Path(self.dst_root).joinpath(ARTEMIS_PROFILE)

    def get_bootstrap_file(self):
        return Path(self.dst_root).joinpath(BOOTSTRAP)

    def get_broker_xml_file(self):
        return Path(self.dst_root).joinpath(BROKER_XML)

    def get_users_prop_file(self):
        return Path(self.dst_root).joinpath(USERS_PROP_FILE)

    def get_roles_prop_file(self):
        return Path(self.dst_root).joinpath(ROLES_PROP_FILE)

    def get_management_xml_file(self):
        return Path(self.dst_root).joinpath(MANAGEMENT_XML)

    def set_broker_settings(self, settings):
        self.broker_security_settings = BrokerSecuritySettings(settings)

    def get_management_setting(self):
        return self.management_setting

    def set_management_setting(self, setting):
        self.management_setting = setting

    def add_extra_resources(self, res):
        self.extra_resources.append(res)

    def add_login_module(self, m):
        self.login_modules[m.name] = m

    def get_login_module(self, m_name):
        return self.login_modules[m_name]

    def set_broker_domain(self, domain):
        self.broker_domain = domain

    def get_login_config_file(self):
        return Path(self.dst_root).joinpath(LOGIN_CONFIG)

    def apply_login_config(self):
        print('Applying login modules')
        if self.broker_domain:
            self.broker_domain.configure(self)
        if self.console_domain:
            self.console_domain.configure(self)
        if len(self.login_modules) > 0 and (self.broker_domain is None or self.broker_domain.is_empty()) and (self.console_domain is None or self.console_domain.is_empty()):
            print("WARNING: Login module defined but not used!")
            for lm in self.login_modules:
                print("Defined module:", lm)

    def apply_broker_security(self):
        print("Applying broker security settings")
        if self.broker_security_settings:
            self.broker_security_settings.configure(self)

    def apply_management(self):
        if self.management_setting:
            self.management_setting.configure(self)

    def create_extra_resources(self):
        if len(self.extra_resources) > 0:
            for extra_res in self.extra_resources:
                extra_res.create(self.dst_root)

    def apply(self):
        self.apply_login_config()
        self.apply_broker_security()
        self.apply_management()
        self.create_extra_resources()

    def set_console_domain(self, console_domain):
        self.console_domain = console_domain

    def parse_config_cr(self, cr_file):
        with open(cr_file, "r") as file:
            self.security_cr = yaml.safe_load(file)
            # login_modules = {}
            propertiesLoginModules = self.security_cr['spec']['loginmodules']['propertiesloginmodules']
            for module in propertiesLoginModules:
                self.add_login_module(PropertiesLoginModule(module['name'], module))

            guestloginmodules = self.security_cr['spec']['loginmodules']['guestloginmodules']
            for module in guestloginmodules:
                self.add_login_module(GuestLoginModule(module['name'], module))

            keycloakloginmodules = self.security_cr['spec']['loginmodules']["keycloakloginmodules"]
            for module in keycloakloginmodules:
                self.add_login_module(KeycloakLoginModule(module['name'], module))

            if 'brokerdomain' in self.security_cr['spec']['securitydomains']:
                broker_domain = self.security_cr['spec']['securitydomains']['brokerdomain']
                if broker_domain['name'] is not None:
                    self.set_broker_domain(BrokerSecurityDomain(broker_domain, 'broker', self))

            if 'consoledomain' in self.security_cr['spec']['securitydomains']:
                console_domain = self.security_cr['spec']['securitydomains']['consoledomain']
                if console_domain['name'] is not None:
                    self.set_console_domain(ConsoleDomain(console_domain, 'console', self))

            # now security-settings for broker.xml
            if 'securitysettings' in self.security_cr['spec']:
                if 'broker' in self.security_cr['spec']['securitysettings']:
                    broker_settings = self.security_cr['spec']['securitysettings']['broker']
                    if len(broker_settings) > 0:
                        self.set_broker_settings(broker_settings)

                if 'management' in self.security_cr['spec']['securitysettings']:
                    mgmt_setting = self.security_cr['spec']['securitysettings']['management']
                    mgmt = ManagementSetting(mgmt_setting)
                    self.set_management_setting(mgmt)
