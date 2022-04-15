from shutil import copyfile
from pathlib import Path
from io import StringIO
import xml.etree.ElementTree as ET
from collections import OrderedDict
import re
import yaml

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

LOGIN_CONFIG = 'etc/login.config'
USERS_PROP_FILE = 'etc/artemis-users.properties'
ROLES_PROP_FILE = 'etc/artemis-roles.properties'
ARTEMIS_PROFILE = 'etc/artemis.profile'
BROKER_XML = 'etc/broker.xml'
MANAGEMENT_XML = 'etc/management.xml'
BOOTSTRAP = 'etc/bootstrap.xml'


class ExtraResource:
    def create(self, dest_dir):
        pass


# create content files under ${instanceDir}/etc
class TextExtraResource(ExtraResource):
    def __init__(self, text, name):
        self.content = text
        self.file_name = name

    def create(self, dest_dir):
        target_path = Path(dest_dir).joinpath('etc/' + self.file_name).absolute()
        with open(target_path, "wt") as extra_file:
            extra_file.write(self.content)


class PropUsersFile:
    def __init__(self, prop_file):
        self.prop_file = prop_file

    def merge_from(self, new_file):
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
                    users[user] = password
        with open(new_file.prop_file, 'rt') as src_user_file:
            for line in src_user_file:
                if not line.startswith('#') and line and line.strip():
                    ulist = line.split('=')
                    user = ulist[0].strip()
                    password = ulist[1].strip()
                    users[user] = password
        with open(self.prop_file, 'wt') as dst:
            dst.writelines(comments)
            for key in users:
                dst.write(key)
                dst.write(' = ')
                dst.write(users[key])
                dst.write('\n')


class PropRolesFile:
    def __init__(self, prop_file):
        self.prop_file = prop_file

    def merge_from(self, new_file):
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
        with open(new_file.prop_file, 'rt') as src_role_file:
            for line in src_role_file:
                if not line.startswith('#') and line and line.strip():
                    user_set = {}
                    rlist = line.split('=')
                    role = rlist[0].strip()
                    users = rlist[1].split(',')
                    for u in users:
                        user_set[u.strip()] = u.strip()
                    if role in roles:
                        existing_user_set = roles[role]
                        user_set.update(existing_user_set)
                    roles[role] = user_set
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


class BaseArtemisXml:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.namespaces = {'amq': 'urn:activemq', 'core': 'urn:activemq:core'}
        self.xml_indent = '   '


class ManagementXml(BaseArtemisXml):
    def __init__(self, mgmtxml):
        BaseArtemisXml.__init__(self, mgmtxml)
        self.namespaces = {'mgmt': "http://activemq.apache.org/schema"}

    def merge_connector_from(self, new_connector):
        new_connector_str = StringIO()
        new_connector_str.write('<connector ')
        for prop in ['connector-host', 'connector-port', 'rmi-registry-port', 'jmx-realm', 'object-name',
                     'authenticator-type', 'secured', 'key-store-provider', 'key-store-type', 'key-store-path',
                     'key-store-password', 'trust-store-provider', 'trust-store-type', 'trust-store-path',
                     'trust-store-password', 'password-codec']:
            if prop in new_connector[0].attrib:
                new_connector_str.write(prop)
                new_connector_str.write('=\"')
                new_connector_str.write(new_connector[0].attrib[prop])
                new_connector_str.write('\" ')
        new_connector_str.write('/>\n')
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
        new_allowed_list_str.write('<whitelist>\n')
        for entry in new_allowed_list:
            new_allowed_list_str.write(self.xml_indent*3)
            new_allowed_list_str.write('<entry')
            if 'domain' in entry.attrib:
                new_allowed_list_str.write(' domain=\"')
                new_allowed_list_str.write(entry.attrib['domain'])
                new_allowed_list_str.write('\"')
            if 'key' in entry.attrib:
                new_allowed_list_str.write(' key=\"')
                new_allowed_list_str.write(entry.attrib['key'])
                new_allowed_list_str.write('\"')
            new_allowed_list_str.write(' />\n')
        new_allowed_list_str.write(self.xml_indent*2)
        new_allowed_list_str.write('</whitelist>')
        with open(self.xml_file, 'rt') as mgmtxml:
            original_xml = mgmtxml.read()
            new_xml = re.sub(r'<whitelist>[\s\S]*</whitelist>', new_allowed_list_str.getvalue(), original_xml, re.M)
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
            new_default_list_str.write(self.xml_indent*3)
            new_default_list_str.write('<access')
            if 'method' in entry.attrib:
                new_default_list_str.write(' method=\"')
                new_default_list_str.write(entry.attrib['method'])
                new_default_list_str.write('\"')
            if 'roles' in entry.attrib:
                new_default_list_str.write(' roles=\"')
                new_default_list_str.write(entry.attrib['roles'])
                new_default_list_str.write('\"')
            new_default_list_str.write(' />\n')
        new_default_list_str.write(self.xml_indent*2)
        new_default_list_str.write('</default-access>')
        print('new default list: ', new_default_list_str.getvalue())
        with open(self.xml_file, 'rt') as mgmtxml:
            original_xml = mgmtxml.read()
            new_xml = re.sub(r'<default-access>[\s\S]*</default-access>', new_default_list_str.getvalue(), original_xml, re.M)
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
        for match in new_role_access_list:
            new_role_access_list_str.write(self.xml_indent*3)
            new_role_access_list_str.write('<match ')
            for prop in ['domain', 'key']:
                if prop in match.attrib:
                    new_role_access_list_str.write(prop)
                    new_role_access_list_str.write('=\"')
                    new_role_access_list_str.write(match.attrib[prop])
                    new_role_access_list_str.write('\" ')
            new_role_access_list_str.write('>\n')
            new_access_list = match.findall('mgmt:access', self.namespaces)
            for access in new_access_list:
                new_role_access_list_str.write(self.xml_indent*4)
                new_role_access_list_str.write('<access ')
                for attr in ['method', 'roles']:
                    if attr in access.attrib:
                        new_role_access_list_str.write(attr)
                        new_role_access_list_str.write('=\"')
                        new_role_access_list_str.write(access.attrib[attr])
                        new_role_access_list_str.write('\" ')
                new_role_access_list_str.write('/>\n')
            new_role_access_list_str.write(self.xml_indent*3)
            new_role_access_list_str.write('</match>\n')
        new_role_access_list_str.write(self.xml_indent*2)
        new_role_access_list_str.write('</role-access>')
        with open(self.xml_file, 'rt') as mgmtxml:
            original_xml = mgmtxml.read()
            new_xml = re.sub(r'<role-access>[\s\S]*</role-access>', new_role_access_list_str.getvalue(), original_xml, re.M)
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

    def merge_security_settings_from(self, new_security_settings):
        print("Merging security settings")
        new_settings = StringIO()
        new_settings.write('<security-settings>')
        new_settings.write('\n')
        for key in new_security_settings:
            new_settings.write(self.xml_indent*3)
            new_settings.write('<security-setting match=\"')
            new_settings.write(key)
            new_settings.write('\">\n')
            permissions = new_security_settings[key].findall('core:permission', self.namespaces)
            for perm in permissions:
                new_settings.write(self.xml_indent*4)
                new_settings.write('<permission type=\"')
                new_settings.write(perm.attrib['type'])
                new_settings.write('\" roles=\"')
                new_settings.write(perm.attrib['roles'])
                new_settings.write('\"/>')
                new_settings.write('\n')
            new_settings.write(self.xml_indent*3)
            new_settings.write('</security-setting>\n')
        new_settings.write(self.xml_indent*2)
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


