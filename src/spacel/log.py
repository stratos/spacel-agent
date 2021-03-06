import logging
import os
import watchtower

logger = logging.getLogger('spacel')

DEFAULT_CWL_LEVEL = logging.INFO


def setup_logging(level=logging.DEBUG):  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger('boto3').setLevel(logging.CRITICAL)
    logging.getLogger('botocore').setLevel(logging.CRITICAL)
    logging.getLogger('dbus.proxies').setLevel(logging.CRITICAL)
    logger.setLevel(level)
    return logger


def parse_level(level_param, default_level):
    if not level_param:
        return default_level

    parsed_level = logging.getLevelName(level_param.upper())
    if isinstance(parsed_level, int):
        return parsed_level

    logger.warn('Invalid log level: "%s"', level_param)
    return default_level


def setup_watchtower(clients, meta, manifest):
    deploy_logging = manifest.logging.get('deploy', {})
    log_group = deploy_logging.get('group')
    if not log_group:
        logger.debug('Deployment logging not configured.')
        return
    level = parse_level(deploy_logging.get('level'), DEFAULT_CWL_LEVEL)

    if log_group.startswith('path:'):
        log_group_path = log_group[5:]
        if os.path.exists(log_group_path):
            with open(log_group_path) as log_group_in:
                log_group = log_group_in.read().strip()

    cwl = watchtower.CloudWatchLogHandler(
        log_group=log_group,
        boto3_session=clients,
        use_queues=True,
        send_interval=2,
        create_log_group=False,
        stream_name=meta.instance_id
    )
    cwl.setLevel(level)
    logging.getLogger('spacel').addHandler(cwl)
