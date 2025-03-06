from flask import Flask, request, send_file, g, jsonify
import traceback
import sys
import os
import time
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
import json
import xml.etree.ElementTree as ET
from config import config_sys
from tools import HourlyLogHandler
from flask_cors import CORS
from threading import Lock

request_id_lock = Lock()

def _print(msg):
    print(msg)
    logger_terminal.info(msg)

app = Flask(__name__)

CORS(app)

# 初始化日志
logger_content = HourlyLogHandler(log_directory=f"{config_sys['log_path']}/api/logger_content/", log_name='logger_content', backupcount=config_sys['log_backup_count'])
logger_performance = HourlyLogHandler(log_directory=f"{config_sys['log_path']}/api/logger_performance/", log_name='logger_performance', backupcount=config_sys['log_backup_count'])
logger_error = HourlyLogHandler(log_directory=f"{config_sys['log_path']}/api/logger_error/", log_name='logger_error', backupcount=config_sys['log_backup_count'])
logger_terminal = HourlyLogHandler(log_directory=f"{config_sys['log_path']}/api/logger_terminal/", log_name='logger_terminal', backupcount=config_sys['log_backup_count'])

# 初始化request_id
if not os.path.exists(f"{config_sys['log_path']}/api/request_id.json"):
    with open(f"{config_sys['log_path']}/api/request_id.json", 'w', encoding='utf-8') as f:
        f.write('{"request_id": 0}')

# 创建token
def create_token(client_name):
    s = Serializer(config_sys['secret_key'])
    token = s.dumps({'client_name': client_name})

    return token

# 验证token
def verify_token(token):
    try:
        s = Serializer(config_sys['secret_key'])
        data = s.loads(token, max_age=config_sys['token_expired_time'])
        return {'status': True, 'data': data}
    except:
        return {'status': False, 'data': ''}


def respond(data_out):

    data_out['request_id'] = g.request_id
    if data_out['code'] == 1000:
        data_out['msg_level'] = 'ok'
    elif data_out['code'] == 1001:
        data_out['msg_level'] = 'error'
    else:
        pass

    try:
        # 输出性能日志
        try:
            request_path = request.path
        except BaseException:
            request_path = '--'
        try:
            request_ip = request.remote_addr
        except BaseException:
            request_ip = '--'
        try:
            request_ip_Forwarded = request.headers['X-Forwarded-For']
        except BaseException:
            request_ip_Forwarded = '--'
        try:
            request_handler_time = (time.time() - g.request_get_time) * 1000  # ms
            _print(f'请求处理耗时:{request_handler_time} ms')
        except BaseException:
            request_handler_time = '--'

        # 输出性能日志
        logger_performance.info({'request_path':request_path, 'request_ip': request_ip, 'request_ip_Forwarded': request_ip_Forwarded, 'request_handler_time': request_handler_time})
        # 打输出业务日志
        logger_content.info({'type': 'request_out', 'request_id': g.request_id,'response': data_out})
    except BaseException:
        pass

    return data_out

# 预处理请求数据
@app.before_request
def before_request():

    try:
        with request_id_lock:
            _print('----------------new_request-------------------')
            # 添加请求id
            with open(f"{config_sys['log_path']}/api/request_id.json", 'r+', encoding='utf-8') as f:
                g.request_id = json.load(f)["request_id"]
                f.seek(0)  # 回到文件开头
                json.dump({"request_id": g.request_id + 1}, f, ensure_ascii=False, indent=4)
                

            g.request_get_time = time.time()

            user_ip = request.remote_addr
            request_path = request.path

            #print(f'request_path:{request_path}')

            if request_path in ['/api/download_images']:
                g.data_in = {}
            else:
                g.data_in = request.get_json(silent=True) if request.is_json else {}

            # 打日志
            msg = {'type': 'request_in', 'request_id': g.request_id, 'user_ip': user_ip, 'url': request.url, 'body': g.data_in}
            logger_content.info(msg)
            _print(f'request_in:{msg}')

            # 检查url是否存在
            _print(request.endpoint)
            if request.endpoint is None:
                logger_error.error({'type': 'request_error', 'request_id': g.request_id, 'traceback': 'url不存在'}) 
                return respond({'code': 1001, 'data': '', 'msg': 'url不存在'})

            # 检查token有效性
            token_free_path = [
                '/api/login'
            ]

            #需要进行token鉴权
            if request_path not in token_free_path:
                # 需要验证权限
                token = request.cookies.get('token')
                _print(f'token:{token}')
                verify_result = verify_token(token)
            
                _print(f'verify_result:{verify_result}')
            
                if not verify_result['status']:
                    logger_error.error({'type': 'request_error', 'request_id': g.request_id, 'traceback': 'token验证失败'}) 
                    return respond({'code': 1002, 'data': '', 'msg': '登录过期,请重新登录!'})
            
                g.token_name = verify_result['data']['client_name']

    except:
        _print(traceback.format_exc())
        logger_error.error({'type': 'request_error', 'request_id': g.request_id, 'traceback': traceback.format_exc()})
        
