import apply_security
from pathlib import Path
import xml.etree.ElementTree as ET


def dump_file(file_path):
    print('begin contents of ', file_path)
    with open(file_path, "rt") as stream:
        print(stream.read())
    print('end of contents of ', file_path)


def check_all_lines_in_file(the_file, the_list):
    with open(the_file, "rt") as role_stream:
        content = role_stream.read()
        for rl in the_list:
            if content.find(rl) == -1:
                print("line absent from property file", the_file, "line", rl)
                dump_file(the_file)
                return False
    return True


def are_files_identical(file1, file2):
    with open(file1, "rt") as file1_stream:
        file1_lines = file1_stream.readlines()
    with open(file2, "rt") as file2_stream:
        file2_lines = file2_stream.readlines()
    if len(file2_lines) != len(file1_lines):
        print("files have different lines", file1, file2)
        return False
    for i in range(len(file1_lines)):
        if file1_lines[i] != file2_lines[i]:
            print("line", i, "not equal", "original", file1_lines[i], "new", file2_lines[i])
            return False
    return True


class SecurityConfigurationChecker:
    def __init__(self, context):
        self.context = context

    def has_broker_domain(self, domain_name):
        with open(self.context.get_login_config_file(), "rt") as login_config:
            content = login_config.read()
        return content.find(domain_name + " {") >= 0

    def domain_has_direct_access_login_module(self, domain_name, flag, debug, reload):
        with open(self.context.get_login_config_file(), "rt") as login_config:
            stage = "start"

            login_module_found = False
            debug_prop_found = False
            reload_prop_found = False
            keycloak_cfg_file_prop_found = False
            role_principal_class_prop_found = False
            for line in login_config:
                if line.find(domain_name + ' {') >= 0:
                    stage = "in-domain"
                    continue
                if stage == "in-domain":
                    if line.find('};') >= 0:
                        break
                    if line.find(
                            "org.keycloak.adapters.jaas.DirectAccessGrantsLoginModule") >= 0 and line.find(
                        flag) >= 0:
                        login_module_found = True
                        continue
                    if login_module_found and line.find("debug=" + debug) >= 0:
                        debug_prop_found = True
                        continue
                    if login_module_found and line.find('reload=' + reload) >= 0:
                        reload_prop_found = True
                        continue
                    if login_module_found and line.find('keycloak-config-file="${artemis.instance}/etc/keycloak-keycloak-broker.json"') >= 0:
                        keycloak_cfg_file_prop_found = True
                        continue
                    if login_module_found and line.find(
                            'role-principal-class="org.apache.activemq.artemis.spi.core.security.jaas.RolePrincipal";') >= 0:
                        role_principal_class_prop_found = True
                        # last prop
                        break
            if debug == '':
                debug_prop_found = not debug_prop_found
            if reload == '':
                reload_prop_found = not reload_prop_found
            result = login_module_found and debug_prop_found and reload_prop_found and keycloak_cfg_file_prop_found and role_principal_class_prop_found
            if not result:
                print('login_module_found', login_module_found)
                print('debug_prop_found', debug_prop_found)
                print('reload_prop_found', reload_prop_found)
                print('keycloak_cfg_file_prop_found', keycloak_cfg_file_prop_found)
                print('role_principal_class_prop_found', role_principal_class_prop_found)
                print("the result file: ")
                dump_file(self.context.get_login_config_file())
        return result

    def domain_has_prop_login_module(self, domain_name, flag, debug, reload):
        with open(self.context.get_login_config_file(), "rt") as login_config:
            stage = "start"

            login_module_found = False
            debug_prop_found = False
            reload_prop_found = False
            user_file_prop_found = False
            roles_file_prop_found = False
            for line in login_config:
                if line.find(domain_name + ' {') >= 0:
                    stage = "in-domain"
                    continue
                if stage == "in-domain":
                    if line.find('};') >= 0:
                        break
                    if line.find(
                            "org.apache.activemq.artemis.spi.core.security.jaas.PropertiesLoginModule") >= 0 and line.find(
                        flag) >= 0:
                        login_module_found = True
                        continue
                    if login_module_found and line.find("debug=" + debug) >= 0:
                        debug_prop_found = True
                        continue
                    if login_module_found and line.find('reload=' + reload) >= 0:
                        reload_prop_found = True
                        continue
                    if login_module_found and line.find('org.apache.activemq.jaas.properties.user="artemis-users.properties"') >= 0:
                        user_file_prop_found = True
                        continue
                    if login_module_found and line.find('org.apache.activemq.jaas.properties.role="artemis-roles.properties";') >= 0:
                        roles_file_prop_found = True
                        # last prop
                        break
            if debug == '':
                debug_prop_found = not debug_prop_found
            if reload == '':
                reload_prop_found = not reload_prop_found
            result = login_module_found and debug_prop_found and reload_prop_found and user_file_prop_found and roles_file_prop_found
            if not result:
                print('login_module_found', login_module_found)
                print('debug_prop_found', debug_prop_found)
                print('reload_prop_found', reload_prop_found)
                print('user_file_prop_found', user_file_prop_found)
                print('roles_file_prop_found', roles_file_prop_found)
                print("the result file: ")
                dump_file(self.context.get_login_config_file())
        return result

    def domain_has_guest_login_module(self, domain_name, flag, debug, reload):
        with open(self.context.get_login_config_file(), "rt") as login_config:
            stage = "start"

            login_module_found = False
            debug_prop_found = False
            reload_prop_found = False
            user_file_prop_found = False
            roles_file_prop_found = False
            for line in login_config:
                if line.find(domain_name + ' {') >= 0:
                    stage = "in-domain"
                    continue
                if stage == "in-domain":
                    if line.find('};') >= 0:
                        break
                    if line.find(
                            "org.apache.activemq.artemis.spi.core.security.jaas.GuestLoginModule") >= 0 and line.find(
                        flag) >= 0:
                        login_module_found = True
                        continue
                    if line.find("debug=" + debug) >= 0:
                        debug_prop_found = True
                        continue
                    if line.find('reload=' + reload) >= 0:
                        reload_prop_found = True
                        continue
                    if line.find('org.apache.activemq.jaas.guest.user="myguest"') >= 0:
                        user_file_prop_found = True
                        continue
                    if line.find('org.apache.activemq.jaas.guest.role="guest";') >= 0:
                        roles_file_prop_found = True
                        continue
            if debug == '':
                debug_prop_found = not debug_prop_found
            if reload == '':
                reload_prop_found = not reload_prop_found
            result = login_module_found and debug_prop_found and reload_prop_found and user_file_prop_found and roles_file_prop_found
            if not result:
                print('login_module_found', login_module_found)
                print('debug_prop_found', debug_prop_found)
                print('reload_prop_found', reload_prop_found)
                print('user_file_prop_found', user_file_prop_found)
                print('roles_file_prop_found', roles_file_prop_found)
                print("the result file: ")
                dump_file(self.context.get_login_config_file())
        return result

    def guest_module_has_guest(self, guest_user, guest_role):
        login_config = self.context.get_login_config_file()
        guest_user_line = 'org.apache.activemq.jaas.guest.user="' + guest_user + '"'
        guest_role_line = 'org.apache.activemq.jaas.guest.role="' + guest_role + '"'
        return check_all_lines_in_file(login_config, [guest_user_line, guest_role_line])

    def prop_module_has_roles(self, role_list):
        role_file = self.context.get_roles_prop_file()
        return check_all_lines_in_file(role_file, role_list)

    def prop_module_has_users(self, user_list):
        users_file = self.context.get_users_prop_file()
        return check_all_lines_in_file(users_file, user_list)

    def bootstrap_has_broker_domain(self, domain_name):
        bootstrap_file = self.context.get_bootstrap_file()
        return check_all_lines_in_file(bootstrap_file, ['   <jaas-security domain="' + domain_name + '"/>'])

    def artemis_profile_not_changed(self, original_dir):
        original_artemis_profile = Path(original_dir).joinpath(apply_security.ARTEMIS_PROFILE_NAME)
        return are_files_identical(original_artemis_profile, self.context.get_artemis_profile_file())

    def broker_xml_not_changed(self, original_dir):
        original_broker_xml = Path(original_dir).joinpath(apply_security.BROKER_XML_NAME)
        return are_files_identical(original_broker_xml, self.context.get_broker_xml_file())

    def management_xml_not_changed(self, original_dir):
        original_management_xml = Path(original_dir).joinpath(apply_security.MANAGEMENT_XML_NAME)
        return are_files_identical(original_management_xml, self.context.get_management_xml_file())

    def has_hawtio_roles(self, role_string):
        artemis_profile = self.context.get_artemis_profile_file()
        hawtio_role_line = "HAWTIO_ROLE=" + role_string
        return check_all_lines_in_file(artemis_profile, [hawtio_role_line])

    def get_security_setting(self, match):
        broker_xml = self.context.get_broker_xml_file()
        security_setting_set = []
        with open(broker_xml, "rt") as broker_stream:
            match_found = False
            for each_line in broker_stream:
                if match_found:
                    if each_line.find('</security-setting>') >= 0:
                        # end
                        break
                    elif each_line.find('<permission') >= 0:
                        security_setting_set.append(each_line.strip())
                elif each_line.find('<security-setting match="' + match + '">') >= 0:
                    match_found = True
        return security_setting_set

    def broker_has_security_settings(self, match, perm_roles_map):
        security_setting_set = self.get_security_setting(match)
        if len(security_setting_set) != len(perm_roles_map):
            print("number of security setting entries not equal", "expected", len(perm_roles_map), "actual",
                  len(security_setting_set))
            return False
        for perm in perm_roles_map:
            security_setting_line = '<permission type="' + perm + '" roles="' + perm_roles_map[perm] + '"/>'
            found = False
            for line in security_setting_set:
                if line == security_setting_line:
                    found = True
                    break
            if not found:
                print("permission missing", security_setting_line)
                dump_file(self.context.get_broker_xml_file())
                return False
        return True

    def management_has_connector(self):
        mgmt_xml = self.context.get_management_xml_file()
        with open(mgmt_xml, "rt") as mgmt_stream:
            for each_line in mgmt_stream:
                if each_line.find("<!--") >= 0:
                    # ignore one line comment
                    continue
                if each_line.find('<connector ') >= 0:
                    return True
        return False

    def management_has_allow_list(self, allow_list):
        actual_allow_list = self.find_allow_list()
        if len(actual_allow_list) != len(allow_list):
            print("number of allow list entries not match", "expected", len(allow_list), "actual",
                  len(actual_allow_list))
            return False
        for ent in allow_list:
            xml_ent = '<entry domain="' + ent + '" />'
            found = False
            for a_ent in actual_allow_list:
                if a_ent == xml_ent:
                    found = True
                    break
            if not found:
                print("didn't found expected allow entry", xml_ent)
                return False
        return True

    def find_allow_list(self):
        allow_list = []
        mgmt_xml = self.context.get_management_xml_file()
        with open(mgmt_xml, "rt") as mgmt_stream:
            parse_state = "normal"
            for each_line in mgmt_stream:
                if each_line.find('<!--') >= 0:
                    if each_line.find('-->') == -1:
                        parse_state = 'in-comment'
                    continue
                if parse_state == 'in-comment':
                    if each_line.find('-->') >= 0:
                        parse_state = "normal"
                    continue
                if parse_state == "normal":
                    if each_line.find('<allowlist>') >= 0:
                        parse_state = "in-allow-list"
                        continue
                if parse_state == "in-allow-list":
                    if each_line.find('</allowlist>') >= 0:
                        # end
                        break
                    if each_line.find('<entry domain') >= 0:
                        allow_list.append(each_line.strip())
        return allow_list

    def management_has_default_list(self, default_list):
        actual_default_list = self.find_default_list()
        if len(actual_default_list) != len(default_list):
            print("number of default list entries not match", "expected", len(default_list), "actual",
                  len(actual_default_list))
            return False
        for ent in default_list:
            xml_ent = '<access method="' + ent[0] + '" roles="' + ent[1] + '" />'
            found = False
            for a_ent in actual_default_list:
                if a_ent == xml_ent:
                    found = True
                    break
            if not found:
                print("didn't found expected allow entry", xml_ent)
                return False
        return True

    def find_default_list(self):
        default_list = []
        mgmt_xml = self.context.get_management_xml_file()
        with open(mgmt_xml, "rt") as mgmt_stream:
            parse_state = "normal"
            for each_line in mgmt_stream:
                if each_line.find('<!--') >= 0:
                    if each_line.find('-->') == -1:
                        parse_state = 'in-comment'
                    continue
                if parse_state == 'in-comment':
                    if each_line.find('-->') >= 0:
                        parse_state = "normal"
                    continue
                if parse_state == "normal":
                    if each_line.find('<default-access>') >= 0:
                        parse_state = "in-default-list"
                        continue
                if parse_state == "in-default-list":
                    if each_line.find('</default-access>') >= 0:
                        # end
                        break
                    if each_line.find('<access method=') >= 0:
                        default_list.append(each_line.strip())
        return default_list

    def management_has_access_list(self, access_list):
        actual_access_list = self.find_access_list()
        if len(actual_access_list) != len(access_list):
            print("number of access list entries not match", "expected", len(access_list), "actual",
                  len(actual_access_list))
            return False
        for match_ent in access_list:
            if not self.compare_access_match(actual_access_list, match_ent):
                return False
        return True

    def key_equivalent_between_maps(self, key, map1, map2):
        if key in map1:
            if key in map2:
                return map1[key] == map2[key]
            return map1[key] is None
        else:
            if key in map2:
                return map2[key] is None
        return True

    def compare_access_match(self, actual_access_list, match_ent):
        # match_ent must exist in actual_access_list
        for each_match in actual_access_list:
            # assume domain is always present
            if each_match['domain'] == match_ent['domain']:
                if self.key_equivalent_between_maps('key', each_match, match_ent):
                    list_a = each_match['list']
                    list_e = match_ent['list']
                    if len(list_a) == len(list_e):
                        all_equal = True
                        for le in list_e:
                            found_it = False
                            for m in list_a:
                                if m[0] == le[0] and m[1] == le[1]:
                                    found_it = True
                            if not found_it:
                                all_equal = False
                                break
                        return all_equal
        print("match not found in actual access list", match_ent, "actual config", actual_access_list)
        return False

    def find_access_list(self):
        # list of maps
        access_list = []
        mgmt_xml = self.context.get_management_xml_file()
        mgmt_tree = ET.parse(mgmt_xml)
        mgmt_root = mgmt_tree.getroot()
        namespaces = {'mgmt': "http://activemq.apache.org/schema"}
        all_access = mgmt_root.findall("mgmt:authorisation/mgmt:role-access", namespaces)
        if len(all_access) == 0:
            print("no role-access element", mgmt_root)
            return access_list
        the_access = all_access[0]
        all_match = the_access.findall('mgmt:match', namespaces)
        if len(all_match) == 0:
            return access_list
        for match in all_match:
            new_match = {}
            if match.attrib['domain'] is not None:
                new_match['domain'] = match.attrib['domain']
            if 'key' in match.attrib and match.attrib['key'] is not None:
                new_match['key'] = match.attrib['key']
            access_entries_list = []
            all_access_entries = match.findall('mgmt:access', namespaces)
            if len(all_access_entries) > 0:
                for entry in all_access_entries:
                    access_entries_list.append(tuple([entry.attrib['method'], entry.attrib['roles']]))
                new_match['list'] = access_entries_list
            access_list.append(new_match)
        return access_list

    def domain_has_bearer_token_login_module(self, domain_name, flag, debug, reload):
        with open(self.context.get_login_config_file(), "rt") as login_config:
            stage = "start"

            login_module_found = False
            debug_prop_found = False
            reload_prop_found = False
            keycloak_cfg_file_prop_found = False
            role_principal_class_prop_found = False
            for line in login_config:
                if line.find(domain_name + ' {') >= 0:
                    stage = "in-domain"
                    continue
                if stage == "in-domain":
                    if line.find('};') >= 0:
                        break
                    if line.find(
                            "org.keycloak.adapters.jaas.BearerTokenLoginModule") >= 0 and line.find(flag) >= 0:
                        login_module_found = True
                        continue
                    if login_module_found and line.find("debug=" + debug) >= 0:
                        debug_prop_found = True
                        continue
                    if login_module_found and line.find('reload=' + reload) >= 0:
                        reload_prop_found = True
                        continue
                    if login_module_found and line.find('keycloak-config-file="${artemis.instance}/etc/keycloak-keycloak-console.json"') >= 0:
                        keycloak_cfg_file_prop_found = True
                        continue
                    if login_module_found and line.find(
                            'role-principal-class="org.apache.activemq.artemis.spi.core.security.jaas.RolePrincipal";') >= 0:
                        role_principal_class_prop_found = True
                        # last prop
                        break
            if debug == '':
                debug_prop_found = not debug_prop_found
            if reload == '':
                reload_prop_found = not reload_prop_found
            result = login_module_found and debug_prop_found and reload_prop_found and keycloak_cfg_file_prop_found and role_principal_class_prop_found
            if not result:
                print('login_module_found', login_module_found)
                print('debug_prop_found', debug_prop_found)
                print('reload_prop_found', reload_prop_found)
                print('keycloak_cfg_file_prop_found', keycloak_cfg_file_prop_found)
                print('role_principal_class_prop_found', role_principal_class_prop_found)
                print("the result file: ")
                dump_file(self.context.get_login_config_file())
        return result

    def domain_has_principal_conversion_login_module(self, domain_name, flag, debug, reload):
        with open(self.context.get_login_config_file(), "rt") as login_config:
            stage = "start"

            login_module_found = False
            debug_prop_found = False
            reload_prop_found = False
            principal_class_list_prop_found = False
            for line in login_config:
                if line.find(domain_name + ' {') >= 0:
                    stage = "in-domain"
                    continue
                if stage == "in-domain":
                    if line.find('};') >= 0:
                        break
                    if line.find(
                            "org.apache.activemq.artemis.spi.core.security.jaas.PrincipalConversionLoginModule") >= 0 and line.find(flag) >= 0:
                        login_module_found = True
                        continue
                    if login_module_found and line.find('principalClassList="org.keycloak.KeycloakPrincipal";') >= 0:
                        principal_class_list_prop_found = True
                        break
                    if login_module_found and line.find("debug=" + debug) >= 0:
                        debug_prop_found = True
                        continue
                    if login_module_found and line.find('reload=' + reload) >= 0:
                        reload_prop_found = True
                        continue
            if debug == '':
                debug_prop_found = not debug_prop_found
            if reload == '':
                reload_prop_found = not reload_prop_found
            result = login_module_found and debug_prop_found and reload_prop_found and principal_class_list_prop_found
            if not result:
                print('login_module_found', login_module_found)
                print('debug_prop_found', debug_prop_found)
                print('reload_prop_found', reload_prop_found)
                print('keycloak_cfg_file_prop_found', principal_class_list_prop_found)
                print("the result file: ")
                dump_file(self.context.get_login_config_file())
        return result

    def artemis_profile_has_line(self, expected_line):
        artemis_profile_file = self.context.get_artemis_profile_file()
        with open(artemis_profile_file, "rt") as profile:
            for each_line in profile:
                if each_line.rstrip() == expected_line:
                    return True
        return False

    def has_config_file(self, file_name, all_lines):
        cfg_file = self.context.get_config_file_path(file_name)
        if not cfg_file.exists():
            print('Config file not exist', cfg_file)
            return False
        with open(cfg_file, "rt") as cfg_stream:
            i = 0
            for each_line in cfg_stream:
                if each_line.rstrip() != all_lines[i]:
                    print('line not match', each_line, 'expected:', all_lines[i])
                    return False
                i += 1
        return True

    def artemis_profile_has_key(self, expected_key):
        artemis_profile_file = self.context.get_artemis_profile_file()
        with open(artemis_profile_file, "rt") as profile:
            for each_line in profile:
                if each_line.find(expected_key) >= 0:
                    return True
        return False
