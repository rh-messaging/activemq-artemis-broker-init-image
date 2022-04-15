import yaml
from pathlib import Path
from io import StringIO
import json
import os
import re
import shutil
from collections import OrderedDict
import urllib.request
import apply_security
from yacfg import yacfg

INDENT_2 = '  '


class LoginModule:
    def __init__(self, name):
        self.name = name

    def get_class_name(self):
        pass

    def get_properties(self):
        return []

    def generate_specific_tunes(self):
        pass

    def get_dependent_modules(self, for_domain):
        pass


class PrincipalConversionLoginModule(LoginModule):
    def __init__(self):
        LoginModule.__init__(self, "internal_principal_conversion")

    def get_class_name(self):
        return 'org.apache.activemq.artemis.spi.core.security.jaas.PrincipalConversionLoginModule'

    def get_properties(self):
        return [["principalClassList", "org.keycloak.KeycloakPrincipal"]]


class PropertiesLoginModule(LoginModule):
    def __init__(self, name, module1):
        LoginModule.__init__(self, name)
        self.module = module1
        self.has_users = False

    def get_class_name(self):
        return 'org.apache.activemq.artemis.spi.core.security.jaas.PropertiesLoginModule'

    def get_properties(self):
        return [['org.apache.activemq.jaas.properties.user', 'artemis-users.properties'], ['org.apache.activemq.jaas'
                                                                                           '.properties.role',
                                                                                               'artemis-roles.properties']]

    def generate_specific_tunes(self):
        if 'users' in self.module and len(self.module['users']) > 0:
            self.has_users = True
            users_roles_tune_data = StringIO()
            role_map = {}
            users_roles_tune_data.write('user_artemis_users:')
            users_roles_tune_data.write('\n')
            for user in self.module['users']:
                users_roles_tune_data.write(INDENT_2)
                users_roles_tune_data.write(user['name'])
                users_roles_tune_data.write(': ')
                users_roles_tune_data.write('\'')
                users_roles_tune_data.write(user['password'])
                users_roles_tune_data.write('\'')
                users_roles_tune_data.write('\n')
                #collect role info
                for role in user['roles']:
                    if role in role_map:
                        ulist = role_map[role]
                        ulist.append(user['name'])
                    else:
                        ulist = [user['name']]
                        role_map[role] = ulist
            users_roles_tune_data.write('user_artemis_roles:')
            users_roles_tune_data.write('\n')
            for key, value in role_map.items():
                users_roles_tune_data.write(INDENT_2)
                users_roles_tune_data.write(key)
                users_roles_tune_data.write(':')
                users_roles_tune_data.write('\n')
                for r in value:
                    users_roles_tune_data.write(INDENT_2 * 2)
                    users_roles_tune_data.write('- ')
                    users_roles_tune_data.write(r)
                    users_roles_tune_data.write('\n')
            yacfg_context.add_tune_data(users_roles_tune_data.getvalue())


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


class CopyKeycloakDependencies(apply_security.ExtraResource):
    def create(self, dest_dir):
        # for upstream may download
        print("checking keycloak dep jars...")
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


class ModifyArtemisProfileForKeycloak(apply_security.ExtraResource):
    def __init__(self, keycloak_cfg, js_client_cfg, console_realm):
        self.keycloak_cfg = keycloak_cfg
        self.js_client_cfg = js_client_cfg
        self.hawtio_realm = console_realm

    def create(self, dest_dir):
        artemis_profile = Path(dest_dir).joinpath(apply_security.ARTEMIS_PROFILE)
        print("now modify artemis profile in", artemis_profile.absolute())
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

    def generate_specific_tunes(self):
        cfg_file = "keycloak-" + self.module['name'] + ".json"
        keycloak_cfg = self.module['configuration']
        keycloak_cfg_json = self.get_json_str(keycloak_cfg)
        yacfg_context.add_extra_resources(apply_security.TextExtraResource(keycloak_cfg_json, cfg_file))
        if self.module['moduletype'] == 'bearerToken' and yacfg_context.console_domain_defined():
            console_js = "keycloak-js-client-" + self.module['name'] + ".json"
            js_cfg_json = self.get_json_str_for_js_client(keycloak_cfg)
            yacfg_context.add_extra_resources(apply_security.TextExtraResource(js_cfg_json, console_js))
            yacfg_context.add_extra_resources(ModifyArtemisProfileForKeycloak(keycloak_cfg, console_js,
                                                                              yacfg_context.get_console_domain_name()))
            yacfg_context.add_extra_resources(CopyKeycloakDependencies())


