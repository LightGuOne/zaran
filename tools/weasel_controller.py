import os
import subprocess
import time
import ctypes
import fnmatch
import ctypes
import winreg
from loguru import logger

# ========== 路径检测相关 ==========
REG_PATHS = {
    'rime_user_dir': (
        r"Software\Rime\Weasel",
        "RimeUserDir",
        winreg.HKEY_CURRENT_USER
    ),
    'weasel_root': (
        r"SOFTWARE\WOW6432Node\Rime\Weasel",
        "WeaselRoot",
        winreg.HKEY_LOCAL_MACHINE
    ),
    'server_exe': (
        r"SOFTWARE\WOW6432Node\Rime\Weasel",
        "ServerExecutable",
        winreg.HKEY_LOCAL_MACHINE
    )
}
def getInstallationInfo(rimePaths):
    """补充nstallation相关信息

    :param rimePaths: 路径字典
    :return: 路径字典
    """
    userFolder = rimePaths.get('rime_user_dir')
    if not userFolder:
        return rimePaths
    yamlPath=os.path.join(userFolder,'installation.yaml')
    if not os.path.exists(yamlPath):
        return rimePaths
    with open(yamlPath, 'r', encoding='utf-8') as inputFile:
        for line in inputFile:
            lineSplit=line.split(':')
            rimePaths[lineSplit[0]]=lineSplit[1].strip()
    return rimePaths

def get_registry_value(key_path, value_name, hive):
    """安全读取注册表值"""
    try:
        with winreg.OpenKey(hive, key_path) as key:
            value, _ = winreg.QueryValueEx(key, value_name)
            return value
    except (FileNotFoundError, PermissionError, OSError):
        return None

def detect_installation_paths():
    """自动检测安装路径"""
    detected = {}
    for key in REG_PATHS:
        path, name, hive = REG_PATHS[key]
        detected[key] = get_registry_value(path, name, hive)

    # 智能路径处理
    if detected['weasel_root'] and detected['server_exe']:
        detected['server_exe'] = os.path.join(detected['weasel_root'], detected['server_exe'])

    # 设置默认值
    defaults = {
        'rime_user_dir': os.path.join(os.environ['APPDATA'], 'Rime'),
        'weasel_root': r"C:\Program Files (x86)\Rime\weasel-0.16.3",
        'server_exe': r"C:\Program Files (x86)\Rime\weasel-0.16.3\WeaselServer.exe"
    }

    for key in detected:
        if not detected[key] or not os.path.exists(detected[key]):
            detected[key] = defaults[key]

    detected=getInstallationInfo(detected)

    return detected

