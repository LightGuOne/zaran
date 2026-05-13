from utils import *
from zrmify import zrmify
import os
from loguru import logger
try:
    from weasel_controller import detect_installation_paths
except ImportError:
    detect_installation_paths = None

# 定位到脚本自身所在目录（即 tools/），并确定模板文件夹
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')          # tools/data/

## gen_chars.py 内容
def getCharsFile(folder):
    with open(os.path.join(folder, 'moran.chars.dict.yaml'), 'w', encoding='utf-8') as outfile:
        print('# 自動生成，請勿編輯。', file=outfile)
        print("# AUTO-GENERATED. DO NOT EDIT.", file=outfile)
        # 使用基于脚本位置的绝对路径读取模板
        header = open(os.path.join(DATA_DIR, 'chars.dict.yaml'), 'r', encoding='utf-8').read()
        header = header.replace('YYYYmmdd', get_chars_version())
        print(header, file=outfile)

        for ((char, py), w) in freq_simp_table.items():
            sp = zrmify(py)
            for aux in aux_table[char]:
                print(f'{char}\t{sp};{aux}\t{w}', file=outfile)
    logger.info('生成单字表：moran.chars.dict.yaml')

## gen_zrmdb.py 内容
def getZrmdbFile(folder):
    with open(os.path.join(folder, 'zrmdb.txt'), 'w', encoding='utf-8', newline='\n') as outfile:
        for (char, auxes) in aux_table.items():
            print(f'{char}\t{" ".join(auxes)}', file=outfile)
    logger.info('生成zrmdb：zrmdb.txt')

## gen_chaifen_filter.py 内容
def getChaifenFile(folder):
    with open(os.path.join(folder, 'zrm_chaifen.dict.yaml'), 'w', encoding='utf-8') as outfile:
        # 同样使用绝对路径读取模板
        header = open(os.path.join(DATA_DIR, 'zrm_chaifen.dict.yaml'), 'r', encoding='utf-8').read()
        header = header.replace('YYYYmmdd', get_chars_version())
        print(header, file=outfile)
        for char in all_chars:
            tip = ''
            for aux in aux_table[char]:
                chai = chai_table.get((char, aux), '.')
                if tip == '':
                    tip = f'{aux}{chai}'
            print(f'{char}\t{tip}', file=outfile)
    logger.info('生成拆分表：zrm_chaifen.dict.yaml')

if __name__ == '__main__':
    # 优先使用环境变量 OUTPUT_DIR（CI 环境），否则自动检测小狼毫路径
    userFolder = os.environ.get('OUTPUT_DIR')
    if not userFolder:
        if detect_installation_paths is None:
            raise RuntimeError("未设置 OUTPUT_DIR 且无法导入 weasel_controller")
        userFolder = detect_installation_paths()['rime_user_dir']

    getCharsFile(userFolder)
    getZrmdbFile(os.path.join(userFolder, 'lua'))
    getChaifenFile(os.path.join(userFolder, 'other_dicts', 'chaifen'))