class SecurityDomain:
    def __init__(self, domain, domain_type):
        self.domain = domain
        self.domain_type = domain_type

    def write_yaml(self, indent, jaas_modules):
        yaml_str = StringIO()
        yaml_str.write(indent)
        yaml_str.write('- name: ')
        yaml_str.write(self.domain['name'])
        yaml_str.write('\n')

        modules = self.domain['loginmodules']
        yaml_str.write(indent*2)
        yaml_str.write('modules:')
        yaml_str.write('\n')
        for mod in modules:
            login_module = jaas_modules[mod['name']]
            yaml_str.write(indent*3)
            yaml_str.write('- class_name: ')
            yaml_str.write(login_module.get_class_name())
            yaml_str.write('\n')
            yaml_str.write(indent*4)
            yaml_str.write('flag: ')
            yaml_str.write(mod['flag'])
            yaml_str.write('\n')
            if 'debug' in mod or 'reload' in mod:
                yaml_str.write(indent*4)
                yaml_str.write('properties: ')
                yaml_str.write('\n')
                if 'debug' in mod and mod['debug']:
                    yaml_str.write(indent*5)
                    yaml_str.write('- debug: ')
                    yaml_str.write(str(mod['debug']))
                    yaml_str.write('\n')
                if 'reload' in mod and mod['reload']:
                    yaml_str.write(indent*5)
                    yaml_str.write('- reload: ')
                    yaml_str.write(str(mod['reload']))
                    yaml_str.write('\n')
            specific_props = login_module.get_properties()
            if len(specific_props) > 0:
                for prop in specific_props:
                    yaml_str.write(indent*5)
                    yaml_str.write('- ')
                    yaml_str.write(prop[0])
                    yaml_str.write(': ')
                    yaml_str.write(prop[1])
                    yaml_str.write('\n')
            login_module.generate_specific_tunes()
            dep_modules = login_module.get_dependent_modules(self.domain_type)
            if dep_modules is not None:
                for dep_mod in dep_modules:
                    yaml_str.write(indent * 3)
                    yaml_str.write('- class_name: ')
                    yaml_str.write(dep_mod.get_class_name())
                    yaml_str.write('\n')
                    yaml_str.write(indent * 4)
                    yaml_str.write('flag: ')
                    yaml_str.write('required')
                    yaml_str.write('\n')
                    specific_props = dep_mod.get_properties()
                    if len(specific_props) > 0:
                        yaml_str.write(indent * 4)
                        yaml_str.write('properties:\n')
                        for prop in specific_props:
                            yaml_str.write(indent * 5)
                            yaml_str.write('- ')
                            yaml_str.write(prop[0])
                            yaml_str.write(': ')
                            yaml_str.write(prop[1])
                            yaml_str.write('\n')
                    login_module.generate_specific_tunes()
        return yaml_str.getvalue()


def process_domains(domains):
    login_config_tune = StringIO()
    login_config_tune.write("login_config:\n")
    for domain in domains:
        if domain.domain['name']:
            login_config_tune.write(domain.write_yaml(INDENT_2, login_modules))
    yacfg_context.add_tune_data(login_config_tune.getvalue())


def get_broker_security_setting_yaml(indent, sec_setting_entry):
    yaml_str = StringIO()
    yaml_str.write(indent)
    yaml_str.write('- match: ')
    yaml_str.write('\'')
    yaml_str.write(sec_setting_entry['match'])
    yaml_str.write('\'')
    yaml_str.write('\n')
    yaml_str.write(indent*2)
    yaml_str.write('permissions:')
    yaml_str.write('\n')
    for perm in sec_setting_entry['permissions']:
        yaml_str.write(indent*3)
        yaml_str.write(perm['operationtype'])
        yaml_str.write(':')
        yaml_str.write('\n')
        for role in perm['roles']:
            yaml_str.write(indent*4)
            yaml_str.write('- ')
            yaml_str.write(role)
            yaml_str.write('\n')
    return yaml_str.getvalue()


