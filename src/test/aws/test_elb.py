from botocore.exceptions import ClientError
from spacel.aws.elb import ElbHealthCheck
from test.aws import MockedClientTest, INSTANCE_ID

ELB_NAME = 'elb-123456'
INSTANCE_IN_SERVICE = {'InstanceStates': [{'State': 'InService'}]}
INSTANCE_NOT_REGISTERED = {'InstanceStates': [{
    'State': 'OutOfService',
    'Description': 'Instance is not currently registered with the LoadBalancer.'
}]}


class TestElbHealthCheck(MockedClientTest):
    def setUp(self):
        super(TestElbHealthCheck, self).setUp()
        self.elb_health = ElbHealthCheck(self.clients, self.meta, 0.000001)

        self.manifest.elb = {'name': ELB_NAME}

    def test_health_no_elb(self):
        self.manifest.elb = None

        health = self.elb_health.health(self.manifest)

        self.assertTrue(health)
        self.elb.describe_instance_health.assert_not_called()

    def test_health_timeout(self):
        self.manifest.elb['timeout'] = 0.01

        health = self.elb_health.health(self.manifest)

        self.assertFalse(health)
        self.assertTrue(self.elb.describe_instance_health.call_count > 1)

    def test_health_healthy(self):
        self.elb.describe_instance_health.return_value = INSTANCE_IN_SERVICE

        health = self.elb_health.health(self.manifest)

        self.assertTrue(health)
        self.elb.describe_instance_health.assert_called_once_with(
            LoadBalancerName=ELB_NAME,
            Instances=[{'InstanceId': INSTANCE_ID}]
        )

    def test_health_retry(self):
        describe_exception = ClientError({'Error': {'Message': 'Kaboom'}},
                                         'DescribeInstanceHealth')
        self.elb.describe_instance_health.side_effect = [
            describe_exception,
            INSTANCE_IN_SERVICE
        ]

        health = self.elb_health.health(self.manifest)
        self.assertTrue(health)

    def test_health_register_instance(self):
        self.elb.describe_instance_health.side_effect = [
            INSTANCE_NOT_REGISTERED,
            INSTANCE_IN_SERVICE]
        register_exception = ClientError({'Error': {'Message': 'Kaboom'}},
                                         'RegisterInstancesWithLoadBalancer')
        self.elb.register_instances_with_load_balancer.side_effect = [
            register_exception,
            {'Instances': [{'InstanceId': INSTANCE_ID}]}]

        health = self.elb_health.health(self.manifest)
        self.assertTrue(health)

        self.elb.register_instances_with_load_balancer.assert_called_once_with(
            LoadBalancerName=ELB_NAME,
            Instances=[{'InstanceId': INSTANCE_ID}]
        )

    def test_health_register_instance_failed(self):
        self.manifest.elb['timeout'] = 0.01
        self.manifest.elb['max_retries'] = 0
        self.elb.describe_instance_health.return_value = INSTANCE_NOT_REGISTERED
        register_exception = ClientError({'Error': {'Message': 'Kaboom'}},
                                         'RegisterInstancesWithLoadBalancer')
        self.elb.register_instances_with_load_balancer.side_effect = \
            register_exception

        health = self.elb_health.health(self.manifest)
        self.assertFalse(health)
