import unittest
from mock import MagicMock, call, patch
from spacel.model import AgentManifest
from spacel.agent.systemd import SystemdUnits

INSTANCE_ID = 'i-123456'
SYSTEMD_SERVICE = 'foo.service'
TIMER_SERVICE = 'bar.service'
TIMER_NAME = 'bar.timer'


class TestSystemdUnits(unittest.TestCase):
    def setUp(self):
        self.unit = MagicMock()
        self.unit.properties.Id = SYSTEMD_SERVICE
        self.timer_service = MagicMock()
        self.timer_service.properties.Id = TIMER_SERVICE
        self.timer_name = MagicMock()
        self.timer_name.properties.Id = TIMER_NAME

        self.manager = MagicMock()
        self.manifest = AgentManifest({
            'systemd': {
                SYSTEMD_SERVICE: '',
                TIMER_SERVICE: '',
                TIMER_NAME: ''
            }
        })

        self.systemd = SystemdUnits(self.manager)

    def test_start_units(self):
        self.systemd._get_units = MagicMock(return_value=[self.unit])

        self.assertEqual(self.systemd.start_units(self.manifest), True)
        self.unit.start.assert_called_with('replace')

    def test_start_units_error(self):
        self.systemd._get_units = MagicMock(return_value=[self.unit])
        self.unit.start.side_effect = Exception()

        self.assertEqual(self.systemd.start_units(self.manifest), False)

    def test_start_units_already_running(self):
        self.systemd._get_units = MagicMock(return_value=[self.unit])
        self.unit.properties.ActiveState = 'active'

        self.assertEqual(self.systemd.start_units(self.manifest), True)
        self.unit.start.assert_not_called()

    def test_start_units_skip_timers(self):
        self.systemd._get_units = MagicMock(return_value=[self.unit,
                                                          self.timer_service,
                                                          self.timer_name])

        self.assertEqual(self.systemd.start_units(self.manifest), True)

        self.timer_service.start.assert_not_called()
        self.timer_name.start.assert_called_with('replace')

    def test_stop_units(self):
        self.systemd._get_units = MagicMock(return_value=[self.unit])
        self.systemd.stop_units(self.manifest)
        self.unit.stop.assert_called_with('replace')

    def test_stop_units_error(self):
        self.systemd._get_units = MagicMock(return_value=[self.unit])
        self.unit.stop.side_effect = Exception()
        self.systemd.stop_units(self.manifest)

    def test_get_units_loaded(self):
        self.manager.list_units.return_value = [self.unit, self.timer_service,
                                                self.timer_name]

        units = [u for u in self.systemd._get_units(self.manifest)]
        self.assertEquals(3, len(units))
        self.assertEquals(self.unit, units[0])
        self.assertEquals(self.timer_service, units[1])
        self.assertEquals(self.timer_name, units[2])

    def test_get_units_load(self):
        self.manager.list_units.return_value = []
        self.manager.load_unit.side_effect = [self.unit, self.timer_service,
                                              self.timer_name]

        units = [u for u in self.systemd._get_units(self.manifest)]
        self.assertEquals([self.unit, self.timer_service, self.timer_name],
                          units)
        self.assertIn(call(SYSTEMD_SERVICE), self.manager.load_unit.mock_calls)
        self.assertIn(call(TIMER_NAME), self.manager.load_unit.mock_calls)
        self.assertIn(call(TIMER_SERVICE), self.manager.load_unit.mock_calls)

    def test_get_units_load_error(self):
        self.manager.list_units.return_value = []
        self.manager.load_unit.side_effect = Exception()

        units = [u for u in self.systemd._get_units(self.manifest)]
        self.assertEquals(0, len(units))

    def test_get_timers(self):
        timers = self.systemd._get_timers(self.manifest)
        self.assertEqual(set(['bar']), timers)

    @patch('spacel.agent.systemd.subprocess')
    def test_log_units(self, mock_subprocess):
        self.systemd.log_units(self.manifest)

        self.assertEquals(3, mock_subprocess.check_output.call_count)