# ========== Run 类 ==========
class Run:
    def __init__(self, paths=None):
        """初始化，可传入paths字典，若不传则自动检测"""
        if paths is None:
            paths = detect_installation_paths()
        self.paths = paths
        self.weasel_server = self.paths['server_exe']
        self.extract_path = self.paths['rime_user_dir']  # Rime用户文件夹路径

    def terminate_processes(self):
        """组合式进程终止策略"""
        if not self.graceful_stop():  # 先尝试优雅停止
            self.hard_stop()          # 失败则强制终止

    def graceful_stop(self):
        """优雅停止服务"""
        try:
            subprocess.run(
                [self.weasel_server, "/q"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            logger.info("服务已优雅退出")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"优雅退出失败: {e}")
            return False
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return False

    def hard_stop(self):
        """强制终止保障"""
        logger.debug("强制终止残留进程")
        for _ in range(3):
            subprocess.run(["taskkill", "/IM", "WeaselServer.exe", "/F"], 
                            shell=True, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/IM", "WeaselDeployer.exe", "/F"], 
                            shell=True, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
        logger.info("进程清理完成")

    def deploy_weasel(self):
        """智能部署引擎"""
        try:
            self.terminate_processes()
            
            # 服务启动重试机制
            for retry in range(3):
                try:
                    logger.debug("启动小狼毫服务")
                    subprocess.Popen(
                        [self.weasel_server],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    time.sleep(2)
                    break
                except Exception as e:
                    if retry == 2:
                        raise
                    logger.warning(f"服务启动失败，重试({retry+1}/3)...")
                    time.sleep(1)
            
            # 部署执行与验证
            logger.debug("执行部署操作")
            deployer = os.path.join(os.path.dirname(self.weasel_server), "WeaselDeployer.exe")
            result = subprocess.run(
                [deployer, "/deploy"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                raise Exception(f"部署失败: {result.stderr.strip()}")
                
            logger.info("部署成功完成")
            return True
        except Exception as e:
            logger.error(f"部署失败: {str(e)}")
            return False

    def sync_user_data(self):
        """执行用户资料同步"""
        try:
            # 获取 WeaselDeployer.exe 的路径
            deployer_dir = os.path.dirname(self.weasel_server)
            deployer_path = os.path.join(deployer_dir, "WeaselDeployer.exe")
            
            if not os.path.exists(deployer_path):
                logger.error(f"未找到部署工具: {deployer_path}")
                return False
            
            logger.info("开始同步用户资料")
            
            # 执行同步命令
            result = subprocess.run(
                [deployer_path, "/sync"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                logger.error(f"同步失败: {result.stderr.strip()}")
                return False
                
            logger.info("用户资料同步成功")
            return True
        except Exception as e:
            logger.error(f"同步过程中出错: {str(e)}")
            return False
    
    def activate_weasel(self, max_wait=10):
        """
        激活小狼毫输入法以确保生成.userdb文件
        :param max_wait: 最大等待时间（秒）
        :return: 是否成功激活
        """
        logger.info("激活小狼毫输入法")
        
        try:
            # 1. 确保服务已启动
            if not self.is_weasel_running():
                self.start_weasel_service()
                
            # 2. 模拟输入法切换（触发初始化）
            self.toggle_input_method()
            
            # 3. 检查.userdb文件生成
            return self.wait_for_userdb(max_wait)
            
        except Exception as e:
            logger.error(f"激活失败: {str(e)}")
            return False
    
    def is_weasel_running(self):
        """检查小狼毫服务是否运行"""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq WeaselServer.exe'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return "WeaselServer.exe" in result.stdout
        except Exception:
            return False
    
    def start_weasel_service(self):
        """启动小狼毫服务"""
        logger.info("启动小狼毫服务...")
        subprocess.Popen(
            [self.weasel_server],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(2)  # 等待服务启动
    
    def toggle_input_method(self):
        """模拟输入法切换以激活.userdb生成"""
        
        # 模拟按键切换输入法
        try:
            # 模拟按下Shift键
            ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # VK_SHIFT
            # 模拟释放Shift键
            ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # KEYEVENTF_KEYUP
            time.sleep(0.5)
        except Exception:
            logger.warning("无法模拟按键，但可能已成功激活")
    
    def wait_for_userdb(self, max_wait=10):
        """等待.userdb文件生成"""
        logger.info("检查.userdb文件生成...")
        start_time = time.time()
        
        # 查找用户目录下的.userdb文件
        userdb_pattern = os.path.join(self.extract_path, "*.userdb")
        
        while time.time() - start_time < max_wait:
            # 检查是否存在.userdb文件
            if any(fnmatch.fnmatch(f, "*.userdb") for f in os.listdir(self.extract_path)):
                logger.success("检测到.userdb文件已生成")
                return True
                
            # 检查是否存在.userdb.old文件（表示已重命名）
            if any(f.endswith(".userdb.old") for f in os.listdir(self.extract_path)):
                logger.success("检测到.userdb更新")
                return True
                
            time.sleep(1)
        
        # 检查是否存在预编译的二进制词典（可能不需要.userdb）
        build_dir = os.path.join(self.extract_path, "build")
        if os.path.exists(build_dir) and os.listdir(build_dir):
            logger.warning("未检测到.userdb文件，但存在编译词典")
            return True
            
        logger.error(f"在{max_wait}秒内未检测到.userdb文件")
        return False