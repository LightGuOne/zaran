from utils import *
from zrmify import zrmify
import os
from loguru import logger
try:
    from weasel_controller import detect_installation_paths
except ImportError:
    detect_installation_paths = None

## gen_chars.py 内容
def getCharsFile(folder):
    with open(os.path.join(folder,'moran.chars.dict.yaml'), 'w', encoding='utf-8') as outfile:
        print('# 自動生成，請勿編輯。', file=outfile)
        print("# AUTO-GENERATED. DO NOT EDIT.", file=outfile)
        header = open('./data/chars.dict.yaml', 'r', encoding='utf-8').read()
        header = header.replace('YYYYmmdd', get_chars_version())
        print(header, file=outfile)

        for ((char, py), w) in freq_simp_table.items():
            sp = zrmify(py)
            for aux in aux_table[char]:
                print(f'{char}\t{sp};{aux}\t{w}', file=outfile)
    logger.info('生成单字表：moran.chars.dict.yaml')

## gen_zrmdb.py 内容
def getZrmdbFile(folder):
    with open(os.path.join(folder,'zrmdb.txt'), 'w', encoding='utf-8',newline='\n') as outfile:
        for (char, auxes) in aux_table.items():
            print(f'{char}\t{" ".join(auxes)}', file=outfile)
    logger.info('生成zrmdb：zrmdb.txt')




## gen_chaifen_filter.py 内容
def getChaifenFile(folder):
    with open(os.path.join(folder,'zrm_chaifen.dict.yaml'), 'w', encoding='utf-8') as outfile:
        header = open('./data/zrm_chaifen.dict.yaml', 'r', encoding='utf-8').read()
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


# if __name__ == '__main__':
#     folder=os.path.dirname(__file__)
#     userFolder=detect_installation_paths()['rime_user_dir'] # 用户文件夹路径
#     getCharsFile(userFolder)                            # 单字表保存位置
#     getZrmdbFile(os.path.join(userFolder,'lua'))        # zrmdb保存位置
#     getChaifenFile(os.path.join(userFolder,'other_dicts','chaifen'))

if __name__ == '__main__':
    folder = os.path.dirname(__file__)
    # 优先使用环境变量（CI 环境），否则使用本地检测
    userFolder = os.environ.get('OUTPUT_DIR')
    if not userFolder:
        if detect_installation_paths is None:
            raise RuntimeError("未设置 OUTPUT_DIR 且无法导入 weasel_controller")
        userFolder = detect_installation_paths()['rime_user_dir']

    getCharsFile(userFolder)
    getZrmdbFile(os.path.join(userFolder, 'lua'))
    getChaifenFile(os.path.join(userFolder, 'other_dicts', 'chaifen'))