import shutil
import sys
import unittest
import os
import apply_security
import random
import string
import security_configuration_checker as checker
import io


def random_str(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


class TestSecurityConfiguration(unittest.TestCase):

    def setUp(self):
        # set this env just to avoid downloading keycloak jars
        # todo: remove this env var and use something else to identify the broker version
        os.environ['YACFG_PROFILE_NAME'] = "something-else"
        self.original_config_dir = "broker-etc"
        self.amq_name = random_str(8)
        self.broker_instance_dir = "./broker-" + random_str(8)
        self.broker_install_dir = self.broker_instance_dir + "/" + self.amq_name
        self.broker_etc_dir = self.broker_install_dir + "/etc"
        shutil.copytree(self.original_config_dir, self.broker_etc_dir)
        self.context = apply_security.ConfigContext(self.broker_install_dir)

    def tearDown(self):
        shutil.rmtree(self.broker_instance_dir)
        pass

    def test_guest_login_modules(self):
        self.context.parse_config_cr("./test-guest-module-cr.yaml")
        self.context.apply()
        the_checker = checker.SecurityConfigurationChecker(self.context)
        self.assertTrue(the_checker.domain_has_prop_login_module('activemq', 'sufficient', '', ''))
        self.assertTrue(the_checker.domain_has_guest_login_module('activemq', 'sufficient', '', ''))
        self.assertTrue(the_checker.prop_module_has_roles(["admin = 9gIY0RrT", "root = superman", "viewer = howard", "guest = howard"]))
        self.assertTrue(the_checker.prop_module_has_users(["9gIY0RrT = ENC(1024:6FB4782966A8C4303569AE7DEFA4A8A0E8BAD0019CD77814CE43E2CAF4F84B4A:046C735DED79CD146A9ADB8C756732BD02EF8CE42704CC43B89C82F6A765C2D706146A9DE521DA71C0283F6D57FBC623EACE687F2EF936A391D8AD263AB71B67",
                                                           "superman = ",
                                                           "howard = "]))
        self.assertTrue(the_checker.guest_module_has_guest("myguest", "guest"))
        self.assertTrue(the_checker.has_hawtio_roles('"guest,root"'))
        self.assertTrue(the_checker.broker_has_security_settings('#', {'createDurableQueue': 'root',
                                                                       'deleteDurableQueue': 'root',
                                                                       'createNonDurableQueue': 'root',
                                                                       'deleteNonDurableQueue': 'root',
                                                                       'createTempQueue': 'root',
                                                                       'deleteTempQueue': 'root',
                                                                       'send': 'root',
                                                                       'consume': 'root',
                                                                       'manage': 'root',
                                                                       'browse': 'root',
                                                                       'createAddress': 'root',
                                                                       'deleteAddress': 'root'}))
        self.assertFalse(the_checker.management_has_connector())
        self.assertTrue(the_checker.management_has_allow_list(['hawtio']))
        self.assertTrue(the_checker.management_has_default_list([('list*', 'root,amq'),
                                                                 ('set*', 'root')]))
        self.assertTrue(the_checker.management_has_access_list([{'domain': 'org.apache.activemq.artemis',
                                                                 'key': None,
                                                                 'list': [
                                                                     ('list*', 'root'),
                                                                     ('get*', 'guest,root'),
                                                                     ('is*', 'guest,root'),
                                                                     ('browse*', 'root'),
                                                                     ('set*', 'root'),
                                                                     ('count*', 'guest,root'),
                                                                     ('*', 'root')
                                                                 ]}
                                                                ]))

    def test_prop_login_modules(self):
        self.context.parse_config_cr("./test-prop-login-module-cr.yaml")
        self.context.apply()
        the_checker = checker.SecurityConfigurationChecker(self.context)
        self.assertTrue(the_checker.has_broker_domain("activemqx"))
        self.assertTrue(the_checker.domain_has_prop_login_module('activemqx', 'required', 'true', 'true'))
        self.assertTrue(the_checker.prop_module_has_roles(["admin = 9gIY0RrT", "role1 = user1,user2", "role2 = user1", "role3 = user2"]))
        self.assertTrue(the_checker.prop_module_has_users(["9gIY0RrT = ENC(1024:6FB4782966A8C4303569AE7DEFA4A8A0E8BAD0019CD77814CE43E2CAF4F84B4A:046C735DED79CD146A9ADB8C756732BD02EF8CE42704CC43B89C82F6A765C2D706146A9DE521DA71C0283F6D57FBC623EACE687F2EF936A391D8AD263AB71B67",
                                                           "user1 = password1",
                                                           "user2 = password2"]))
        self.assertTrue(the_checker.bootstrap_has_broker_domain('activemqx'))
        self.assertTrue(the_checker.artemis_profile_not_changed(self.original_config_dir))
        self.assertTrue(the_checker.broker_xml_not_changed(self.original_config_dir))
        self.assertTrue(the_checker.management_xml_not_changed(self.original_config_dir))

    def test_config_keycloak(self):
        self.context.parse_config_cr("./test-keycloak-cr.yaml")
        self.context.apply()
        the_checker = checker.SecurityConfigurationChecker(self.context)
        self.assertTrue(the_checker.bootstrap_has_broker_domain('activemq'))
        self.assertTrue(the_checker.has_broker_domain("activemq"))
        self.assertTrue(the_checker.has_broker_domain("console"))
        self.assertTrue(the_checker.domain_has_prop_login_module('activemq', 'sufficient', '', ''))
        self.assertTrue(the_checker.domain_has_direct_access_login_module('activemq', 'required', 'true', 'true'))
        self.assertTrue(the_checker.prop_module_has_roles(
            ["admin = 9gIY0RrT", "root = superman"]))
        self.assertTrue(the_checker.prop_module_has_users([
                                                              "9gIY0RrT = ENC(1024:6FB4782966A8C4303569AE7DEFA4A8A0E8BAD0019CD77814CE43E2CAF4F84B4A:046C735DED79CD146A9ADB8C756732BD02EF8CE42704CC43B89C82F6A765C2D706146A9DE521DA71C0283F6D57FBC623EACE687F2EF936A391D8AD263AB71B67",
                                                              "superman = ihavepower"]))
        self.assertTrue(the_checker.domain_has_bearer_token_login_module('console', 'required', '', ''))
        self.assertTrue(the_checker.domain_has_principal_conversion_login_module('activemq', 'required', '', ''))
        self.assertTrue(the_checker.broker_has_security_settings('Info', {'createDurableQueue': 'amq',
                                                                       'deleteDurableQueue': 'amq',
                                                                       'createNonDurableQueue': 'amq',
                                                                       'deleteNonDurableQueue': 'amq',
                                                                       'send': 'guest',
                                                                       'consume': 'amq'}))
        self.assertTrue(the_checker.broker_has_security_settings('#', {'createDurableQueue': 'root',
                                                                       'deleteDurableQueue': 'root',
                                                                       'createNonDurableQueue': 'root',
                                                                       'deleteNonDurableQueue': 'root',
                                                                       'createTempQueue': 'root',
                                                                       'deleteTempQueue': 'root',
                                                                       'send': 'root',
                                                                       'consume': 'root',
                                                                       'manage': 'root',
                                                                       'browse': 'root',
                                                                       'createAddress': 'root',
                                                                       'deleteAddress': 'root'}))
        self.assertTrue(the_checker.has_hawtio_roles('"guest"'))
        self.assertTrue(the_checker.artemis_profile_has_line('    JAVA_ARGS="-XX:+PrintClassHistogram -XX:+UseG1GC -XX:+UseStringDeduplication  -Dhawtio.rolePrincipalClasses=org.apache.activemq.artemis.spi.core.security.jaas.RolePrincipal -Djolokia.policyLocation=${ARTEMIS_INSTANCE_ETC_URI}jolokia-access.xml -Djava.net.preferIPv4Stack=true -Dbroker.properties=/amq/extra/configmaps/ex-aao-props-00000001/broker.properties"'))
        self.assertTrue(the_checker.artemis_profile_has_line('JAVA_ARGS="${JAVA_ARGS} -Dhawtio.keycloakEnabled=true -Dhawtio.keycloakClientConfig=${ARTEMIS_INSTANCE_ETC_URI}keycloak-js-client-keycloak-console.json -Dhawtio.authenticationEnabled=true -Dhawtio.realm=console"'))
        self.assertTrue(the_checker.management_has_access_list([{'domain': 'org.apache.activemq.artemis',
                                                                 'key': None,
                                                                 'list': [
                                                                     ('list*', 'amq,guest,root'),
                                                                     ('get*', 'amq,guest,root'),
                                                                     ('is*', 'amq,guest,root'),
                                                                     ('set*', 'amq,guest,root'),
                                                                     ('browse*', 'amq,guest,root'),
                                                                     ('count*', 'amq,guest,root'),
                                                                     ('*', 'amq,guest,root')
                                                                 ]}
                                                                ]))
        self.assertTrue(the_checker.has_config_file('keycloak-js-client-keycloak-console.json', ['{',
                                                         '  "realm": "artemis-keycloak-demo",',
                                                         '  "clientId": "artemis-console",',
                                                         '  "url": "http://keycloak.3387.com/auth"',
                                                         '}']))

        self.assertTrue(the_checker.has_config_file('keycloak-keycloak-broker.json', ['{',
                                                         '  "realm": "artemis-keycloak-demo",',
                                                         '  "auth-server-url": "http://10.109.131.209:8080/auth",',
                                                         '  "ssl-required": "external",',
                                                         '  "credentials": {',
                                                         '    "secret": "9699685c-8a30-45cf-bf19-0d38bbac5fdc"',
                                                         '  },',
                                                         '  "resource": "artemis-broker",',
                                                         '  "use-resource-role-mappings": true,',
                                                         '  "principal-attribute": "preferred_username"',
                                                         '}']))

        self.assertTrue(the_checker.has_config_file('keycloak-keycloak-console.json', ['{',
                                                         '  "realm": "artemis-keycloak-demo",',
                                                         '  "auth-server-url": "http://keycloak.3387.com/auth",',
                                                         '  "ssl-required": "external",',
                                                         '  "resource": "artemis-console",',
                                                         '  "use-resource-role-mappings": true,',
                                                         '  "principal-attribute": "preferred_username",',
                                                         '  "confidential-port": 0',
                                                         '}']))

    def test_warnings_on_users_without_roles(self):
        self.context.parse_config_cr("./test-prop-user-no-roles-cr.yaml")
        captured_output = io.StringIO()
        current_stdout = sys.stdout
        sys.stdout = captured_output
        self.context.apply()
        sys.stdout = current_stdout
        contents = captured_output.getvalue()
        wanted = "WARNING: user bob doesn't have any roles defined!"
        self.assertTrue(wanted in contents)

    def test_warnings_on_login_module_not_used(self):
        self.context.parse_config_cr("./test-login-module-not-used-cr.yaml")
        captured_output = io.StringIO()
        current_stdout = sys.stdout
        sys.stdout = captured_output
        self.context.apply()
        sys.stdout = current_stdout
        contents = captured_output.getvalue()
        wanted1 = "WARNING: Login module defined but not used!"
        wanted2 = "Defined module: prop-module"
        print(contents)
        self.assertTrue(wanted1 in contents)
        self.assertTrue(wanted2 in contents)

    def test_hawtio_domain_update_in_artemis_profile(self):
        self.context.parse_config_cr("./test-hawtio-console-domain-cr.yaml")
        self.context.apply()
        the_checker = checker.SecurityConfigurationChecker(self.context)
        self.assertTrue(the_checker.artemis_profile_has_key("-Dhawtio.realm=console2"))

    def test_management_connector_attr(self):
        self.context.parse_config_cr("./test-mgmt-connector-cr.yaml")
        self.context.apply()
        the_checker = checker.SecurityConfigurationChecker(self.context)
        self.assertTrue(the_checker.management_has_connector())
        self.assertTrue(the_checker.management_has_connector_attribute("secured", "false"))
        self.assertTrue(the_checker.management_has_connector_attribute("connector-port", "9091"))
        self.assertTrue(the_checker.management_has_connector_attribute("rmi-registry-port", "1234"))
        self.assertTrue(the_checker.management_has_connector_attribute("connector-host", "0.0.0.0"))
        self.assertTrue(the_checker.management_has_connector_attribute("jmx-realm", "activemq"))
        self.assertTrue(the_checker.management_has_connector_attribute("object-name", "connector:name=rmi"))
        self.assertTrue(the_checker.management_has_connector_attribute("authenticator-type", "password"))
        self.assertTrue(the_checker.management_has_connector_attribute("key-store-path", "/etc/keystore/broker.ks"))
        self.assertTrue(the_checker.management_has_connector_attribute("key-store-password", "kspassword"))
        self.assertTrue(the_checker.management_has_connector_attribute("trust-store-provider", "tSUN"))
        self.assertTrue(the_checker.management_has_connector_attribute("trust-store-path", "/etc/truststore/broker.ts"))
        self.assertTrue(the_checker.management_has_connector_attribute("trust-store-password", "tspassword"))
        self.assertTrue(the_checker.management_has_connector_attribute("password-codec", "org.apache.activemq.SomeClass"))
        self.assertTrue(the_checker.management_has_connector_attribute("key-store-type", "PKCS12"))
        self.assertTrue(the_checker.management_has_connector_attribute("trust-store-type", "JKS"))


if __name__ == '__main__':
    unittest.main()
