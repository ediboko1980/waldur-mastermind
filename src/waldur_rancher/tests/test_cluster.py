import json
from unittest import mock

import pkg_resources
from rest_framework import status, test
from rest_framework.response import Response

from waldur_openstack.openstack.tests import factories as openstack_factories
from waldur_openstack.openstack_tenant.models import Flavor
from waldur_openstack.openstack_tenant.tests import (
    factories as openstack_tenant_factories,
)

from .. import models, tasks
from . import factories, fixtures


class ClusterGetTest(test.APITransactionTestCase):
    def setUp(self):
        super(ClusterGetTest, self).setUp()
        self.fixture = fixtures.RancherFixture()
        self.fixture_2 = fixtures.RancherFixture()
        self.url = factories.ClusterFactory.get_list_url()

    def test_get_cluster_list(self):
        self.client.force_authenticate(self.fixture.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list(response.data)), 2)

    def test_user_cannot_get_strangers_clusters(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list(response.data)), 1)


class BaseClusterCreateTest(test.APITransactionTestCase):
    def setUp(self):
        super(BaseClusterCreateTest, self).setUp()
        self.fixture = fixtures.RancherFixture()
        self.url = factories.ClusterFactory.get_list_url()
        openstack_service_settings = openstack_factories.OpenStackServiceSettingsFactory(
            customer=self.fixture.customer
        )
        openstack_service = openstack_factories.OpenStackServiceFactory(
            customer=self.fixture.customer, settings=openstack_service_settings
        )
        openstack_spl = openstack_factories.OpenStackServiceProjectLinkFactory(
            project=self.fixture.project, service=openstack_service
        )
        self.tenant = openstack_factories.TenantFactory(
            service_project_link=openstack_spl
        )

        instance_spl = self.fixture.tenant_spl

        openstack_tenant_factories.FlavorFactory(settings=instance_spl.service.settings)
        image = openstack_tenant_factories.ImageFactory(
            settings=instance_spl.service.settings
        )
        openstack_tenant_factories.SecurityGroupFactory(
            name='default', settings=instance_spl.service.settings
        )
        self.fixture.settings.options['base_image_name'] = image.name
        self.fixture.settings.save()

        network = openstack_tenant_factories.NetworkFactory(
            settings=instance_spl.service.settings
        )
        self.subnet = openstack_tenant_factories.SubNetFactory(
            network=network, settings=instance_spl.service.settings
        )
        self.flavor = Flavor.objects.get(settings=instance_spl.service.settings)
        self.flavor.ram = 1024 * 8
        self.flavor.cores = 2
        self.flavor.save()
        self.fixture.settings.options['base_subnet_name'] = self.subnet.name
        self.fixture.settings.save()

    def _create_request_(self, name, disk=1024, memory=1, cpu=2, add_payload=None):
        add_payload = add_payload or {}
        payload = {
            'name': name,
            'service_project_link': factories.RancherServiceProjectLinkFactory.get_url(
                self.fixture.spl
            ),
            'tenant_settings': openstack_tenant_factories.OpenStackTenantServiceSettingsFactory.get_url(
                self.fixture.tenant_spl.service.settings
            ),
            'nodes': [
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': disk,
                    'memory': memory,
                    'cpu': cpu,
                    'roles': ['worker'],
                },
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': disk,
                    'memory': memory,
                    'cpu': cpu,
                    'roles': ['controlplane', 'worker'],
                },
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': disk,
                    'memory': memory,
                    'cpu': cpu,
                    'roles': ['controlplane', 'etcd'],
                },
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': disk,
                    'memory': memory,
                    'cpu': cpu,
                    'roles': ['worker'],
                },
            ],
        }
        payload.update(add_payload)
        return self.client.post(self.url, payload)