def process_broker_security_settings(broker_settings):
    if len(broker_settings) > 0:
        broker_security_tune_data = StringIO()
        broker_security_tune_data.write('user_security_settings:')
        broker_security_tune_data.write('\n')
        for setting in broker_settings:
            broker_security_tune_data.write(get_broker_security_setting_yaml(INDENT_2, setting))
        yacfg_context.add_tune_data(broker_security_tune_data.getvalue())
        yacfg_context.set_broker_security_settings_defined(True)


def get_mgmt_connector_yaml(indent, connector):
    all_none = True
    for attr in connector.items():
        if attr[1] is not None:
            all_none = False
            break
    if all_none:
        return ''
    yaml_str = StringIO()
    yaml_str.write(indent)
    yaml_str.write('connector:')
    yaml_str.write('\n')
    for attr in connector.items():
        if attr[1] is not None:
            yaml_str.write(indent*2)
            yaml_str.write(attr[0])
            yaml_str.write(': ')
            yaml_str.write(str(attr[1]))
            yaml_str.write('\n')
    return yaml_str.getvalue()


def get_allowed_list_yaml(indent, allowed_list):
    yaml_str = StringIO()
    yaml_str.write(indent)
    yaml_str.write('whitelist:')
    yaml_str.write('\n')
    for entry in allowed_list:
        yaml_str.write(indent * 2)
        yaml_str.write('- ')
        first = True
        for attr in entry.items():
            if attr[1] is not None:
                if not first:
                    yaml_str.write(indent*3)
                yaml_str.write(attr[0])
                yaml_str.write(': ')
                yaml_str.write(str(attr[1]))
                yaml_str.write('\n')
                first = False
    return yaml_str.getvalue()


def get_defaultaccess_yaml(indent, defaultaccess):
    yaml_str = StringIO()
    yaml_str.write(indent)
    yaml_str.write('default_access:')
    yaml_str.write('\n')
    for entry in defaultaccess:
        yaml_str.write(indent * 2)
        yaml_str.write('- method: \'')
        yaml_str.write(entry['method'])
        yaml_str.write('\'')
        yaml_str.write('\n')
        yaml_str.write(indent*3)
        yaml_str.write('roles:')
        yaml_str.write('\n')
        for role in entry['roles']:
            yaml_str.write(indent * 4)
            yaml_str.write('- \'')
            yaml_str.write(role)
            yaml_str.write('\'')
            yaml_str.write('\n')
    return yaml_str.getvalue()


def get_roleaccess_yaml(indent, roleaccess):
    yaml_str = StringIO()
    yaml_str.write(indent)
    yaml_str.write('role_access:')
    yaml_str.write('\n')
    for entry in roleaccess:
        yaml_str.write(indent * 2)
        yaml_str.write('- domain: \'')
        yaml_str.write(entry['domain'])
        yaml_str.write('\'')
        yaml_str.write('\n')
        if 'key' in entry and entry['key'] is not None:
            yaml_str.write(indent*3)
            yaml_str.write('key: \'')
            yaml_str.write(entry['key'])
            yaml_str.write('\'\n')
        yaml_str.write(indent*3)
        yaml_str.write('access: ')
        yaml_str.write('\n')
        for ent in entry['accesslist']:
            yaml_str.write(indent * 4)
            yaml_str.write('- method: \'')
            yaml_str.write(ent['method'])
            yaml_str.write('\'')
            yaml_str.write('\n')
            yaml_str.write(indent*5)
            yaml_str.write('roles:')
            yaml_str.write('\n')
            for role in ent['roles']:
                yaml_str.write(indent * 6)
                yaml_str.write('- \'')
                yaml_str.write(role)
                yaml_str.write('\'')
                yaml_str.write('\n')
    return yaml_str.getvalue()


