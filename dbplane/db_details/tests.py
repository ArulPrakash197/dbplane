from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from db_details.models import CredentialRecord
from db_details.services.connection_store import DATABASES_COMPONENT

class ConnectionViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_add_connection_preserves_details_on_test(self):
        # Test postgresql password preservation on test connection
        url = reverse("add_connection_url", args=["postgresql"])
        data = {
            "action": "test",
            "display_name": "Test PG",
            "host": "localhost",
            "port": "5432",
            "dbname": "testdb",
            "username": "testuser",
            "password": "mysecretpassword"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="mysecretpassword"')
        self.assertContains(response, 'value="Test PG"')
        self.assertContains(response, 'value="localhost"')

        # Test mongo connection URI preservation on test connection
        url = reverse("add_connection_url", args=["mongo"])
        data = {
            "action": "test",
            "display_name": "Test Mongo",
            "connection": "mongodb://testuser:mongopass@localhost:27017"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mongodb://testuser:mongopass@localhost:27017")
        self.assertContains(response, "Test Mongo")

    def test_edit_connection_shows_password_and_details(self):
        # Create a connection in db first
        record = CredentialRecord.objects.create(
            component=DATABASES_COMPONENT,
            credential_type="postgresql",
            display_name="Saved PG",
            public_data={"host": "127.0.0.1", "port": "5432", "database": "saveddb", "username": "saveduser"},
            # encrypted_secret_data can be empty for test or we can set it up, but since get_credential decrypts, let's encrypt it.
        )
        from db_details.services.credential_crypto import encrypt_dict
        record.encrypted_secret_data = encrypt_dict({"password": "savedpassword"})
        record.save()

        # Get index: it's the 0th item for postgresql component/credential_type
        url = reverse("edit_connection", args=["postgresql", 0])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Verify that all details are shown:
        # password should be populated in value (and hidden/masked via input type="password")
        self.assertContains(response, 'value="savedpassword"')
        self.assertContains(response, 'value="Saved PG"')
        self.assertContains(response, 'value="127.0.0.1"')
        self.assertContains(response, 'value="saveduser"')

        # Test mongo editing
        mongo_record = CredentialRecord.objects.create(
            component=DATABASES_COMPONENT,
            credential_type="mongo",
            display_name="Saved Mongo",
            public_data={}
        )
        mongo_record.encrypted_secret_data = encrypt_dict({"uri": "mongodb://localhost:27017"})
        mongo_record.save()

        url = reverse("edit_connection", args=["mongo", 0])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'mongodb://localhost:27017')
        self.assertContains(response, 'title="Show Mongo String"')
        self.assertContains(response, 'value="Saved Mongo"')

    @patch("db_details.views.verify_mongo_connection")
    @patch("db_details.views.test_postgres")
    def test_ajax_test_connection_api(self, mock_test_postgres, mock_verify_mongo):
        # 1. Test postgres failure (make mock raise error)
        mock_test_postgres.side_effect = Exception("Postgres connection timeout")
        url = reverse("test_connection_api", args=["postgresql"])
        data = {
            "display_name": "Ajax Test PG",
            "host": "localhost",
            "port": "5432",
            "dbname": "testdb",
            "username": "testuser",
            "password": "mysecretpassword"
        }
        response = self.client.post(url, data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertFalse(json_data["success"])
        self.assertIn("error", json_data)

        # 2. Test mongo connection success (mock succeeds)
        mock_verify_mongo.side_effect = None
        url = reverse("test_connection_api", args=["mongo"])
        data = {
            "display_name": "",
            "connection": "mongodb://localhost:27017"
        }
        response = self.client.post(url, data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["message"], "Connection test successful")

        # 3. Test mongo connection failure (mock raises connection error)
        mock_verify_mongo.side_effect = Exception("Mongo server selection timeout")
        response = self.client.post(url, data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("Mongo server selection timeout", response.json()["error"])

        # 4. Test mongo connection api failure when empty
        data_empty = {
            "display_name": "",
            "connection": ""
        }
        response = self.client.post(url, data_empty, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("Missing required fields", response.json()["error"])

    def test_cluster_configuration_page(self):
        url = reverse("cluster_configuration")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cluster Configuration")
        self.assertContains(response, 'href="/cluster-configuration/db/mongo/"')
        self.assertContains(response, 'href="/cluster-configuration/db/postgresql/"')

    @patch("db_details.views.check_driver_port_reachability")
    @patch("db_details.views.verify_server_mongod_via_driver")
    def test_cluster_crud_operations(self, mock_ssh_check, mock_port_check):
        mock_ssh_check.return_value = (True, "5.0.0")
        mock_port_check.return_value = (True, "Reachable")

        # 1. Test Add Cluster configuration
        add_url = reverse("add_cluster", args=["mongo"])
        data = {
            "display_name": "My Mongo Cluster",
            "dc_ips": "127.0.0.1, 127.0.0.1",
            "dc_ports": "8000",
            "dc_ha_ips": "127.0.0.1",
            "dc_ha_ports": "8000",
            "dr_ips": "127.0.0.1",
            "dr_ports": "8000",
            "dr_ha_ips": "127.0.0.1",
            "dr_ha_ports": "8000",
            "db_username": "admin",
            "db_name": "admin",
            "db_password": "secretpassword",
            "server_username": "ubuntu",
            "server_password": "sshpassword",
        }
        response = self.client.post(add_url, data)
        self.assertEqual(response.status_code, 302) # Redirect to cluster list

        # 2. Verify it is listed in Cluster list
        list_url = reverse("cluster_list", args=["mongo"])
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Mongo Cluster")

        # 3. Test Edit Cluster configuration
        edit_url = reverse("edit_cluster", args=["mongo", 0])
        edit_get_response = self.client.get(edit_url)
        self.assertEqual(edit_get_response.status_code, 200)
        self.assertContains(edit_get_response, "My Mongo Cluster")
        self.assertContains(edit_get_response, "127.0.0.1, 127.0.0.1")
        self.assertContains(edit_get_response, "secretpassword")
        self.assertContains(edit_get_response, "ubuntu")
        self.assertContains(edit_get_response, "sshpassword")

        # Update IPs
        updated_data = {
            "display_name": "Updated Mongo Cluster",
            "dc_ips": "127.0.0.1, 127.0.0.1",
            "dc_ports": "8000",
            "dc_ha_ips": "127.0.0.1",
            "dc_ha_ports": "8000",
            "dr_ips": "127.0.0.1",
            "dr_ports": "8000",
            "dr_ha_ips": "127.0.0.1",
            "dr_ha_ports": "8000",
            "db_username": "admin",
            "db_name": "admin",
            "db_password": "newsecretpassword",
            "server_username": "ubuntu",
            "server_password": "sshpassword",
        }
        edit_post_response = self.client.post(edit_url, updated_data)
        self.assertEqual(edit_post_response.status_code, 302)

        # Verify updated values
        response = self.client.get(list_url)
        self.assertContains(response, "Updated Mongo Cluster")

        # 4. Test verify API failure (since IP is unreachable)
        verify_fail_data = {
            "display_name": "Updated Mongo Cluster",
            "dc_ips": "192.0.2.1",
            "dc_ports": "9999",
            "dc_ha_ips": "192.0.2.1",
            "dc_ha_ports": "9999",
            "dr_ips": "192.0.2.1",
            "dr_ports": "9999",
            "dr_ha_ips": "192.0.2.1",
            "dr_ha_ports": "9999",
            "db_username": "admin",
            "db_name": "admin",
            "db_password": "newsecretpassword",
            "server_username": "ubuntu",
            "server_password": "sshpassword",
        }
        verify_url = reverse("cluster_verify_api", args=["mongo"])
        verify_response = self.client.post(verify_url, verify_fail_data, content_type="application/json")
        self.assertEqual(verify_response.status_code, 200)
        verify_json = verify_response.json()
        self.assertFalse(verify_json["success"])

        # 4b. Test validation: Providing only DC (now allowed under new rules, should bypass validation error and fail on reachability)
        only_dc_data = {
            "display_name": "DC Only",
            "dc_ips": "192.0.2.1",
            "dc_ports": "9999",
            "dc_ha_ips": "",
            "dc_ha_ports": "",
            "dr_ips": "",
            "dr_ports": "",
            "dr_ha_ips": "",
            "dr_ha_ports": "",
            "db_username": "admin",
            "db_name": "admin",
            "db_password": "pass",
            "server_username": "ubuntu",
            "server_password": "sshpassword",
        }
        verify_response = self.client.post(verify_url, only_dc_data, content_type="application/json")
        self.assertEqual(verify_response.status_code, 200)
        self.assertFalse(verify_response.json()["success"])
        # Should fail on reachability (unreachable), not validation error
        self.assertNotIn("Validation error", verify_response.json().get("error", ""))

        # 4c. Test validation failure: Providing DC and DR_HA, but leaving DR empty (disallowed)
        invalid_setup_data = {
            "display_name": "Invalid Cluster",
            "dc_ips": "192.0.2.1",
            "dc_ports": "9999",
            "dc_ha_ips": "",
            "dc_ha_ports": "",
            "dr_ips": "",
            "dr_ports": "",
            "dr_ha_ips": "192.0.2.1",
            "dr_ha_ports": "9999",
            "db_username": "admin",
            "db_name": "admin",
            "db_password": "pass",
            "server_username": "ubuntu",
            "server_password": "sshpassword",
        }
        verify_response = self.client.post(verify_url, invalid_setup_data, content_type="application/json")
        self.assertEqual(verify_response.status_code, 200)
        self.assertIn("Validation error", verify_response.json()["error"])

        # 4d. Test validation: Providing DC + DR + DR_HA (Combination v: allowed, should bypass validation error and fail on reachability)
        combination_v_data = {
            "display_name": "Comb V Cluster",
            "dc_ips": "192.0.2.1",
            "dc_ports": "9999",
            "dc_ha_ips": "",
            "dc_ha_ports": "",
            "dr_ips": "192.0.2.1",
            "dr_ports": "9999",
            "dr_ha_ips": "192.0.2.1",
            "dr_ha_ports": "9999",
            "db_username": "admin",
            "db_name": "admin",
            "db_password": "pass",
            "server_username": "ubuntu",
            "server_password": "sshpassword",
        }
        verify_response = self.client.post(verify_url, combination_v_data, content_type="application/json")
        self.assertEqual(verify_response.status_code, 200)
        self.assertFalse(verify_response.json()["success"])
        self.assertNotIn("Validation error", verify_response.json().get("error", ""))

        # 5. Test Delete Cluster configuration
        delete_url = reverse("delete_cluster", args=["mongo", 0])
        delete_response = self.client.post(delete_url)
        self.assertEqual(delete_response.status_code, 302)

        # Verify deleted
        response = self.client.get(list_url)
        self.assertNotContains(response, "Updated Mongo Cluster")

    @patch("socket.create_connection")
    @patch("pymongo.MongoClient")
    def test_verify_mongo_connection(self, mock_client, mock_socket):
        from db_details.views import verify_mongo_connection

        # Case 1: Reachable & Connected
        mock_socket.side_effect = None
        mock_client.return_value.server_info.return_value = {}
        verify_mongo_connection("mongodb://localhost:27017") # should pass silently

        # Case 2: Unreachable
        mock_socket.side_effect = Exception("Unreachable")
        with self.assertRaises(ValueError) as ctx:
            verify_mongo_connection("mongodb://localhost:27017")
        self.assertEqual(str(ctx.exception), "server is not reachable kindly check the connectivity")

        # Case 3: Reachable but fails connection (generic error)
        mock_socket.side_effect = None
        mock_client.side_effect = Exception("Generic error")
        with self.assertRaises(ValueError) as ctx:
            verify_mongo_connection("mongodb://localhost:27017")
        self.assertEqual(str(ctx.exception), "kindly check with the URI")

        # Case 4: Reachable but authentication fails
        import pymongo
        mock_client.side_effect = pymongo.errors.OperationFailure("Authentication failed", code=18)
        with self.assertRaises(ValueError) as ctx:
            verify_mongo_connection("mongodb://localhost:27017")
        self.assertEqual(str(ctx.exception), "Authentication failed: kindly check username and password")

    @patch("pymongo.MongoClient")
    def test_verify_server_mongod_via_driver(self, mock_client):
        from db_details.views import verify_server_mongod_via_driver

        # Success case
        mock_client.return_value.server_info.return_value = {"version": "6.0.5"}
        ok, version = verify_server_mongod_via_driver("localhost", 27017, "admin", "admin", "secret")
        self.assertTrue(ok)
        self.assertEqual(version, "6.0.5")

        # Failure case
        mock_client.side_effect = Exception("Connect error")
        ok, error = verify_server_mongod_via_driver("localhost", 27017, "admin", "admin", "secret")
        self.assertFalse(ok)
        self.assertIn("Connection failed", error)

    def test_deploy_cluster_view(self):
        # Setup mock db data
        from db_details.models import ClusterDetails
        ClusterDetails.objects.all().delete()
        ClusterDetails.objects.create(
            db_type="mongo",
            display_name="Test Mongo Deploy",
            dc_ips="127.0.0.1",
            dc_ports="27017",
            db_username="admin",
            db_name="admin",
            db_password="encrypted_pass",
            server_username="ubuntu",
            server_password="sshpassword"
        )
        url = reverse("deploy_cluster", args=["mongo", 0])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        # Check success message
        messages = [str(m) for m in response.wsgi_request._messages]
        self.assertIn("Mongo cluster 'Test Mongo Deploy' deployment initiated successfully!", messages)

    def test_version_parsing_and_matching(self):
        from db_details.views import parse_version
        self.assertEqual(parse_version("8.0.18"), (8, 0, 18))
        self.assertEqual(parse_version("v7.2.1"), (7, 2, 1))
        self.assertEqual(parse_version("unknown"), (0, 0, 0))

    @patch("socket.create_connection")
    @patch("pymongo.MongoClient")
    def test_check_driver_port_reachability(self, mock_client, mock_socket):
        from db_details.views import check_driver_port_reachability

        # Case 1: Reachable via replica set health status query
        mock_client.return_value.admin.command.return_value = {
            "members": [
                {"name": "localhost:27017", "health": 1}
            ]
        }
        ok, msg = check_driver_port_reachability("localhost", 27017, "localhost", 27017, "admin", "admin", "secret")
        self.assertTrue(ok)
        self.assertEqual(msg, "Reachable")

        # Case 2: Reachable via direct socket fallback
        mock_client.side_effect = Exception("No replica set active")
        mock_socket.side_effect = None
        ok, msg = check_driver_port_reachability("localhost", 27017, "localhost", 27018, "admin", "admin", "secret")
        self.assertTrue(ok)
        self.assertEqual(msg, "Reachable")

        # Case 3: Totally unreachable
        mock_socket.side_effect = Exception("Timeout")
        ok, msg = check_driver_port_reachability("localhost", 27017, "localhost", 27019, "admin", "admin", "secret")
        self.assertFalse(ok)
        self.assertIn("Not Connected", msg)