@app.errorhandler(Exception)
def error_handler(e):

    try:
        _print(traceback.format_exc())
        exc_type, exc_value, exc_traceback = sys.exc_info()
        exc_type = str(exc_type.__name__)
        exc_value = str(exc_value)

        error_abstract_inner = exc_type + ':' + exc_value,
    except:
        logger_error.error({'type': 'request_error', 'request_id': g.request_id, 'traceback': traceback.format_exc()})

        _print(traceback.format_exc())
        error_abstract_inner = ['异常信息获取失败']

    error_abstract_inner2 = error_abstract_inner[0]
    data = {
        "code": 1001,
        "data": '',
        "msg": '接口服务异常||' + error_abstract_inner2 + '||' + '请求id:' + str(g.request_id),
        'msg_level': 'error',
        "traceback": traceback.format_exc()}

    return respond(data)


@app.route('/api/status', methods=['GET'])
def status():
    response = {'code': 1000, 
                'data': {'server_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), 
                         'version': f"{config_sys['server_version']}"}, 
                'msg': '获取服务器时间成功'}
    return respond(response)


@app.route('/api/login', methods=['POST'])
def login():
    data=request.get_json()
    if data is None:
        return respond({'code': 1001, 'data': '', 'msg': '请上传json数据'})

    if 'client_name' not in data or 'password' not in data:
        return respond({'code': 1001, 'data': '', 'msg': '缺少参数'})
    
    client_name=data['client_name']
    password=data['password']
    
    if client_name not in config_sys['accounts_info']:
        return respond({'code': 1001, 'data': '', 'msg': '账户不存在'})

    if password == config_sys['accounts_info'][client_name]['password']:
        token = create_token(client_name=client_name)

        response = {'code': 1000, 'data': {'token': token}, 'msg': f'登陆成功'}

    else:
        response = {'code': 1001, 'data': '', 'msg': '密码错误'}

    return respond(response)


@app.route('/api/get_info', methods=['POST'])
def get_info():  
    file_path=os.path.join(config_sys['data_path'],'home_info.json')
    if not os.path.exists(file_path):
        return respond({'code': 1001,'msg': '首页信息不存在'})
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data=json.load(f)

    return respond({'code': 1000,'msg': '首页信息获取成功', 'data': data})


@app.route('/api/download', methods=['POST'])
def download():
    data = request.get_json()
    if 'type' not in data:
        return respond({'code': 1001,'msg': '请选择文件类型'})
    
    if data['type'] == 'carousel_images':
        download_folder = os.path.join(config_sys['data_path'], 'carousel_images')
    elif data['type'] == 'article_images':
        download_folder = os.path.join(config_sys['data_path'], 'article_images')
    else:
        return respond({'code': 1001,'msg': '下载类型错误'})
    
    url=data['filename']
    filename=os.path.basename(url)
    _print(filename)
    file_path=os.path.join(download_folder,filename)
    if not os.path.exists(file_path):
        return respond({'code': 1001,'msg': '文件不存在'})
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/upload', methods=['POST'])
def upload_images():
    _print(f'request:{request.files}')
    if 'file' not in request.files:
        _print('请上传文件')
        return respond({'code': 1001,'msg': '请上传文件'})
    
    file=request.files['file']
    _print(f'file:{file}')
    
    if not file:
        _print('文件为空')
        return respond({'code': 1001,'msg': '文件提取异常'})
    
    filename = os.path.basename(file.filename)
    _print(f'filename:{filename}')
    
    data=request.form.to_dict()
    _print(f'data:{data}')
    
    if 'type' not in data:
        return respond({'code': 1001,'msg': '请选择图片类型'})
    
    if data['type'] == 'carousel_images':
        upload_folder = os.path.join(config_sys['data_path'], 'carousel_images')
    elif data['type'] == 'article_images':
        upload_folder = os.path.join(config_sys['data_path'], 'article_images')
    else:
        return respond({'code':1001,'msg': '上传类型错误'})
    
    # 检查并创建目标目录
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    filepath = os.path.join(upload_folder,filename)
    file.save(filepath)
    return respond({'code': 1000,'msg': '上传成功', 'filename': filename})


@app.route('/api/save', methods=['POST'])
def save():
    if request.get_json() is None:
        return respond({'code': 1001,'msg': '请上传json数据'})
    
    # 前端传来json数据，将其保存在home_info.json文件中
    data = request.get_json()
    _print(f'data:{data}')

    file_path=os.path.join(config_sys['data_path'],'home_info.json')

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    
    return respond({'code': 1000,'msg': '上传成功'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)