def process_management_settings(mgmt_setting):
    if 'hawtioroles' in mgmt_setting:
        for hirole in mgmt_setting['hawtioroles']:
            yacfg_context.add_hawtio_role(hirole)
    mgmt_tune_data = StringIO()
    mgmt_tune_data.write('user_management_xml:')
    mgmt_tune_data.write('\n')
    if 'connector' in mgmt_setting:
        connector_val = get_mgmt_connector_yaml(INDENT_2, mgmt_setting['connector'])
        if connector_val:
            mgmt_tune_data.write(connector_val)
            yacfg_context.set_management_connector_defined(True)
    if len(mgmt_setting['authorisation']['allowedlist']) > 0:
        mgmt_tune_data.write(get_allowed_list_yaml(INDENT_2, mgmt_setting['authorisation']['allowedlist']))
        yacfg_context.set_management_allowed_list_defined(True)
    if len(mgmt_setting['authorisation']['defaultaccess']) > 0:
        mgmt_tune_data.write(get_defaultaccess_yaml(INDENT_2, mgmt_setting['authorisation']['defaultaccess']))
        yacfg_context.set_management_default_list_defined(True)
    if len(mgmt_setting['authorisation']['roleaccess']) > 0:
        mgmt_tune_data.write(get_roleaccess_yaml(INDENT_2, mgmt_setting['authorisation']['roleaccess']))
        yacfg_context.set_management_role_access_list_defined(True)
    yacfg_context.add_tune_data(mgmt_tune_data.getvalue())


def list_my_dir(targetdir):
    results = os.listdir(targetdir)
    print("files under dir", targetdir)
    for item in results:
        print(item)


# As we use python, we should be able to directly call
# yacfg within instead of generate tune files first!!!
if __name__ == '__main__':
    inst_dir = os.environ['CONFIG_INSTANCE_DIR']
    amq_name = os.environ['AMQ_NAME']
    target_dir = inst_dir + "/" + amq_name
    source_dir = 'yacfg-etc'

    print("config target dir root is(instancedir) ", target_dir)

    yacfg_context = apply_security.ConfigContext(Path(source_dir).absolute(), Path(target_dir).absolute())

    print("yacfg output dir root: ", Path(source_dir).absolute())

    cr_file = os.getenv('SECURITY_CFG_YAML')

    with open(cr_file, "r") as file:
        security = yaml.safe_load(file)
        login_modules = {}
        propertiesLoginModules = security['spec']['loginmodules']['propertiesloginmodules']
        for module in propertiesLoginModules:
            m = PropertiesLoginModule(module['name'], module)
            login_modules[module['name']] = m
            yacfg_context.add_prop_login_module(m)

        guestloginmodules = security['spec']['loginmodules']['guestloginmodules']
        for module in guestloginmodules:
            login_modules[module['name']] = GuestLoginModule(module['name'], module)

        keycloakloginmodules = security['spec']['loginmodules']["keycloakloginmodules"]
        for module in keycloakloginmodules:
            login_modules[module['name']] = KeycloakLoginModule(module['name'], module)

        securityDomains = []
        if 'brokerdomain' in security['spec']['securitydomains']:
            brokerDomain = security['spec']['securitydomains']['brokerdomain']
            securityDomains.append(SecurityDomain(brokerDomain, 'broker'))
            yacfg_context.set_domain_defined(True)
            yacfg_context.set_broker_domain(brokerDomain['name'])

        if 'consoledomain' in security['spec']['securitydomains']:
            consoleDomain = security['spec']['securitydomains']['consoledomain']
            securityDomains.append(SecurityDomain(consoleDomain, 'console'))
            yacfg_context.set_domain_defined(True)
            yacfg_context.set_console_domain_name(consoleDomain['name'])
            yacfg_context.set_console_domain_defined(True)

        process_domains(securityDomains)

        # now security-settings for broker.xml
        if 'securitysettings' in security['spec']:
            if 'broker' in security['spec']['securitysettings']:
                process_broker_security_settings(security['spec']['securitysettings']['broker'])

            if 'management' in security['spec']['securitysettings']:
                process_management_settings(security['spec']['securitysettings']['management'])

    yacfg_profile_name = os.environ['YACFG_PROFILE_NAME']
    yacfg_profile_version = os.environ['YACFG_PROFILE_VERSION']
    print("Using yacfg profile version", yacfg_profile_version)

    ya_profile = yacfg_profile_name + "/" + yacfg_profile_version + '/default_with_security.yaml.jinja2'

    print('yacfg profile to use', ya_profile)
    yacfg.generate(profile=ya_profile,
                   output_path=source_dir+'/etc',
                   tuning_data_list=yacfg_context.get_tune_data())
    print("now apply changes...")
    yacfg_context.apply()
