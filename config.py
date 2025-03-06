
import os

project_path = os.path.dirname(os.path.abspath(__file__))

config_sys = {
    'server_name': '昂凯智惠管家运营',
    'server_version': 'v1.0',

    'port': 5000,

    'accounts_info': {'admin': {'name': 'admin', 'password': '1'},'test':{'name':'test','password':'2'}},
    # token密钥
    'secret_key': '465789789',
    'token_expired_time': 86400*100,

    'project_path': project_path,
    
    'log_path': os.path.join(project_path, 'logs'),
    'log_backup_count': 24000,

    'data_path': os.path.join(project_path, 'data'),

    # 数据库参数
    # 'mongodb_hostname': '',
    # 'mongodb_port': '',
    # 'mongodb_dbname': '',
    # 'username': '',
    # 'password': '',
}