class ConfigContext:
    def __init__(self, source_root, target_root):
        self.src_root = source_root
        self.dst_root = target_root
        self.prop_login_modules = []
        self.is_domain_defined = False
        self.is_broker_security_settings_defined = False
        self.is_management_connector_defined = False
        self.is_management_allowed_list_defined = False
        self.is_management_default_list_defined = False
        self.is_management_role_access_list_defined = False
        self.broker_domain = ''
        self.extra_resources = []
        self.is_console_domain_defined = False
        self.console_domain_name = None
        self.hawtio_roles = []
        self.tune_data_list = []

    def console_domain_defined(self):
        return self.is_console_domain_defined

    def set_console_domain_defined(self, defined):
        self.is_console_domain_defined = defined

    def add_extra_resources(self, res):
        self.extra_resources.append(res)

    def set_domain_defined(self, defined):
        self.is_domain_defined = defined

    def domain_defined(self):
        return self.domain_defined

    def set_broker_security_settings_defined(self, defined):
        self.is_broker_security_settings_defined = defined

    def broker_security_settings_defined(self):
        return self.is_broker_security_settings_defined

    def get_hawtio_roles(self):
        return self.hawtio_roles

    def update_console_domain(self):
        print('Updating hawtio domain/roles')
        hawtio_roles = self.get_hawtio_roles()
        dst_artemis_profile = Path(self.dst_root).joinpath(ARTEMIS_PROFILE)
        lines = []
        with open(dst_artemis_profile.absolute(), "rt") as artemis_profile:
            for line in artemis_profile:
                if line.startswith('HAWTIO_ROLE=') and len(hawtio_roles) > 0:
                    new_line = StringIO()
                    new_line.write('HAWTIO_ROLE="')
                    first_role = True
                    for role in hawtio_roles:
                        if not first_role:
                            new_line.write(',')
                        new_line.write(role)
                        first_role = False
                    new_line.write('"')
                    lines.append(new_line.getvalue())
                else:
                    lines.append(line)
        with open(dst_artemis_profile.absolute(), "wt") as artemis_profile:
            artemis_profile.writelines(lines)

    def add_prop_login_module(self, m):
        self.prop_login_modules.append(m)

    def properties_login_module_defined(self):
        return len(self.prop_login_modules) > 0

    def set_management_connector_defined(self, defined):
        self.is_management_connector_defined = defined

    def management_connector_defined(self):
        return self.is_management_connector_defined

    def set_management_allowed_list_defined(self, defined):
        self.is_management_allowed_list_defined = defined

    def management_allowed_list_defined(self):
        return self.is_management_allowed_list_defined

    def set_management_default_list_defined(self, defined):
        self.is_management_default_list_defined = defined

    def management_default_list_defined(self):
        return self.is_management_default_list_defined

    def set_management_role_access_list_defined(self, defined):
        self.is_management_role_access_list_defined = defined

    def management_role_access_list_defined(self):
        return self.is_management_role_access_list_defined

    def management_defined(self):
        return self.management_connector_defined() or self.management_allowed_list_defined() \
               or self.management_default_list_defined() or self.management_role_access_list_defined()

    def apply_prop_users_roles(self):
        has_users = False
        for module in self.prop_login_modules:
            if module.has_users:
                has_users = True
                break
        if not has_users:
            print("properties login module doesn't configure new users")
            return
        src_prop_users_cfg = Path(self.src_root).joinpath(USERS_PROP_FILE)
        dst_prop_users_cfg = Path(self.dst_root).joinpath(USERS_PROP_FILE)
        src_prop_users = PropUsersFile(src_prop_users_cfg.absolute())
        dst_prop_users = PropUsersFile(dst_prop_users_cfg.absolute())
        dst_prop_users.merge_from(src_prop_users)
        src_prop_roles_cfg = Path(self.src_root).joinpath(ROLES_PROP_FILE)
        dst_prop_roles_cfg = Path(self.dst_root).joinpath(ROLES_PROP_FILE)
        src_prop_roles = PropRolesFile(src_prop_roles_cfg)
        dst_prop_roles = PropRolesFile(dst_prop_roles_cfg)
        dst_prop_roles.merge_from(src_prop_roles)

    def set_broker_domain(self, name):
        self.broker_domain = name

    def update_bootstrap(self):
        print('Updating bootstrap.xml')
        if self.broker_domain:
            dst_bootstrap = Path(self.dst_root).joinpath(BOOTSTRAP)
            new_bootstrap = ''
            with open(dst_bootstrap.absolute(), 'rt') as bootstrap_xml:
                bootstrap = bootstrap_xml.read()
                new_bootstrap = re.sub(r'<jaas-security domain="activemq"/>', '<jaas-security domain="' + self.broker_domain + '"/>', bootstrap)
            with open(dst_bootstrap.absolute(), 'wt') as bootstrap_xml:
                bootstrap_xml.write(new_bootstrap)

    def apply_login_config(self):
        # override login.config
        print('Applying login modules')
        src_login_cfg = Path(self.src_root).joinpath(LOGIN_CONFIG)
        dst_login_cfg = Path(self.dst_root).joinpath(LOGIN_CONFIG)
        print("Copying ", src_login_cfg.absolute(), " to ", dst_login_cfg.absolute())
        copyfile(src_login_cfg.absolute(), dst_login_cfg.absolute())
        self.update_bootstrap()
        self.update_console_domain()

    def apply_broker_security(self):
        print("Applying broker security settings")
        src_broker_xml = Path(self.src_root).joinpath(BROKER_XML)
        dst_broker_xml = Path(self.dst_root).joinpath(BROKER_XML)
        src_broker = BrokerXml(src_broker_xml.absolute())
        dst_broker = BrokerXml(dst_broker_xml.absolute())
        dst_broker.merge_security_settings_from(src_broker.get_security_settings())

    def apply_management(self):
        src_mgmt_xml = Path(self.src_root).joinpath(MANAGEMENT_XML)
        dst_mgmt_xml = Path(self.dst_root).joinpath(MANAGEMENT_XML)
        src_mgmt = ManagementXml(src_mgmt_xml.absolute())
        dst_mgmt = ManagementXml(dst_mgmt_xml.absolute())
        if self.management_connector_defined():
            dst_mgmt.merge_connector_from(src_mgmt.get_connector())
        if self.management_allowed_list_defined():
            dst_mgmt.merge_allowed_list_from(src_mgmt.get_allowed_list())
        if self.management_default_list_defined():
            dst_mgmt.merge_default_list_from(src_mgmt.get_default_list())
        if self.management_role_access_list_defined():
            dst_mgmt.merge_role_access_list_from(src_mgmt.get_role_access_list())

    def create_extra_resources(self):
        if len(self.extra_resources) > 0:
            for extra_res in self.extra_resources:
                extra_res.create(self.dst_root)

    def apply(self):
        if self.domain_defined():
            self.apply_login_config()
        if self.broker_security_settings_defined():
            self.apply_broker_security()
        if self.management_defined():
            self.apply_management()
        if self.properties_login_module_defined():
            self.apply_prop_users_roles()
        self.create_extra_resources()

    def set_console_domain_name(self, console_domain_name):
        self.console_domain_name = console_domain_name

    def get_console_domain_name(self):
        return self.console_domain_name

    def add_hawtio_role(self, hirole):
        self.hawtio_roles.append(hirole)

    def add_tune_data(self, yml_str):
        new_data = yaml.safe_load(yml_str)
        self.tune_data_list.append(new_data)

    def get_tune_data(self):
        return self.tune_data_list