class ClusterCreateTest(BaseClusterCreateTest):
    @mock.patch('waldur_rancher.executors.core_tasks')
    def test_create_cluster(self, mock_core_tasks):
        self.client.force_authenticate(self.fixture.owner)
        response = self._create_request_('new-cluster')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(models.Cluster.objects.filter(name='new-cluster').exists())
        cluster = models.Cluster.objects.get(name='new-cluster')
        mock_core_tasks.BackendMethodTask.return_value.si.assert_called_once_with(
            'waldur_rancher.cluster:%s' % cluster.id,
            'create_cluster',
            state_transition='begin_creating',
        )

    @mock.patch('waldur_rancher.executors.core_tasks')
    def test_use_data_volumes(self, mock_core_tasks):
        self.client.force_authenticate(self.fixture.owner)
        volume_type = openstack_tenant_factories.VolumeTypeFactory(
            settings=self.fixture.tenant_spl.service.settings
        )
        payload = {
            'nodes': [
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': 1024,
                    'memory': 1,
                    'cpu': 1,
                    'roles': ['controlplane', 'etcd', 'worker'],
                    'data_volumes': [
                        {
                            'size': 12 * 1024,
                            'volume_type': openstack_tenant_factories.VolumeTypeFactory.get_url(
                                volume_type
                            ),
                            'mount_point': '/var/lib/etcd',
                        }
                    ],
                }
            ]
        }
        response = self._create_request_('new-cluster', add_payload=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(models.Cluster.objects.filter(name='new-cluster').exists())
        cluster = models.Cluster.objects.get(name='new-cluster')
        self.assertEqual(len(cluster.node_set.first().initial_data['data_volumes']), 1)

    def test_node_name_uniqueness(self):
        self.client.force_authenticate(self.fixture.owner)
        payload = {
            'nodes': [
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': 1024,
                    'memory': 1,
                    'cpu': 1,
                    'roles': ['controlplane', 'etcd', 'worker'],
                },
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': 1024,
                    'memory': 1,
                    'cpu': 1,
                    'roles': ['worker'],
                },
            ]
        }
        response = self._create_request_('new-cluster', add_payload=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(models.Cluster.objects.filter(name='new-cluster').exists())
        cluster = models.Cluster.objects.get(name='new-cluster')
        self.assertNotEquals(
            cluster.node_set.all()[0].name, cluster.node_set.all()[1].name
        )

    def test_validate_etcd_node_count(self):
        self.client.force_authenticate(self.fixture.owner)
        payload = {
            'nodes': [
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': 1024,
                    'memory': 1,
                    'cpu': 1,
                    'roles': ['controlplane', 'etcd', 'worker'],
                },
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': 1024,
                    'memory': 1,
                    'cpu': 1,
                    'roles': ['controlplane', 'etcd', 'worker'],
                },
            ]
        }
        response = self._create_request_('new-cluster', add_payload=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            'Total count of etcd nodes must be 1, 3 or 5.' in response.data['nodes'][0]
        )

    def test_validate_worker_node_count(self):
        self.client.force_authenticate(self.fixture.owner)
        payload = {
            'nodes': [
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': 1024,
                    'memory': 1,
                    'cpu': 1,
                    'roles': ['controlplane', 'etcd',],
                },
            ]
        }
        response = self._create_request_('new-cluster', add_payload=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            'Count of workers roles must be min 1.' in response.data['nodes'][0]
        )

    def test_validate_controlplane_node_count(self):
        self.client.force_authenticate(self.fixture.owner)
        payload = {
            'nodes': [
                {
                    'subnet': openstack_tenant_factories.SubNetFactory.get_url(
                        self.subnet
                    ),
                    'system_volume_size': 1024,
                    'memory': 1,
                    'cpu': 1,
                    'roles': ['etcd', 'worker'],
                },
            ]
        }
        response = self._create_request_('new-cluster', add_payload=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            'Count of controlplane nodes must be min 1.' in response.data['nodes'][0]
        )

    def test_validate_name_uniqueness(self):
        self.client.force_authenticate(self.fixture.owner)
        self._create_request_('new-cluster')
        response = self._create_request_('new-cluster')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_name(self):
        self.client.force_authenticate(self.fixture.owner)
        response = self._create_request_('new_cluster')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ClusterUpdateTest(test.APITransactionTestCase):
    def setUp(self):
        super(ClusterUpdateTest, self).setUp()
        self.fixture = fixtures.RancherFixture()
        self.cluster_name = self.fixture.cluster.name
        self.url = factories.ClusterFactory.get_url(self.fixture.cluster)

    @mock.patch('waldur_rancher.executors.core_tasks')
    def test_send_backend_request_if_update_cluster_name(self, mock_core_tasks):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.patch(self.url, {'name': 'new-name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_core_tasks.BackendMethodTask.return_value.si.assert_called_once_with(
            'waldur_rancher.cluster:%s' % self.fixture.cluster.id,
            'update_cluster',
            state_transition='begin_updating',
        )

    @mock.patch('waldur_rancher.executors.core_tasks')
    def test_not_send_backend_request_if_update_cluster_description(
        self, mock_core_tasks
    ):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.patch(self.url, {'description': 'description'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_core_tasks.StateTransitionTask.return_value.si.assert_called_once_with(
            'waldur_rancher.cluster:%s' % self.fixture.cluster.id,
            state_transition='begin_updating',
        )


class ClusterDeleteTest(test.APITransactionTestCase):
    def setUp(self):
        super(ClusterDeleteTest, self).setUp()
        self.fixture = fixtures.RancherFixture()
        self.cluster_name = self.fixture.cluster.name
        self.url = factories.ClusterFactory.get_url(self.fixture.cluster)
        self.fixture.node.instance.runtime_state = (
            self.fixture.node.instance.RuntimeStates.SHUTOFF
        )
        self.fixture.node.instance.save()

    @mock.patch('waldur_rancher.executors.core_tasks')
    def test_delete_cluster_if_related_nodes_are_not_exist(self, mock_core_tasks):
        self.fixture.node.delete()
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_core_tasks.BackendMethodTask.return_value.si.assert_called_once_with(
            'waldur_rancher.cluster:%s' % self.fixture.cluster.id,
            'delete_cluster',
            state_transition='begin_deleting',
        )

    def test_not_delete_cluster_if_state_is_not_ok(self):
        self.client.force_authenticate(self.fixture.owner)
        self.fixture.cluster.state = models.Cluster.States.CREATION_SCHEDULED
        self.fixture.cluster.save()
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    @mock.patch('waldur_rancher.executors.chain')
    @mock.patch('waldur_rancher.executors.tasks')
    def test_on_cluster_deletion_node_deletion_is_requested(
        self, mock_tasks, mock_chain
    ):
        self.client.force_authenticate(self.fixture.owner)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_tasks.DeleteNodeTask.return_value.si.assert_called_once_with(
            'waldur_rancher.node:%s' % self.fixture.node.id,
            user_id=self.fixture.owner.id,
        )

    @mock.patch('waldur_rancher.tasks.common_utils.delete_request')
    def test_on_node_deletion_instance_deletion_is_requested(self, mock_delete_request):
        mock_delete_request.return_value = Response(status=status.HTTP_202_ACCEPTED)
        tasks.DeleteNodeTask().execute(self.fixture.node, user_id=self.fixture.owner.id)
        self.assertEqual(mock_delete_request.call_count, 1)
        self.assertEqual(mock_delete_request.call_args[0][1], self.fixture.owner)
        self.assertEqual(
            mock_delete_request.call_args[1],
            {
                'uuid': self.fixture.node.instance.uuid.hex,
                'query_params': {'delete_volumes': True},
            },
        )

    @mock.patch('waldur_rancher.backend.RancherBackend.client')
    def test_if_instance_has_been_deleted_node_and_cluster_are_deleted(
        self, mock_client
    ):
        self.fixture.cluster.state = models.Node.States.DELETING
        self.fixture.cluster.save()
        self.fixture.node.backend_id = 'backend_id'
        self.fixture.node.save()
        self.fixture.instance.delete()
        self.assertRaises(
            models.Cluster.DoesNotExist, self.fixture.cluster.refresh_from_db
        )
        self.assertRaises(models.Node.DoesNotExist, self.fixture.node.refresh_from_db)
        mock_client.delete_cluster.assert_called_once_with(
            self.fixture.cluster.backend_id
        )
        mock_client.delete_node.assert_called_once_with(self.fixture.node.backend_id)


class BaseProjectImportTest(test.APITransactionTestCase):
    def _generate_backend_clusters(self):
        backend_cluster = json.loads(
            pkg_resources.resource_stream(__name__, 'backend_cluster.json')
            .read()
            .decode()
        )
        return [backend_cluster]


class ClusterImportableResourcesTest(BaseProjectImportTest):
    def setUp(self):
        super(ClusterImportableResourcesTest, self).setUp()
        self.url = factories.ClusterFactory.get_list_url('importable_resources')
        self.fixture = fixtures.RancherFixture()
        self.client.force_authenticate(self.fixture.owner)

    @mock.patch('waldur_rancher.backend.RancherBackend.get_clusters_for_import')
    def test_importable_clusters_are_returned(self, get_projects_mock):
        backend_clusters = self._generate_backend_clusters()
        get_projects_mock.return_value = backend_clusters
        data = {
            'service_project_link': factories.RancherServiceProjectLinkFactory.get_url(
                self.fixture.spl
            )
        }

        response = self.client.get(self.url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), len(backend_clusters))
        returned_backend_ids = [item['backend_id'] for item in response.data]
        expected_backend_ids = [item['id'] for item in backend_clusters]
        self.assertEqual(sorted(returned_backend_ids), sorted(expected_backend_ids))
        self.assertEqual(get_projects_mock.call_count, 1)


class ClusterImportResourceTest(BaseProjectImportTest):
    def setUp(self):
        super(ClusterImportResourceTest, self).setUp()
        self.url = factories.ClusterFactory.get_list_url('import_resource')
        self.fixture = fixtures.RancherFixture()
        self.client.force_authenticate(self.fixture.owner)

        self.patcher_import = mock.patch(
            'waldur_rancher.backend.RancherBackend.import_cluster'
        )
        self.mock_import = self.patcher_import.start()
        self.mock_import.return_value = self._generate_backend_clusters()[0]

    def tearDown(self):
        mock.patch.stopall()

    def test_backend_cluster_is_imported(self):
        backend_id = 'backend_id'

        payload = {
            'backend_id': backend_id,
            'service_project_link': factories.RancherServiceProjectLinkFactory.get_url(
                self.fixture.spl
            ),
        }

        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_backend_cluster_cannot_be_imported_if_it_is_registered_in_waldur(self):
        cluster = factories.ClusterFactory(
            settings=self.fixture.settings, service_project_link=self.fixture.spl
        )

        payload = {
            'backend_id': cluster.backend_id,
            'service_project_link': factories.RancherServiceProjectLinkFactory.get_url(
                self.fixture.spl
            ),
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
